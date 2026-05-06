import type { Transaction } from '../types/transaction'
import type { Dividend } from '../types/dividend'

interface Lot {
  quantity: number
  costPerShare: number
}

export interface Position {
  ticker: string
  stockName: string | null
  currency: string
  sharesHeld: number
  avgCostPerShare: number
  currentPrice: number | null
  /** 目前總市值（= totalCost + unrealizedPnl），null 表示無股價 */
  positionValue: number | null
  unrealizedPnl: number | null
  unrealizedPnlPct: number | null
  realizedGains: number
  cashDividends: number
}

export interface PortfolioSummary {
  positions: Position[]
  /** 以 TWD 計價的總成本（USD 持倉已換算） */
  totalCost: number
  /** 以 TWD 計價的總市值；若任一持倉缺少股價則為 null */
  totalValue: number | null
  /** 以 TWD 計價的總未實現損益 */
  totalUnrealizedPnl: number
  /** 以 TWD 計價的總已實現損益 */
  totalRealizedGains: number
  /** 以 TWD 計價的總現金股利 */
  totalCashDividends: number
  /** 換算時使用的 USD→TWD 匯率（null 表示匯率尚未取得，合計數字含混合幣別） */
  usdToTwd: number | null
}

// Unified event for sorting by date
type Event =
  | { kind: 'BUY' | 'SELL'; date: string; ticker: string; currency: string; stockName: string | null; quantity: number; price: number; fee: number }
  | { kind: 'STOCK' | 'DRIP'; date: string; ticker: string; currency: string; stockName: string | null; sharesReceived: number; amount: number }
  | { kind: 'CASH'; date: string; ticker: string; currency: string; stockName: string | null; amount: number }

function toEvents(transactions: Transaction[], dividends: Dividend[]): Event[] {
  const events: Event[] = []

  for (const tx of transactions) {
    events.push({
      kind: tx.transaction_type,
      date: tx.transaction_date,
      ticker: tx.ticker,
      currency: '',  // filled from stock info in prices, not needed for FIFO math
      stockName: tx.stock_name,
      quantity: parseFloat(tx.quantity),
      price: parseFloat(tx.price),
      fee: parseFloat(tx.fee),
    })
  }

  for (const div of dividends) {
    if (div.dividend_type === 'CASH') {
      events.push({
        kind: 'CASH',
        date: div.ex_dividend_date,
        ticker: div.ticker,
        currency: div.currency,
        stockName: div.stock_name,
        amount: parseFloat(div.amount),
      })
    } else {
      events.push({
        kind: div.dividend_type as 'STOCK' | 'DRIP',
        date: div.ex_dividend_date,
        ticker: div.ticker,
        currency: div.currency,
        stockName: div.stock_name,
        sharesReceived: parseFloat(div.shares_received ?? '0'),
        amount: parseFloat(div.amount),
      })
    }
  }

  // Sort by date ascending (FIFO requires chronological order)
  events.sort((a, b) => a.date.localeCompare(b.date))
  return events
}

