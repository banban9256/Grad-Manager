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
    <div className="space-y-6 px-4 pb-6 pt-5 md:max-w-6xl md:mx-auto md:px-6">
      {/* Greeting */}
      <div>
        <p className="text-xs text-muted-foreground md:text-sm">
          {userInfo.university} {userInfo.department}
        </p>
        <h1 className="text-xl font-bold text-foreground md:text-2xl">
          {userInfo.name}님, 졸업까지 한 걸음 더!
        </h1>
      </div>

      {/* Grid wrapper for responsive 2-column layout on Desktop */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-12 items-start">
        {/* Left Column: Overall Progress & Digital Twin Entry */}
        <div className="space-y-4 md:col-span-5 lg:col-span-4">
          {/* Progress hero card */}
          <section className="rounded-3xl bg-navy p-5 text-navy-foreground shadow-sm">
            <div className="flex flex-col xl:flex-row items-center justify-between gap-5 w-full">
              <div className="shrink-0 flex justify-center w-full xl:w-auto">
                <CircularProgress value={userInfo.overallProgress} label="총 졸업 진행률" light />
              </div>
              <div className="flex flex-col gap-3 w-full xl:flex-1 min-w-0">
                <div className="rounded-2xl bg-white/10 p-3 min-w-[140px] w-full flex flex-col justify-center">
                  <p className="text-[10px] sm:text-xs text-navy-foreground/75 font-medium whitespace-nowrap">남은 이수 학점</p>
                  <p className="text-xl sm:text-2xl font-extrabold text-white mt-1 whitespace-nowrap">
                    {userInfo.remainingCredits}
                    <span className="ml-1 text-xs font-semibold text-navy-foreground/75">학점</span>
                  </p>
                </div>
                <div className="flex items-center gap-2.5 rounded-2xl bg-white/10 p-3 min-w-[140px] w-full">
                  <Trophy className="h-5 w-5 text-amber-300 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-[10px] sm:text-xs text-navy-foreground/75 font-medium whitespace-nowrap">누적 마일리지</p>
                    <p className="text-base sm:text-lg font-extrabold text-white mt-0.5 truncate whitespace-nowrap">
                      {userInfo.mileage.toLocaleString()}P
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <p className="mt-4 text-center text-xs text-navy-foreground/70">
              {userInfo.track} · {userInfo.earnedCredits}/{userInfo.totalRequired}학점 이수
            </p>
          </section>

          {/* Digital Twin entry */}
          <button
            onClick={onOpenDigitalTwin}
            className="flex w-full items-center gap-3 rounded-2xl border border-primary/20 bg-accent p-4 text-left transition-colors hover:bg-accent/70"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <Orbit className="h-5 w-5" />
            </span>
            <div className="flex-1">
              <p className="text-sm font-bold text-foreground">디지털 트윈 시뮬레이션</p>
              <p className="text-xs text-muted-foreground">AI 예측 졸업 경로를 실시간으로 확인하세요</p>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground" />
          </button>
        </div>

        {/* Right Column: Category progress bars & Quick Menu grid */}
        <div className="space-y-6 md:col-span-7 lg:col-span-8">
          {/* Linear progress by category */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-foreground">이수 구분별 진행률</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 md:grid-cols-1 lg:grid-cols-1">
              {creditCategories.map((c) => {
                const pct = Math.round((c.current / c.required) * 100)
                return (
                  <div key={c.key} className="rounded-2xl bg-card p-4 shadow-sm">
                    <div className="mb-2 flex items-baseline justify-between">
                      <span className="text-sm font-medium text-foreground">{c.label}</span>
                      <span className="text-xs text-muted-foreground md:text-sm">
                        <span className="font-semibold text-foreground">{c.current}</span> / {c.required} 학점
                      </span>
                    </div>
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full transition-[width] duration-700 ease-out"
                        style={{ width: `${pct}%`, backgroundColor: toneVar[c.tone] }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          {/* Quick menu grid */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-foreground">빠른 메뉴</h2>
            <div className="grid grid-cols-3 gap-3 md:grid-cols-3">
              {quickMenus.map((m) => {
                const Icon = iconMap[m.icon] ?? Sparkles
                return (
                  <button
                    key={m.key}
                    onClick={m.key === "recommend" ? onOpenRecommendations : () => showToast("준비 중인 기능입니다.")}
                    className="flex flex-col items-center gap-2 rounded-2xl bg-card p-4 text-center shadow-sm transition-colors hover:bg-accent"
                  >
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-accent-foreground">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="text-xs font-medium text-foreground">{m.label}</span>
                  </button>
                )
              })}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
