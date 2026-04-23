import { useState } from 'react'
import { refreshPrices, syncCatalog } from '../api/admin'
import type { PriceRefreshResult, CatalogSyncResult } from '../api/admin'

type ActionState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string }

function AdminCard({
  title,
  description,
  buttonLabel,
  onRun,
}: {
  title: string
  description: string
  buttonLabel: string
  onRun: () => Promise<string>
}) {
  const [state, setState] = useState<ActionState>({ status: 'idle' })

  async function handleClick() {
    setState({ status: 'loading' })
    try {
      const message = await onRun()
      setState({ status: 'success', message })
    } catch {
      setState({ status: 'error', message: 'Request failed. Check server logs.' })
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      <h2 className="mb-1 text-base font-semibold text-gray-900">{title}</h2>
      <p className="mb-4 text-sm text-gray-500">{description}</p>

      <button
        onClick={handleClick}
        disabled={state.status === 'loading'}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {state.status === 'loading' ? 'Running…' : buttonLabel}
      </button>

      {state.status === 'success' && (
        <p className="mt-3 text-sm text-green-600">{state.message}</p>
      )}
      {state.status === 'error' && (
        <p className="mt-3 text-sm text-red-500">{state.message}</p>
      )}
    </div>
  )
}

export default function AdminPage() {
  async function handleRefreshPrices(): Promise<string> {
    const result: PriceRefreshResult = await refreshPrices()
    return `Done — updated ${result.updated_stocks} stock(s).`
  }

  async function handleSyncCatalog(): Promise<string> {
    const result: CatalogSyncResult = await syncCatalog()
    return `Done — added ${result.added}, updated ${result.updated}.`
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 pb-20 lg:pb-6">
      <h1 className="mb-6 text-xl font-bold text-gray-900">Admin Console</h1>

      <div className="space-y-4">
        <AdminCard
          title="Refresh Stock Prices"
          description="Manually trigger a price update for all tracked stocks (track_price = true). Equivalent to one scheduler tick."
          buttonLabel="Refresh Prices"
          onRun={handleRefreshPrices}
        />

        <AdminCard
          title="Sync Stock Catalog"
          description="Re-fetch the full stock list from TWSE, TPEX, and NASDAQ. New tickers are inserted; existing ones are skipped."
          buttonLabel="Sync Catalog"
          onRun={handleSyncCatalog}
        />
      </div>
    </div>
  )
}