export function calculatePortfolio(
  transactions: Transaction[],
  dividends: Dividend[],
  prices: Record<string, { last_price: number | null; currency: string; name?: string | null }>,
  usdToTwd: number | null = null,
): PortfolioSummary {
  const events = toEvents(transactions, dividends)

  // Per-ticker state
  const lots: Record<string, Lot[]> = {}
  const realizedGains: Record<string, number> = {}
  const cashDividends: Record<string, number> = {}
  const currencies: Record<string, string> = {}
  const stockNames: Record<string, string | null> = {}

  for (const evt of events) {
    const { ticker } = evt
    if (!lots[ticker]) lots[ticker] = []
    if (!realizedGains[ticker]) realizedGains[ticker] = 0
    if (!cashDividends[ticker]) cashDividends[ticker] = 0
    if (evt.stockName) stockNames[ticker] = evt.stockName

    if (evt.kind === 'BUY') {
      const costPerShare = (evt.price * evt.quantity + evt.fee) / evt.quantity
      lots[ticker].push({ quantity: evt.quantity, costPerShare })
    } else if (evt.kind === 'SELL') {
      let remaining = evt.quantity
      const sellPrice = evt.price
      // Deduct fee from sell proceeds for realized gain calc
      const feePerShare = evt.fee / evt.quantity

      while (remaining > 0 && lots[ticker].length > 0) {
        const lot = lots[ticker][0]
        const consumed = Math.min(lot.quantity, remaining)
        realizedGains[ticker] += (sellPrice - feePerShare - lot.costPerShare) * consumed
        lot.quantity -= consumed
        remaining -= consumed
        if (lot.quantity < 1e-9) lots[ticker].shift()
      }
    } else if (evt.kind === 'STOCK') {
      lots[ticker].push({ quantity: evt.sharesReceived, costPerShare: 0 })
    } else if (evt.kind === 'DRIP') {
      const costPerShare = evt.sharesReceived > 0 ? evt.amount / evt.sharesReceived : 0
      lots[ticker].push({ quantity: evt.sharesReceived, costPerShare })
    } else if (evt.kind === 'CASH') {
      cashDividends[ticker] += evt.amount
      currencies[ticker] = evt.currency
    }
  }

  // Build positions (only tickers with remaining shares)
  const positions: Position[] = []
  const allTickers = new Set([
    ...Object.keys(lots),
    ...Object.keys(realizedGains),
    ...Object.keys(cashDividends),
  ])

  for (const ticker of allTickers) {
    const tickerLots = lots[ticker] ?? []
    const sharesHeld = tickerLots.reduce((s, l) => s + l.quantity, 0)

    if (sharesHeld < 1e-9 && (realizedGains[ticker] ?? 0) === 0 && (cashDividends[ticker] ?? 0) === 0) {
      continue
    }

    const totalCost = tickerLots.reduce((s, l) => s + l.costPerShare * l.quantity, 0)
    const avgCostPerShare = sharesHeld > 1e-9 ? totalCost / sharesHeld : 0

    const priceInfo = prices[ticker]
    const currentPrice = priceInfo?.last_price ?? null
    const currency = priceInfo?.currency ?? currencies[ticker] ?? ''

    let unrealizedPnl: number | null = null
    let unrealizedPnlPct: number | null = null
    let positionValue: number | null = null
    if (currentPrice !== null && sharesHeld > 1e-9) {
      positionValue = currentPrice * sharesHeld
      unrealizedPnl = positionValue - totalCost
      unrealizedPnlPct = avgCostPerShare > 0 ? (unrealizedPnl / (avgCostPerShare * sharesHeld)) * 100 : null
    }

    positions.push({
      ticker,
      stockName: stockNames[ticker] ?? priceInfo?.name ?? null,
      currency,
      sharesHeld,
      avgCostPerShare,
      currentPrice,
      positionValue,
      unrealizedPnl,
      unrealizedPnlPct,
      realizedGains: realizedGains[ticker] ?? 0,
      cashDividends: cashDividends[ticker] ?? 0,
    })
  }

  // Sort: currently held (sharesHeld > 0) first, then by ticker
  positions.sort((a, b) => {
    if (a.sharesHeld > 0 && b.sharesHeld <= 0) return -1
    if (a.sharesHeld <= 0 && b.sharesHeld > 0) return 1
    return a.ticker.localeCompare(b.ticker)
  })

  // Convert an amount to TWD. If usdToTwd is unavailable, return as-is (mixed-currency fallback).
  const toTwd = (amount: number, currency: string): number => {
    if (currency === 'TWD') return amount
    if (currency === 'USD' && usdToTwd !== null) return amount * usdToTwd
    return amount  // unknown currency or missing rate — pass through unchanged
  }

  // Only count currently held positions for cost / value
  const heldPositions = positions.filter(p => p.sharesHeld > 1e-9)
  const totalCost = heldPositions.reduce(
    (s, p) => s + toTwd(p.avgCostPerShare * p.sharesHeld, p.currency), 0
  )
  const hasNullPrice = heldPositions.some(p => p.currentPrice === null)
  const totalValue = hasNullPrice
    ? null
    : heldPositions.reduce((s, p) => s + toTwd(p.currentPrice! * p.sharesHeld, p.currency), 0)

  const totalUnrealizedPnl = positions.reduce(
    (s, p) => s + toTwd(p.unrealizedPnl ?? 0, p.currency), 0
  )
  const totalRealizedGains = positions.reduce(
    (s, p) => s + toTwd(p.realizedGains, p.currency), 0
  )
  const totalCashDividends = positions.reduce(
    (s, p) => s + toTwd(p.cashDividends, p.currency), 0
  )

  return { positions, totalCost, totalValue, totalUnrealizedPnl, totalRealizedGains, totalCashDividends, usdToTwd }
}
