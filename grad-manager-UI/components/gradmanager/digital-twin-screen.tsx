"use client"

import { Activity, ChevronLeft, User } from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"

export function DigitalTwinScreen({ onBack }: { onBack: () => void }) {
  const { digitalTwin } = useGradData()
  const { showToast } = useToast()

  return (
    <div className="relative flex h-full flex-col bg-[#0B1120] text-white overflow-y-auto md:overflow-hidden">
      {/* Grid + concentric radar background */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(rgba(59,130,246,0.12) 1px, transparent 1px), linear-gradient(90deg, rgba(59,130,246,0.12) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2"
      >
        {[560, 420, 280, 150].map((size) => (
          <span
            key={size}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-500/25"
            style={{ width: size, height: size }}
          />
        ))}
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-4 py-4 md:max-w-5xl md:mx-auto md:w-full md:px-6 shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm font-medium text-white/80 transition-colors hover:text-white"
        >
          <ChevronLeft className="h-5 w-5" />
          <span className="text-base font-bold text-white">Digital Twin Simulation</span>
        </button>
        <button
          onClick={() => showToast("준비 중인 기능입니다.")}
          className="flex items-center gap-1.5 rounded-full border border-blue-400/40 bg-blue-500/15 px-3 py-1.5 text-xs font-semibold text-blue-200 transition-colors hover:bg-blue-500/25"
        >
          <Activity className="h-3.5 w-3.5" />
          실시간 분석
        </button>
      </header>

      {/* Responsive Grid for Desktop / Flex for Mobile */}
      <div className="relative z-10 flex-1 grid grid-cols-1 md:grid-cols-12 md:max-w-5xl md:mx-auto md:w-full items-center gap-6 px-4 md:px-6 pb-6 md:pb-8 overflow-y-auto md:overflow-hidden min-h-0">
        {/* Radar Diagram - 6 Cols on Desktop */}
        <div className="md:col-span-6 flex items-center justify-center py-4 relative h-[320px] md:h-full shrink-0">
          <div className="relative flex items-center justify-center">
            {/* pulsing rings */}
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="radar-ring absolute h-40 w-40 rounded-full border border-blue-400/50 bg-blue-500/10"
                style={{ animationDelay: `${i * 1}s` }}
              />
            ))}
            {/* glowing core */}
            <div className="core-glow relative flex h-28 w-28 flex-col items-center justify-center rounded-full border border-blue-300/60 bg-blue-500/25 backdrop-blur">
              <User className="h-9 w-9 text-blue-100" />
              <span className="mt-1 text-sm font-bold text-white">{digitalTwin.name}</span>
            </div>
          </div>
        </div>

        {/* Stats & Info Cards Panel - 6 Cols on Desktop */}
        <div className="md:col-span-6 space-y-4 w-full md:overflow-y-auto md:max-h-full py-2">
          {/* Top floating stat cards */}
          <div className="flex items-start justify-between gap-4 w-full">
            <GlassCard className="flex-1">
              <p className="text-2xl font-bold text-white">{digitalTwin.progress}%</p>
              <p className="mt-0.5 text-xs text-white/60">졸업 진행률</p>
            </GlassCard>
            <GlassCard className="flex-1 text-right">
              <p className="text-2xl font-bold text-white">{digitalTwin.remainingCredits}학점</p>
              <p className="mt-0.5 text-xs text-white/60">남은 학점</p>
            </GlassCard>
          </div>

          {/* Bottom info cards */}
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="w-1/2 rounded-2xl border border-teal-400/30 bg-teal-500/10 p-3">
                <p className="text-xl font-bold text-teal-300">{digitalTwin.aiProbability}%</p>
                <p className="mt-0.5 text-xs text-white/60">AI 예측 확률</p>
              </div>
              <div className="w-1/2 rounded-2xl border border-purple-400/30 bg-purple-500/10 p-3">
                <p className="text-xl font-bold text-purple-300">{digitalTwin.expectedGraduation}</p>
                <p className="mt-0.5 text-xs text-white/60">예상 졸업</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
              <div className="border-r border-white/10 pr-4">
                <p className="text-lg font-bold text-white">{digitalTwin.completedCourses}개</p>
                <p className="text-xs text-white/60">이수 과목</p>
                <p className="mt-1 text-[11px] text-white/45">
                  전공 {digitalTwin.majorCourses}, 교양 {digitalTwin.liberalCourses}
                </p>
              </div>
              <div>
                <p className="text-lg font-bold text-white">{digitalTwin.scenarioCount}가지</p>
                <p className="text-xs text-white/60">예상 시나리오</p>
                <p className="mt-1 text-[11px] text-white/45">{digitalTwin.scenarioStatus}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function GlassCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-white/10 bg-white/5 p-4 shadow-lg backdrop-blur ${className}`}
    >
      {children}
    </div>
  )
}
