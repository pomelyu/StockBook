import { useNavigate } from 'react-router-dom'
import { usePortfolio } from '../hooks/usePortfolio'

function fmtNumber(n: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

function PnlBadge({ value }: { value: number }) {
  const positive = value >= 0
  return (
    <span className={`text-sm font-medium ${positive ? 'text-green-600' : 'text-red-600'}`}>
      {positive ? '+' : ''}{fmtNumber(value)}
    </span>
  )
}

function ClosedRow({
  ticker,
  stockName,
  realizedGains,
  cashDividends,
  isTW,
  onSelect,
}: {
  ticker: string
  stockName: string | null
  realizedGains: number
  cashDividends: number
  isTW: boolean
  onSelect: () => void
}) {
  const totalPnl = realizedGains + cashDividends
  const displayTicker = isTW ? ticker.replace(/\.TWO?$/, '') : ticker

  return (
    <>
      {/* Desktop row */}
      <tr
        onClick={onSelect}
        className="hidden sm:table-row border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
      >
        <td className="px-4 py-3">
          <div className="font-medium text-gray-900 text-sm">{displayTicker}</div>
          {stockName && <div className="text-xs text-gray-500 truncate max-w-[160px]">{stockName}</div>}
        </td>
        <td className="px-4 py-3 text-right">
          <PnlBadge value={realizedGains} />
        </td>
        <td className="px-4 py-3 text-right text-sm font-medium text-green-600">
          {cashDividends > 0 ? `+${fmtNumber(cashDividends)}` : '—'}
        </td>
        <td className="px-4 py-3 text-right">
          <PnlBadge value={totalPnl} />
        </td>
      </tr>

      {/* Mobile card */}
      <div
        onClick={onSelect}
        className="sm:hidden border border-gray-200 rounded-xl p-4 cursor-pointer active:bg-gray-50"
      >
        <div className="flex items-start justify-between mb-2">
          <div>
            <div className="font-medium text-gray-900">{displayTicker}</div>
            {stockName && <div className="text-xs text-gray-500">{stockName}</div>}
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-400 mb-0.5">總損益</div>
            <PnlBadge value={totalPnl} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-gray-100">
          <div>
            <div className="text-gray-400">已實現損益</div>
            <PnlBadge value={realizedGains} />
          </div>
          <div>
            <div className="text-gray-400">現金股息</div>
            <span className="text-sm font-medium text-green-600">
              {cashDividends > 0 ? `+${fmtNumber(cashDividends)}` : '—'}
            </span>
          </div>
        </div>
      </div>
    </>
  )
}

function MarketSection({
  title,
  rows,
  onSelect,
}: {
  title: string
  rows: Array<{ ticker: string; stockName: string | null; realizedGains: number; cashDividends: number }>
  onSelect: (ticker: string) => void
}) {
  const isTW = title === 'TW'
  return (
    <div className="mb-6">
      <h2 className="mb-2 text-sm font-semibold text-gray-500 uppercase tracking-wide">{title}</h2>
      {/* Desktop table */}
      <div className="hidden sm:block rounded-xl border border-gray-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 text-left">股票</th>
              <th className="px-4 py-3 text-right">已實現損益</th>
              <th className="px-4 py-3 text-right">現金股息</th>
              <th className="px-4 py-3 text-right">總損益</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <ClosedRow key={r.ticker} {...r} isTW={isTW} onSelect={() => onSelect(r.ticker)} />
            ))}
          </tbody>
        </table>
      </div>
      {/* Mobile card list */}
      <div className="sm:hidden space-y-3">
        {rows.map((r) => (
          <ClosedRow key={r.ticker} {...r} isTW={isTW} onSelect={() => onSelect(r.ticker)} />
        ))}
      </div>
    </div>
  )
}

export default function ClosedPositionsPage() {
  const navigate = useNavigate()
  const { data, isLoading, isError } = usePortfolio()

  const closedPositions = data?.positions.filter(p => p.sharesHeld <= 1e-9) ?? []
  const twRows = closedPositions.filter(p => p.ticker.endsWith('.TW') || p.ticker.endsWith('.TWO'))
  const usRows = closedPositions.filter(p => !p.ticker.endsWith('.TW') && !p.ticker.endsWith('.TWO'))

  const totalRealizedGains = closedPositions.reduce((s, p) => s + p.realizedGains, 0)
  const totalCashDividends = closedPositions.reduce((s, p) => s + p.cashDividends, 0)

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 pb-24 lg:pb-6">
      <h1 className="mb-4 text-xl font-bold text-gray-900">已出清</h1>

      {/* Summary cards */}
      {data && closedPositions.length > 0 && (
        <div className="mb-6 grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">已實現損益</div>
            <PnlBadge value={totalRealizedGains} />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">現金股息</div>
            <span className="text-sm font-medium text-green-600">{fmtNumber(totalCashDividends)}</span>
          </div>
          <div className="col-span-2 sm:col-span-1 rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">總損益</div>
            <PnlBadge value={totalRealizedGains + totalCashDividends} />
          </div>
        </div>
      )}

      {isLoading && (
        <div className="py-16 text-center text-gray-400 text-sm">載入中…</div>
      )}
      {isError && (
        <div className="py-16 text-center text-red-500 text-sm">載入失敗，請重新整理</div>
      )}

      {!isLoading && !isError && closedPositions.length === 0 && (
        <div className="py-16 text-center">
          <div className="text-4xl mb-3">📭</div>
          <div className="text-gray-500 text-sm">尚無已出清的股票</div>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {twRows.length > 0 && (
            <MarketSection
              title="TW"
              rows={twRows}
              onSelect={(t) => navigate(`/holdings/${t}`)}
            />
          )}
          {usRows.length > 0 && (
            <MarketSection
              title="US"
              rows={usRows}
              onSelect={(t) => navigate(`/holdings/${t}`)}
            />
          )}
        </>
      )}
    </div>
  )
}
