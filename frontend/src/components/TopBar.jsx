import { useState } from "react"
import { Search, Bell, Menu, ChevronDown } from "lucide-react"

export default function TopBar({ onOpenMobileSidebar, onSearch, currentSearch = "" }) {
  const [query, setQuery] = useState(currentSearch)
  const [notificationsOpen, setNotificationsOpen] = useState(false)

  function handleKeyDown(e) {
    if (e.key === "Enter") {
      onSearch?.(query)
    }
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-100 bg-white/80 px-4 sm:px-6 backdrop-blur-md dark:border-slate-800/80 dark:bg-[#0E131F]/80">
      {/* Left: Mobile hamburger & Global Search */}
      <div className="flex items-center gap-3 flex-1 max-w-md">
        <button
          type="button"
          onClick={onOpenMobileSidebar}
          aria-label="Open navigation menu"
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200/80 text-slate-600 hover:bg-slate-50 lg:hidden dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <Menu size={18} />
        </button>

        <div className="relative w-full">
          <Search
            size={16}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              onSearch?.(e.target.value)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search cases, complaints, patients..."
            className="h-10 w-full rounded-full border border-slate-200/70 bg-slate-50/60 pl-10 pr-4 text-xs font-medium text-slate-800 placeholder-slate-400 transition-all focus:border-pink-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-pink-500/20 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-100 dark:placeholder-slate-500 dark:focus:border-pink-500 dark:focus:bg-slate-900"
          />
        </div>
      </div>

      {/* Right: Notifications & Clinician Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Notification Bell */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            aria-label="Notifications"
            className="relative flex h-9 w-9 items-center justify-center rounded-full text-slate-600 hover:bg-pink-50 hover:text-pink-600 transition-colors dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-pink-400"
          >
            <Bell size={17} />
            <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-pink-500 ring-2 ring-white dark:ring-slate-900" />
          </button>

          {notificationsOpen && (
            <div className="absolute right-0 mt-2 w-72 rounded-2xl border border-slate-100 bg-white p-3 shadow-soft dark:border-slate-800 dark:bg-slate-900 z-50 animate-fadeIn">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="text-xs font-semibold text-slate-900 dark:text-white">Intake Alerts</span>
                <span className="rounded-full bg-pink-50 px-2 py-0.5 text-[10px] font-semibold text-pink-600 dark:bg-pink-950/60 dark:text-pink-400">Live</span>
              </div>
              <div className="py-2.5 text-xs text-slate-600 dark:text-slate-300">
                <p className="font-medium text-slate-800 dark:text-slate-200">System Ready</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Clinical triage copilot is actively monitoring bedside queue.</p>
              </div>
            </div>
          )}
        </div>

        {/* Separator */}
        <div className="h-5 w-px bg-slate-200/80 dark:bg-slate-800" />

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-1 cursor-pointer select-none">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-tr from-pink-500 to-pink-400 text-white shadow-sm ring-2 ring-pink-500/20">
            <span className="text-xs font-bold">SJ</span>
          </div>
          <div className="hidden text-left sm:block">
            <p className="text-xs font-semibold leading-tight text-slate-900 dark:text-white">
              Dr. Sarah Jenkins
            </p>
            <p className="text-[10px] font-medium leading-tight text-pink-600 dark:text-pink-400">
              Emergency Triage
            </p>
          </div>
          <ChevronDown size={14} className="hidden text-slate-400 sm:block" />
        </div>
      </div>
    </header>
  )
}
