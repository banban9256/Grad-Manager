"use client"

import { useState, useEffect } from "react"
import { ChevronLeft, Plus, X, Check, Star } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { aiColorMap } from "@/lib/grad-data"
import type { AiCourse } from "@/data/types"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { saveUserSchedule } from "@/lib/api"

// 요일 및 교시 파싱 및 시간표 충돌 검증 헬퍼
const dayStringToNum = (dayVal: any): number => {
  if (typeof dayVal === "number") return dayVal
  if (typeof dayVal !== "string") return -1
  const clean = dayVal.trim().toUpperCase()
  
  // 첫 단어가 한글 요일명인지 단축 검사
  const firstChar = clean.charAt(0)
  const quickMapping: Record<string, number> = {
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4
  }
  if (quickMapping[firstChar] !== undefined) {
    return quickMapping[firstChar]
  }

  const mapping: Record<string, number> = {
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4,
    "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3, "금요일": 4,
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4,
    "MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3, "FRIDAY": 4
  }
  return mapping[clean] !== undefined ? mapping[clean] : -1
}

const timeToHoursValue = (timeStr: string): number => {
  if (!timeStr) return 9
  const [h, m] = timeStr.split(":").map(Number)
  return h + m / 60
}

const normalizeSchedules = (rawSchedules: any[]): any[] => {
  const normalized: any[] = []
  if (!rawSchedules || rawSchedules.length === 0) return normalized

  rawSchedules.forEach((s: any) => {
    const dayStr = String(s.day || "")
    const startStr = String(s.start_time || "")
    const endStr = String(s.end_time || "")
    const roomStr = String(s.classroom || s.room || "")

    let delimiter = ","
    if (dayStr.includes("/")) {
      delimiter = "/"
    } else if (!dayStr.includes(",") && (startStr.includes(",") || endStr.includes(","))) {
      delimiter = ","
    } else if (!dayStr.includes("/") && (startStr.includes("/") || endStr.includes("/"))) {
      delimiter = "/"
    }

    const days = dayStr.split(delimiter).map(x => x.trim())
    const starts = startStr.split(delimiter).map(x => x.trim())
    const ends = endStr.split(delimiter).map(x => x.trim())
    const rooms = roomStr.split(delimiter).map(x => x.trim())

    const maxLen = Math.max(days.length, starts.length, ends.length)

    for (let i = 0; i < maxLen; i++) {
      const d = days[i] || days[0] || "월"
      const st = starts[i] || starts[0] || "09:00"
      const et = ends[i] || ends[0] || "10:30"
      const r = rooms[i] || rooms[0] || roomStr || "미정"

      normalized.push({
        day: d,
        start_time: st,
        end_time: et,
        classroom: r
      })
    }
  })

  return normalized
}

