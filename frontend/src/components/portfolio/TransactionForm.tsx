import { useState, useEffect, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTransaction, updateTransaction } from '../../api/transactions'
import { searchStocks } from '../../api/stocks'
import type { Transaction, TransactionCreate, TransactionUpdate } from '../../types/transaction'
import type { Stock } from '../../types/watchlist'

interface Props {
  onSuccess: () => void
  onCancel: () => void
  currentPosition?: (ticker: string) => number
  initialData?: Transaction
}

export default function TransactionForm({ onSuccess, onCancel, currentPosition, initialData }: Props) {
  const isEdit = !!initialData
  const queryClient = useQueryClient()
  const [txType, setTxType] = useState<'BUY' | 'SELL'>(initialData?.transaction_type ?? 'BUY')
  const [ticker, setTicker] = useState(initialData?.ticker ?? '')
  const [quantity, setQuantity] = useState(initialData?.quantity ?? '')
  const [price, setPrice] = useState(initialData?.price ?? '')
  const [fee, setFee] = useState(initialData?.fee ?? '0')
  const [date, setDate] = useState(initialData?.transaction_date ?? new Date().toISOString().slice(0, 10))
  const [note, setNote] = useState(initialData?.note ?? '')
  const [error, setError] = useState<string | null>(null)

  // Stock search autocomplete (only for create mode)
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (isEdit) return
    if (ticker.length < 1) { setSearchResults([]); return }
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(async () => {
      const results = await searchStocks(ticker)
      setSearchResults(results)
      setShowSuggestions(results.length > 0)
    }, 300)
  }, [ticker, isEdit])

  const position = currentPosition ? currentPosition(ticker.toUpperCase()) : null

  const mutation = useMutation({
    mutationFn: (data: TransactionCreate | TransactionUpdate) =>
      isEdit
        ? updateTransaction(initialData!.id, data as TransactionUpdate)
        : createTransaction(data as TransactionCreate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      onSuccess()
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? (isEdit ? '修改失敗，請確認資料後重試' : '新增失敗，請確認資料後重試'))
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!ticker || !quantity || !price || !date) {
      setError('請填寫必填欄位')
      return
    }
    mutation.mutate({
      ticker,
      transaction_type: txType,
      quantity,
      price,
      fee: fee || '0',
      transaction_date: date,
      note: note || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* BUY / SELL toggle */}
      <div className="flex rounded-lg border border-gray-200 overflow-hidden">
        {(['BUY', 'SELL'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTxType(t)}
            className={`flex-1 py-2 text-sm font-medium transition-colors ${
              txType === t
                ? t === 'BUY'
                  ? 'bg-green-600 text-white'
                  : 'bg-red-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {t === 'BUY' ? '買入' : '賣出'}
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
          disabled={isEdit}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
        />
        {!isEdit && showSuggestions && (
          <ul className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {searchResults.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                  onClick={() => { setTicker(s.ticker); setShowSuggestions(false) }}
                >
                  <span className="font-medium">{s.ticker}</span>
                  {s.name && <span className="ml-2 text-gray-500">{s.name}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
        {txType === 'SELL' && position !== null && (
          <p className="mt-1 text-xs text-gray-500">目前持倉：{position} 股</p>
        )}
      </div>

      {/* Quantity & Price */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            股數 <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            min="0"
            step="any"
            placeholder="0"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            單價 <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            min="0"
            step="any"
            placeholder="0.00"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Fee & Date */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">手續費</label>
          <input
            type="number"
            value={fee}
            onChange={(e) => setFee(e.target.value)}
            min="0"
            step="any"
            placeholder="0"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            交割日 <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
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
          {mutation.isPending ? (isEdit ? '修改中…' : '新增中…') : (isEdit ? '確認修改' : '確認新增')}
        </button>
      </div>
    </form>
  )
}
