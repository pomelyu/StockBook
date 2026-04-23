import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/layout/ProtectedRoute'
import Navbar from './components/layout/Navbar'
import BottomTabBar from './components/layout/BottomTabBar'
import LoginPage from './pages/LoginPage'
import WatchlistPage from './pages/WatchlistPage'
import HoldingsPage from './pages/HoldingsPage'
import AdminPage from './pages/AdminPage'
import StockDetailPage from './pages/StockDetailPage'
import ClosedPositionsPage from './pages/ClosedPositionsPage'

const queryClient = new QueryClient()

function AppLayout() {
  const { user } = useAuth()
  if (!user) return null
  return (
    <>
      <Navbar />
      <main className="min-h-[calc(100vh-57px)]">
        <Routes>
          <Route path="/" element={<HoldingsPage />} />
          <Route path="/holdings/:ticker" element={<StockDetailPage />} />
          <Route path="/closed" element={<ClosedPositionsPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          {user.is_superuser && (
            <Route path="/admin" element={<AdminPage />} />
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <BottomTabBar />
    </>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
