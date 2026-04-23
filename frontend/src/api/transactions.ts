import client from './client'
import type { Transaction, TransactionCreate, TransactionUpdate } from '../types/transaction'

interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export async function listAllTransactions(): Promise<Transaction[]> {
  const res = await client.get<Page<Transaction>>('/transactions/?include_all=true')
  return res.data.items
}

export async function listTransactions(params?: {
  ticker?: string
  transaction_type?: 'BUY' | 'SELL'
  page?: number
  page_size?: number
  include_all?: boolean
}): Promise<Page<Transaction>> {
  const res = await client.get<Page<Transaction>>('/transactions/', { params })
  return res.data
}

export async function createTransaction(data: TransactionCreate): Promise<Transaction> {
  const res = await client.post<Transaction>('/transactions/', data)
  return res.data
}

export async function updateTransaction(id: string, data: TransactionUpdate): Promise<Transaction> {
  const res = await client.put<Transaction>(`/transactions/${id}`, data)
  return res.data
}

export async function deleteTransaction(id: string): Promise<void> {
  await client.delete(`/transactions/${id}`)
}
