import { useEffect, useState } from "react"
import { Download, User, ShieldCheck, FileText, Search } from "lucide-react"
import { fetchCases, fetchCaseDetail, downloadExport } from "../lib/api.js"
import { Panel, UrgencyBadge, formatTimestamp } from "../components/ui.jsx"

export default function CaseHistory({ activeCaseId, setActiveCaseId, initialSearch = "" }) {
  const [cases, setCases] = useState([])
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState("ALL")
  const [searchQuery, setSearchQuery] = useState(initialSearch)

  useEffect(() => {
    fetchCases(300)
      .then(setCases)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (activeCaseId) {
      fetchCaseDetail(activeCaseId).then(setDetail)
    }
  }, [activeCaseId])

  const filtered = cases.filter((c) => {
    const matchesFilter = filter === "ALL" || c.urgency_level === filter
    const matchesSearch =
      !searchQuery ||
      (c.chief_complaint && c.chief_complaint.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.case_id && c.case_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.department && c.department.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesFilter && matchesSearch
  })

  return (
    <div className="mx-auto grid h-full max-w-6xl grid-cols-1 gap-6 px-4 sm:px-8 py-8 lg:grid-cols-[360px_1fr]">
      {/* Left Column: Filter & Case List */}
      <div className="space-y-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Case History
          </h1>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            {cases.length} clinical cases recorded in archive
          </p>
        </div>

        {/* Search input */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter cases by symptom or ID…"
            className="h-9 w-full rounded-xl border border-slate-200/80 bg-white pl-9 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:border-pink-500 focus:outline-none dark:border-slate-800 dark:bg-[#121824] dark:text-white"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-1">
          {["ALL", "EMERGENCY", "URGENT", "STANDARD", "UNDETERMINED"].map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`rounded-full px-2.5 py-1 text-[10px] font-semibold tracking-wide transition-all ${
                filter === f
                  ? "bg-pink-500 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-pink-50 hover:text-pink-600 dark:bg-slate-800 dark:text-slate-400"
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Cases List */}
        <Panel className="max-h-[calc(100vh-16rem)] divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800/80">
          {loading && (
            <div className="p-8 text-center text-xs text-slate-400 animate-pulse">
              Loading case records…
            </div>
          )}
          {!loading && filtered.length === 0 && (
            <div className="p-8 text-center text-xs text-slate-400">
              No cases match your filters.
            </div>
          )}
          {filtered.map((c) => {
            const isSelected = activeCaseId === c.case_id
            return (
              <button
                key={c.case_id}
                type="button"
                onClick={() => setActiveCaseId(c.case_id)}
                className={`block w-full px-4 py-3 text-left transition-colors duration-150 ${
                  isSelected
                    ? "bg-pink-50/70 border-l-4 border-pink-500 dark:bg-pink-950/30"
                    : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                }`}
              >
                <p className="truncate text-xs font-semibold text-slate-900 dark:text-white">
                  {c.chief_complaint || "Unspecified complaint"}
                </p>
                <div className="mt-1 flex items-center justify-between">
                  <span className="font-mono text-[10px] text-slate-400">
                    {formatTimestamp(c.created_at)}
                  </span>
                  <UrgencyBadge level={c.urgency_level} size="sm" />
                </div>
              </button>
            )
          })}
        </Panel>
      </div>

      {/* Right Column: Case Details */}
      <div>
        {!detail && (
          <Panel className="flex h-72 flex-col items-center justify-center p-8 text-center text-slate-400">
            <p className="text-xs">Select any case from the list on the left to inspect details.</p>
          </Panel>
        )}
        {detail && <CaseDetailView detail={detail} />}
      </div>
    </div>
  )
}

function CaseDetailView({ detail }) {
  const { case: c, conversation, triage } = detail
  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Overview Card */}
      <Panel className="p-5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
          <div>
            <p className="font-mono text-[11px] text-slate-400">{c.case_id}</p>
            <h2 className="mt-1 text-base font-bold text-slate-900 dark:text-white">
              {c.chief_complaint || "Chief complaint"}
            </h2>
          </div>
          <UrgencyBadge level={c.urgency_level} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4 border-t border-slate-100 pt-3 dark:border-slate-800">
          <div>
            <p className="text-[10px] font-semibold text-slate-400">Department</p>
            <p className="font-medium text-slate-800 dark:text-slate-200">{c.department || "—"}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-slate-400">Status</p>
            <p className="font-medium capitalize text-slate-800 dark:text-slate-200">{c.status}</p>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-slate-400">Escalated</p>
            <p className="font-medium text-slate-800 dark:text-slate-200">
              {c.escalation_required ? "Yes" : "No"}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold text-slate-400">Recorded</p>
            <p className="font-medium text-slate-800 dark:text-slate-200">{formatTimestamp(c.updated_at)}</p>
          </div>
        </div>

        <div className="mt-4 flex gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
          <button
            type="button"
            onClick={() => downloadExport("pdf", c.case_id, `triage_report_${c.case_id}.pdf`)}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <FileText size={13} className="text-rose-500" /> Export PDF
          </button>
          <button
            type="button"
            onClick={() => downloadExport("json", c.case_id, `triage_report_${c.case_id}.json`)}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Download size={13} className="text-pink-500" /> Export JSON
          </button>
        </div>
      </Panel>

      {/* Clinical Reasoning */}
      {triage && (
        <Panel className="p-5">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Clinical Reasoning & Evidence
          </p>
          <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
            {triage.reasoning}
          </p>
        </Panel>
      )}

      {/* Transcript */}
      <Panel className="p-5">
        <p className="mb-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Intake Conversation Transcript
        </p>
        <div className="space-y-3">
          {conversation
            .filter((t) => t.role === "patient" || t.role === "assistant")
            .map((t) => (
              <div
                key={t.turn_id}
                className={`flex gap-2.5 ${t.role === "patient" ? "flex-row-reverse" : ""}`}
              >
                <div
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                    t.role === "patient"
                      ? "bg-slate-800 text-white dark:bg-slate-700"
                      : "bg-pink-500 text-white shadow-sm"
                  }`}
                >
                  {t.role === "patient" ? <User size={11} /> : <ShieldCheck size={11} />}
                </div>
                <div
                  className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed ${
                    t.role === "patient"
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "bg-pink-50/70 border border-pink-100 text-slate-800 dark:bg-pink-950/30 dark:border-pink-900/40 dark:text-slate-200"
                  }`}
                >
                  {t.message}
                </div>
              </div>
            ))}
        </div>
      </Panel>
    </div>
  )
}
