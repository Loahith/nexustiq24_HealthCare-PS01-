import { useEffect, useState } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts"
import { fetchAnalytics } from "../lib/api.js"
import { Panel, SectionLabel } from "../components/ui.jsx"

const URGENCY_COLORS = {
  EMERGENCY: "#E11D48",
  URGENT: "#EA580C",
  STANDARD: "#10B981",
  UNDETERMINED: "#64748B",
}

export default function Analytics() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetchAnalytics().then(setData)
  }, [])

  if (!data) {
    return (
      <div className="mx-auto max-w-6xl px-4 sm:px-8 py-8 text-xs text-slate-400 animate-pulse">
        Loading clinical analytics…
      </div>
    )
  }

  const urgencyData = [
    { name: "Emergency", value: data.emergency_cases, key: "EMERGENCY" },
    { name: "Urgent", value: data.urgent_cases, key: "URGENT" },
    { name: "Standard", value: data.standard_cases, key: "STANDARD" },
  ].filter((d) => d.value > 0)

  const deptData = Object.entries(data.department_distribution || {}).map(([name, value]) => ({
    name,
    value,
  }))

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-8 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Analytics
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
          Aggregate metrics on intake volume, urgency breakdown, and department routing.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-5">
        {[
          ["Total Cases", data.total_cases],
          ["Emergency", data.emergency_cases],
          ["Urgent", data.urgent_cases],
          ["Standard", data.standard_cases],
          ["Escalated", data.escalated_cases],
        ].map(([label, value]) => (
          <Panel key={label} className="p-4">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{label}</p>
            <p className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              {value}
            </p>
          </Panel>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel className="p-6">
          <SectionLabel>Urgency Breakdown</SectionLabel>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={urgencyData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={65}
                  outerRadius={95}
                  paddingAngle={3}
                >
                  {urgencyData.map((entry) => (
                    <Cell key={entry.key} fill={URGENCY_COLORS[entry.key]} />
                  ))}
                </Pie>
                <Legend verticalAlign="bottom" height={30} iconType="circle" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: "1rem",
                    border: "1px solid #F1F5F9",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
                    fontSize: "12px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel className="p-6">
          <SectionLabel>Department Distribution</SectionLabel>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deptData} layout="vertical" margin={{ left: 10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
                <XAxis type="number" allowDecimals={false} fontSize={11} stroke="#94A3B8" />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  fontSize={11}
                  stroke="#94A3B8"
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "rgba(236, 72, 153, 0.05)" }}
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderRadius: "1rem",
                    border: "1px solid #F1F5F9",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="value" fill="#EC4899" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
    </div>
  )
}
