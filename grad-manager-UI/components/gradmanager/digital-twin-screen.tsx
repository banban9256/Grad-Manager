"use client"

import { Activity, ChevronLeft, User } from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"

const CATEGORY_LABELS: Record<string, string> = {
  "전공필수": "전공필수",
  "전공선택": "전공선택",
  "교양필수": "교양필수",
  "교양선택": "교양선택",
  "계열공통": "계열공통",
}

const CATEGORY_COLORS: Record<string, string> = {
  "전공필수": "bg-[#3182f6]",
  "전공선택": "bg-[#8f5cf0]",
  "교양필수": "bg-[#00b5a3]",
  "교양선택": "bg-[#f04452]",
  "계열공통": "bg-[#ffc900]",
}

export function DigitalTwinScreen({ onBack }: { onBack: () => void }) {

  const { user, digitalTwin } = useGradData()
  const { showToast } = useToast()

  const categoryProgress = digitalTwin.categoryProgress || {}
  const specTrack = digitalTwin.specializedTrack || ""
  const convMajor = digitalTwin.convergenceMajor || ""

  return (
    <div className="relative flex h-full flex-col bg-background text-foreground overflow-y-auto md:overflow-hidden">
      {/* Light concentric radar background (TDS Style) */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-15"
        style={{
          backgroundImage:
            "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 opacity-60"
      >
        {[560, 420, 280, 150].map((size) => (
          <span
            key={size}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-primary/20"
            style={{ width: size, height: size }}
          />
        ))}
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-4 py-4 md:max-w-5xl md:mx-auto md:w-full md:px-6 shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="h-5 w-5" />
          <span className="text-base font-bold text-foreground">Digital Twin Simulation</span>
        </button>
        <button
          onClick={() => showToast("준비 중인 기능입니다.")}
          className="flex items-center gap-1.5 rounded-full bg-accent px-3 py-1.5 text-xs font-semibold text-[#1b64da] dark:text-[#5592f2] transition-colors hover:opacity-90"
        >
          <Activity className="h-3.5 w-3.5" />
          실시간 분석
        </button>
      </header>

      {/* Responsive Grid for Desktop / Flex for Mobile */}
      <div className="relative z-10 flex-1 grid grid-cols-1 md:grid-cols-12 md:max-w-5xl md:mx-auto md:w-full items-start gap-4 px-4 md:px-6 pb-6 md:pb-8 overflow-y-auto md:overflow-hidden min-h-0">
        {/* Radar Diagram - 5 Cols on Desktop */}
        <div className="md:col-span-5 flex items-center justify-center py-4 relative h-[280px] md:h-full shrink-0">
          <div className="relative flex items-center justify-center">
            {/* pulsing rings (TDS soft blue) */}
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="radar-ring absolute h-40 w-40 rounded-full border border-primary/30 bg-primary/5"
                style={{ animationDelay: `${i * 1}s` }}
              />
            ))}
            {/* glowing core */}
            <div className="core-glow relative flex h-28 w-28 flex-col items-center justify-center rounded-full border border-primary/30 bg-card shadow-sm">
              <User className="h-9 w-9 text-primary" />
              <span className="mt-1 text-sm font-bold text-foreground">{digitalTwin.name}</span>
            </div>
          </div>
        </div>

        {/* Stats & Info Cards Panel - 7 Cols on Desktop */}
        <div className="md:col-span-7 space-y-3 w-full md:overflow-y-auto md:max-h-full py-2">
          {/* Top floating stat cards */}
          <div className="flex items-start justify-between gap-3 w-full">
            <GlassCard className="flex-1">
              <p className="text-2xl font-bold text-foreground">{user.userInfo.overallProgress}%</p>
              <p className="mt-0.5 text-xs text-muted-foreground">졸업 진행률</p>
            </GlassCard>
            <GlassCard className="flex-1 text-right">
              <p className="text-2xl font-bold text-foreground">{user.userInfo.remainingCredits}학점</p>
              <p className="mt-0.5 text-xs text-muted-foreground">남은 학점</p>
            </GlassCard>
          </div>

          {/* Bottom info cards */}
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="w-1/2 rounded-2xl bg-card border border-border p-4 shadow-sm">
                <p className="text-xl font-bold text-[#00b5a3]">{digitalTwin.aiProbability}%</p>
                <p className="mt-0.5 text-xs text-muted-foreground">AI 예측 확률</p>
                <p className="mt-1 text-[10px] text-muted-foreground/60">*데이터 기반 추정*</p>
              </div>
              <div className="w-1/2 rounded-2xl bg-card border border-border p-4 shadow-sm">
                <p className="text-xl font-bold text-[#8f5cf0]">{digitalTwin.expectedGraduation}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">예상 졸업</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-2xl border border-border bg-card p-4 shadow-sm">
              <div className="border-r border-border pr-4">
                <p className="text-lg font-bold text-foreground">{digitalTwin.completedCourses}개</p>
                <p className="text-xs text-muted-foreground">이수 과목</p>
                <p className="mt-1 text-[11px] text-muted-foreground/75">
                  전공 {digitalTwin.majorCourses}, 교양 {digitalTwin.liberalCourses}
                </p>
              </div>
              <div>
                <p className="text-lg font-bold text-foreground">{digitalTwin.scenarioCount}가지</p>
                <p className="text-xs text-muted-foreground">예상 시나리오</p>
                <p className="mt-1 text-[11px] text-muted-foreground/75">{digitalTwin.scenarioStatus}</p>
              </div>
            </div>
          </div>

          {/* 카테고리별 이수 진행률 바 */}
          {Object.keys(categoryProgress).length > 0 && (
            <div className="rounded-2xl border border-border bg-card p-4 shadow-sm space-y-3">
              <p className="text-xs font-bold text-muted-foreground">카테고리별 이수 진행률</p>
              {Object.entries(categoryProgress).map(([cat, info]) => {
                const pct = info.required > 0 ? Math.min(100, Math.round((info.earned / info.required) * 100)) : 100
                const barColor = CATEGORY_COLORS[cat] || "bg-primary"
                return (
                  <div key={cat} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-foreground">{CATEGORY_LABELS[cat] || cat}</span>
                      <span className="text-[10px] text-muted-foreground">
                        {info.earned}/{info.required}학점
                        {info.remaining > 0 && <span className="text-destructive ml-1">(잔여 {info.remaining})</span>}
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${barColor}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* 특화전공/융합전공 현황 */}
          {(specTrack || convMajor) && (
            <div className="rounded-2xl border border-border bg-card p-4 shadow-sm space-y-2">
              <p className="text-xs font-bold text-muted-foreground">트랙/융합전공 이수 현황</p>
              {specTrack && (
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-foreground">특화: {specTrack}</span>
                  <span className="text-muted-foreground">
                    {digitalTwin.specializedEarned || 0}/{digitalTwin.specializedRequired || 21}학점
                  </span>
                </div>
              )}
              {convMajor && (
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-foreground">융합: {convMajor}</span>
                  <span className="text-muted-foreground">
                    {digitalTwin.convergenceEarned || 0}/{digitalTwin.convergenceRequired || 21}학점
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function GlassCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-border bg-card p-4 shadow-sm ${className}`}
    >
      {children}
    </div>
  )
}
