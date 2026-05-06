import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePortfolio } from '../hooks/usePortfolio'
import AddRecordModal from '../components/portfolio/AddRecordModal'
import MarketUpdateBadge from '../components/ui/MarketUpdateBadge'
import type { Position } from '../utils/pnl'

function fmtNumber(n: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n)
}

function PnlBadge({ value, pct }: { value: number | null; pct?: number | null }) {
  if (value === null) return <span className="text-gray-400 text-sm">—</span>
  const positive = value >= 0
  const color = positive ? 'text-green-600' : 'text-red-600'
  return (
    <span className={`${color} text-sm font-medium`}>
      {positive ? '+' : ''}{fmtNumber(value)}
      {pct != null && (
        <span className="ml-1 text-xs">
          ({positive ? '+' : ''}{fmtNumber(pct, 1)}%)
        </span>
      )}
    </span>
  )
}

function PositionRow({ pos, isTW, onSelect, exchangeRate }: { pos: Position; isTW: boolean; onSelect: (ticker: string) => void; exchangeRate?: number | null }) {
  const shareDecimals = isTW ? 0 : 3
  const fx = (!isTW && exchangeRate != null) ? exchangeRate : null
  const toTwd = (v: number) => fx !== null ? fmtNumber(v * fx, 0) : null

  return (
    <>
      {/* Desktop row */}
      <tr
        onClick={() => onSelect(pos.ticker)}
        className="hidden sm:table-row border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
      >
        <td className="px-4 py-3">
          <div className="font-medium text-gray-900 text-sm">{pos.ticker}</div>
          {pos.stockName && <div className="text-xs text-gray-500 truncate max-w-[160px]">{pos.stockName}</div>}
        </td>
        <td className="px-4 py-3 text-right text-sm text-gray-700">{fmtNumber(pos.sharesHeld, shareDecimals)}</td>
        <td className="px-4 py-3 text-right text-sm text-gray-700">
          <div>{fmtNumber(pos.avgCostPerShare)}</div>
          {toTwd(pos.avgCostPerShare) && <div className="text-xs text-gray-400">{toTwd(pos.avgCostPerShare)}</div>}
        </td>
        <td className="px-4 py-3 text-right text-sm text-gray-700">
          {pos.currentPrice !== null ? (
            <>
              <div>{fmtNumber(pos.currentPrice)}</div>
              {toTwd(pos.currentPrice) && <div className="text-xs text-gray-400">{toTwd(pos.currentPrice)}</div>}
            </>
          ) : '—'}
        </td>
        <td className="px-4 py-3 text-right text-sm text-gray-700">
          {pos.positionValue !== null ? (
            <>
              <div>{fmtNumber(pos.positionValue)}</div>
              {toTwd(pos.positionValue) && <div className="text-xs text-gray-400">{toTwd(pos.positionValue)}</div>}
            </>
          ) : '—'}
        </td>
        <td className="px-4 py-3 text-right">
          <PnlBadge value={pos.unrealizedPnl} pct={pos.unrealizedPnlPct} />
          {pos.unrealizedPnl !== null && toTwd(pos.unrealizedPnl) && (
            <div className="text-xs text-gray-400">{toTwd(pos.unrealizedPnl)}</div>
          )}
        </td>
        <td className="px-4 py-3 text-right">
          <PnlBadge value={pos.realizedGains} />
          {pos.realizedGains !== 0 && toTwd(pos.realizedGains) && (
            <div className="text-xs text-gray-400">{toTwd(pos.realizedGains)}</div>
          )}
        </td>
        <td className="px-4 py-3 text-right text-sm">
          <span className={pos.cashDividends !== 0 ? 'text-green-600' : 'text-gray-400'}>
            {fmtNumber(pos.cashDividends)}
          </span>
          {pos.cashDividends !== 0 && toTwd(pos.cashDividends) && (
            <div className="text-xs text-gray-400">{toTwd(pos.cashDividends)}</div>
          )}
        </td>
      </tr>

      {/* Mobile card */}
      <div
        onClick={() => onSelect(pos.ticker)}
        className="sm:hidden border border-gray-200 rounded-xl p-4 space-y-2 cursor-pointer active:bg-gray-50"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="font-medium text-gray-900">{pos.ticker}</div>
            {pos.stockName && <div className="text-xs text-gray-500">{pos.stockName}</div>}
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500">未實現損益</div>
            <PnlBadge value={pos.unrealizedPnl} pct={pos.unrealizedPnlPct} />
            {pos.unrealizedPnl !== null && toTwd(pos.unrealizedPnl) && (
              <div className="text-xs text-gray-400">{toTwd(pos.unrealizedPnl)}</div>
            )}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-xs text-gray-600 pt-1 border-t border-gray-100">
          <div>
            <div className="text-gray-400">持股數</div>
            <div>{fmtNumber(pos.sharesHeld, shareDecimals)}</div>
          </div>
          <div>
            <div className="text-gray-400">均攤成本</div>
            <div>{fmtNumber(pos.avgCostPerShare)}</div>
            {toTwd(pos.avgCostPerShare) && <div className="text-gray-400">{toTwd(pos.avgCostPerShare)}</div>}
          </div>
          <div>
            <div className="text-gray-400">現價 / 總值</div>
            <div>{pos.currentPrice !== null ? fmtNumber(pos.currentPrice) : '—'}</div>
            {pos.currentPrice !== null && toTwd(pos.currentPrice) && (
              <div className="text-gray-400">{toTwd(pos.currentPrice)}</div>
            )}
            {pos.positionValue !== null && (
              <div className="text-gray-400">{fmtNumber(pos.positionValue)}</div>
            )}
            {pos.positionValue !== null && toTwd(pos.positionValue) && (
              <div className="text-gray-400">{toTwd(pos.positionValue)}</div>
            )}
          </div>
        </div>
        {pos.realizedGains !== 0 && (
          <div className="text-xs text-gray-500">
            已實現：<PnlBadge value={pos.realizedGains} />
            {toTwd(pos.realizedGains) && <span className="text-gray-400 ml-1">{toTwd(pos.realizedGains)}</span>}
          </div>
        )}
        {pos.cashDividends !== 0 && (
          <div className="text-xs text-gray-500">
            配息：<span className="text-green-600">{fmtNumber(pos.cashDividends)}</span>
            {toTwd(pos.cashDividends) && <span className="text-gray-400 ml-1">{toTwd(pos.cashDividends)}</span>}
          </div>
        )}
      </div>
    </>
  )
}

