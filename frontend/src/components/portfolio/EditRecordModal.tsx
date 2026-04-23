import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteTransaction } from '../../api/transactions'
import { deleteDividend } from '../../api/dividends'
import TransactionForm from './TransactionForm'
import DividendForm from './DividendForm'
import type { HistoryEntry } from '../../hooks/useStockHistory'
import type { Transaction } from '../../types/transaction'
import type { Dividend } from '../../types/dividend'

interface Props {
  entry: HistoryEntry
  currentPosition: (ticker: string) => number
  onClose: () => void
}

const TITLE: Record<HistoryEntry['kind'], string> = {
  BUY: '編輯買入',
  SELL: '編輯賣出',
  DIVIDEND: '編輯股息',
}

export default function EditRecordModal({ entry, currentPosition, onClose }: Props) {
  const queryClient = useQueryClient()
  const [confirmDelete, setConfirmDelete] = useState(false)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['transactions'] })
    queryClient.invalidateQueries({ queryKey: ['dividends'] })
  }

  const handleSuccess = () => {
    invalidate()
    onClose()
  }

  const deleteMutation = useMutation({
    mutationFn: () =>
      entry.kind === 'DIVIDEND'
        ? deleteDividend(entry.id)
        : deleteTransaction(entry.id),
    onSuccess: () => {
      invalidate()
      onClose()
    },
  })

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-t-2xl bg-white p-6 sm:rounded-xl max-h-[90dvh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">{TITLE[entry.kind]}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        {/* Pre-filled form */}
        {entry.kind === 'DIVIDEND' ? (
          <DividendForm
            initialData={entry.raw as Dividend}
            onSuccess={handleSuccess}
            onCancel={onClose}
          />
        ) : (
          <TransactionForm
            initialData={entry.raw as Transaction}
            currentPosition={currentPosition}
            onSuccess={handleSuccess}
            onCancel={onClose}
          />
        )}

        {/* Delete zone */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              className="text-sm text-red-500 hover:text-red-700"
            >
              刪除此紀錄
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm text-red-600">確認刪除？</span>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? '刪除中…' : '確認'}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
              >
                取消
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
