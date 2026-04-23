import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const BASE_NAV_ITEMS = [
  { label: 'Holdings', path: '/' },
  { label: 'Closed', path: '/closed' },
  { label: 'Watchlist', path: '/watchlist' },
]

export default function Navbar() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const navItems = [
    ...BASE_NAV_ITEMS,
    ...(user?.is_superuser ? [{ label: 'Admin', path: '/admin' }] : []),
  ]

  return (
    <nav className="border-b border-gray-200 bg-white px-4 py-3 lg:px-6">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="text-lg font-bold text-blue-600">StockBook</span>
          <div className="hidden gap-4 lg:flex">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`text-sm font-medium ${
                  location.pathname === item.path
                    ? 'text-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-gray-500 lg:block">{user?.username}</span>
          <button
            onClick={logout}
            className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}
