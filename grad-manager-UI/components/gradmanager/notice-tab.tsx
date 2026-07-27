"use client"

import { useState } from "react"
import { AlertTriangle, Bell, BellOff, CalendarDays, Info, Plus, X, Loader2, CheckCircle2, Clock, BellRing } from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"

export function NoticeTab() {
  const { notice, addInterestKeyword, removeInterestKeyword, notifyEnabled = true, setNotifyEnabled = () => {} } = useGradData()
  const { showToast } = useToast()
  const { academicCalendar = [], interestKeywords, urgentNotice, keywordNotices = [], notificationTriggers = [] } = notice || {}

  // 날짜 한글 포맷팅 헬퍼 함수
  const formatEventDate = (dateStr: string) => {
    if (!dateStr) return ""
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})$/)
    if (match) {
      const month = parseInt(match[2], 10)
      const day = parseInt(match[3], 10)
      return `${month}월 ${day}일`
    }
    return dateStr
  }

  // 4대 고정 일정 정의 (키워드 상관없이 무조건 렌더링될 대상)
  const fixedMandatoryEvents = [
    {
      id: "fixed-pre-reg",
      title: "2026-2학기 예비 수강신청",
      date: "2026-07-28",
      endDate: "2026-07-31",
      isMandatory: true,
      isUpcoming: true,
      category: "수강신청",
      content: "예비 수강신청 기간입니다. 원하는 과목을 미리 희망과목에 담아두세요.",
      desc: "예비 수강신청 기간입니다. 원하는 과목을 미리 희망과목에 담아두세요."
    },
    {
      id: "fixed-reg",
      title: "2026-2학기 본 수강신청",
      date: "2026-08-04",
      endDate: "2026-08-08",
      isMandatory: true,
      isUpcoming: true,
      category: "수강신청",
      content: "2026학년도 2학기 본 수강신청 기간입니다. 개설 강좌 시간표를 다시 확인하세요.",
      desc: "2026학년도 2학기 본 수강신청 기간입니다. 개설 강좌 시간표를 다시 확인하세요."
    },
    {
      id: "fixed-tuition",
      title: "2026-2학기 등록금 납부",
      date: "2026-08-11",
      endDate: "2026-08-13",
      isMandatory: true,
      isUpcoming: true,
      category: "등록",
      content: "2026학년도 2학기 등록금 정규 납부 기간입니다. 지정 은행 및 계좌를 통해 납부해 주세요.",
      desc: "2026학년도 2학기 등록금 정규 납부 기간입니다. 지정 은행 및 계좌를 통해 납부해 주세요."
    },
    {
      id: "fixed-change",
      title: "2026-2학기 수강신청 변경기간",
      date: "2026-08-25",
      endDate: "2026-08-27",
      isMandatory: true,
      isUpcoming: true,
      category: "수강신청",
      content: "수강신청 변경 및 정정 기간입니다. 공석이 있는 강좌에 한해 정정이 가능합니다.",
      desc: "수강신청 변경 및 정정 기간입니다. 공석이 있는 강좌에 한해 정정이 가능합니다."
    }
  ]

  const mergedCalendar = [...(academicCalendar || [])]

  fixedMandatoryEvents.forEach((fixedEvt) => {
    const isAlreadyPresent = mergedCalendar.some(
      (item) =>
        (item.title && item.title.includes("예비 수강신청") && fixedEvt.title.includes("예비 수강신청")) ||
        (item.title && item.title.includes("본 수강신청") && fixedEvt.title.includes("본 수강신청")) ||
        (item.title && item.title.includes("등록금 납부") && fixedEvt.title.includes("등록금 납부")) ||
        (item.title && item.title.includes("수강신청 변경") && fixedEvt.title.includes("수강신청 변경")) ||
        item.id === fixedEvt.id
    )

    if (!isAlreadyPresent) {
      mergedCalendar.push(fixedEvt)
    } else {
      const idx = mergedCalendar.findIndex(
        (item) =>
          (item.title && item.title.includes("예비 수강신청") && fixedEvt.title.includes("예비 수강신청")) ||
          (item.title && item.title.includes("본 수강신청") && fixedEvt.title.includes("본 수강신청")) ||
          (item.title && item.title.includes("등록금 납부") && fixedEvt.title.includes("등록금 납부")) ||
          (item.title && item.title.includes("수강신청 변경") && fixedEvt.title.includes("수강신청 변경")) ||
          item.id === fixedEvt.id
      )
      if (idx !== -1) {
        mergedCalendar[idx] = {
          ...mergedCalendar[idx],
          isMandatory: true,
          isUpcoming: mergedCalendar[idx].isUpcoming ?? true,
          date: mergedCalendar[idx].date || fixedEvt.date,
          endDate: mergedCalendar[idx].endDate || fixedEvt.endDate
        }
      }
    }
  })

  // 날짜 기준으로 오름차순 정렬하되, Upcoming 일정이 먼저 뜨게 정렬
  mergedCalendar.sort((a, b) => {
    const aDate = a.date || ""
    const bDate = b.date || ""
    const aUpcoming = a.isUpcoming ?? true
    const bUpcoming = b.isUpcoming ?? true

    if (aUpcoming !== bUpcoming) {
      return aUpcoming ? -1 : 1
    }
    return aDate.localeCompare(bDate)
  })

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
        showToast("키워드 삭제가 완료되었습니다.")
      }
    } catch {
      showToast("키워드 삭제에 실패했습니다.")
    } finally {
      setIsUpdating(false)
    }
  }

  const renderHighlightedTitle = (title: string, keywords: any[]) => {
    const kws = keywords.map(k => k.label || k.text).filter(Boolean)
    if (kws.length === 0) return title

    const regex = new RegExp(`(${kws.join("|")})`, "gi")
    const parts = title.split(regex)

    return parts.map((part, i) =>
      regex.test(part) ? (
        <span key={i} className="bg-[#3182f6]/10 text-[#3182f6] px-1 py-0.5 rounded font-bold">
          {part}
        </span>
      ) : (
        part
      )
    )
  }

  const kws = (interestKeywords || []).map(k => k.label || k.text).filter(Boolean)

  return (
    <div className="space-y-6 px-4 pb-6 pt-5 md:max-w-4xl md:mx-auto md:px-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">공지 &amp; 알림</h1>
        <div className="flex items-center gap-2">
          {isUpdating && <Loader2 className="h-4.5 w-4.5 animate-spin text-primary" />}
          <button
            onClick={() => {
              const nextVal = !notifyEnabled
              setNotifyEnabled(nextVal)
              showToast(nextVal ? "알림이 수신 허용되었습니다." : "알림이 수신 거부(음소거)되었습니다.")
            }}
            className={`flex h-9.5 w-9.5 items-center justify-center rounded-full border transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95 ${
              notifyEnabled
                ? "bg-[#3182f6]/10 border-[#3182f6]/20 text-[#3182f6]"
                : "bg-secondary border-border text-muted-foreground/60"
            }`}
            title={notifyEnabled ? "알림 끄기" : "알림 켜기"}
          >
            {notifyEnabled ? (
              <Bell className="h-5 w-5" />
            ) : (
              <BellOff className="h-5 w-5" />
            )}
          </button>
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

      {/* 긴급 공지 (urgentNotice) */}
      {urgentNotice && urgentNotice.title && (
        <section
          className="rounded-2xl bg-[#fff3f5] dark:bg-[#381e25] p-5 shadow-sm border border-transparent"
          role="alert"
        >
          <div className="mb-2 flex items-center gap-2">
            <span className="flex items-center gap-1 rounded-full bg-[#e42939] px-2.5 py-0.5 text-[10px] font-bold text-white">
              <AlertTriangle className="h-3 w-3" />
              긴급 · {urgentNotice.date}
            </span>
            <span className="rounded-full bg-[#e42939]/10 px-2.5 py-0.5 text-[10px] font-bold text-[#e42939] dark:text-[#ff6b8b]">
              #{urgentNotice.keyword || "공통"}
            </span>
          </div>
          <h3 className="text-[15px] font-bold text-foreground">{urgentNotice.title}</h3>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{urgentNotice.desc || urgentNotice.content || ""}</p>
          {urgentNotice.url && (
            <div className="mt-3 pt-2.5 border-t border-[#e42939]/10 flex justify-end">
              <a
                href={urgentNotice.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[10.5px] font-bold text-[#e42939] hover:underline"
              >
                <span>원문 보기</span>
                <span className="text-[8px]">↗</span>
              </a>
            </div>
          )}
        </section>
      )}

      {/* 알림 트리거 (키워드 마감 임박 알림) */}
      {notificationTriggers.length > 0 && (
        <section>
          <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
            <BellRing className="h-4.5 w-4.5 text-[#ff9f1a]" />
            키워드 알림 트리거
          </h2>
          <div className="space-y-2.5">
            {notificationTriggers.map((trigger: any, idx: number) => {
              const isUrgent = trigger.alert_type === "긴급"
              const isWarning = trigger.alert_type === "주의"
              return (
                <div
                  key={`trigger-${trigger.id || idx}`}
                  className={`rounded-2xl p-4 shadow-sm border transition-all ${
                    isUrgent
                      ? "border-[#e42939]/30 bg-[#fff3f5] dark:bg-[#381e25]"
                      : isWarning
                        ? "border-[#ff9f1a]/30 bg-[#fff9e6] dark:bg-[#3d321d]"
                        : "border-border bg-card"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isUrgent
                            ? "bg-[#e42939] text-white"
                            : isWarning
                              ? "bg-[#ff9f1a] text-white"
                              : "bg-primary/10 text-primary"
                        }`}>
                          {trigger.alert_type}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-semibold">{trigger.date}</span>
                      </div>
                      <p className="text-sm font-semibold text-foreground leading-relaxed">{trigger.title}</p>
                      {trigger.matched_keywords && trigger.matched_keywords.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {trigger.matched_keywords.map((kw: string, ki: number) => (
                            <span key={ki} className="text-[9px] font-bold text-[#3182f6] bg-[#3182f6]/10 px-1.5 py-0.5 rounded">
                              #{kw}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* 키워드 매칭 공지 */}
      {keywordNotices.length > 0 && (
        <section>
          <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
            <CheckCircle2 className="h-4.5 w-4.5 text-[#008f80]" />
            키워드 매칭 공지
          </h2>
          <div className="space-y-2.5">
            {keywordNotices.map((notice: any, idx: number) => {
              const isMatched = kws.some(kw => notice.title.includes(kw) || (notice.content || "").includes(kw))
              return (
                <div
                  key={`kw-notice-${notice.id || idx}`}
                  className={`rounded-2xl p-4 shadow-sm border transition-all ${
                    isMatched
                      ? "border-[#3182f6]/30 bg-[#3182f6]/5 dark:bg-[#3182f6]/10"
                      : "border-border bg-card"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-bold text-[#3182f6] bg-[#3182f6]/10 px-2 py-0.5 rounded-full">
                          키워드 매칭
                        </span>
                        <span className="text-[10px] text-muted-foreground font-semibold">{notice.date}</span>
                        {notice.category && (
                          <span className="text-[9px] text-muted-foreground bg-secondary px-1.5 py-0.5 rounded font-semibold">
                            {notice.category}
                          </span>
                        )}
                      </div>
                      <h3 className="text-sm font-bold text-foreground">
                        {renderHighlightedTitle(notice.title, interestKeywords || [])}
                      </h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground line-clamp-2">
                        {notice.content || "상세 내용이 없습니다."}
                      </p>
                      {notice.matched_keywords && notice.matched_keywords.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {notice.matched_keywords.map((kw: string, ki: number) => (
                            <span key={ki} className="text-[9px] font-bold text-[#008f80] bg-[#daf2ee] px-1.5 py-0.5 rounded">
                              #{kw}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  {notice.url && (
                    <div className="mt-3 pt-2.5 border-t border-border/40 flex justify-end">
                      <a
                        href={notice.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[10.5px] font-bold text-[#3182f6] hover:underline"
                      >
                        <span>원문 보기</span>
                        <span className="text-[8px]">↗</span>
                      </a>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* 학사일정 타임라인 (고정 일정) */}
      <section>
        <h2 className="mb-4 flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
          <CalendarDays className="h-4.5 w-4.5 text-primary" />
          학사일정 (고정 일정)
        </h2>
        <ol className="relative ml-2.5 border-l border-border">
          {mergedCalendar.map((item: any, idx: number) => {
            const isUpcoming = item.isUpcoming ?? false
            const isMandatory = item.isMandatory ?? false
            const isPast = !isUpcoming
            const kwsList = (interestKeywords || []).map((k: any) => k.label || k.text).filter(Boolean)
            const isMatched = kwsList.some((kw: string) => item.title.includes(kw) || (item.content || "").includes(kw))

            return (
              <li key={`${item.id || idx}-${idx}`} className="relative mb-5 pl-5.5 last:mb-0">
                <span
                  className={`absolute -left-[6.5px] top-1.5 h-3 w-3 rounded-full ring-4 ring-background ${
                    isMatched ? "bg-[#3182f6]" : isMandatory && isUpcoming ? "bg-[#e42939]" : isPast ? "bg-muted-foreground/30" : "bg-primary"
                  }`}
                />
                <div
                  className={`rounded-2xl p-4.5 shadow-sm border transition-all ${
                    isMatched
                      ? "border-[#3182f6]/40 bg-[#3182f6]/5 dark:bg-[#3182f6]/10"
                      : isPast
                        ? "border-border/50 bg-secondary/30 opacity-70"
                        : isMandatory
                          ? "border-[#e42939]/20 bg-[#fff3f5] dark:bg-[#381e25]"
                          : "border-border bg-card"
                  }`}
                >
                  <div className="mb-1.5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${
                        isMatched ? "text-[#3182f6]" : isPast ? "text-muted-foreground" : isMandatory ? "text-[#e42939]" : "text-primary"
                      }`}>
                        {formatEventDate(item.date)}
                        {item.endDate && item.endDate !== item.date && (
                          <span className="text-muted-foreground"> ~ {formatEventDate(item.endDate)}</span>
                        )}
                      </span>
                      {isMatched ? (
                        <span className="text-[9px] font-bold text-[#3182f6] bg-[#3182f6]/15 px-2 py-0.5 rounded-full select-none">
                          # 키워드 일치
                        </span>
                      ) : isMandatory && isUpcoming ? (
                        <span className="text-[9px] font-bold text-[#e42939] bg-[#e42939]/10 px-2 py-0.5 rounded-full select-none">
                          필수 일정
                        </span>
                      ) : isPast ? (
                        <span className="text-[9px] font-bold text-muted-foreground bg-secondary px-2 py-0.5 rounded-full select-none">
                          지난 일정
                        </span>
                      ) : (
                        <Info className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                  <h3 className="text-[15px] font-bold text-foreground">
                    {renderHighlightedTitle(item.title, interestKeywords || [])}
                  </h3>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {item.content || item.desc || "상세 공지 내용이 존재하지 않습니다."}
                  </p>
                  {item.url && (
                    <div className="mt-3 pt-2.5 border-t border-border/40 flex justify-end">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[10.5px] font-bold text-[#3182f6] hover:underline"
                      >
                        <span>원문 보기</span>
                        <span className="text-[8px]">↗</span>
                      </a>
                    </div>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      </section>
    </div>
  )
}