export function AiRecommendationScreen({ onBack }: { onBack: () => void }) {
  const { aiRecommendation, messages, setMessages, allCourses, user } = useGradData()
  const { showToast } = useToast()
  const { aiCourses } = aiRecommendation

  const activeStudentId = user?.userInfo?.studentId || "20210001"

  // 수동 편집된 시간표 상태 로딩 (localStorage / sessionStorage 영구 싱크용)
  const [customBlocks, setCustomBlocks] = useState<any[]>(() => {
    if (typeof window !== "undefined") {
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${activeStudentId}`
      const storedLocal = localStorage.getItem(scheduleBlocksKey)
      const storedSession = sessionStorage.getItem(scheduleBlocksKey)
      
      let localBlocks: any[] = []
      let sessionBlocks: any[] = []
      
      if (storedLocal) {
        try {
          const parsed = JSON.parse(storedLocal)
          if (Array.isArray(parsed)) localBlocks = parsed
        } catch (e) {}
      }
      
      if (storedSession) {
        try {
          const parsed = JSON.parse(storedSession)
          if (Array.isArray(parsed)) sessionBlocks = parsed
        } catch (e) {}
      }
      
      if (localBlocks.length > 0) return localBlocks
      if (sessionBlocks.length > 0) return sessionBlocks
    }
    return []
  })

  // 시간표 겹침 충돌 체크 함수
  const checkTimeConflict = (newSchedules: any[], existingBlocks: any[]) => {
    for (const ns of newSchedules) {
      const newDayNum = dayStringToNum(ns.day)
      if (newDayNum === -1) continue

      const newStart = timeToHoursValue(ns.start_time)
      const newEnd = timeToHoursValue(ns.end_time)

      for (const eb of existingBlocks) {
        const ebDayNum = dayStringToNum(eb.day)
        if (ebDayNum !== newDayNum) continue

        const ebStart = Number(eb.start)
        const ebEnd = Number(eb.start) + Number(eb.span)

        if (newStart < ebEnd && ebStart < newEnd) {
          return eb.name 
        }
      }
    }
    return null
  }

  // 추천 과목 카드 시간표 추가 핸들러
  const handleAddToSchedule = (course: AiCourse) => {
    // 1. 과목명 기준 중복 기입 차단
    const courseName = course.name || matched?.title || matched?.name || course.code || "과목명 미정"
    const cleanCourseName = courseName.trim().toLowerCase()
    const isDuplicate = customBlocks.some(b => b.name.trim().toLowerCase() === cleanCourseName)
    if (isDuplicate) {
      showToast(`'${courseName}' 과목은 이미 시간표에 등록되어 있습니다.`)
      return
    }

    const matched = allCourses?.find(c => {
      const targetId = String(course.code || "");
      return String(c.course_id || "") === targetId ||
             String(c.code || "") === targetId ||
             String(c.id || "") === targetId;
    })

    // 2. 추천 과목에 매칭되는 시뮬레이션 schedules 직접 상속
    let schedules = (course as any).schedules || []

    if (schedules.length === 0) {
      // 텍스트("월 10:30~11:45" 등)로부터 간편 파싱 시도 또는 가상 폴백 생성
      const rawSchedules = matched?.schedules || []
      
      // 단일 분반 시간대만 추출하여 타 분반 누적 충돌 방지
      if (rawSchedules.length > 0) {
        const normalized = normalizeSchedules(rawSchedules)
        const first = normalized[0]
        const firstRoom = (first.classroom || first.room || "미정").trim()
        const firstStart = first.start_time
        const firstEnd = first.end_time

        // 첫 번째 슬롯과 동일 강의실 및 시간대를 만족하는 단일 분반 세트 일정만 정밀 추출
        const filtered = normalized.filter((s: any) => {
          const room = (s.classroom || s.room || "미정").trim()
          return room === firstRoom && s.start_time === firstStart && s.end_time === firstEnd
        })
        
        const uniqueSet: any[] = []
        const seenKeys = new Set<string>()
        filtered.forEach((s: any) => {
          const key = `${s.day}-${s.start_time}-${s.end_time}`
          if (!seenKeys.has(key)) {
            seenKeys.add(key)
            uniqueSet.push(s)
          }
        })
        schedules = uniqueSet
      }
    }

    if (schedules.length === 0) {
      const hash = course.code.charCodeAt(0) % 2
      if (hash === 0) {
        schedules = [
          { day: "월", start_time: "13:30", end_time: "14:45", classroom: "장공관 101호" },
          { day: "수", start_time: "13:30", end_time: "14:45", classroom: "장공관 101호" }
        ]
      } else {
        schedules = [
          { day: "화", start_time: "10:30", end_time: "11:45", classroom: "만우관 302호" },
          { day: "목", start_time: "10:30", end_time: "11:45", classroom: "만우관 302호" }
        ]
      }
    }

    // 3. 시간표 교시 충돌 체크
    const normalizedSchedules = normalizeSchedules(schedules)
    const conflictName = checkTimeConflict(normalizedSchedules, customBlocks)
    if (conflictName) {
      showToast(`기존 과목 '${conflictName}'과 수업 시간이 겹쳐 추가할 수 없습니다.`)
      return
    }

    // 4. 시간표 블록 생성 및 추가
    const newBlocks: any[] = []
    const profName = course.professor || matched?.professor || matched?.professor_name || "미지정"

    normalizedSchedules.forEach((s: any, sIdx: number) => {
      const start = timeToHoursValue(s.start_time)
      const end = timeToHoursValue(s.end_time)

      newBlocks.push({
        id: `ai-rec-block-${String(course.code || "")}-${s.day}-${s.start_time}-${sIdx}`,
        groupId: String(matched?.course_id || course.code || ""),
        name: courseName,
        day: s.day,
        start: start,
        span: end - start,
        room: s.classroom || matched?.classroom || "미정",
        professor: profName,
        colorIndex: (customBlocks.length + newBlocks.length) % 3
      })
    })

    const nextBlocks = [...customBlocks, ...newBlocks]
    setCustomBlocks(nextBlocks)
    if (typeof window !== "undefined") {
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${activeStudentId}`
      localStorage.setItem(scheduleBlocksKey, JSON.stringify(nextBlocks))
      sessionStorage.setItem(scheduleBlocksKey, JSON.stringify(nextBlocks))
    }
    saveUserSchedule(Number(activeStudentId), nextBlocks).catch((err) => {
      console.error("Failed to save user schedule to backend:", err)
    })

    showToast(`'${courseName}' 과목이 시간표에 추가되었습니다.`)
  }

  // 동적 필터 리스트 상태 (sessionStorage 연계)
  const [filters, setFilters] = useState<{ key: string; label: string }[]>(() => {
    if (typeof window !== "undefined") {
      const filtersKey = `active_recommend_filters_${activeStudentId}`
      const stored = sessionStorage.getItem(filtersKey)
      if (stored) {
        try {
          return JSON.parse(stored)
        } catch (e) {
          console.error("세션 필터 목록 로드 실패:", e)
        }
      }
    }
    // 디폴트 필터 제공
    return [
      { key: "all", label: "전체" },
      { key: "major", label: "전공필수/선택" },
      { key: "liberal", label: "교양" }
    ]
  })

  // 현재 탭 칩 활성화 상태
  const [active, setActive] = useState<string>("all")

  // 필터 추가 폼 노출 여부 및 입력 상태
  const [showAddForm, setShowAddForm] = useState(false)
  const [newFilterLabel, setNewFilterLabel] = useState("")

  // 초기 렌더링 시 세션 스토리지에 동적 필터 상태 기록
  useEffect(() => {
    if (typeof window !== "undefined") {
      const filtersKey = `active_recommend_filters_${activeStudentId}`
      if (!sessionStorage.getItem(filtersKey)) {
        sessionStorage.setItem(filtersKey, JSON.stringify(filters))
      }
    }
  }, [activeStudentId])

  // 계정 전환 시 새로운 학번의 시간표 및 필터 데이터를 재로드
  useEffect(() => {
    if (typeof window !== "undefined" && activeStudentId) {
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${activeStudentId}`
      const storedLocal = localStorage.getItem(scheduleBlocksKey)
      const storedSession = sessionStorage.getItem(scheduleBlocksKey)
      let localBlocks: any[] = []
      let sessionBlocks: any[] = []
      
      if (storedLocal) {
        try {
          const parsed = JSON.parse(storedLocal)
          if (Array.isArray(parsed)) localBlocks = parsed
        } catch (e) {}
      }
      if (storedSession) {
        try {
          const parsed = JSON.parse(storedSession)
          if (Array.isArray(parsed)) sessionBlocks = parsed
        } catch (e) {}
      }
      const activeStored = localBlocks.length > 0 ? localBlocks : sessionBlocks
      setCustomBlocks(activeStored)

      const filtersKey = `active_recommend_filters_${activeStudentId}`
      const storedFilters = sessionStorage.getItem(filtersKey)
      if (storedFilters) {
        try {
          setFilters(JSON.parse(storedFilters))
        } catch (e) {}
      } else {
        const defaultFilters = [
          { key: "all", label: "전체" },
          { key: "major", label: "전공필수/선택" },
          { key: "liberal", label: "교양" }
        ]
        setFilters(defaultFilters)
        sessionStorage.setItem(filtersKey, JSON.stringify(defaultFilters))
      }
    }
  }, [activeStudentId])

  // 필터 목록 동기화 및 글로벌 AI 시뮬레이터 재생성 트리거
  const syncFilters = (nextFilters: { key: string; label: string }[]) => {
    setFilters(nextFilters)
    if (typeof window !== "undefined") {
      const filtersKey = `active_recommend_filters_${activeStudentId}`
      sessionStorage.setItem(filtersKey, JSON.stringify(nextFilters))
    }
    // 글로벌 챗 시뮬레이션 상태 트리거를 호출해 simulatedSchedule 및 추천 시간표 리프레시
    if (setMessages && messages) {
      setMessages(prev => [...prev])
    }
  }

  // 신규 필터 태그 제출 등록
  const handleAddFilter = (labelText: string) => {
    const cleanText = labelText.trim()
    if (!cleanText) return

    // 중복 등록 방지
    if (filters.some(f => f.label.toLowerCase() === cleanText.toLowerCase())) {
      showToast("이미 등록되어 있는 필터 조건입니다.")
      return
    }

    const newKey = `custom-${Date.now()}`
    const newFilter = { key: newKey, label: cleanText }
    const nextFilters = [...filters, newFilter]

    syncFilters(nextFilters)
    setActive(newKey) // 즉시 활성 탭으로 반영
    setNewFilterLabel("")
    setShowAddForm(false)
    showToast(`'${cleanText}' 필터가 등록되었습니다.`)
  }

  // 필터 태그 삭제 핸들러
  const handleRemoveFilter = (keyToRemove: string, e: React.MouseEvent) => {
    e.stopPropagation() // 부모 탭 칩 클릭 전파 제어
    const nextFilters = filters.filter(f => f.key !== keyToRemove)
    syncFilters(nextFilters)

    // 지운 필터가 활성 중인 탭이었다면 전체로 리턴
    if (active === keyToRemove) {
      setActive("all")
    }
    showToast("필터 태그가 삭제되었습니다.")
  }

  // 프론트엔드 추천 과목 데이터 필터링 연산
  const filteredCourses = aiCourses.filter((course) => {
    if (active === "all") return true
    
    // 전공 대분류 필터링
    if (active === "major") {
      return (
        course.category === "전공필수" || 
        course.category === "전공선택" ||
        course.category === "계열공통" ||
        course.tags.some(tag => tag === "전공필수" || tag === "전공선택" || tag === "계열공통")
      )
    }

    // 교양 대분류 필터링
    if (active === "liberal") {
      return (
        course.category.includes("교양") || 
        course.category === "일반선택" ||
        course.tags.some(tag => tag.includes("교양") || tag.includes("일반"))
      )
    }

    // 사용자 추가 필터 조건인 경우
    const activeFilterObj = filters.find(f => f.key === active)
    if (!activeFilterObj) return true

    const query = activeFilterObj.label.toLowerCase()

    // 1. 학점 조건 필터링
    if (query.includes("3학점")) return course.credit === 3
    if (query.includes("2학점")) return course.credit === 2

    // 2. 오전 교시 기피 필터링 (09:00 시작 교과목 제외)
    if ((query.includes("오전") || query.includes("9시")) && query.includes("제외")) {
      return !course.tags.some(t => t.includes("09:") || t.includes("1교시"))
    }

    // 3. 다차원 키워드 매칭
    return (
      course.name.toLowerCase().includes(query) ||
      course.code.toLowerCase().includes(query) ||
      course.tags.some(tag => tag.toLowerCase().includes(query)) ||
      (course.professor && course.professor.toLowerCase().includes(query)) ||
      (course.reason && course.reason.toLowerCase().includes(query))
    )
  })

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="shrink-0 space-y-3 px-4 pb-4 pt-4 border-b border-border bg-card shadow-sm z-10">
        <div className="mx-auto w-full max-w-5xl space-y-3.5">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
          >
            <ChevronLeft className="h-5 w-5" />
            <span className="text-lg font-bold text-foreground">AI 과목 추천</span>
          </button>

          {/* 대화형 필터 칩 스크롤 영역 */}
          <div className="flex flex-wrap items-center gap-2 select-none">
            {filters.map((f) => {
              const isActive = active === f.key
              const isDefault = f.key === "all" || f.key === "major" || f.key === "liberal"
              
              return (
                <div
                  key={f.key}
                  onClick={() => setActive(f.key)}
                  className={`flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold transition-all cursor-pointer ${
                    isActive
                      ? "bg-[#3182f6] text-white shadow-sm"
                      : "bg-secondary text-secondary-foreground hover:bg-[#e8f3ff] hover:text-primary"
                  }`}
                >
                  <span>{f.label}</span>
                  {!isDefault && (
                    <button
                      type="button"
                      onClick={(e) => handleRemoveFilter(f.key, e)}
                      className={`p-0.5 rounded-full hover:bg-black/10 transition-colors ${
                        isActive ? "text-white/80 hover:text-white" : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </div>
              )
            })}

            {/* 인라인 필터 등록 폼 */}
            <AnimatePresence>
              {showAddForm ? (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.93 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.93 }}
                  className="flex items-center gap-1.5 bg-secondary px-2.5 py-1.2 rounded-full border border-border"
                >
                  <input
                    type="text"
                    placeholder="예: 3학점, AI, 금요일 공강"
                    value={newFilterLabel}
                    onChange={(e) => setNewFilterLabel(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAddFilter(newFilterLabel)
                      if (e.key === "Escape") setShowAddForm(false)
                    }}
                    autoFocus
                    className="bg-transparent border-none text-xs font-bold text-foreground focus:outline-none focus:ring-0 w-[140px] px-1 py-0.5"
                  />
                  <button
                    type="button"
                    onClick={() => handleAddFilter(newFilterLabel)}
                    className="p-1 text-[#3182f6] hover:bg-[#3182f6]/10 rounded-full cursor-pointer"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="p-1 text-destructive hover:bg-destructive/10 rounded-full cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </motion.div>
              ) : (
                <button
                  onClick={() => setShowAddForm(true)}
                  className="flex items-center gap-1 rounded-full border border-dashed border-border px-3.5 py-1.5 text-xs font-bold text-muted-foreground transition-colors hover:bg-secondary cursor-pointer"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>필터 추가</span>
                </button>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* List */}
      <div className="min-h-0 flex-1 overflow-y-auto bg-background">
        <div className="mx-auto w-full max-w-5xl px-4 pb-6 pt-4 space-y-4">
          <h2 className="text-sm font-semibold text-muted-foreground">관심분야 기반 추천</h2>
          {filteredCourses.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {filteredCourses.map((course) => (
                <CourseCard 
                  key={course.id} 
                  course={course} 
                  customBlocks={customBlocks} 
                  onAddToSchedule={handleAddToSchedule} 
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
              <p className="text-sm font-medium">선택한 필터에 해당하는 추천 과목이 없습니다.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CourseCard({ 
  course, 
  customBlocks, 
  onAddToSchedule 
}: { 
  course: AiCourse
  customBlocks: any[]
  onAddToSchedule: (course: AiCourse) => void 
}) {
  const c = aiColorMap[course.color] || aiColorMap.violet
  const isAdded = customBlocks.some(b => b.name.trim().toLowerCase() === course.name.trim().toLowerCase())

  return (
    <article
      className={`overflow-hidden rounded-2xl border border-b-4 bg-card border-border shadow-sm flex flex-col justify-between ${c.border}`}
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

          {/* 고유 시간대 정화 및 한 줄 정제 포맷팅 */}
          {(() => {
            const rawSchedules = (course as any).schedules || []
            const uniqueSchedules: any[] = []
            const seen = new Set<string>()
            rawSchedules.forEach((s: any) => {
              const key = `${s.day}-${s.start_time}-${s.end_time}`
              if (!seen.has(key)) {
                seen.add(key)
                uniqueSchedules.push(s)
              }
            })

            const timeText = uniqueSchedules.length > 0
              ? uniqueSchedules.map((s: any) => `${s.day}요일 ${s.start_time}~${s.end_time}`).join(", ")
              : "시간 미정"

            return (
              <p className="text-[11px] text-[#3182f6] font-semibold font-mono mt-1.5 leading-relaxed text-left">
                🕒 {timeText}
              </p>
            )
          })()}

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
        <p className={`text-xs ${c.bannerText} flex-1`}>{course.reason}</p>
      </div>

      {/* [신규] 시간표 추가/추가됨 동작 패널 */}
      <div className="px-4.5 pb-4.5 pt-2 border-t border-border/40 flex justify-end bg-card">
        {isAdded ? (
          <button
            type="button"
            disabled
            className="w-full flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl text-xs font-extrabold bg-[#3182f6]/10 text-[#3182f6] border border-[#3182f6]/20 cursor-not-allowed"
          >
            <Check className="h-3.5 w-3.5" />
            시간표에 추가됨
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onAddToSchedule(course)}
            className="w-full flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-xl text-xs font-extrabold bg-[#3182f6] text-white hover:bg-[#1b64da] active:scale-95 transition-all shadow-[0_4px_12px_rgba(49,130,246,0.15)] cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            시간표에 추가
          </button>
        )}
      </div>
    </article>
  )
}
