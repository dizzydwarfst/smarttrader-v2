import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, BarChart3, BookOpen, Bot, Menu, X, Activity, Search, Bell, ArrowLeftRight } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/trades', label: 'Trades', icon: ArrowLeftRight },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/journal', label: 'Journal', icon: BookOpen },
  { path: '/ai-hub', label: 'AI & News', icon: Bot },
];

export default function Layout({ children }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen" style={{ background: '#0B0E14' }}>
      {/* Crystal Glassmorphism Header */}
      <header data-testid="app-header"
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-16 px-5 lg:px-8 backdrop-blur-xl"
        style={{ background: 'rgba(11,14,20,0.72)', borderBottom: '1px solid #2A3548' }}>
        <div className="flex items-center gap-4">
          <button data-testid="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 rounded-xl transition-all"
            style={{ color: '#94A3B8' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#1E2532'; e.currentTarget.style.color = '#F8FAFC'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}>
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #F59E0B, #FBBF24)', boxShadow: '0 0 0 1px rgba(245,158,11,0.4), 0 4px 16px rgba(245,158,11,0.15)' }}>
              <Activity className="w-5 h-5" style={{ color: '#0B0E14' }} />
            </div>
            <span className="text-[18px] font-black tracking-tight" style={{ color: '#F8FAFC', fontFamily: 'Outfit, sans-serif' }}>
              Smart<span style={{ color: '#F59E0B' }}>Trader</span>
            </span>
          </div>
        </div>
        <div className="hidden md:flex items-center flex-1 max-w-lg mx-10">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: '#64748B' }} />
            <input data-testid="global-search" placeholder="Search anything..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-[14px] focus:outline-none transition-all"
              style={{ background: '#151A24', color: '#F8FAFC', border: '1px solid #2A3548' }}
              onFocus={(e) => e.target.style.borderColor = '#F59E0B'}
              onBlur={(e) => e.target.style.borderColor = '#2A3548'} />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="w-10 h-10 rounded-xl flex items-center justify-center transition-all"
            style={{ border: '1px solid #2A3548', background: '#151A24' }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#F59E0B'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2A3548'; }}>
            <Bell className="w-5 h-5" style={{ color: '#94A3B8' }} />
          </button>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-[13px] font-black"
            style={{ background: '#F59E0B', color: '#0B0E14', fontFamily: 'Outfit, sans-serif' }}>
            ST
          </div>
        </div>
      </header>

      <div className="flex pt-16">
        {/* Sidebar - Desktop */}
        <aside data-testid="sidebar" className="hidden lg:flex flex-col fixed left-0 top-16 bottom-0 z-40"
          style={{ width: 220, background: '#0B0E14', borderRight: '1px solid #2A3548' }}>
          <nav className="px-4 pt-6 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.path;
              return (
                <Link key={item.path} to={item.path}
                  data-testid={`nav-${item.label.toLowerCase().replace(/ & /g, '-')}`}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all relative"
                  style={{
                    background: active ? 'rgba(245,158,11,0.10)' : 'transparent',
                    color: active ? '#F59E0B' : '#94A3B8',
                    border: active ? '1px solid rgba(245,158,11,0.25)' : '1px solid transparent',
                  }}
                  onMouseEnter={(e) => { if (!active) { e.currentTarget.style.background = '#1E2532'; e.currentTarget.style.color = '#F8FAFC'; } }}
                  onMouseLeave={(e) => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; } }}>
                  <Icon className="w-5 h-5" style={{ color: active ? '#F59E0B' : '#64748B' }} />
                  {item.label}
                  {active && <span className="absolute right-3 w-1.5 h-1.5 rounded-full" style={{ background: '#F59E0B', boxShadow: '0 0 8px #F59E0B' }} />}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <>
            <div className="lg:hidden fixed inset-0 z-40 pt-16 backdrop-blur-sm"
              style={{ background: 'rgba(0,0,0,0.6)' }} onClick={() => setSidebarOpen(false)} />
            <aside data-testid="mobile-nav" className="lg:hidden fixed left-0 top-16 bottom-0 z-50 flex flex-col"
              style={{ width: 260, background: '#0B0E14', borderRight: '1px solid #2A3548' }}>
              <nav className="flex-1 px-4 pt-4 space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = location.pathname === item.path;
                  return (
                    <Link key={item.path} to={item.path}
                      data-testid={`mobile-nav-${item.label.toLowerCase().replace(/ & /g, '-')}`}
                      className="flex items-center gap-3 px-4 py-3.5 rounded-xl text-[15px] font-medium transition-all"
                      style={{
                        background: active ? 'rgba(245,158,11,0.10)' : 'transparent',
                        color: active ? '#F59E0B' : '#94A3B8',
                        border: active ? '1px solid rgba(245,158,11,0.25)' : '1px solid transparent',
                      }}
                      onClick={() => setSidebarOpen(false)}>
                      <Icon className="w-5 h-5" style={{ color: active ? '#F59E0B' : '#64748B' }} />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </aside>
          </>
        )}

        {/* Main */}
        <main className="flex-1 lg:ml-[220px]">
          <div className="p-5 md:p-7 lg:p-8 max-w-[1400px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
