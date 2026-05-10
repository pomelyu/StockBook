export interface Account {
  id: string
  name: string
  market: 'TW' | 'US'
  created_at: string
}

export interface AccountCreate {
  name: string
  market: 'TW' | 'US'
}

export interface AccountUpdate {
  name: string
}
