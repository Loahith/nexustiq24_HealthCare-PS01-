import { useEffect, useRef, useState, useCallback } from "react"
import {
  Send,
  User,
  ShieldCheck,
  Download,
  Sparkles,
  RotateCcw,
  CheckCircle2,
  Settings,
  Activity,
  ChevronDown,
  ChevronUp,
  X,
  ShieldAlert,
  FileText,
  Zap,
} from "lucide-react"
import { sendChatMessage, downloadExport, getSettings, updateAiKey } from "../lib/api.js"
import { UrgencyBadge } from "../components/ui.jsx"

const STARTER_PROMPTS = [
  { label: "Chest Discomfort", text: "I have severe chest tightness and shortness of breath." },
  { label: "Migraine / Head", text: "I have an intense, throbbing migraine with vision changes and nausea." },
  { label: "Allergic Reaction", text: "I ate peanuts and my lips are swelling with hives across my chest." },
  { label: "Eye Irritation", text: "Chemical cleaning spray accidentally splashed directly into my left eye." },
  { label: "Fever / Chills", text: "I have had a high fever for four days with severe body aches." },
  { label: "Abdominal Pain", text: "Severe sharp abdominal pain in my lower right side with nausea." },
]

export default function PatientIntake({ onCaseCreated }) {
  const [caseId, setCaseId] = useState(null)
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello, I am your clinical intake copilot. Please describe what you are experiencing today in your own words — including your main symptoms, when they began, and how severe they feel.",
      options: [],
    },
  ])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [triage, setTriage] = useState(null)
  const scrollRef = useRef(null)

  // Clinical Profile & Vitals State
  const [profileOpen, setProfileOpen] = useState(false)
  const [patientName, setPatientName] = useState("")
  const [age, setAge] = useState("")
  const [sex, setSex] = useState("")
  const [medicalHistory, setMedicalHistory] = useState("")
  const [allergies, setAllergies] = useState("")
  const [temperature, setTemperature] = useState("")
  const [spo2, setSpo2] = useState("")
  const [bloodPressure, setBloodPressure] = useState("")
  const [heartRate, setHeartRate] = useState("")

  // AI Settings & Key Modal State
  const [aiModalOpen, setAiModalOpen] = useState(false)
  const [aiSettings, setAiSettings] = useState(null)
  const [keyInput, setKeyInput] = useState("")
  const [aiConnecting, setAiConnecting] = useState(false)
  const [aiFeedback, setAiFeedback] = useState(null)

  const loadSettings = useCallback(async () => {
    try {
      const data = await getSettings()
      setAiSettings(data)
    } catch {
      setAiSettings({
        gemini_enabled: false,
        has_api_key: false,
        model_name: "gemini-1.5-flash",
        active_mode: "universal_clinical_fallback",
      })
    }
  }, [])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, sending])

  async function handleSaveKey(e) {
    e?.preventDefault()
    setAiConnecting(true)
    setAiFeedback(null)
    try {
      const res = await updateAiKey(keyInput.trim())
      setAiFeedback({ success: res.success, message: res.message })
      if (res.status) {
        setAiSettings(res.status)
      }
      if (res.success) {
        setTimeout(() => {
          setAiModalOpen(false)
          setAiFeedback(null)
        }, 1200)
      }
    } catch (err) {
      setAiFeedback({ success: false, message: err.message || "Failed to update API key" })
    } finally {
      setAiConnecting(false)
    }
  }

  function toggleChip(currentStr, setStr, chipValue) {
    const items = currentStr
      ? currentStr.split(",").map((s) => s.trim()).filter(Boolean)
      : []
    const exists = items.includes(chipValue)
    const updated = exists ? items.filter((i) => i !== chipValue) : [...items, chipValue]
    setStr(updated.join(", "))
  }

  async function submit(text, displayLabel) {
    const trimmed = (text || "").trim()
    if (!trimmed || sending) return

    const userText = displayLabel || trimmed
    setMessages((m) => [...m, { role: "patient", text: userText }])
    setInput("")
    setSending(true)

    // Assemble vitals dictionary
    const vitalsObj = {}
    if (temperature.trim()) vitalsObj.temperature = parseFloat(temperature.trim())
    if (spo2.trim()) vitalsObj.spo2 = parseFloat(spo2.trim())
    if (bloodPressure.trim()) vitalsObj.blood_pressure = bloodPressure.trim()
    if (heartRate.trim()) vitalsObj.heart_rate = parseFloat(heartRate.trim())

    const payload = {
      case_id: caseId,
      message: trimmed,
      patient_name: patientName.trim() || undefined,
      age: age ? parseInt(age, 10) : undefined,
      sex: sex || undefined,
      medical_history: medicalHistory.trim() || undefined,
      allergies: allergies.trim() || undefined,
      vitals: Object.keys(vitalsObj).length > 0 ? vitalsObj : undefined,
    }

    try {
      const res = await sendChatMessage(payload)
      if (!caseId) {
        setCaseId(res.case_id)
        onCaseCreated?.(res.case_id)
      }
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: res.assistant_message,
          options: res.options || [],
          currentQuestion: res.current_question,
        },
      ])
      if (res.triage) {
        setTriage(res.triage)
      }
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: `Connection error reaching copilot: ${err.message}. Please try again or notify clinical staff.`,
          options: [],
        },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleReset() {
    setCaseId(null)
    setTriage(null)
    setInput("")
    setMessages([
      {
        role: "assistant",
        text: "Hello, I am your clinical intake copilot. Please describe what you are experiencing today in your own words — including your main symptoms, when they began, and how severe they feel.",
        options: [],
      },
    ])
  }

  const hasVitals = temperature || spo2 || bloodPressure || heartRate
  const isGeminiLive = aiSettings?.gemini_enabled

  return (
    <div className="mx-auto flex h-[calc(100vh-4.25rem)] max-w-4xl flex-col px-4 sm:px-6 py-4 space-y-3">
      {/* Top Header & Tidy Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Intake Copilot
          </h1>
          {isGeminiLive ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-300 ring-1 ring-emerald-500/30">
              <Zap size={11} className="animate-pulse text-emerald-600 dark:text-emerald-400" />
              Gemini Live
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-pink-50 px-2.5 py-0.5 text-[11px] font-semibold text-pink-700 dark:bg-pink-950/70 dark:text-pink-300 ring-1 ring-pink-500/20">
              <ShieldCheck size={11} />
              Universal AI
            </span>
          )}

          {caseId && (
            <span className="hidden sm:inline-flex font-mono text-xs text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md">
              {caseId}
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setProfileOpen((o) => !o)}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-all ${
              profileOpen || hasVitals || patientName
                ? "border-pink-300 bg-pink-50 text-pink-700 dark:border-pink-800 dark:bg-pink-950/50 dark:text-pink-300"
                : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:bg-[#121824] dark:text-slate-300"
            }`}
          >
            <Activity size={13} />
            <span>Profile & Vitals</span>
            {hasVitals && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />}
            {profileOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          <button
            type="button"
            onClick={() => setAiModalOpen(true)}
            className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors dark:border-slate-800 dark:bg-[#121824] dark:text-slate-300"
          >
            <Settings size={13} />
            <span className="hidden sm:inline">AI Settings</span>
          </button>

          {caseId && (
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors dark:border-slate-800 dark:bg-[#121824] dark:text-slate-300"
            >
              <RotateCcw size={13} />
              <span>New Case</span>
            </button>
          )}
        </div>
      </div>

      {/* Collapsible Profile & Vitals Card (Clean, uncrowded) */}
      {profileOpen && (
        <div className="shrink-0 rounded-2xl border border-pink-100 bg-white p-4 shadow-card dark:border-slate-800 dark:bg-[#121824] animate-fadeIn">
          <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2 dark:border-slate-800">
            <span className="text-xs font-bold text-slate-900 dark:text-white">
              Optional Patient Profile & Vital Signs
            </span>
            <button
              onClick={() => setProfileOpen(false)}
              className="text-xs font-medium text-pink-600 hover:underline"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <label className="text-[10px] font-semibold text-slate-400">Patient Name</label>
              <input
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                placeholder="e.g. Sarah Jenkins"
                className="mt-0.5 h-8 w-full rounded-lg border border-slate-200 bg-slate-50/50 px-2.5 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-slate-400">Age & Sex</label>
              <div className="mt-0.5 flex gap-1.5">
                <input
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  placeholder="Age"
                  type="number"
                  className="h-8 w-16 rounded-lg border border-slate-200 bg-slate-50/50 px-2 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
                <select
                  value={sex}
                  onChange={(e) => setSex(e.target.value)}
                  className="h-8 flex-1 rounded-lg border border-slate-200 bg-slate-50/50 px-2 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  <option value="">Sex</option>
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-[10px] font-semibold text-slate-400">Temp (°F) & SpO2 (%)</label>
              <div className="mt-0.5 flex gap-1.5">
                <input
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                  placeholder="98.6"
                  className="h-8 w-1/2 rounded-lg border border-slate-200 bg-slate-50/50 px-2 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
                <input
                  value={spo2}
                  onChange={(e) => setSpo2(e.target.value)}
                  placeholder="SpO2"
                  className="h-8 w-1/2 rounded-lg border border-slate-200 bg-slate-50/50 px-2 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </div>
            </div>
            <div>
              <label className="text-[10px] font-semibold text-slate-400">BP & Pulse (bpm)</label>
              <div className="mt-0.5 flex gap-1.5">
                <input
                  value={bloodPressure}
                  onChange={(e) => setBloodPressure(e.target.value)}
                  placeholder="120/80"
                  className="h-8 w-1/2 rounded-lg border border-slate-200 bg-slate-50/50 px-2 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
                <input
                  value={heartRate}
                  onChange={(e) => setHeartRate(e.target.value)}
                  placeholder="HR"
                  className="h-8 w-1/2 rounded-lg border border-slate-200 bg-slate-50/50 px-2 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </div>
            </div>

            <div className="col-span-2 sm:col-span-4 grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
              <div>
                <label className="text-[10px] font-semibold text-slate-400">Past Medical History</label>
                <input
                  value={medicalHistory}
                  onChange={(e) => setMedicalHistory(e.target.value)}
                  placeholder="e.g. Asthma, Hypertension"
                  className="mt-0.5 h-8 w-full rounded-lg border border-slate-200 bg-slate-50/50 px-2.5 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-400">Known Allergies</label>
                <input
                  value={allergies}
                  onChange={(e) => setAllergies(e.target.value)}
                  placeholder="e.g. Penicillin, Peanuts"
                  className="mt-0.5 h-8 w-full rounded-lg border border-slate-200 bg-slate-50/50 px-2.5 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Chat & Intake Container */}
      <div className="flex flex-1 flex-col overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-card dark:border-slate-800/80 dark:bg-[#121824]">
        {/* Step Indicator Header */}
        {!triage && (
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-2.5 text-xs dark:border-slate-800">
            <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
              <span className="h-2 w-2 rounded-full bg-pink-500 animate-pulse" />
              <span>Assessing Seriousness & Clinical Acuity</span>
            </div>
            <span className="font-mono text-[11px] text-slate-400">
              Step {Math.min(messages.filter((m) => m.role === "patient").length + 1, 4)} of ~4
            </span>
          </div>
        )}

        {/* Scrollable Messages Stream */}
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
          {messages.map((m, i) => {
            const isLatestAssistant = m.role === "assistant" && i === messages.length - 1
            const hasOptions = m.options && m.options.length > 0

            return (
              <div
                key={i}
                className={`flex flex-col ${m.role === "patient" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`flex gap-3 max-w-[85%] ${
                    m.role === "patient" ? "flex-row-reverse" : ""
                  }`}
                >
                  <div
                    className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                      m.role === "patient"
                        ? "bg-slate-800 text-white dark:bg-slate-700"
                        : "bg-pink-500 text-white shadow-sm shadow-pink-500/25"
                    }`}
                  >
                    {m.role === "patient" ? <User size={13} /> : <Sparkles size={13} />}
                  </div>

                  <div
                    className={`rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed ${
                      m.role === "patient"
                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                        : "bg-pink-50/70 border border-pink-100 text-slate-800 dark:bg-pink-950/30 dark:border-pink-900/40 dark:text-slate-100"
                    }`}
                  >
                    {m.text}
                  </div>
                </div>

                {/* Quick Choice Option Pills */}
                {isLatestAssistant && hasOptions && !triage && !sending && (
                  <div className="ml-10 mt-3 max-w-[85%] animate-fadeIn">
                    <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                      <CheckCircle2 size={12} className="text-pink-500" />
                      <span>Choose an option or type below:</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {m.options.map((opt, optIdx) => (
                        <button
                          key={optIdx}
                          type="button"
                          disabled={sending}
                          onClick={() => submit(opt.value, opt.label)}
                          className="rounded-full border border-pink-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition-all duration-150 hover:border-pink-500 hover:bg-pink-500 hover:text-white active:scale-95 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-pink-600"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          {sending && (
            <div className="flex items-center gap-2 pl-10 text-xs text-slate-400">
              <span className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-pink-500" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-pink-500 [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-pink-500 [animation-delay:300ms]" />
              </span>
              <span>Evaluating symptoms & clinical safety…</span>
            </div>
          )}

          {/* Triage Outcome Card (Appears cleanly upon triage conclusion) */}
          {triage && (
            <div className="mt-4 rounded-2xl border border-pink-200 bg-gradient-to-br from-white to-pink-50/40 p-5 shadow-sm dark:border-slate-700 dark:from-[#121824] dark:to-pink-950/20 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={18} className="text-pink-600 dark:text-pink-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                    Triage Recommendation
                  </span>
                </div>
                <UrgencyBadge level={triage.urgency_level} />
              </div>

              <div className="mt-3">
                <p className="text-base font-bold text-slate-900 dark:text-white">
                  {triage.recommended_department}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                  {triage.reasoning}
                </p>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() =>
                    downloadExport("pdf", caseId, `triage_report_${caseId}.pdf`)
                  }
                  className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  <FileText size={13} className="text-rose-500" />
                  <span>Download PDF</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    downloadExport("json", caseId, `triage_report_${caseId}.json`)
                  }
                  className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  <Download size={13} className="text-pink-500" />
                  <span>Export JSON</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Example Starter Pills (shown only initially) */}
        {messages.length === 1 && (
          <div className="border-t border-slate-100 bg-slate-50/50 px-5 py-3 dark:border-slate-800 dark:bg-slate-900/30">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Quick Test Prompts:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {STARTER_PROMPTS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => submit(p.text)}
                  className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:border-pink-300 hover:bg-pink-50 hover:text-pink-600 transition-colors dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            submit(input)
          }}
          className="flex items-center gap-2 border-t border-slate-100 bg-white p-3 dark:border-slate-800 dark:bg-[#121824]"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={sending}
            placeholder="Type your symptoms or answer here…"
            className="flex-1 rounded-full border border-slate-200 bg-slate-50/60 px-4 py-2.5 text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:border-pink-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-pink-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:placeholder-slate-500"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-pink-500 text-white shadow-sm transition-all hover:bg-pink-600 active:scale-95 disabled:opacity-40"
          >
            <Send size={15} />
          </button>
        </form>
      </div>

      {/* AI Mode Configuration Modal */}
      {aiModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm"
            onClick={() => setAiModalOpen(false)}
          />
          <div className="relative z-10 w-full max-w-md rounded-2xl border border-slate-100 bg-white p-6 shadow-soft dark:border-slate-800 dark:bg-[#121824] animate-fadeIn">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
              <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-white">
                <Sparkles size={16} className="text-pink-500" />
                <span>Google Gemini AI Settings</span>
              </div>
              <button
                type="button"
                onClick={() => setAiModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveKey} className="mt-4 space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Gemini API Key
                </label>
                <input
                  type="password"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                  placeholder="AIzaSy..."
                  className="mt-1 h-9 w-full rounded-xl border border-slate-200 px-3 text-xs text-slate-800 focus:border-pink-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
                <p className="mt-1 text-[11px] text-slate-400">
                  Optional. When not configured, the system uses the offline universal clinical engine.
                </p>
              </div>

              {aiFeedback && (
                <div
                  className={`rounded-xl p-3 text-xs ${
                    aiFeedback.success
                      ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200"
                      : "bg-rose-50 text-rose-800 dark:bg-rose-950/50 dark:text-rose-200"
                  }`}
                >
                  {aiFeedback.message}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setAiModalOpen(false)}
                  className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={aiConnecting || !keyInput.trim()}
                  className="rounded-xl bg-pink-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-pink-600 disabled:opacity-50"
                >
                  {aiConnecting ? "Connecting…" : "Save Key"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
