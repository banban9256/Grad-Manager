"use client"

import { useState, useEffect } from "react"
import { BrainCircuit, CalendarOff, Clock, GraduationCap, Sparkles, X, type LucideIcon } from "lucide-react"
import { useGradData } from "./grad-data-provider"

const reasonIconMap: Record<string, LucideIcon> = {
  CalendarOff,
  BrainCircuit,
  GraduationCap,
  Clock,
  Sparkles,
}

const ROW_H = 52 // px per hour row

const dayStringToNum = (dayVal: any): number => {
  if (typeof dayVal === "number") return dayVal
  if (typeof dayVal !== "string") return -1
  
  const clean = dayVal.trim().toUpperCase()
  const mapping: Record<string, number> = {
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4,
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4,
    "MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3, "FRIDAY": 4
  }
  return mapping[clean] !== undefined ? mapping[clean] : -1
}

export function ScheduleTab() {
  const { schedule, refreshData, simulatedSchedule, resetSimulation } = useGradData()

  useEffect(() => {
    // 탭 진입 시 최신 개인화 시간표 갱신 호출
    if (refreshData) {
      refreshData()
    }
  }, [])

  const activeSchedule = simulatedSchedule || schedule
  const showBanner = simulatedSchedule !== null

  const handleCloseBanner = () => {
    if (resetSimulation) {
      resetSimulation()
    }
  }

  const { pastelPalette, scheduleBlocks, scheduleDays, scheduleHours, scheduleReasons } = activeSchedule

  // 동적 통계 데이터 계산
  const uniqueCourses = Array.from(new Set(scheduleBlocks.map((b) => b.name)))
  const courseCount = uniqueCourses.length

  const activeDays = new Set(scheduleBlocks.map((b) => dayStringToNum(b.day)))
  const freeDays = scheduleDays.filter((_, idx) => !activeDays.has(idx))
  const freeDayText = freeDays.length > 0 ? `${freeDays.join(", ")} 공강` : "공강 없음"

  // 추천 이유 목록 구성
  const dynamicReasons = scheduleReasons || []

  return (
    <div className="space-y-6 px-4 pb-6 pt-5 md:max-w-6xl md:mx-auto md:px-6">
      {showBanner && (
        <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#e8f3ff] dark:bg-[#182945] px-5 py-3.5 border border-[#3182f6]/20 shadow-sm transition-all duration-300">
          <div className="flex items-center gap-2.5">
            <Sparkles className="h-5 w-5 text-[#3182f6] shrink-0 animate-pulse" />
            <p className="text-xs sm:text-sm font-semibold text-[#1b64da] dark:text-[#5592f2]">
              최근 챗봇 대화 추천(선호 요일/기피 시간 등)을 적극 반영하여 생성된 개인화 시간표 결과입니다.
            </p>
          </div>
          <button
            onClick={handleCloseBanner}
            className="text-[#1b64da] dark:text-[#5592f2] hover:bg-black/5 dark:hover:bg-white/5 rounded-full p-1.5 transition-colors cursor-pointer"
          >
            <X className="h-4.5 w-4.5" />
          </button>
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-foreground">추천 시간표</h1>
        <p className="text-sm text-muted-foreground mt-0.5">{freeDayText} · 총 {courseCount}개 과목 추천</p>
      </div>

      {/* Timetable grid */}
      <section className="rounded-2xl bg-card border border-border p-3.5 shadow-sm">
        <div className="grid grid-cols-[28px_repeat(5,1fr)]">
          {/* header row */}
          <div />
          {scheduleDays.map((d, i) => (
            <div
              key={d}
              className={`pb-2.5 text-center text-xs font-bold ${
                i === 4 ? "text-muted-foreground/50" : "text-foreground"
              }`}
            >
              {d}
            </div>
          ))}

          {/* time label column */}
          <div className="relative">
            {scheduleHours.map((h) => (
              <div
                key={h}
                className="text-right text-[10px] text-muted-foreground font-semibold"
                style={{ height: ROW_H }}
              >
                {h}
              </div>
            ))}
          </div>

          {/* day columns */}
          {scheduleDays.map((day, dayIndex) => (
            <div
              key={day}
              className="relative border-l border-border"
              style={{ height: ROW_H * scheduleHours.length }}
            >
              {/* hour gridlines */}
              {scheduleHours.map((h) => (
                <div key={h} className="border-b border-border/60" style={{ height: ROW_H }} />
              ))}

              {/* subject blocks */}
              {scheduleBlocks
                .filter((b) => dayStringToNum(b.day) === dayIndex)
                .map((b) => {
                  // 1. colorIndex가 없거나 범위를 벗어날 경우 대비 백엔드 반환 color 매핑
                  const hasColorIndex = b.colorIndex !== undefined && b.colorIndex !== null
                  const c = hasColorIndex
                    ? pastelPalette[b.colorIndex % pastelPalette.length]
                    : {
                        bg: b.color || "bg-blue-100",
                        text: b.textColor || "text-blue-700",
                        bar: b.color || "bg-blue-500",
                      }

                  // c가 여전히 undefined일 경우 최종 방어코드
                  const safeC = c || { bg: "bg-blue-100", text: "text-blue-700", bar: "bg-blue-500" }

                  // 2. start 실제 시간(예: 9.0, 10.5) 처리 혹은 index 처리
                  const startHour = b.start !== undefined ? b.start : 9
                  const startOffset = startHour >= 8 ? (startHour - scheduleHours[0]) : startHour

                  // 3. span 계산 (end가 있을 경우 end - start, 없을 경우 fallback 1)
                  const span = b.span !== undefined 
                    ? b.span 
                    : (b.end !== undefined ? (b.end - startHour) : 1)

                  return (
                    <div
                      key={b.id}
                      className={`absolute inset-x-0.5 overflow-hidden rounded-xl p-2 ${safeC.bg}`}
                      style={{ top: startOffset * ROW_H + 2, height: span * ROW_H - 4 }}
                    >
                      <div className={`h-full border-l-2 pl-2 ${(safeC.bar || "bg-blue-500").replace("bg-", "border-")}`}>
                        <p className={`text-[11px] font-bold leading-tight ${safeC.text}`}>{b.name}</p>
                        <p className={`mt-1 text-[9px] leading-tight ${safeC.text} opacity-80`}>
                          {b.room || b.professor || ""}
                        </p>
                      </div>
                    </div>
                  )
                })}
            </div>
          ))}
        </div>
      </section>

      {/* AI recommendation reasons */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground">AI 추천 이유</h2>
        {dynamicReasons.filter((r) => r && r.title).map((r, i) => {
          const Icon = reasonIconMap[r.icon] ?? BrainCircuit
          return (
            <div key={i} className="flex items-start gap-3 rounded-2xl bg-card border border-border p-4.5 shadow-sm">
              <span className="flex h-9.5 w-9.5 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Icon className="h-5 w-5 text-primary" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-foreground">{r.title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{r.desc}</p>
              </div>
            </div>
          )
        })}
      </section>
    </div>
  )
}
