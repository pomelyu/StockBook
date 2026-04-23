import { useState, useEffect, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createDividend } from '../../api/dividends'
import { searchStocks } from '../../api/stocks'
import type { DividendCreate, DividendType } from '../../types/dividend'
import type { Stock } from '../../types/watchlist'

interface Props {
  onSuccess: () => void
  onCancel: () => void
}

const TYPE_LABELS: Record<DividendType, string> = {
  CASH: '現金股息',
  STOCK: '配股',
  DRIP: '股息再投入',
}

export default function DividendForm({ onSuccess, onCancel }: Props) {
  const queryClient = useQueryClient()
  const [divType, setDivType] = useState<DividendType>('CASH')
  const [ticker, setTicker] = useState('')
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('TWD')
  const [sharesReceived, setSharesReceived] = useState('')
  const [exDate, setExDate] = useState(new Date().toISOString().slice(0, 10))
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Stock search autocomplete
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (ticker.length < 1) { setSearchResults([]); return }
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(async () => {
      const results = await searchStocks(ticker)
      setSearchResults(results)
      setShowSuggestions(results.length > 0)
    }, 300)
  }, [ticker])

  const mutation = useMutation({
    mutationFn: (data: DividendCreate) => createDividend(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dividends', 'all'] })
      onSuccess()
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? '新增失敗，請確認資料後重試')
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!ticker || !exDate) { setError('請填寫必填欄位'); return }
    if (divType === 'CASH' && !amount) { setError('請填寫現金金額'); return }
    if ((divType === 'STOCK' || divType === 'DRIP') && !sharesReceived) {
      setError('請填寫取得股數')
      return
    }

    mutation.mutate({
      ticker,
      dividend_type: divType,
      amount: divType === 'STOCK' ? '0' : (amount || '0'),
      currency,
      shares_received: divType !== 'CASH' ? sharesReceived : null,
      ex_dividend_date: exDate,
      note: note || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Type toggle */}
      <div className="flex rounded-lg border border-gray-200 overflow-hidden">
        {(['CASH', 'STOCK', 'DRIP'] as DividendType[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setDivType(t)}
            className={`flex-1 py-2 text-xs font-medium transition-colors ${
              divType === t ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {TYPE_LABELS[t]}
          </button>
        ))}
      </div>

      {/* Ticker with autocomplete */}
      <div className="relative">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          股票代號 <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          placeholder="例：2330、AAPL"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {showSuggestions && (
          <ul className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {searchResults.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                  onClick={() => {
                    setTicker(s.ticker)
                    if (s.currency) setCurrency(s.currency)
                    setShowSuggestions(false)
                  }}
                >
                  <span className="font-medium">{s.ticker}</span>
                  {s.name && <span className="ml-2 text-gray-500">{s.name}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Amount & Currency (not for STOCK) */}
      {divType !== 'STOCK' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {divType === 'DRIP' ? '再投入金額' : '現金金額'} <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              min="0"
              step="any"
              placeholder="0.00"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">幣別</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="TWD">TWD</option>
              <option value="USD">USD</option>
            </select>
          </div>
        </div>
      )}

      {/* Shares received (STOCK & DRIP) */}
      {divType !== 'CASH' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            取得股數 <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            value={sharesReceived}
            onChange={(e) => setSharesReceived(e.target.value)}
            min="0"
            step="any"
            placeholder="0"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      )}

      {/* Ex-dividend date */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          除息日 <span className="text-red-500">*</span>
        </label>
        <input
          type="date"
          value={exDate}
          onChange={(e) => setExDate(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Note */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">備註</label>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="選填"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-lg border border-gray-300 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {mutation.isPending ? '新增中…' : '確認新增'}
        </button>
      </div>
    </form>
  )
}
