export const URGENCY_STYLES = {
  EMERGENCY: {
    text: "text-rose-700 dark:text-rose-300",
    bg: "bg-rose-50/80 dark:bg-rose-950/40",
    border: "border-rose-200/90 dark:border-rose-900/60",
    dot: "bg-rose-500 animate-pulse",
  },
  URGENT: {
    text: "text-amber-700 dark:text-amber-300",
    bg: "bg-amber-50/80 dark:bg-amber-950/40",
    border: "border-amber-200/90 dark:border-amber-900/60",
    dot: "bg-amber-500",
  },
  STANDARD: {
    text: "text-emerald-700 dark:text-emerald-300",
    bg: "bg-emerald-50/80 dark:bg-emerald-950/40",
    border: "border-emerald-200/90 dark:border-emerald-900/60",
    dot: "bg-emerald-500",
  },
  UNDETERMINED: {
    text: "text-slate-600 dark:text-slate-400",
    bg: "bg-slate-50/80 dark:bg-slate-900/40",
    border: "border-slate-200/80 dark:border-slate-800/60",
    dot: "bg-slate-400",
  },
}

export function UrgencyBadge({ level, size = "md" }) {
  const key = level || "UNDETERMINED"
  const style = URGENCY_STYLES[key] || URGENCY_STYLES.UNDETERMINED
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-sans font-semibold tracking-wide ${pad} ${style.bg} ${style.border} ${style.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {key}
    </span>
  )
}

export function Panel({ children, className = "" }) {
  return (
    <div
      className={`rounded-2xl border border-slate-100 bg-white shadow-card transition-all duration-200 dark:border-slate-800/80 dark:bg-[#121824] ${className}`}
    >
      {children}
    </div>
  )
}

export function SectionLabel({ children }) {
  return (
    <h3 className="mb-3 text-sm font-semibold tracking-tight text-ink-800 dark:text-ink-200">
      {children}
    </h3>
  )
}

export function formatTimestamp(ts) {
  if (!ts) return "—"
  try {
    const d = new Date(ts)
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch (_) {
    return ts
  }
}