function PositionTable({ title, positions, onSelect, exchangeRate }: { title: string; positions: Position[]; onSelect: (ticker: string) => void; exchangeRate?: number | null }) {
  const isTW = title === 'TW'
  const fx = (!isTW && exchangeRate != null) ? exchangeRate : null
  const toTwd = (v: number) => fx !== null ? fmtNumber(v * fx, 0) : null

  const subtotalValue = positions.every(p => p.positionValue !== null)
    ? positions.reduce((s, p) => s + (p.positionValue ?? 0), 0)
    : null
  const subtotalUnrealized = positions.every(p => p.unrealizedPnl !== null)
    ? positions.reduce((s, p) => s + (p.unrealizedPnl ?? 0), 0)
    : null
  const subtotalRealized = positions.reduce((s, p) => s + p.realizedGains, 0)
  const subtotalDividends = positions.reduce((s, p) => s + p.cashDividends, 0)

  return (
    <div className="mb-6">
      <div className="mb-2 flex items-baseline gap-2">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">{title}</h2>
        {exchangeRate != null && (
          <span className="text-xs text-gray-400">USD/TWD {exchangeRate.toFixed(2)}</span>
        )}
      </div>
      {/* Desktop table */}
      <div className="hidden sm:block rounded-xl border border-gray-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 text-left">股票</th>
              <th className="px-4 py-3 text-right">持股數</th>
              <th className="px-4 py-3 text-right">均攤成本</th>
              <th className="px-4 py-3 text-right">現價</th>
              <th className="px-4 py-3 text-right">總值</th>
              <th className="px-4 py-3 text-right">未實現損益</th>
              <th className="px-4 py-3 text-right">已實現損益</th>
              <th className="px-4 py-3 text-right">配息</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((pos) => (
              <PositionRow key={pos.ticker} pos={pos} isTW={isTW} onSelect={onSelect} exchangeRate={exchangeRate} />
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50 text-sm font-semibold">
              <td className="px-4 py-3 text-gray-700">小計</td>
              <td /><td /><td />
              <td className="px-4 py-3 text-right text-gray-700">
                {subtotalValue !== null ? (
                  <>
                    <div>{fmtNumber(subtotalValue)}</div>
                    {toTwd(subtotalValue) && <div className="text-xs text-gray-400 font-normal">{toTwd(subtotalValue)}</div>}
                  </>
                ) : '—'}
              </td>
              <td className="px-4 py-3 text-right">
                <PnlBadge value={subtotalUnrealized} />
                {subtotalUnrealized !== null && toTwd(subtotalUnrealized) && (
                  <div className="text-xs text-gray-400 font-normal">{toTwd(subtotalUnrealized)}</div>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                <PnlBadge value={subtotalRealized} />
                {subtotalRealized !== null && toTwd(subtotalRealized) && (
                  <div className="text-xs text-gray-400 font-normal">{toTwd(subtotalRealized)}</div>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                <span className="text-green-600 font-normal">{fmtNumber(subtotalDividends)}</span>
                {toTwd(subtotalDividends) && <div className="text-xs text-gray-400 font-normal">{toTwd(subtotalDividends)}</div>}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      {/* Mobile card list */}
      <div className="sm:hidden space-y-3">
        {positions.map((pos) => (
          <PositionRow key={pos.ticker} pos={pos} isTW={isTW} onSelect={onSelect} exchangeRate={exchangeRate} />
        ))}
        {/* Mobile subtotal card */}
        <div className="border border-gray-200 rounded-xl p-4 bg-gray-50">
          <div className="text-xs font-semibold text-gray-500 mb-2">小計</div>
          <div className="grid grid-cols-3 gap-2 text-xs text-gray-600">
            <div>
              <div className="text-gray-400">總值</div>
              <div className="font-medium">{subtotalValue !== null ? fmtNumber(subtotalValue) : '—'}</div>
              {subtotalValue !== null && toTwd(subtotalValue) && (
                <div className="text-gray-400">{toTwd(subtotalValue)}</div>
              )}
            </div>
            <div>
              <div className="text-gray-400">未實現損益</div>
              <PnlBadge value={subtotalUnrealized} />
              {subtotalUnrealized !== null && toTwd(subtotalUnrealized) && (
                <div className="text-gray-400">{toTwd(subtotalUnrealized)}</div>
              )}
            </div>
            <div>
              <div className="text-gray-400">已實現損益</div>
              <PnlBadge value={subtotalRealized} />
              {subtotalRealized !== 0 && toTwd(subtotalRealized) && (
                <div className="text-gray-400">{toTwd(subtotalRealized)}</div>
              )}
            </div>
            <div>
              <div className="text-gray-400">配息</div>
              <span className={subtotalDividends !== 0 ? 'text-green-600 font-medium' : 'text-gray-600'}>{fmtNumber(subtotalDividends)}</span>
              {subtotalDividends !== 0 && toTwd(subtotalDividends) && (
                <div className="text-gray-400">{toTwd(subtotalDividends)}</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function HoldingsPage() {
  const navigate = useNavigate()
  const { data, isLoading, isError, marketUpdateTimes } = usePortfolio()
  const [showModal, setShowModal] = useState(false)

  function currentPosition(ticker: string): number {
    if (!data) return 0
    return data.positions.find(p => p.ticker === ticker)?.sharesHeld ?? 0
  }

  const heldPositions = data?.positions.filter(p => p.sharesHeld > 1e-9) ?? []
  const twPositions = heldPositions.filter(p => p.ticker.endsWith('.TW') || p.ticker.endsWith('.TWO'))
  const usPositions = heldPositions.filter(p => !p.ticker.endsWith('.TW') && !p.ticker.endsWith('.TWO'))

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 pb-24 lg:pb-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">持倉總覽</h1>
        <MarketUpdateBadge us={marketUpdateTimes.us} tw={marketUpdateTimes.tw} />
      </div>

      {/* Summary cards */}
      {data && (
        <div className="mb-6 grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">總成本</div>
            <span className="text-sm font-medium text-gray-700">{fmtNumber(data.totalCost)}</span>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">總市值</div>
            <span className="text-sm font-medium text-gray-700">
              {data.totalValue !== null ? fmtNumber(data.totalValue) : '—'}
            </span>
          </div>
          <div className="col-span-2 sm:col-span-1 rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">總損益</div>
            <PnlBadge
              value={data.totalUnrealizedPnl + data.totalRealizedGains + data.totalCashDividends}
            />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">未實現損益</div>
            <PnlBadge value={data.totalUnrealizedPnl} />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">已實現損益</div>
            <PnlBadge value={data.totalRealizedGains} />
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="text-xs text-gray-500 mb-1">現金股息</div>
            <span className="text-sm font-medium text-gray-700">
              {fmtNumber(data.totalCashDividends)}
            </span>
          </div>
        </div>
      )}

      {/* Loading / Error */}
      {isLoading && (
        <div className="py-16 text-center text-gray-400 text-sm">載入中…</div>
      )}
      {isError && (
        <div className="py-16 text-center text-red-500 text-sm">載入失敗，請重新整理</div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && heldPositions.length === 0 && (
        <div className="py-16 text-center">
          <div className="text-4xl mb-3">📊</div>
          <div className="text-gray-500 text-sm">尚無持倉紀錄</div>
          <div className="text-gray-400 text-xs mt-1">點右下角的 + 新增第一筆交易</div>
        </div>
      )}

      {/* Position tables by market */}
      {!isLoading && !isError && (
        <>
          {twPositions.length > 0 && <PositionTable title="TW" positions={twPositions} onSelect={(t) => navigate(`/holdings/${t}`)} />}
          {usPositions.length > 0 && <PositionTable title="US" positions={usPositions} onSelect={(t) => navigate(`/holdings/${t}`)} exchangeRate={data?.usdToTwd} />}
        </>
      )}

      {/* FAB */}
      <button
        onClick={() => setShowModal(true)}
        className="fixed bottom-20 right-4 lg:bottom-6 lg:right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg text-2xl hover:bg-blue-700 active:scale-95 transition-transform"
        aria-label="新增紀錄"
      >
        +
      </button>

      {showModal && (
        <AddRecordModal
          onClose={() => setShowModal(false)}
          currentPosition={currentPosition}
        />
      )}
    </div>
  )
}
