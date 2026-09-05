import { useEffect, useState } from "react"
import {
  AlertTriangle,
  ArrowUpRight,
  Plus,
  Siren,
  Activity,
  AlertCircle,
  Clock,
  CheckCircle2,
  TrendingUp,
} from "lucide-react"
import { fetchAnalytics, fetchCases } from "../lib/api.js"
import { Panel, SectionLabel, UrgencyBadge, formatTimestamp } from "../components/ui.jsx"

function StatCard({ label, value, tone = "default", icon: Icon }) {
  const styles = {
    default: {
      text: "text-slate-900 dark:text-white",
      iconBg: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    },
    emergency: {
      text: "text-rose-600 dark:text-rose-400",
      iconBg: "bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400",
    },
    urgent: {
      text: "text-amber-600 dark:text-amber-400",
      iconBg: "bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400",
    },
    standard: {
      text: "text-emerald-600 dark:text-emerald-400",
      iconBg: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400",
    },
    escalated: {
      text: "text-purple-600 dark:text-purple-400",
      iconBg: "bg-purple-50 text-purple-600 dark:bg-purple-950/60 dark:text-purple-400",
    },
  }[tone] || styles.default

  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-card transition-all duration-200 hover:shadow-soft dark:border-slate-800/80 dark:bg-[#121824]">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">{label}</p>
        {Icon && (
          <div className={`flex h-8 w-8 items-center justify-center rounded-xl ${styles.iconBg}`}>
            <Icon size={16} />
          </div>
        )}
      </div>
      <p className={`mt-3 text-3xl font-bold tracking-tight ${styles.text}`}>
        {value !== undefined && value !== null ? value : "—"}
      </p>
    </div>
  )
}

export default function Dashboard({ goToIntake, goToCase }) {
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [a, c] = await Promise.all([fetchAnalytics(), fetchCases(8)])
        if (!cancelled) {
          setStats(a)
          setRecent(c)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-8 py-8 space-y-8">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            Overview of intake volume and triage outcomes across all cases.
          </p>
        </div>
        <button
          type="button"
          onClick={goToIntake}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-pink-500 hover:bg-pink-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm shadow-pink-500/25 transition-all duration-150 hover:scale-[1.02] active:scale-98"
        >
          <Plus size={16} strokeWidth={2.5} />
          <span>New Intake</span>
        </button>
      </div>

      {/* Stats Cards Row */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-5">
          <StatCard label="Total Cases" value={stats.total_cases} icon={Activity} />
          <StatCard label="Emergency" value={stats.emergency_cases} tone="emergency" icon={AlertCircle} />
          <StatCard label="Urgent" value={stats.urgent_cases} tone="urgent" icon={Clock} />
          <StatCard label="Standard" value={stats.standard_cases} tone="standard" icon={CheckCircle2} />
          <StatCard label="Escalated" value={stats.escalated_cases} tone="escalated" icon={TrendingUp} />
        </div>
      )}

      {/* Emergency Alert (Rendered cleanly when acute cases exist) */}
      {stats && stats.emergency_cases > 0 && (
        <div
          onClick={() => goToCase(null)}
          className="flex items-center justify-between gap-3 rounded-2xl border border-rose-200/90 bg-rose-50/70 p-4 text-xs sm:text-sm text-rose-800 shadow-sm transition-all hover:bg-rose-50 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200 cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-rose-500 text-white">
              <Siren size={17} />
            </div>
            <div>
              <p className="font-semibold text-rose-900 dark:text-rose-100">
                {stats.emergency_cases} case{stats.emergency_cases === 1 ? "" : "s"} currently classified EMERGENCY
              </p>
              <p className="text-xs text-rose-700 dark:text-rose-300 mt-0.5">
                Confirm clinical physician evaluation has been initiated immediately.
              </p>
            </div>
          </div>
          <ArrowUpRight size={16} className="text-rose-500 shrink-0" />
        </div>
      )}

      {/* Recent Cases Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <SectionLabel>Recent Intake Cases</SectionLabel>
          <span className="text-xs text-slate-400 font-medium">Live Queue</span>
        </div>

        <Panel className="overflow-hidden divide-y divide-slate-100 dark:divide-slate-800/80">
          {loading && (
            <div className="p-8 text-center text-xs text-slate-400 animate-pulse">
              Loading recent clinical cases…
            </div>
          )}

          {!loading && recent.length === 0 && (
            <div className="p-12 text-center text-xs text-slate-400">
              No cases recorded yet. Click <strong>+ New Intake</strong> to begin triage.
            </div>
          )}

          {!loading &&
            recent.map((c) => (
              <button
                key={c.case_id}
                type="button"
                onClick={() => goToCase(c.case_id)}
                className="group flex w-full items-center justify-between px-5 py-3.5 text-left transition-colors duration-150 hover:bg-pink-50/40 dark:hover:bg-slate-800/50"
              >
                <div className="min-w-0 flex-1 pr-4">
                  <p className="truncate text-xs sm:text-sm font-semibold text-slate-900 group-hover:text-pink-600 transition-colors dark:text-white dark:group-hover:text-pink-400">
                    {c.chief_complaint || "Undescribed chief complaint"}
                  </p>
                  <p className="mt-0.5 font-mono text-[11px] text-slate-400 dark:text-slate-500">
                    {c.case_id} &middot; {formatTimestamp(c.created_at)}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  {c.department && (
                    <span className="hidden text-xs font-medium text-slate-500 sm:inline dark:text-slate-400">
                      {c.department}
                    </span>
                  )}
                  <UrgencyBadge level={c.urgency_level} size="sm" />
                  <ArrowUpRight
                    size={16}
                    className="text-slate-300 group-hover:text-pink-500 transition-colors dark:text-slate-600"
                  />
                </div>
              </button>
            ))}
        </Panel>
      </div>

      {/* Subtle Clinical Boundary Note */}
      <div className="flex items-center gap-2.5 rounded-xl bg-slate-50/60 p-3 text-[11px] text-slate-400 dark:bg-slate-900/40 dark:text-slate-500">
        <AlertTriangle size={14} className="shrink-0 text-slate-400" />
        <span>
          Decision support only. The copilot provides acuity recommendations and never diagnoses. All cases can be escalated to attending staff.
        </span>
      </div>
    </div>
  )
}
