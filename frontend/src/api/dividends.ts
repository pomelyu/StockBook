import client from './client'
import type { Dividend, DividendCreate, DividendUpdate } from '../types/dividend'

interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export async function listAllDividends(): Promise<Dividend[]> {
  const res = await client.get<Page<Dividend>>('/dividends/?include_all=true')
  return res.data.items
}

export async function listDividends(params?: {
  ticker?: string
  page?: number
  page_size?: number
  include_all?: boolean
}): Promise<Page<Dividend>> {
  const res = await client.get<Page<Dividend>>('/dividends/', { params })
  return res.data
}

export async function createDividend(data: DividendCreate): Promise<Dividend> {
  const res = await client.post<Dividend>('/dividends/', data)
  return res.data
}

export async function updateDividend(id: string, data: DividendUpdate): Promise<Dividend> {
  const res = await client.put<Dividend>(`/dividends/${id}`, data)
  return res.data
}

export async function deleteDividend(id: string): Promise<void> {
  await client.delete(`/dividends/${id}`)
}
