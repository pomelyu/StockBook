import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWatchlist, addToWatchlist, removeFromWatchlist, searchStocks } from '../api/watchlist'
import type { Stock } from '../types/watchlist'

function formatPrice(price: number | null, currency: string) {
  if (price === null) return '—'
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price)
}

function formatUpdated(ts: string | null) {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function AddStockModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Stock[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  const addMutation = useMutation({
    mutationFn: (ticker: string) => addToWatchlist(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      onClose()
    },
  })

  async function handleSearch() {
    if (!query.trim()) return
    setSearching(true)
    setSearchError('')
    try {
      const data = await searchStocks(query.trim())
      setResults(data)
      if (data.length === 0) setSearchError('No stocks found.')
    } catch {
      setSearchError('Search failed. Please try again.')
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center">
      <div className="w-full max-w-md rounded-t-2xl bg-white p-6 sm:rounded-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Add Stock</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="e.g. AAPL or 2330"
            autoFocus
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {searching ? '…' : 'Search'}
          </button>
        </div>

        {searchError && <p className="mt-2 text-sm text-red-500">{searchError}</p>}

        {results.length > 0 && (
          <ul className="mt-4 divide-y divide-gray-100 rounded-lg border border-gray-200">
            {results.map((stock) => (
              <li key={stock.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <span className="font-medium text-gray-900">{stock.ticker}</span>
                  {stock.name && (
                    <span className="ml-2 text-sm text-gray-500">{stock.name}</span>
                  )}
                  <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                    {stock.market}
                  </span>
                </div>
                <button
                  onClick={() => addMutation.mutate(stock.ticker)}
                  disabled={addMutation.isPending}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  Add
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default function WatchlistPage() {
  const queryClient = useQueryClient()
  const [showAddModal, setShowAddModal] = useState(false)

  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['watchlist'],
    queryFn: getWatchlist,
    refetchInterval: 60_000, // refresh every 60 s
  })

  const removeMutation = useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <p className="text-red-500">Failed to load watchlist. Please refresh.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 pb-20 lg:pb-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Watchlist</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Add Stock
        </button>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 py-16 text-center">
          <p className="text-gray-500">No stocks in your watchlist yet.</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="mt-3 text-sm font-medium text-blue-600 hover:underline"
          >
            Add your first stock →
          </button>
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden overflow-hidden rounded-xl border border-gray-200 sm:block">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Ticker</th>
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-center">Market</th>
                  <th className="px-4 py-3 text-right">Price</th>
                  <th className="px-4 py-3 text-right">Updated</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-semibold text-gray-900">{item.ticker}</td>
                    <td className="px-4 py-3 text-gray-600">{item.name ?? '—'}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                        {item.market}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                      {formatPrice(item.last_price, item.currency)}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-gray-400">
                      {formatUpdated(item.price_updated_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => removeMutation.mutate(item.ticker)}
                        disabled={removeMutation.isPending}
                        className="text-xs text-red-500 hover:text-red-700 disabled:opacity-40"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card list */}
          <div className="space-y-3 sm:hidden">
            {items.map((item) => (
              <div key={item.id} className="rounded-xl border border-gray-200 bg-white p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900">{item.ticker}</span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                      {item.market}
                    </span>
                  </div>
                  <button
                    onClick={() => removeMutation.mutate(item.ticker)}
                    disabled={removeMutation.isPending}
                    className="text-xs text-red-500 disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>
                {item.name && <p className="mb-2 text-sm text-gray-500">{item.name}</p>}
                <div className="flex items-center justify-between">
                  <span className="text-lg font-semibold text-gray-900">
                    {formatPrice(item.last_price, item.currency)}
                  </span>
                  <span className="text-xs text-gray-400">{formatUpdated(item.price_updated_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {showAddModal && <AddStockModal onClose={() => setShowAddModal(false)} />}
    </div>
  )
}
