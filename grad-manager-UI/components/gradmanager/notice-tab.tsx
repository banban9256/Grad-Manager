"use client"

import { AlertTriangle, Bell, CalendarDays, Info, Plus } from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"

export function NoticeTab() {
  const { notice } = useGradData()
  const { showToast } = useToast()
  const { academicCalendar, interestKeywords, urgentNotice } = notice

  return (
    <div className="space-y-6 px-4 pb-6 pt-5 md:max-w-4xl md:mx-auto md:px-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">공지 &amp; 알림</h1>
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-card shadow-sm">
          <Bell className="h-5 w-5 text-primary" />
        </span>
      </div>

      {/* Interest keyword chips */}
      <section>
        <h2 className="mb-2 text-sm font-semibold text-foreground">관심 키워드</h2>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {interestKeywords.map((k) => (
            <button
              key={k.key}
              onClick={() => showToast("준비 중인 기능입니다.")}
              className={`flex shrink-0 items-center gap-1 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
                k.urgent
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-secondary-foreground shadow-sm hover:bg-accent"
              }`}
            >
              #{k.label}
            </button>
          ))}
          <button
            onClick={() => showToast("준비 중인 기능입니다.")}
            className="flex shrink-0 items-center gap-1 rounded-full border border-dashed border-border px-3 py-1.5 text-sm text-muted-foreground"
          >
            <Plus className="h-4 w-4" />
            추가
          </button>
        </div>
      </section>

      {/* Urgent notice matched with 특화 */}
      <section
        className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4"
        role="alert"
      >
        <div className="mb-1 flex items-center gap-2">
          <span className="flex items-center gap-1 rounded-full bg-destructive px-2 py-0.5 text-xs font-semibold text-white">
            <AlertTriangle className="h-3.5 w-3.5" />
            긴급 · {urgentNotice.date}
          </span>
          <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">
            #{urgentNotice.keyword}
          </span>
        </div>
        <h3 className="text-sm font-bold text-foreground">{urgentNotice.title}</h3>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{urgentNotice.desc}</p>
      </section>

      {/* Academic calendar timeline */}
      <section>
        <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-foreground">
          <CalendarDays className="h-4 w-4 text-primary" />
          학사 일정
        </h2>
        <ol className="relative ml-2 border-l-2 border-border">
          {academicCalendar.map((item) => {
            const isWarning = item.type === "warning"
            return (
              <li key={item.id} className="relative mb-4 pl-5 last:mb-0">
                <span
                  className={`absolute -left-[7px] top-1.5 h-3 w-3 rounded-full ring-4 ring-background ${
                    isWarning ? "bg-destructive" : "bg-primary"
                  }`}
                />
                <div
                  className={`rounded-2xl p-3.5 shadow-sm ${
                    isWarning ? "border border-amber-300 bg-amber-50" : "bg-card"
                  }`}
                >
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-xs font-semibold text-primary">{item.date}</span>
                    {isWarning ? (
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                    ) : (
                      <Info className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">{item.title}</h3>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{item.desc}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </section>
    </div>
  )
}
