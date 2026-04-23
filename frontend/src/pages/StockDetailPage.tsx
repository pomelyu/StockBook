import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { usePortfolio } from '../hooks/usePortfolio'
import { useStockHistory } from '../hooks/useStockHistory'
import EditRecordModal from '../components/portfolio/EditRecordModal'
import type { HistoryEntry } from '../hooks/useStockHistory'

function fmtNumber(n: number, decimals = 0): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

const KIND_LABEL: Record<HistoryEntry['kind'], string> = {
  BUY: '買',
  SELL: '賣',
  DIVIDEND: '股利',
}
const KIND_COLOR: Record<HistoryEntry['kind'], string> = {
  BUY: 'text-blue-600 bg-blue-50',
  SELL: 'text-green-700 bg-green-50',
  DIVIDEND: 'text-green-700 bg-green-50',
}
const AMOUNT_COLOR: Record<HistoryEntry['kind'], string> = {
  BUY: 'text-red-600',
  SELL: 'text-green-600',
  DIVIDEND: 'text-green-600',
}

function HistoryRow({ entry, isTW, onClick }: { entry: HistoryEntry; isTW: boolean; onClick: () => void }) {
  const isBuySell = entry.kind !== 'DIVIDEND'
  const shareDecimals = isTW ? 0 : 3
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-4 py-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 active:bg-gray-100 transition-colors"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-gray-400 shrink-0">{entry.date}</span>
          <span className={`rounded px-1.5 py-0.5 text-xs font-medium shrink-0 ${KIND_COLOR[entry.kind]}`}>
            {KIND_LABEL[entry.kind]}
          </span>
          {isBuySell && entry.shares !== null && (
            <span className="text-sm text-gray-700 truncate">
              {fmtNumber(entry.shares, shareDecimals)}股
              {entry.price !== null && (
                <span className="text-gray-400"> @{fmtNumber(entry.price, 2)}</span>
              )}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <span className="text-xs text-gray-400">{entry.kind === 'BUY' ? '支出' : '收入'}</span>
          <span className={`text-sm font-medium ${AMOUNT_COLOR[entry.kind]}`}>
            {fmtNumber(entry.amount, 2)}
          </span>
          <span className="text-gray-300 text-xs ml-1">›</span>
        </div>
      </div>
      {entry.note && (
        <p className="mt-1 text-xs text-gray-400 text-left">{entry.note}</p>
      )}
    </button>
  )
}

export default function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>()
  const navigate = useNavigate()
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio()
  const { entries, isLoading: historyLoading } = useStockHistory(ticker ?? '')
  const [editingEntry, setEditingEntry] = useState<HistoryEntry | null>(null)

  const position = portfolio?.positions.find(p => p.ticker === ticker)

  function currentPosition(t: string): number {
    return portfolio?.positions.find(p => p.ticker === t)?.sharesHeld ?? 0
  }

  // Loading state
  if (portfolioLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  // Ticker not in portfolio
  if (!position) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8 text-center">
        <p className="text-gray-500">找不到此股票的持倉資料</p>
        <button onClick={() => navigate('/')} className="mt-3 text-sm text-blue-600 hover:underline">
          ← 返回
        </button>
      </div>
    )
  }

  const isTW = ticker?.endsWith('.TW') ?? false
  const displayTicker = isTW ? ticker!.replace('.TW', '') : ticker!
  const totalCost = position.sharesHeld * position.avgCostPerShare
  const totalReceived = position.realizedGains + position.cashDividends

  const priceChange = position.unrealizedPnlPct
  const priceUp = priceChange !== null && priceChange >= 0

  return (
    <div className="mx-auto max-w-2xl pb-24 lg:pb-8">
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <button
          onClick={() => navigate('/')}
          className="mb-3 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          ← 返回
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {position.stockName ?? displayTicker}
            </h1>
            <span className="text-sm text-gray-400">{displayTicker}</span>
          </div>
          <div className="text-right">
            <div className="text-xl font-bold text-gray-900">
              {position.currentPrice !== null ? fmtNumber(position.currentPrice, 2) : '—'}
            </div>
            {priceChange !== null && (
              <div className={`text-sm font-medium ${priceUp ? 'text-green-600' : 'text-red-600'}`}>
                {priceUp ? '▲' : '▼'} {Math.abs(priceChange).toFixed(2)}%
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary grid */}
      <div className="mx-4 mb-3 grid grid-cols-2 rounded-xl border border-gray-200 bg-white overflow-hidden">
        <div className="px-4 py-3 border-r border-b border-gray-100">
          <div className="text-xs text-gray-400 mb-0.5">買均價</div>
          <div className="text-sm font-medium text-gray-900">{fmtNumber(position.avgCostPerShare, 2)}</div>
        </div>
        <div className="px-4 py-3 border-b border-gray-100">
          <div className="text-xs text-gray-400 mb-0.5">支出</div>
          <div className="text-sm font-medium text-gray-900">{fmtNumber(totalCost, 2)}</div>
        </div>
        <div className="px-4 py-3 border-r border-gray-100">
          <div className="text-xs text-gray-400 mb-0.5">股息</div>
          <div className="text-sm font-medium text-green-600">{fmtNumber(position.cashDividends, 2)}</div>
        </div>
        <div className="px-4 py-3">
          <div className="text-xs text-gray-400 mb-0.5">實收</div>
          <div className={`text-sm font-medium ${totalReceived >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {fmtNumber(totalReceived, 2)}
          </div>
        </div>
      </div>


      {/* History list */}
      <div className="mx-4 rounded-xl border border-gray-200 bg-white overflow-hidden">
        {historyLoading ? (
          <div className="py-12 text-center text-gray-400 text-sm">載入中…</div>
        ) : entries.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">尚無交易紀錄</div>
        ) : (
          entries.map((entry) => (
            <HistoryRow
              key={entry.id}
              entry={entry}
              isTW={isTW}
              onClick={() => setEditingEntry(entry)}
            />
          ))
        )}
      </div>

      {/* Edit modal */}
      {editingEntry && (
        <EditRecordModal
          entry={editingEntry}
          currentPosition={currentPosition}
          onClose={() => setEditingEntry(null)}
        />
      )}
    </div>
  )
}
