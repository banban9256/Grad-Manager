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
import { motion, AnimatePresence } from "framer-motion"

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
    timer.current = setTimeout(() => setLoading(false), 200)
  }

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [])

  const renderTab = () => {
    if (active === "chat") return <ChatTab onOpenSchedule={() => handleChange("schedule")} />

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
    return Tab
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f2f4f6] dark:bg-[#0f151c] p-0 sm:p-6 transition-all duration-300">
      <div className="relative flex h-screen w-full max-w-[420px] md:max-w-none flex-col overflow-hidden bg-background shadow-xl sm:h-[860px] md:h-screen sm:rounded-[2rem] md:rounded-none sm:border-[6px] md:border-0 sm:border-[#e5e8eb] dark:sm:border-[#273240] transition-all duration-300">
        <div className="flex h-full w-full overflow-hidden md:flex-row">
          <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-border md:bg-card shrink-0">
            <div className="flex h-16 items-center gap-2.5 border-b border-border px-6">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#3182f6] text-white">
                <GraduationCap className="h-5 w-5" />
              </span>
              <span className="text-lg font-bold tracking-tight text-foreground">GradManager</span>
            </div>
            <nav className="flex-1 space-y-1.5 px-4 py-6">
              {sidebarTabs.map((t) => {
                const isActive = active === t.key
                const Icon = t.icon
                return (
                  <button
                    key={t.key}
                    onClick={() => handleChange(t.key)}
                    className={`flex w-full items-center gap-3.5 rounded-2xl px-4.5 py-3 text-sm font-semibold transition-all cursor-pointer ${
                      isActive
                        ? "bg-[#3182f6] text-white shadow-md shadow-primary/15"
                        : "text-[#4e5968] dark:text-[#b0b8c1] hover:bg-[#f2f4f6] dark:hover:bg-[#212836] hover:text-foreground"
                    }`}
                  >
                    <Icon className="h-4.5 w-4.5" />
                    {t.label}
                  </button>
                )
              })}
            </nav>
            <div className="p-4 border-t border-border shrink-0">
              <button
                onClick={logout}
                className="flex w-full items-center gap-3.5 rounded-2xl px-4.5 py-3 text-sm font-semibold text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
              >
                <LogOut className="h-4.5 w-4.5" />
                로그아웃
              </button>
            </div>
          </aside>

          <div className="flex flex-1 flex-col overflow-hidden">
            <header className="flex items-center gap-2 border-b border-border bg-card px-4 py-3 md:hidden">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <GraduationCap className="h-4.5 w-4.5" />
              </span>
              <span className="text-base font-bold text-foreground">{titles[active]}</span>
            </header>

            <div className="relative min-h-0 flex-1 overflow-hidden">
              <AnimatePresence mode="wait">
                {loading ? (
                  <motion.div 
                    key="skeleton"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="h-full overflow-y-auto"
                  >
                    <TabSkeleton />
                  </motion.div>
                ) : (
                  <motion.div
                    key={active}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -16 }}
                    transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                    className="h-full overflow-y-auto"
                  >
                    {renderTab()}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="md:hidden">
              <BottomNav active={active} onChange={handleChange} />
            </div>
          </div>
        </div>

        <AnimatePresence>
          {overlay === "twin" && (
            <motion.div
              key="overlay-twin"
              initial={{ opacity: 0, y: "100%" }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: "100%" }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0 z-20"
            >
              <DigitalTwinScreen onBack={() => setOverlay(null)} />
            </motion.div>
          )}
          {overlay === "recommend" && (
            <motion.div
              key="overlay-recommend"
              initial={{ opacity: 0, y: "100%" }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: "100%" }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0 z-20"
            >
              <AiRecommendationScreen onBack={() => setOverlay(null)} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  )
}
