"use client"

import { useState } from "react"
import { AlertTriangle, Bell, CalendarDays, Info, Plus, X, Loader2 } from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"

export function NoticeTab() {
  const { notice, addInterestKeyword, removeInterestKeyword } = useGradData()
  const { showToast } = useToast()
  const { academicCalendar, interestKeywords, urgentNotice } = notice

  const [isAdding, setIsAdding] = useState(false)
  const [newKeyword, setNewKeyword] = useState("")
  const [isUpdating, setIsUpdating] = useState(false)

  const handleAddKeyword = async (keyword: string) => {
    const trimmed = keyword.trim()
    if (!trimmed) {
      setIsAdding(false)
      return
    }

    const currentKeywords = interestKeywords.map((k) => k.label || k.text)
    if (currentKeywords.includes(trimmed)) {
      showToast("이미 등록된 키워드입니다.")
      return
    }

    setIsUpdating(true)
    try {
      if (addInterestKeyword) {
        await addInterestKeyword(trimmed)
        showToast("알림 키워드가 등록되었습니다.")
      }
      setNewKeyword("")
      setIsAdding(false)
    } catch {
      showToast("키워드 등록에 실패했습니다.")
    } finally {
      setIsUpdating(false)
    }
  }

  const handleRemoveKeyword = async (keyword: string) => {
    setIsUpdating(true)
    try {
      if (removeInterestKeyword) {
        await removeInterestKeyword(keyword)
        showToast("알림 키워드가 삭제되었습니다.")
      }
    } catch {
      showToast("키워드 삭제에 실패했습니다.")
    } finally {
      setIsUpdating(false)
    }
  }

  return (
    <div className="space-y-6 px-4 pb-6 pt-5 md:max-w-4xl md:mx-auto md:px-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">공지 &amp; 알림</h1>
        <div className="flex items-center gap-2">
          {isUpdating && <Loader2 className="h-4.5 w-4.5 animate-spin text-primary" />}
          <span className="flex h-9.5 w-9.5 items-center justify-center rounded-full bg-card border border-border shadow-sm">
            <Bell className="h-5 w-5 text-primary" />
          </span>
        </div>
      </div>

      {/* Interest keyword chips */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-muted-foreground">관심 키워드</h2>
          <span className="text-[11px] font-semibold text-muted-foreground">{(interestKeywords || []).length}개 설정됨</span>
        </div>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {(interestKeywords || []).map((k, idx) => {
            const kw = k.label || k.text
            const isUrgent = k.urgent ?? false

            return (
              <div
                key={`keyword-${kw}-${idx}`}
                className={`flex shrink-0 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-bold border border-border shadow-sm transition-all ${
                  isUrgent
                    ? "bg-primary text-white border-transparent"
                    : "bg-secondary text-foreground hover:bg-[#e8f3ff] hover:text-primary"
                }`}
              >
                <span>#{kw}</span>
                <button
                  onClick={() => handleRemoveKeyword(kw)}
                  disabled={isUpdating}
                  className="ml-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 p-0.5 text-muted-foreground hover:text-foreground transition-colors cursor-pointer disabled:opacity-50"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )
          })}
          {isAdding ? (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleAddKeyword(newKeyword)
              }}
              className="flex shrink-0 items-center gap-1"
            >
              <input
                type="text"
                autoFocus
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                placeholder="키워드 입력"
                className="rounded-full border border-primary px-3 py-1.5 text-xs bg-background text-foreground focus:outline-none w-28 transition-all"
                onBlur={() => {
                  setTimeout(() => {
                    if (!newKeyword.trim()) {
                      setIsAdding(false)
                    }
                  }, 200)
                }}
              />
              <button
                type="submit"
                disabled={isUpdating}
                className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-white text-xs font-bold hover:bg-primary-hover transition-colors disabled:opacity-50 cursor-pointer"
              >
                <Plus className="h-4 w-4" />
              </button>
            </form>
          ) : (
            <button
              onClick={() => setIsAdding(true)}
              className="flex shrink-0 items-center gap-1 rounded-full border border-dashed border-border px-3.5 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-secondary transition-colors cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" />
              추가
            </button>
          )}
        </div>
      </section>

      {/* Urgent notice matched with 특화 */}
      <section
        className="rounded-2xl bg-[#fff3f5] dark:bg-[#381e25] p-5 shadow-sm"
        role="alert"
      >
        <div className="mb-2 flex items-center gap-2">
          <span className="flex items-center gap-1 rounded-full bg-[#e42939] px-2.5 py-0.5 text-[10px] font-bold text-white">
            <AlertTriangle className="h-3 w-3" />
            긴급 · {urgentNotice.date}
          </span>
          <span className="rounded-full bg-[#e42939]/10 px-2.5 py-0.5 text-[10px] font-bold text-[#e42939] dark:text-[#ff6b8b]">
            #{urgentNotice.keyword}
          </span>
        </div>
        <h3 className="text-[15px] font-bold text-foreground">{urgentNotice.title}</h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{urgentNotice.desc}</p>
      </section>

      {/* Academic calendar timeline */}
      <section>
        <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
          <CalendarDays className="h-4.5 w-4.5 text-primary" />
          학사 일정
        </h2>
        <ol className="relative ml-2.5 border-l border-border">
          {academicCalendar.map((item, idx) => {
            const isWarning = item.type === "warning"
            return (
              <li key={`${item.id || idx}-${idx}`} className="relative mb-5 pl-5.5 last:mb-0">
                <span
                  className={`absolute -left-[6.5px] top-1.5 h-3 w-3 rounded-full ring-4 ring-background ${
                    isWarning ? "bg-[#ff9f1a]" : "bg-primary"
                  }`}
                />
                <div
                  className={`rounded-2xl p-4.5 shadow-sm border ${
                    isWarning 
                      ? "border-transparent bg-[#fff9e6] dark:bg-[#3d321d]" 
                      : "border-border bg-card"
                  }`}
                >
                  <div className="mb-1.5 flex items-center gap-2">
                    <span className={`text-xs font-bold ${isWarning ? "text-[#b27600] dark:text-[#ffca57]" : "text-primary"}`}>{item.date}</span>
                    {isWarning ? (
                      <AlertTriangle className="h-4 w-4 text-[#ff9f1a]" />
                    ) : (
                      <Info className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <h3 className="text-[15px] font-bold text-foreground">{item.title}</h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{item.desc}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </section>
    </div>
  )
}
