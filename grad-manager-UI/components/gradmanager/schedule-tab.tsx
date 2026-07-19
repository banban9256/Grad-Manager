"use client"

import { BrainCircuit, CalendarOff, Clock, GraduationCap, type LucideIcon } from "lucide-react"
import { useGradData } from "./grad-data-provider"

const reasonIconMap: Record<string, LucideIcon> = {
  CalendarOff,
  BrainCircuit,
  GraduationCap,
  Clock,
}

const ROW_H = 52 // px per hour row

export function ScheduleTab() {
  const { schedule } = useGradData()
  const { pastelPalette, scheduleBlocks, scheduleDays, scheduleHours, scheduleReasons } = schedule

  return (
    <div className="space-y-6 px-4 pb-6 pt-5 md:max-w-6xl md:mx-auto md:px-6">
      <div>
        <h1 className="text-xl font-bold text-foreground">추천 시간표</h1>
        <p className="text-sm text-muted-foreground">금요일 공강 · 총 12학점 · 4과목</p>
      </div>

      {/* Timetable grid */}
      <section className="rounded-2xl bg-card p-3 shadow-sm">
        <div className="grid grid-cols-[28px_repeat(5,1fr)]">
          {/* header row */}
          <div />
          {scheduleDays.map((d, i) => (
            <div
              key={d}
              className={`pb-2 text-center text-xs font-semibold ${
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
                className="text-right text-[10px] text-muted-foreground"
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
                .filter((b) => b.day === dayIndex)
                .map((b) => {
                  const c = pastelPalette[b.colorIndex % pastelPalette.length]
                  return (
                    <div
                      key={b.id}
                      className={`absolute inset-x-0.5 overflow-hidden rounded-lg p-1.5 ${c.bg}`}
                      style={{ top: b.start * ROW_H + 2, height: b.span * ROW_H - 4 }}
                    >
                      <div className={`h-full border-l-2 pl-1.5 ${c.bar.replace("bg-", "border-")}`}>
                        <p className={`text-[11px] font-bold leading-tight ${c.text}`}>{b.name}</p>
                        <p className={`mt-0.5 text-[9px] leading-tight ${c.text} opacity-80`}>
                          {b.room}
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
        <h2 className="text-sm font-semibold text-foreground">AI 추천 이유</h2>
        {scheduleReasons.map((r, i) => {
          const Icon = reasonIconMap[r.icon] ?? BrainCircuit
          return (
            <div key={i} className="flex items-start gap-3 rounded-2xl bg-card p-4 shadow-sm">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Icon className="h-5 w-5 text-primary" />
              </span>
              <div>
                <h3 className="text-sm font-semibold text-foreground">{r.title}</h3>
                <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{r.desc}</p>
              </div>
            </div>
          )
        })}
      </section>
    </div>
  )
}
