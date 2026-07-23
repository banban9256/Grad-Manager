"use client"

import {
  BarChart3,
  Calendar,
  ChevronRight,
  GraduationCap,
  MessageCircleQuestion,
  Orbit,
  PencilLine,
  Sparkles,
  Trophy,
  type LucideIcon,
} from "lucide-react"
import { CircularProgress } from "./circular-progress"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { motion } from "framer-motion"

type HomeTabProps = {
  onOpenDigitalTwin: () => void
  onOpenRecommendations: () => void
}

const iconMap: Record<string, LucideIcon> = {
  Sparkles,
  GraduationCap,
  PencilLine,
  BarChart3,
  Trophy,
  MessageCircleQuestion,
  Calendar,
}

const toneVar: Record<string, string> = {
  "chart-1": "var(--chart-1)",
  "chart-2": "var(--chart-2)",
  "chart-3": "var(--chart-3)",
}

export function HomeTab({ onOpenDigitalTwin, onOpenRecommendations }: HomeTabProps) {
  const { user } = useGradData()
  const { showToast } = useToast()
  const { userInfo, creditCategories, quickMenus } = user

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6 px-4 pb-6 pt-5 md:max-w-6xl md:mx-auto md:px-6"
    >
      {/* Greeting */}
      <div>
        <p className="text-xs text-muted-foreground md:text-sm">
          {userInfo.university} · {userInfo.department}
        </p>
        <h1 className="text-2xl font-bold text-foreground md:text-3xl mt-1">
          {userInfo.name}님, 졸업 요건을 확인해 보세요
        </h1>
      </div>

      {/* Grid wrapper for responsive 2-column layout on Desktop */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-12 items-start">
        {/* Left Column: Overall Progress & Digital Twin Entry */}
        <div className="space-y-4 md:col-span-5 lg:col-span-4">
          {/* Progress hero card */}
          <section className="rounded-3xl bg-card border border-border p-5 text-foreground shadow-sm">
            <div className="flex flex-col xl:flex-row items-center justify-between gap-5 w-full">
              <div className="shrink-0 flex justify-center w-full xl:w-auto">
                <CircularProgress value={userInfo.overallProgress} label="총 졸업 진행률" />
              </div>
              <div className="flex flex-col gap-3 w-full xl:flex-1 min-w-0">
                <div className="rounded-2xl bg-secondary p-3 min-w-[140px] w-full flex flex-col justify-center">
                  <p className="text-[10px] sm:text-xs text-muted-foreground font-semibold whitespace-nowrap">남은 이수 학점</p>
                  <p className="text-xl sm:text-2xl font-bold text-foreground mt-0.5 whitespace-nowrap">
                    {userInfo.remainingCredits}
                    <span className="ml-1 text-xs font-semibold text-muted-foreground">학점</span>
                  </p>
                </div>
                <div className="flex items-center gap-2.5 rounded-2xl bg-secondary p-3 min-w-[140px] w-full">
                  <Trophy className="h-5 w-5 text-amber-500 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] sm:text-xs text-muted-foreground font-semibold whitespace-nowrap">누적 마일리지</p>
                    <p className="text-base sm:text-lg font-bold text-foreground mt-0.5 truncate whitespace-nowrap">
                      {userInfo.mileage.toLocaleString()}P
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <p className="mt-4 text-center text-xs text-muted-foreground">
              {userInfo.track} · {userInfo.earnedCredits}/{userInfo.totalRequired}학점 이수
            </p>
          </section>

          {/* Digital Twin entry */}
          <button
            onClick={onOpenDigitalTwin}
            className="flex w-full items-center gap-4 rounded-2xl bg-accent p-4.5 text-left transition-all hover:bg-opacity-85 border border-transparent cursor-pointer"
          >
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-white">
              <Orbit className="h-5.5 w-5.5" />
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[15px] font-bold text-[#1b64da] dark:text-[#5592f2]">디지털 트윈 시뮬레이션</p>
              <p className="text-xs text-[#1b64da]/80 dark:text-[#5592f2]/80 mt-0.5 truncate">AI 예측 졸업 경로를 실시간으로 확인하세요</p>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-[#1b64da] dark:text-[#5592f2]" />
          </button>
        </div>

        {/* Right Column: Category progress bars & Quick Menu grid */}
        <div className="space-y-6 md:col-span-7 lg:col-span-8">
          {/* Linear progress by category */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground">이수 구분별 진행률</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 md:grid-cols-1 lg:grid-cols-1">
              {creditCategories.map((c) => {
                const pct = Math.min(100, Math.round((c.current / c.required) * 100))
                return (
                  <div key={c.key} className="rounded-2xl bg-card border border-border p-4 shadow-sm">
                    <div className="mb-2.5 flex items-baseline justify-between">
                      <span className="text-sm font-bold text-foreground">{c.label}</span>
                      <span className="text-xs text-muted-foreground md:text-sm">
                        <span className="font-semibold text-foreground">{c.current}</span> / {c.required} 학점
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                        className="h-full rounded-full"
                        style={{ backgroundColor: toneVar[c.tone] || "var(--primary)" }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          {/* Quick menu grid */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground">빠른 메뉴</h2>
            <div className="grid grid-cols-3 gap-3 md:grid-cols-3">
              {quickMenus.map((m, idx) => {
                const Icon = iconMap[m.icon] ?? Sparkles
                return (
                  <button
                    key={m.key ? `${m.key}-${idx}` : `menu-${idx}`}
                    onClick={m.key === "recommend" ? onOpenRecommendations : () => showToast("준비 중인 기능입니다.")}
                    className="flex flex-col items-center gap-2 rounded-2xl bg-card border border-border p-4 text-center shadow-sm transition-all hover:bg-secondary hover:border-transparent cursor-pointer"
                  >
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-primary">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="text-xs font-semibold text-foreground">{m.label}</span>
                  </button>
                )
              })}
            </div>
          </section>
        </div>
      </div>
    </motion.div>
  )
}
