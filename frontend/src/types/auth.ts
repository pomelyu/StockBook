export interface User {
  id: string
  username: string
  email: string
  is_active: boolean
  is_superuser: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  username: string
  password: string
}
