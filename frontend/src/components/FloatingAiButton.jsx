import { useState } from "react"
import { Sparkles } from "lucide-react"

export default function FloatingAiButton({ onClick, currentPage }) {
  const [hovered, setHovered] = useState(false)
  const isIntake = currentPage === "intake"

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5">
      {/* Tooltip */}
      <div
        className={`pointer-events-none hidden sm:block whitespace-nowrap rounded-xl bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white shadow-lg transition-all duration-200 dark:bg-white dark:text-slate-900 ${
          hovered ? "translate-x-0 opacity-100" : "translate-x-2 opacity-0"
        }`}
      >
        <span>{isIntake ? "Active Intake Copilot" : "Ask AI Assistant"}</span>
        <span className="ml-1.5 text-[10px] text-pink-400 font-mono">24/7 Bedside</span>
      </div>

      {/* Floating Action Button */}
      <button
        type="button"
        onClick={onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        aria-label="Open Intake Copilot AI Assistant"
        className="group relative flex h-14 w-14 sm:h-16 sm:w-16 items-center justify-center rounded-full bg-gradient-to-tr from-pink-600 via-pink-500 to-pink-400 text-white shadow-glow transition-all duration-300 hover:scale-110 active:scale-95 focus:outline-none focus:ring-4 focus:ring-pink-500/30"
      >
        {/* Animated Outer Glow Ring */}
        <span className="absolute -inset-1 rounded-full bg-pink-500/30 opacity-75 blur-sm animate-pulse group-hover:opacity-100" />
        
        {/* Outer gentle ping ring */}
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-pink-400 opacity-20" />

        {/* Core Icon & Text */}
        <div className="relative flex flex-col items-center justify-center">
          <Sparkles size={20} className="transition-transform duration-300 group-hover:rotate-12" />
          <span className="mt-0.5 text-[10px] font-black uppercase tracking-wider">AI</span>
        </div>
      </button>
    </div>
  )
}
