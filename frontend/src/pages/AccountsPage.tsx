import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listAccounts, createAccount, updateAccount, deleteAccount } from '../api/accounts'
import type { Account, AccountCreate } from '../types/account'

type ModalState =
  | { mode: 'none' }
  | { mode: 'add'; market: 'TW' | 'US' }
  | { mode: 'edit'; account: Account }

export default function AccountsPage() {
  const queryClient = useQueryClient()
  const [modal, setModal] = useState<ModalState>({ mode: 'none' })
  const [nameInput, setNameInput] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<Account | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: listAccounts,
  })

  const createMutation = useMutation({
    mutationFn: (data: AccountCreate) => createAccount(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      setModal({ mode: 'none' })
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFormError(msg ?? '新增失敗，請重試')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => updateAccount(id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      setModal({ mode: 'none' })
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFormError(msg ?? '修改失敗，請重試')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAccount(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      setDeleteConfirm(null)
      setDeleteError(null)
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setDeleteError(msg ?? '刪除失敗，請重試')
    },
  })

  function openAdd(market: 'TW' | 'US') {
    setNameInput('')
    setFormError(null)
    setModal({ mode: 'add', market })
  }

  function openEdit(account: Account) {
    setNameInput(account.name)
    setFormError(null)
    setModal({ mode: 'edit', account })
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (!nameInput.trim()) { setFormError('請輸入帳戶名稱'); return }
    if (modal.mode === 'add') {
      createMutation.mutate({ name: nameInput.trim(), market: modal.market })
    } else if (modal.mode === 'edit') {
      updateMutation.mutate({ id: modal.account.id, name: nameInput.trim() })
    }
  }

  const twAccounts = accounts.filter(a => a.market === 'TW')
  const usAccounts = accounts.filter(a => a.market === 'US')

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-8">
      <h1 className="text-xl font-bold text-gray-900">帳戶管理</h1>

      {isLoading ? (
        <p className="text-sm text-gray-500">載入中…</p>
      ) : (
        <>
          {/* TW Accounts */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-gray-700">台股帳戶</h2>
              <button
                onClick={() => openAdd('TW')}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                + 新增
              </button>
            </div>
            {twAccounts.length === 0 ? (
              <p className="text-sm text-gray-400">尚未建立台股帳戶</p>
            ) : (
              <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 overflow-hidden">
                {twAccounts.map(a => (
                  <AccountRow
                    key={a.id}
                    account={a}
                    onEdit={() => openEdit(a)}
                    onDelete={() => { setDeleteConfirm(a); setDeleteError(null) }}
                  />
                ))}
              </ul>
            )}
          </section>

          {/* US Accounts */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-gray-700">美股帳戶</h2>
              <button
                onClick={() => openAdd('US')}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                + 新增
              </button>
            </div>
            {usAccounts.length === 0 ? (
              <p className="text-sm text-gray-400">尚未建立美股帳戶</p>
            ) : (
              <ul className="divide-y divide-gray-100 rounded-xl border border-gray-200 overflow-hidden">
                {usAccounts.map(a => (
                  <AccountRow
                    key={a.id}
                    account={a}
                    onEdit={() => openEdit(a)}
                    onDelete={() => { setDeleteConfirm(a); setDeleteError(null) }}
                  />
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {/* Add / Edit Modal */}
      {modal.mode !== 'none' && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setModal({ mode: 'none' })} />
          <div className="relative w-full sm:max-w-sm bg-white rounded-t-2xl sm:rounded-2xl shadow-xl p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">
              {modal.mode === 'add'
                ? `新增${modal.market === 'TW' ? '台股' : '美股'}帳戶`
                : '修改帳戶名稱'}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">帳戶名稱</label>
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  placeholder="例：富邦、TW-預設"
                  autoFocus
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              {formError && <p className="text-sm text-red-600">{formError}</p>}
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setModal({ mode: 'none' })}
                  className="flex-1 rounded-lg border border-gray-300 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="flex-1 rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {modal.mode === 'add' ? '確認新增' : '確認修改'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDeleteConfirm(null)} />
          <div className="relative w-full sm:max-w-sm bg-white rounded-t-2xl sm:rounded-2xl shadow-xl p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-2">刪除帳戶</h3>
            <p className="text-sm text-gray-600 mb-4">
              確定要刪除帳戶「{deleteConfirm.name}」嗎？若帳戶下有交易或股息紀錄，則無法刪除。
            </p>
            {deleteError && <p className="text-sm text-red-600 mb-3">{deleteError}</p>}
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="flex-1 rounded-lg border border-gray-300 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirm.id)}
                disabled={deleteMutation.isPending}
                className="flex-1 rounded-lg bg-red-600 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? '刪除中…' : '確認刪除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function AccountRow({ account, onEdit, onDelete }: {
  account: Account
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <li className="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50">
      <span className="text-sm font-medium text-gray-800">{account.name}</span>
      <div className="flex gap-3">
        <button onClick={onEdit} className="text-xs text-blue-600 hover:text-blue-800">編輯</button>
        <button onClick={onDelete} className="text-xs text-red-500 hover:text-red-700">刪除</button>
      </div>
    </li>
  )
}
