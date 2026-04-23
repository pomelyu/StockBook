import { useState } from 'react'
import TransactionForm from './TransactionForm'
import DividendForm from './DividendForm'

type Step = 'choose' | 'transaction' | 'dividend'

interface Props {
  onClose: () => void
  currentPosition: (ticker: string) => number
}

export default function AddRecordModal({ onClose, currentPosition }: Props) {
  const [step, setStep] = useState<Step>('choose')

  function handleSuccess() {
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Sheet */}
      <div className="relative w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-xl p-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            {step !== 'choose' && (
              <button
                onClick={() => setStep('choose')}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                ←
              </button>
            )}
            <h2 className="text-base font-semibold text-gray-900">
              {step === 'choose' && '新增紀錄'}
              {step === 'transaction' && '新增交易'}
              {step === 'dividend' && '新增股息'}
            </h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
            ×
          </button>
        </div>

        {step === 'choose' && (
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setStep('transaction')}
              className="flex flex-col items-center gap-3 rounded-xl border-2 border-gray-200 p-5 hover:border-blue-500 hover:bg-blue-50 transition-colors"
            >
              <span className="text-3xl">📈</span>
              <span className="text-sm font-medium text-gray-800">交易紀錄</span>
              <span className="text-xs text-gray-500 text-center">買入 / 賣出</span>
            </button>
            <button
              onClick={() => setStep('dividend')}
              className="flex flex-col items-center gap-3 rounded-xl border-2 border-gray-200 p-5 hover:border-blue-500 hover:bg-blue-50 transition-colors"
            >
              <span className="text-3xl">💰</span>
              <span className="text-sm font-medium text-gray-800">股息紀錄</span>
              <span className="text-xs text-gray-500 text-center">現金 / 配股 / 再投入</span>
            </button>
          </div>
        )}

        {step === 'transaction' && (
          <TransactionForm
            onSuccess={handleSuccess}
            onCancel={() => setStep('choose')}
            currentPosition={currentPosition}
          />
        )}

        {step === 'dividend' && (
          <DividendForm
            onSuccess={handleSuccess}
            onCancel={() => setStep('choose')}
          />
        )}
      </div>
    </div>
  )
}
