import client from './client'
import type { LoginRequest, TokenResponse, User } from '../types/auth'

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const res = await client.post<TokenResponse>('/auth/login', data)
  return res.data
}

export async function refreshToken(refreshToken: string): Promise<TokenResponse> {
  const res = await client.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
  return res.data
}

export async function getMe(): Promise<User> {
  const res = await client.get<User>('/auth/me')
  return res.data
}
