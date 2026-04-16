import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, BarChart3, BookOpen, Bot, Menu, X, Activity, Search, Bell, ArrowLeftRight, Settings } from 'lucide-react';

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
    <div className="min-h-screen" style={{ background: '#F0F2F5' }}>
      {/* Top header */}
      <header data-testid="app-header" className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-16 px-5 lg:px-8 shadow-sm"
        style={{ background: '#fff', borderBottom: '1px solid #E5E7EB' }}>
        <div className="flex items-center gap-4">
          <button data-testid="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 rounded-xl hover:bg-gray-100" style={{ color: '#6B7280' }}>
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: '#2563EB' }}>
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-[17px] font-bold" style={{ color: '#111827' }}>SmartTrader</span>
          </div>
        </div>
        <div className="hidden md:flex items-center flex-1 max-w-lg mx-10">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: '#9CA3AF' }} />
            <input data-testid="global-search" placeholder="Search anything..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              style={{ background: '#F0F2F5', color: '#111827', border: '1px solid #E5E7EB' }} />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="w-10 h-10 rounded-xl flex items-center justify-center hover:bg-gray-100" style={{ border: '1px solid #E5E7EB' }}>
            <Bell className="w-5 h-5" style={{ color: '#6B7280' }} />
          </button>
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-[13px] font-bold text-white" style={{ background: '#2563EB' }}>
            ST
          </div>
        </div>
      </header>

      <div className="flex pt-16">
        {/* Sidebar - Desktop */}
        <aside data-testid="sidebar" className="hidden lg:flex flex-col fixed left-0 top-16 bottom-0 z-40 shadow-sm"
          style={{ width: 220, background: '#fff', borderRight: '1px solid #E5E7EB' }}>
          <nav className="px-4 pt-6 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.path;
              return (
                <Link key={item.path} to={item.path}
                  data-testid={`nav-${item.label.toLowerCase().replace(/ & /g, '-')}`}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl text-[14px] font-medium transition-all"
                  style={{
                    background: active ? '#EFF6FF' : 'transparent',
                    color: active ? '#2563EB' : '#6B7280',
                  }}>
                  <Icon className="w-5 h-5" style={{ color: active ? '#2563EB' : '#9CA3AF' }} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <>
            <div className="lg:hidden fixed inset-0 z-40 pt-16" style={{ background: 'rgba(0,0,0,0.3)' }} onClick={() => setSidebarOpen(false)} />
            <aside data-testid="mobile-nav" className="lg:hidden fixed left-0 top-16 bottom-0 z-50 flex flex-col shadow-xl"
              style={{ width: 260, background: '#fff' }}>
              <nav className="flex-1 px-4 pt-4 space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = location.pathname === item.path;
                  return (
                    <Link key={item.path} to={item.path}
                      data-testid={`mobile-nav-${item.label.toLowerCase().replace(/ & /g, '-')}`}
                      className="flex items-center gap-3 px-4 py-3.5 rounded-xl text-[15px] font-medium transition-all"
                      style={{ background: active ? '#EFF6FF' : 'transparent', color: active ? '#2563EB' : '#6B7280' }}
                      onClick={() => setSidebarOpen(false)}>
                      <Icon className="w-5 h-5" style={{ color: active ? '#2563EB' : '#9CA3AF' }} />
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
