'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function Nav() {
  const path = usePathname()
  const links = [
    { href: '/', label: 'PLACAR' },
    { href: '/history', label: 'HISTÓRICO' },
    { href: '/balancer', label: 'BALANCEADOR' },
    { href: '/admin', label: 'ADMIN' },
  ]
  return (
    <header className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        <span className="font-bold text-amber-400 tracking-widest text-sm">X5 TRACKER</span>
        <nav className="flex gap-1">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`px-3 py-1.5 rounded text-xs font-semibold tracking-wider transition-colors ${
                path === l.href
                  ? 'bg-amber-400 text-gray-950'
                  : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
