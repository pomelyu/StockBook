import client from './client'
import type { Account, AccountCreate, AccountUpdate } from '../types/account'

export async function listAccounts(): Promise<Account[]> {
  const res = await client.get<Account[]>('/accounts/')
  return res.data
}

export async function createAccount(data: AccountCreate): Promise<Account> {
  const res = await client.post<Account>('/accounts/', data)
  return res.data
}

export async function updateAccount(id: string, data: AccountUpdate): Promise<Account> {
  const res = await client.put<Account>(`/accounts/${id}`, data)
  return res.data
}

export async function deleteAccount(id: string): Promise<void> {
  await client.delete(`/accounts/${id}`)
}
