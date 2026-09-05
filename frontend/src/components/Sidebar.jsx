import {
  LayoutDashboard,
  Bot,
  History,
  FileText,
  BarChart3,
  Moon,
  Sun,
  ShieldCheck,
  X,
} from "lucide-react"

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "intake", label: "Intake Copilot", icon: Bot, badge: "AI" },
  { key: "history", label: "Case History", icon: History },
  { key: "reports", label: "Generated Reports", icon: FileText },
  { key: "analytics", label: "Analytics", icon: BarChart3 },
]

export default function Sidebar({ page, setPage, dark, setDark, mobileOpen, onCloseMobile }) {
  const content = (
    <div className="flex h-full w-[250px] flex-col border-r border-slate-100 bg-white dark:border-slate-800/80 dark:bg-[#0E131F] select-none">
      {/* Top Brand Header */}
      <div className="flex items-center justify-between px-5 py-5 border-b border-slate-50 dark:border-slate-800/50">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-pink-600 to-pink-400 text-white shadow-sm shadow-pink-500/25">
            <ShieldCheck size={20} strokeWidth={2.2} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold tracking-tight text-slate-900 dark:text-white">
                Nexus Intake
              </span>
            </div>
            <p className="text-[11px] font-medium text-slate-400 dark:text-slate-500">
              AI Triage Assistant
            </p>
          </div>
        </div>

        {mobileOpen && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Navigation List */}
      <nav className="flex-1 space-y-1.5 px-3 py-4">
        {NAV_ITEMS.map(({ key, label, icon: Icon, badge }) => {
          const active = page === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => {
                setPage(key)
                onCloseMobile?.()
              }}
              className={`group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-left text-xs font-semibold transition-all duration-150 ${
                active
                  ? "bg-pink-50 text-pink-600 shadow-sm dark:bg-pink-950/40 dark:text-pink-300"
                  : "text-slate-600 hover:bg-pink-50/50 hover:text-pink-600 dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-pink-300"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon
                  size={18}
                  strokeWidth={2}
                  className={`transition-colors ${
                    active ? "text-pink-600 dark:text-pink-400" : "text-slate-400 group-hover:text-pink-500"
                  }`}
                />
                <span>{label}</span>
              </div>
              {badge && (
                <span
                  className={`rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                    active
                      ? "bg-pink-500 text-white"
                      : "bg-pink-100 text-pink-600 dark:bg-pink-950 dark:text-pink-300"
                  }`}
                >
                  {badge}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Bottom Area: Dark Mode & Disclaimer */}
      <div className="border-t border-slate-100 p-4 dark:border-slate-800/80">
        <button
          type="button"
          onClick={() => setDark(!dark)}
          className="flex w-full items-center justify-between rounded-xl border border-slate-200/70 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors dark:border-slate-800 dark:text-slate-400 dark:hover:bg-slate-800"
        >
          <span className="flex items-center gap-2">
            {dark ? <Sun size={15} className="text-amber-500" /> : <Moon size={15} className="text-slate-500" />}
            <span>{dark ? "Light mode" : "Dark mode"}</span>
          </span>
          <span className="text-[10px] text-slate-400 font-mono">{dark ? "ON" : "OFF"}</span>
        </button>

        <div className="mt-4 rounded-xl bg-slate-50/80 p-2.5 dark:bg-slate-900/50">
          <p className="text-[10px] leading-relaxed text-slate-400 dark:text-slate-500">
            Decision support only. Never a diagnosis. Escalate to a clinician.
          </p>
        </div>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop Sidebar (hidden on mobile) */}
      <aside className="hidden lg:flex h-full shrink-0">
        {content}
      </aside>

      {/* Mobile Off-Canvas Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative z-10 flex h-full shadow-2xl animate-fadeIn">
            {content}
          </div>
        </div>
      )}
    </>
  )
}
