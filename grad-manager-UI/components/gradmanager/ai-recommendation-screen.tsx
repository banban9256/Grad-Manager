"use client"

import { useState } from "react"
import { ChevronLeft, Plus, Settings2, Star } from "lucide-react"
import { aiColorMap } from "@/lib/grad-data"
import type { AiCourse } from "@/data/types"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"

export function AiRecommendationScreen({ onBack }: { onBack: () => void }) {
  const { aiRecommendation } = useGradData()
  const { showToast } = useToast()
  const { aiCourses, aiFilters } = aiRecommendation
  const [active, setActive] = useState<string>("ai")

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="shrink-0 space-y-3 px-4 pb-4 pt-4 border-b border-border bg-card">
        <div className="mx-auto w-full max-w-5xl space-y-3.5">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronLeft className="h-5 w-5" />
            <span className="text-lg font-bold text-foreground">AI 과목 추천</span>
          </button>

          {/* Filter chips */}
          <div className="flex flex-wrap gap-2">
            {aiFilters.map((f) => {
              if (f.addOnly) {
                return (
                  <button
                    key={f.key}
                    onClick={() => showToast("준비 중인 기능입니다.")}
                    className="flex items-center gap-1 rounded-full border border-dashed border-border px-3.5 py-1.5 text-xs font-bold text-muted-foreground transition-colors hover:bg-secondary"
                  >
                    <Settings2 className="h-3.5 w-3.5" />
                    {f.label}
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                )
              }
              const isActive = active === f.key
              return (
                <button
                  key={f.key}
                  onClick={() => setActive(f.key)}
                  className={`rounded-full px-4 py-1.5 text-xs font-bold transition-all ${
                    isActive
                      ? "bg-primary text-white"
                      : "bg-secondary text-secondary-foreground hover:bg-[#e8f3ff] hover:text-primary"
                  }`}
                >
                  {f.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* List */}
      <div className="min-h-0 flex-1 overflow-y-auto bg-background">
        <div className="mx-auto w-full max-w-5xl px-4 pb-6 pt-4 space-y-4">
          <h2 className="text-sm font-semibold text-muted-foreground">관심분야 기반 추천</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {aiCourses.map((course) => (
              <CourseCard key={course.id} course={course} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function CourseCard({ course }: { course: AiCourse }) {
  const c = aiColorMap[course.color]
  return (
    <article
      className={`overflow-hidden rounded-2xl border border-b-4 bg-card border-border shadow-sm ${c.border}`}
    >
      <div className="flex items-center gap-3.5 p-4.5">
        {/* Credit badge */}
        <div
          className={`flex h-13 w-13 shrink-0 flex-col items-center justify-center rounded-full text-white ${c.badge}`}
        >
          <span className="text-[15px] font-bold leading-none">{course.credit}</span>
          <span className="text-[9px] leading-tight mt-0.5">학점</span>
        </div>

        {/* Middle */}
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-[15px] font-bold text-foreground">{course.name}</h3>
          <p className="text-xs text-muted-foreground mt-0.5">{course.code}</p>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {course.tags.map((t) => (
              <span
                key={t}
                className="rounded bg-secondary px-2 py-0.5 text-[10px] font-bold text-muted-foreground"
              >
                {t}
              </span>
            ))}
          </div>
        </div>

        {/* Match */}
        <div className="shrink-0 text-right">
          <p className="text-base font-bold text-primary">{course.match}%</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">적합도</p>
        </div>
      </div>

      {/* Reason banner */}
      <div className={`flex items-center gap-2 px-4.5 py-3 ${c.banner}`}>
        <Star className={`h-4 w-4 shrink-0 ${c.bannerText}`} fill="currentColor" />
        <p className={`text-xs ${c.bannerText}`}>{course.reason}</p>
      </div>
    </article>
  )
}
