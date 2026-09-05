import { useEffect, useState } from "react"
import { FileJson, FileText, Download } from "lucide-react"
import { fetchReports, downloadExport } from "../lib/api.js"
import { Panel, formatTimestamp } from "../components/ui.jsx"

export default function Reports() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchReports()
      .then(setReports)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-8 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Generated Reports
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          Archived clinical records, PDF exports, and JSON clinical summaries.
        </p>
      </div>

      <Panel className="overflow-hidden divide-y divide-slate-100 dark:divide-slate-800/80">
        {loading && (
          <div className="p-8 text-center text-xs text-slate-400 animate-pulse">
            Loading generated clinical reports…
          </div>
        )}
        {!loading && reports.length === 0 && (
          <div className="p-12 text-center text-xs text-slate-400">
            No exported reports yet. Complete a triage assessment to generate clinical reports.
          </div>
        )}
        {reports.map((r) => (
          <div
            key={r.report_id}
            className="flex items-center justify-between px-5 py-4 transition-colors hover:bg-slate-50/50 dark:hover:bg-slate-800/40"
          >
            <div className="flex items-center gap-3.5">
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-xl ${
                  r.format === "pdf"
                    ? "bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400"
                    : "bg-pink-50 text-pink-600 dark:bg-pink-950/60 dark:text-pink-400"
                }`}
              >
                {r.format === "pdf" ? <FileText size={18} /> : <FileJson size={18} />}
              </div>
              <div>
                <p className="font-mono text-xs font-semibold text-slate-900 dark:text-white">
                  {r.case_id}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  <span className="font-bold text-slate-500 dark:text-slate-400 uppercase">
                    {r.format}
                  </span>{" "}
                  &middot; {formatTimestamp(r.created_at)}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() =>
                downloadExport(r.format, r.case_id, `triage_report_${r.case_id}.${r.format}`)
              }
              className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-pink-300 hover:bg-pink-50 hover:text-pink-600 transition-all dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
            >
              <Download size={13} />
              <span>Download</span>
            </button>
          </div>
        ))}
      </Panel>
    </div>
  )
}
