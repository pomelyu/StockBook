import client from './client'

export interface PriceRefreshResult {
  updated_stocks: number
}

export interface CatalogSyncResult {
  added: number
  updated: number
}

export async function refreshPrices(): Promise<PriceRefreshResult> {
  const res = await client.post<PriceRefreshResult>('/admin/prices/refresh')
  return res.data
}

export async function syncCatalog(): Promise<CatalogSyncResult> {
  const res = await client.post<CatalogSyncResult>('/admin/catalog/sync')
  return res.data
}
