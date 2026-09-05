import { useEffect, useState } from "react"
import Sidebar from "./components/Sidebar.jsx"
import TopBar from "./components/TopBar.jsx"
import FloatingAiButton from "./components/FloatingAiButton.jsx"
import Dashboard from "./pages/Dashboard.jsx"
import PatientIntake from "./pages/PatientIntake.jsx"
import CaseHistory from "./pages/CaseHistory.jsx"
import Reports from "./pages/Reports.jsx"
import Analytics from "./pages/Analytics.jsx"

export default function App() {
  const [page, setPage] = useState("dashboard")
  const [dark, setDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches)
  const [activeCaseId, setActiveCaseId] = useState(null)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])

  function handleSearch(q) {
    setSearchQuery(q)
    if (page !== "history") {
      setPage("history")
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#FAFAFC] dark:bg-[#0B0F17]">
      {/* Sidebar Navigation */}
      <Sidebar
        page={page}
        setPage={setPage}
        dark={dark}
        setDark={setDark}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <TopBar
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
          onSearch={handleSearch}
          currentSearch={searchQuery}
        />

        <main className="flex-1 overflow-y-auto">
          {page === "dashboard" && (
            <Dashboard
              goToIntake={() => setPage("intake")}
              goToCase={(id) => {
                setActiveCaseId(id)
                setPage("history")
              }}
            />
          )}
          {page === "intake" && <PatientIntake onCaseCreated={setActiveCaseId} />}
          {page === "history" && (
            <CaseHistory
              activeCaseId={activeCaseId}
              setActiveCaseId={setActiveCaseId}
              initialSearch={searchQuery}
            />
          )}
          {page === "reports" && <Reports />}
          {page === "analytics" && <Analytics />}
        </main>
      </div>

      {/* Always Visible Floating Action AI Button */}
      <FloatingAiButton
        currentPage={page}
        onClick={() => setPage("intake")}
      />
    </div>
  )
}
