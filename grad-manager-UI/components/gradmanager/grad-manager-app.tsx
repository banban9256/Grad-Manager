"use client"

import { useEffect, useRef, useState } from "react"
import { GraduationCap, Home, Sparkles, CalendarRange, Bell, LogOut, User } from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { BottomNav, type TabKey } from "./bottom-nav"
import { HomeTab } from "./home-tab"
import { ChatTab } from "./chat-tab"
import { ScheduleTab } from "./schedule-tab"
import { NoticeTab } from "./notice-tab"
import { ProfileTab } from "./profile-tab"
import { TabSkeleton } from "./tab-skeleton"
import { DigitalTwinScreen } from "./digital-twin-screen"
import { AiRecommendationScreen } from "./ai-recommendation-screen"

type Overlay = "twin" | "recommend" | null

const titles: Record<TabKey, string> = {
  home: "GradManager",
  chat: "AI 추천",
  schedule: "시간표",
  notice: "알림",
  profile: "마이페이지",
}

const sidebarTabs = [
  { key: "home" as const, label: "홈 대시보드", icon: Home },
  { key: "chat" as const, label: "AI 수강 추천", icon: Sparkles },
  { key: "schedule" as const, label: "추천 시간표", icon: CalendarRange },
  { key: "notice" as const, label: "공지 & 알림", icon: Bell },
  { key: "profile" as const, label: "마이페이지", icon: User },
]

export function GradManagerApp() {
  const { logout } = useGradData()
  const [active, setActive] = useState<TabKey>("home")
  const [loading, setLoading] = useState(false)
  const [overlay, setOverlay] = useState<Overlay>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleChange = (key: TabKey) => {
    if (key === active) return
    setActive(key)
    setLoading(true)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setLoading(false), 500)
  }

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [])

  const renderTab = () => {
    // Chat manages its own full-height layout (fixed input bar)
    if (active === "chat") return <ChatTab />

    const Tab =
      active === "home" ? (
        <HomeTab
          onOpenDigitalTwin={() => setOverlay("twin")}
          onOpenRecommendations={() => setOverlay("recommend")}
        />
      ) : active === "schedule" ? (
        <ScheduleTab />
      ) : active === "profile" ? (
        <ProfileTab />
      ) : (
        <NoticeTab />
      )
    return <div className="h-full overflow-y-auto">{Tab}</div>
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy p-0 md:p-0 sm:p-6 transition-all duration-300">
      {/* Container - acts as mobile mock on mobile/tablet, expands to full-screen on desktop */}
      <div className="relative flex h-screen w-full max-w-[420px] md:max-w-none flex-col overflow-hidden bg-background shadow-2xl sm:h-[860px] md:h-screen sm:rounded-[2.5rem] md:rounded-none sm:border-8 md:border-0 sm:border-navy transition-all duration-300">
        <div className="flex h-full w-full overflow-hidden md:flex-row">
          {/* Desktop Left Sidebar (Hidden on Mobile) */}
          <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-border md:bg-card shrink-0">
            <div className="flex h-16 items-center gap-2.5 border-b border-border px-6">
              <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
                <GraduationCap className="h-5 w-5" />
              </span>
              <span className="text-lg font-bold text-foreground">GradManager</span>
            </div>
            <nav className="flex-1 space-y-1.5 px-4 py-6">
              {sidebarTabs.map((t) => {
                const isActive = active === t.key
                const Icon = t.icon
                return (
                  <button
                    key={t.key}
                    onClick={() => handleChange(t.key)}
                    className={`flex w-full items-center gap-3.5 rounded-2xl px-4.5 py-3 text-sm font-semibold transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    <Icon className="h-4.5 w-4.5" />
                    {t.label}
                  </button>
                )
              })}
            </nav>
            {/* Sidebar Footer Logout Button */}
            <div className="p-4 border-t border-border shrink-0">
              <button
                onClick={logout}
                className="flex w-full items-center gap-3.5 rounded-2xl px-4.5 py-3 text-sm font-semibold text-destructive hover:bg-destructive/10 transition-colors"
              >
                <LogOut className="h-4.5 w-4.5" />
                로그아웃
              </button>
            </div>
          </aside>

          {/* Right Main Content Panel */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Mobile Header (Hidden on Desktop) */}
            <header className="flex items-center gap-2 border-b border-border bg-card px-4 py-3 md:hidden">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <GraduationCap className="h-5 w-5" />
              </span>
              <span className="text-base font-bold text-foreground">{titles[active]}</span>
            </header>

            {/* Scrollable Content View */}
            <div className="relative min-h-0 flex-1 overflow-hidden">
              {loading ? (
                <div className="h-full overflow-y-auto">
                  <TabSkeleton />
                </div>
              ) : (
                renderTab()
              )}
            </div>

            {/* Mobile Bottom Navigation (Hidden on Desktop) */}
            <div className="md:hidden">
              <BottomNav active={active} onChange={handleChange} />
            </div>
          </div>
        </div>

        {/* Full-frame overlays (Adaptive within the main window) */}
        {overlay === "twin" && (
          <div className="absolute inset-0 z-20">
            <DigitalTwinScreen onBack={() => setOverlay(null)} />
          </div>
        )}
        {overlay === "recommend" && (
          <div className="absolute inset-0 z-20">
            <AiRecommendationScreen onBack={() => setOverlay(null)} />
          </div>
        )}
      </div>
    </main>
  )
}
