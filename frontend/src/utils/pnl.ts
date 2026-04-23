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
  unrealizedPnl: number | null
  unrealizedPnlPct: number | null
  realizedGains: number
  cashDividends: number
}

export interface PortfolioSummary {
  positions: Position[]
  totalUnrealizedPnl: number
  totalRealizedGains: number
  totalCashDividends: number
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
  prices: Record<string, { last_price: number | null; currency: string; name?: string | null }>
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
    if (currentPrice !== null && sharesHeld > 1e-9) {
      unrealizedPnl = (currentPrice - avgCostPerShare) * sharesHeld
      unrealizedPnlPct = avgCostPerShare > 0 ? (unrealizedPnl / (avgCostPerShare * sharesHeld)) * 100 : null
    }

    positions.push({
      ticker,
      stockName: stockNames[ticker] ?? priceInfo?.name ?? null,
      currency,
      sharesHeld,
      avgCostPerShare,
      currentPrice,
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

  const totalUnrealizedPnl = positions.reduce((s, p) => s + (p.unrealizedPnl ?? 0), 0)
  const totalRealizedGains = positions.reduce((s, p) => s + p.realizedGains, 0)
  const totalCashDividends = positions.reduce((s, p) => s + p.cashDividends, 0)

  return { positions, totalUnrealizedPnl, totalRealizedGains, totalCashDividends }
}
