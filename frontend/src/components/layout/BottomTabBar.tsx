import { Link, useLocation } from 'react-router-dom'

const TABS = [{ label: 'Watchlist', path: '/', icon: '★' }]

export default function BottomTabBar() {
  const location = useLocation()

  return (
    <nav className="fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white lg:hidden">
      <div className="flex">
        {TABS.map((tab) => {
          const active = location.pathname === tab.path
          return (
            <Link
              key={tab.path}
              to={tab.path}
              className={`flex flex-1 flex-col items-center py-3 text-xs font-medium ${
                active ? 'text-blue-600' : 'text-gray-500'
              }`}
            >
              <span className="mb-0.5 text-lg leading-none">{tab.icon}</span>
              {tab.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
