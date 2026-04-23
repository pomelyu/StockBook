import axios from 'axios'
import type { TokenResponse } from '../types/auth'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Separate instance for refresh calls — no interceptors, avoids infinite loop
const refreshClient = axios.create({ baseURL: '/api/v1' })

function clearSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/login'
}

// Inject Bearer token on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401: try to silently refresh the access token, then retry the original request.
// If the refresh token is also expired or missing, redirect to login.
let isRefreshing = false
let pendingQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = []

function drainQueue(error: unknown, token: string | null) {
  pendingQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)))
  pendingQueue = []
}

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config

    // Only handle 401; ignore retried requests to avoid loops
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    const storedRefreshToken = localStorage.getItem('refresh_token')
    if (!storedRefreshToken) {
      clearSession()
      return Promise.reject(error)
    }

    // If a refresh is already in flight, queue this request until it resolves
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then((newToken) => {
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      })
    }

    original._retry = true
    isRefreshing = true

    try {
      const res = await refreshClient.post<TokenResponse>('/auth/refresh', {
        refresh_token: storedRefreshToken,
      })
      const { access_token, refresh_token } = res.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      drainQueue(null, access_token)
      original.headers.Authorization = `Bearer ${access_token}`
      return client(original)
    } catch (refreshError) {
      drainQueue(refreshError, null)
      clearSession()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default client
