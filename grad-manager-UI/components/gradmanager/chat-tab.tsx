"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "motion/react"
import {
  AlertTriangle,
  BrainCircuit,
  CalendarOff,
  CheckCircle2,
  GraduationCap,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  X,
  type LucideIcon,
} from "lucide-react"
import type { RecommendedCourse } from "@/data/types"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { sendChatMessage, saveUserSchedule, updateProfile } from "@/lib/api"
import { CONVERGENCE_MAJORS, SPECIALIZED_TRACKS } from "@/lib/constants"

const reasonIconMap: Record<string, LucideIcon> = {
  CalendarOff,
  BrainCircuit,
  GraduationCap,
  Sparkles,
}

const tagStyle: Record<string, string> = {
  필수: "bg-[#e8f3ff] text-[#1b64da] dark:bg-[#1b2d45] dark:text-[#5592f2]",
  "관심사 매칭": "bg-[#daf2ee] text-[#008f80] dark:bg-[#183531] dark:text-[#00caab]",
  "특화전공 인정": "bg-[#fff3f5] text-[#d6284a] dark:bg-[#381e25] dark:text-[#ff6b8b]",
  "융합전공 매칭": "bg-[#f4edff] text-[#6b31f6] dark:bg-[#2c1d3c] dark:text-[#a880f7]",
}

const SEMESTER_OPTIONS = [
  "2026-2학기",
]

type Message = {
  id: string
  role: "ai" | "user"
  content: string
  displayedContent?: string
}

function TypewriterText({ text, onComplete }: { text: string; onComplete?: () => void }) {
  const [displayed, setDisplayed] = useState("")
  const indexRef = useRef(0)

  useEffect(() => {
    indexRef.current = 0
    setDisplayed("")

    const interval = setInterval(() => {
      if (indexRef.current < text.length) {
        setDisplayed(text.slice(0, indexRef.current + 1))
        indexRef.current++
      } else {
        clearInterval(interval)
        onComplete?.()
      }
    }, 18)

    return () => clearInterval(interval)
  }, [text, onComplete])

  return (
    <span>
      {displayed}
      {indexRef.current < text.length && (
        <span className="inline-block w-[2px] h-4 bg-primary/70 animate-pulse ml-0.5 align-text-bottom" />
      )}
    </span>
  )
}



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

export function ChatTab({ onOpenSchedule }: { onOpenSchedule?: () => void }) {
  const { chat, refreshData, schedule, messages = [], setMessages, simulatedSchedule, setSimulatedSchedule, allCourses, user, selectedSemester = "2026-2학기", setSelectedSemester, semesters = [] } = useGradData()
  const { recommendedCourses } = chat
  const { showToast } = useToast()

  const activeStudentId = user?.userInfo?.studentId || "20210001"

  const handleSemesterChange = (newSem: string) => {
    if (setSelectedSemester) {
      setSelectedSemester(newSem)
    }
    if (typeof window !== "undefined") {
      localStorage.setItem(`grad_last_viewed_semester_${activeStudentId}`, newSem)
    }
  }

  const localSimData = simulatedSchedule
  const simDone = localSimData !== null
  const simLoading = false // Real-time calculation on client

  // 수동 편집된 시간표 상태 로딩 (localStorage / sessionStorage 영구 싱크용)
  const [customBlocks, setCustomBlocks] = useState<any[]>(() => {
    if (typeof window !== "undefined") {
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${activeStudentId}_${selectedSemester}`
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

  // 로컬/세션 저장소 싱크 함수
  const saveBlocks = (nextBlocks: any[]) => {
    setCustomBlocks(nextBlocks)
    if (typeof window !== "undefined") {
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${activeStudentId}_${selectedSemester}`
      localStorage.setItem(scheduleBlocksKey, JSON.stringify(nextBlocks))
      sessionStorage.setItem(scheduleBlocksKey, JSON.stringify(nextBlocks))
    }
    saveUserSchedule(Number(activeStudentId), nextBlocks, selectedSemester).catch((err) => {
      console.error("Failed to save user schedule to backend:", err)
    })
  }

  // 외부 편집 연동 동기화용 이펙트
  useEffect(() => {
    const syncLocal = () => {
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${activeStudentId}_${selectedSemester}`
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
      if (activeStored.length > 0) {
        setCustomBlocks(activeStored)
      } else {
        setCustomBlocks([])
      }
    }
    window.addEventListener("focus", syncLocal)
    return () => window.removeEventListener("focus", syncLocal)
  }, [activeStudentId, selectedSemester])

  // 계정 전환 및 선택 학기 변경 시 새로운 학번/학기의 시간표 데이터를 재로드
  useEffect(() => {
    if (typeof window !== "undefined" && activeStudentId) {
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${activeStudentId}_${selectedSemester}`
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
    }
  }, [activeStudentId, selectedSemester])

  // 시간 포맷을 실수형 숫자로 파싱
  const timeToHoursValue = (timeStr: string): number => {
    if (!timeStr) return 9
    const [h, m] = timeStr.split(":").map(Number)
    return h + m / 60
  }

  // 결합 시간표 분산 쪼개기 헬퍼
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

  // 시간표 겹침 충돌 체크
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

  // [신규 1] 시뮬레이션 추천 시간표 일괄 한 번에 적용
  const handleBulkApply = () => {
    if (!localSimData || !localSimData.scheduleBlocks) {
      showToast("적용할 시뮬레이션 시간표가 없습니다.")
      return
    }
    const nextBlocks = [...localSimData.scheduleBlocks]
    saveBlocks(nextBlocks)
    showToast("추천 시간표 시뮬레이션 결과가 한 번에 적용되었습니다!")
  }

  // [신규 2] 추천 과목 카드별 개별 추가 핸들러
  const handleAddToSchedule = (course: RecommendedCourse, e: React.MouseEvent) => {
    e.stopPropagation()

    const matched = allCourses?.find(c => {
      const targetId = String(course.code || "");
      return String(c.course_id || "") === targetId ||
             String(c.code || "") === targetId ||
             String(c.id || "") === targetId;
    })

    // 1. 중복 체크
    const courseName = course.name || matched?.title || matched?.name || course.code || "과목명 미정"
    const cleanCourseName = courseName.trim().toLowerCase()
    const isDuplicate = customBlocks.some(b => b.name.trim().toLowerCase() === cleanCourseName)
    if (isDuplicate) {
      showToast(`'${courseName}' 과목은 이미 시간표에 등록되어 있습니다.`)
      return
    }

    // 2. 추천 과목에 매칭되는 시뮬레이션 schedules 직접 상속
    let schedules = (course as any).schedules || []

    if (schedules.length === 0) {
      const rawSchedules = matched?.schedules || []
      
      // 단일 분반 시간대만 추출하여 타 분반 누적 충돌 방지
      if (rawSchedules.length > 0) {
        const firstClassroom = rawSchedules[0].classroom || "미정"
        const filteredByClassroom = rawSchedules.filter((s: any) => (s.classroom || "미정") === firstClassroom)
        
        const uniqueSet: any[] = []
        const seenScheduleKeys = new Set<string>()
        filteredByClassroom.forEach((s: any) => {
          const key = `${s.day}-${s.start_time}-${s.end_time}`
          if (!seenScheduleKeys.has(key)) {
            seenScheduleKeys.add(key)
            uniqueSet.push(s)
          }
        })
        schedules = uniqueSet
      }
    }

    if (schedules.length === 0) {
      const timeStr = course.time || ""
      const day = timeStr.charAt(0)
      const range = timeStr.slice(1).trim()
      if (day && range.includes("~")) {
        const [start_time, end_time] = range.split("~").map(x => x.trim())
        schedules = [{ day, start_time, end_time, classroom: "강의실 미정" }]
      } else {
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
    const profName = course.professor || matched?.professor || matched?.professor_name || (course as any).professor_name || "미지정"

    normalizedSchedules.forEach((s: any, sIdx: number) => {
      const start = timeToHoursValue(s.start_time)
      const end = timeToHoursValue(s.end_time)

      newBlocks.push({
        id: `rec-chat-block-${String(course.code || "")}-${s.day}-${s.start_time}-${sIdx}`,
        groupId: String(course.code || ""), // 분반 그룹 단위 일괄 제어를 위한 groupId 바인딩
        name: courseName,
        day: s.day,
        start: start,
        span: end - start,
        room: s.classroom || matched?.classroom || (course as any).room || "미정",
        professor: profName,
        colorIndex: (customBlocks.length + newBlocks.length) % 3
      })
    })

    const nextBlocks = [...customBlocks, ...newBlocks]
    saveBlocks(nextBlocks)
    showToast(`'${courseName}' 과목이 시간표에 추가되었습니다.`)
  }

  // 동적 통계 데이터 실시간 계산
  let freeDayText = "공강 없음"
  let courseCount = 0
  let totalCreditsText = "0"
  let displayReasons: any[] = []

  if (localSimData) {
    const prefs = localSimData.preferences
    if (prefs && Array.isArray(prefs.freeDays)) {
      freeDayText = prefs.freeDays.length > 0 ? `${prefs.freeDays.join(", ")} 공강` : "공강 없음"
    } else {
      const blocks = localSimData.scheduleBlocks || []
      const days = localSimData.scheduleDays || ["월", "화", "수", "목", "금"]
      const actDays = new Set(blocks.map((b: any) => dayStringToNum(b.day)))
      const freeD = days.filter((_, idx) => !actDays.has(idx))
      freeDayText = freeD.length > 0 ? `${freeD.join(", ")} 공강` : "공강 없음"
    }

    const uniqueC = Array.from(new Set((localSimData.scheduleBlocks || []).map((b: any) => b.name)))
    courseCount = uniqueC.length
    totalCreditsText = localSimData.totalCredits !== undefined ? String(localSimData.totalCredits) : String(courseCount * 3)
    displayReasons = localSimData.scheduleReasons || []
  } else {
    // 디폴트 밸런스 시간표 정보 적용
    const blocks = schedule?.scheduleBlocks || []
    const days = schedule?.scheduleDays || ["월", "화", "수", "목", "금"]
    const actDays = new Set(blocks.map((b: any) => dayStringToNum(b.day)))
    const freeD = days.filter((_, idx) => !actDays.has(idx))
    freeDayText = freeD.length > 0 ? `${freeD.join(", ")} 공강` : "공강 없음"

    const uniqueC = Array.from(new Set(blocks.map((b: any) => b.name)))
    courseCount = uniqueC.length
    totalCreditsText = String(courseCount * 3)
    displayReasons = schedule?.scheduleReasons || []
  }

  const [retakeCourse, setRetakeCourse] = useState<RecommendedCourse | null>(null)
  const [inputText, setInputText] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  // 융합/특화 전공 설정 상태 및 모달 제어
  const [majorPrefs, setMajorPrefs] = useState<{ convergenceMajor?: string; specializedTrack?: string } | null>(null)
  const [showEasySetting, setShowEasySetting] = useState(false)
  const [easyConv, setEasyConv] = useState("")
  const [easySpec, setEasySpec] = useState("")

  const loadMajorPrefs = () => {
    if (typeof window !== "undefined") {
      const prefKey = `grad_major_preferences_${activeStudentId}`
      const stored = sessionStorage.getItem(prefKey)
      if (stored) {
        try {
          setMajorPrefs(JSON.parse(stored))
        } catch {
          setMajorPrefs(null)
        }
      } else {
        setMajorPrefs(null)
      }
    }
  }

  useEffect(() => {
    loadMajorPrefs()
    window.addEventListener("focus", loadMajorPrefs)
    return () => window.removeEventListener("focus", loadMajorPrefs)
  }, [activeStudentId])

  useEffect(() => {
    if (showEasySetting && majorPrefs) {
      setEasyConv(majorPrefs.convergenceMajor || "")
      setEasySpec(majorPrefs.specializedTrack || "")
    }
  }, [showEasySetting, majorPrefs])

  const handleSaveEasy = async () => {
    const nextPrefs = { convergenceMajor: easyConv, specializedTrack: easySpec }
    if (typeof window !== "undefined") {
      const prefKey = `grad_major_preferences_${activeStudentId}`
      sessionStorage.setItem(prefKey, JSON.stringify(nextPrefs))
    }
    setMajorPrefs(nextPrefs)
    
    // 백엔드 프로필 DB 동기화
    try {
      const name = user?.userInfo?.name || ""
      const dept = user?.userInfo?.department || ""
      const mileage = user?.userInfo?.mileage || 0
      const sem = user?.userInfo?.currentSemester || 8
      
      const tracks: string[] = []
      if (easyConv) tracks.push(easyConv)
      if (easySpec) tracks.push(easySpec)
      
      await updateProfile(name, activeStudentId, dept, mileage, sem, tracks)
    } catch (err) {
      console.error("Failed to sync major tracks to backend:", err)
    }

    setShowEasySetting(false)
    if (refreshData) refreshData()
  }

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim() || isLoading) return

    const userMsg: Message = {
      id: `msg-${Date.now()}-user`,
      role: "user",
      content: inputText,
    }

    if (setMessages) {
      setMessages((prev) => [...prev, userMsg])
    }
    setInputText("")
    setIsLoading(true)

    try {
      const formattedHistory = messages
        .filter((m) => m.id !== "welcome")
        .map((m) => ({
          role: m.role === "user" ? ("user" as const) : ("assistant" as const),
          content: m.content,
        }))
      
      const chatResult = await sendChatMessage(userMsg.content, formattedHistory, selectedSemester, user?.userInfo?.department)
      
      const aiMsg: Message = {
        id: `msg-${Date.now()}-ai`,
        role: "ai",
        content: chatResult.message,
      }
      if (setMessages) {
        setMessages((prev) => [...prev, aiMsg])
      }

      // 원칙 4: 백엔드에서 반환된 structured_data가 있을 경우 UI 시뮬레이션 데이터와 동기화
      if (chatResult.structured_data && chatResult.structured_data.recommendations?.length > 0 && setSimulatedSchedule) {
        const sd = chatResult.structured_data
        // 기존 simulated_timetable가 있으면 그걸 우선 사용하고, 없으면 structured_data로 구성
        if (!chatResult.simulated_timetable?.scheduleBlocks || chatResult.simulated_timetable.scheduleBlocks.length === 0) {
          // structured_data로부터 시뮬레이션 시간표 블록 구성
          const dayMap: Record<string, number> = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 }
          const scheduleBlocks: any[] = []
          const pastelPalette = [
            { bg: "bg-[#e8f3ff]", text: "text-[#1b64da]", bar: "bg-[#3182f6]" },
            { bg: "bg-[#daf2ee]", text: "text-[#008f80]", bar: "bg-[#00b5a3]" },
            { bg: "bg-[#fff3f5]", text: "text-[#d6284a]", bar: "bg-[#f04452]" },
            { bg: "bg-[#f4edff]", text: "text-[#6b31f6]", bar: "bg-[#8f5cf0]" },
            { bg: "bg-[#fffae8]", text: "text-[#b08b00]", bar: "bg-[#ffc900]" },
          ]

          sd.recommendations.forEach((rec: any, idx: number) => {
            const color = pastelPalette[idx % pastelPalette.length]
            ;(rec.time_slots || []).forEach((slot: any[]) => {
              const [day, start, end] = slot
              if (dayMap[day] !== undefined) {
                const [sh, sm] = start.split(":").map(Number)
                const [eh, em] = end.split(":").map(Number)
                const startH = sh + sm / 60
                const endH = eh + em / 60
                scheduleBlocks.push({
                  id: `structured-${rec.code}-${day}-${start}-${end}`,
                  name: rec.name,
                  professor: rec.professor || "미정",
                  room: "미정",
                  day: dayMap[day],
                  start: startH,
                  end: endH,
                  span: endH - startH,
                  color: color.bg,
                  textColor: color.text,
                })
              }
            })
          })

          const structuredTimetable = {
            scheduleDays: ["월", "화", "수", "목", "금"],
            scheduleHours: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            scheduleBlocks,
            scheduleReasons: sd.recommendations.map((rec: any) => ({
              icon: "Sparkles",
              title: `${rec.name} (${rec.code})`,
              desc: rec.reason || "추천 과목",
            })),
            pastelPalette,
            totalCredits: sd.total_credits || 0,
            courseCount: sd.recommendations.length,
            preferences: {
              freeDays: sd.free_days || [],
              preferredDays: ["월", "화", "수", "목", "금"],
              avoidMorning: false,
              preferAfternoon: false,
            },
          }
          setSimulatedSchedule(structuredTimetable)
          if (typeof window !== "undefined") {
            const simulatedTimetableKey = `grad_simulated_timetable_${activeStudentId}_${selectedSemester}`
            const simulationAppliedKey = `chatbot_simulation_applied_${activeStudentId}_${selectedSemester}`
            const aiRecommendedTimetableKey = `grad_manager_ai_recommended_timetable_${activeStudentId}_${selectedSemester}`
            sessionStorage.setItem(simulatedTimetableKey, JSON.stringify(structuredTimetable))
            sessionStorage.setItem(simulationAppliedKey, "true")
            localStorage.setItem(aiRecommendedTimetableKey, JSON.stringify(structuredTimetable))
          }
        } else {
          // 기존 simulated_timetable이 있으면 그걸 사용
          const timetable = chatResult.simulated_timetable
          if (timetable.scheduleBlocks && timetable.scheduleBlocks.length > 0) {
            setSimulatedSchedule(timetable)
            if (typeof window !== "undefined") {
              const simulatedTimetableKey = `grad_simulated_timetable_${activeStudentId}_${selectedSemester}`
              const simulationAppliedKey = `chatbot_simulation_applied_${activeStudentId}_${selectedSemester}`
              const aiRecommendedTimetableKey = `grad_manager_ai_recommended_timetable_${activeStudentId}_${selectedSemester}`
              sessionStorage.setItem(simulatedTimetableKey, JSON.stringify(timetable))
              sessionStorage.setItem(simulationAppliedKey, "true")
              localStorage.setItem(aiRecommendedTimetableKey, JSON.stringify(timetable))
            }
          }
        }
      } else if (chatResult.simulated_timetable && setSimulatedSchedule) {
        // structured_data가 없으면 기존 방식대로 simulated_timetable 사용
        const timetable = chatResult.simulated_timetable
        const hasBlocks = timetable.scheduleBlocks && timetable.scheduleBlocks.length > 0
        if (hasBlocks) {
          setSimulatedSchedule(timetable)
          if (typeof window !== "undefined") {
            const simulatedTimetableKey = `grad_simulated_timetable_${activeStudentId}_${selectedSemester}`
            const simulationAppliedKey = `chatbot_simulation_applied_${activeStudentId}_${selectedSemester}`
            const aiRecommendedTimetableKey = `grad_manager_ai_recommended_timetable_${activeStudentId}_${selectedSemester}`
            sessionStorage.setItem(simulatedTimetableKey, JSON.stringify(timetable))
            sessionStorage.setItem(simulationAppliedKey, "true")
            localStorage.setItem(aiRecommendedTimetableKey, JSON.stringify(timetable))
          }
        }
      }
    } catch (err) {
      const errMsg: Message = {
        id: `msg-${Date.now()}-err`,
        role: "ai",
        content: "분석을 처리하는 중 오류가 발생했습니다. 다시 시도해 주세요.",
      }
      if (setMessages) {
        setMessages((prev) => [...prev, errMsg])
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelect = (course: RecommendedCourse) => {
    if (course.retake) setRetakeCourse(course)
  }

  const coursesToRender = localSimData && localSimData.courses ? localSimData.courses : recommendedCourses

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card px-4 py-4 shrink-0 shadow-sm">
        <div className="mx-auto w-full max-w-4xl flex items-center justify-between gap-4">
          <div className="text-left">
            <h1 className="flex items-center gap-2 text-lg font-bold text-foreground">
              <Sparkles className="h-5 w-5 text-primary" />
              AI 수강 추천 &amp; 상담
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">조건을 말씀하시면 최적의 과목과 시간표를 추천해 드립니다</p>
          </div>
          {/* 학기 선택기 드롭다운 추가 */}
          <div className="flex items-center gap-1.5 shrink-0 bg-secondary/40 px-3 py-1.8 rounded-xl border border-border/50">
            <span className="text-[10px] font-black text-muted-foreground shrink-0">학기 선택:</span>
            <select
              value={selectedSemester}
              onChange={(e) => handleSemesterChange(e.target.value)}
              className="rounded-lg bg-card border border-border px-2 py-1 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6] cursor-pointer font-bold"
            >
              {(semesters.length > 0 ? semesters : SEMESTER_OPTIONS).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 융합/특화 전공 상태 배너 (Toss UI 스타일) */}
      <div className="bg-[#f2f4f6] dark:bg-[#18212c] px-4 py-2.5 shrink-0 border-b border-border transition-colors">
        <div className="mx-auto w-full max-w-4xl flex items-center justify-between flex-wrap gap-2 text-[11px] md:text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground font-semibold">
            <Sparkles className="h-3.5 w-3.5 text-primary animate-pulse" />
            <span>AI 맞춤 전공 설정:</span>
            {majorPrefs?.convergenceMajor || majorPrefs?.specializedTrack ? (
              <div className="flex gap-1.5 flex-wrap">
                {majorPrefs.convergenceMajor && (
                  <span className="bg-primary/10 text-primary px-2.5 py-0.5 rounded-full font-bold">
                    {majorPrefs.convergenceMajor}
                  </span>
                )}
                {majorPrefs.specializedTrack && (
                  <span className="bg-[#8f5cf0]/10 text-[#8f5cf0] dark:text-[#a880f7] px-2.5 py-0.5 rounded-full font-bold">
                    {majorPrefs.specializedTrack}
                  </span>
                )}
              </div>
            ) : (
              <span className="text-destructive font-bold">설정되지 않음 (일반 주전공만 반영)</span>
            )}
          </div>
          
          <button 
            type="button"
            onClick={() => setShowEasySetting(true)}
            className="text-primary hover:underline font-bold cursor-pointer select-none"
          >
            {majorPrefs?.convergenceMajor || majorPrefs?.specializedTrack ? "변경하기" : "지금 설정하기"}
          </button>
        </div>
      </div>

      {/* Chat scroll area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto bg-[#f9fafb] dark:bg-[#0f151c] px-4 py-6">
        <div className="mx-auto w-full max-w-4xl space-y-6">
          <AnimatePresence>
            {messages.map((msg) => (
              <ChatBubble key={msg.id} role={msg.role}>
                {msg.content}
              </ChatBubble>
            ))}
          </AnimatePresence>

          {isLoading && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-2.5"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="h-4 w-4 text-primary" />
              </span>
              <div className="flex items-center gap-2 max-w-[80%] rounded-2xl rounded-tl-sm bg-card border border-border px-4 py-3 text-sm text-muted-foreground shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>답변을 생성하고 있어요…</span>
              </div>
            </motion.div>
          )}

          {/* Simulation summary card */}
          <div className="ml-9.5">
            <AnimatePresence mode="wait">
              {simLoading ? (
                <motion.div 
                  key="sim-loading"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex items-center gap-3 rounded-2xl bg-card border border-border p-5 shadow-sm"
                >
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">시뮬레이션을 실행하는 중…</span>
                </motion.div>
              ) : simDone ? (
                <motion.div 
                  key="sim-done"
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-2xl border border-border bg-card p-5 shadow-md shadow-primary/5 hover:shadow-lg transition-all duration-300 space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-[15px] font-bold text-foreground">
                      <CheckCircle2 className="h-4.5 w-4.5 text-[#3182f6]" />
                      추천 시간표 시뮬레이션
                    </span>
                    <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                      적합도 {localSimData ? 100 : 95}%
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <SummaryStat label="공강일" value={freeDayText} />
                    <SummaryStat label="총 학점" value={`${totalCreditsText}학점`} />
                    <SummaryStat label="과목 수" value={`${courseCount}개`} />
                  </div>

                  {/* 미니 시간표 그리드 시각화 */}
                  {localSimData && localSimData.scheduleBlocks && localSimData.scheduleBlocks.length > 0 && (
                    <div className="border border-border/80 rounded-2xl p-3 bg-secondary/20 space-y-2 select-none overflow-x-auto">
                      <div className="grid grid-cols-[30px_repeat(5,1fr)] min-w-[280px] w-full [--mini-row-h:20px]">
                        <div />
                        {["월", "화", "수", "목", "금"].map((d) => (
                          <div key={d} className="text-center text-[10px] font-bold text-muted-foreground pb-1">
                            {d}
                          </div>
                        ))}
                        {/* 시간 라벨 열 및 그리드 */}
                        <div className="relative pr-1 pt-0.5 flex flex-col justify-between h-[180px] text-right text-[8px] text-muted-foreground/60 font-mono">
                          {[9, 11, 13, 15, 17].map((h) => (
                            <div key={h} className="leading-none" style={{ height: "calc(var(--mini-row-h) * 2)" }}>
                              {h}:00
                            </div>
                          ))}
                        </div>
                        {/* 요일별 컬럼 */}
                        {["월", "화", "수", "목", "금"].map((day, dayIdx) => (
                          <div key={day} className="relative border-l border-border/40 h-[180px] bg-secondary/5">
                            {/* gridlines */}
                            {[9, 10, 11, 12, 13, 14, 15, 16, 17].map((h) => (
                              <div key={h} className="border-b border-border/30 h-[var(--mini-row-h)]" />
                            ))}
                            {/* 과목 블록들 */}
                            {localSimData.scheduleBlocks
                              .filter((b: any) => {
                                let bDay = b.day;
                                if (typeof bDay === "string") {
                                  const mapping: Record<string, number> = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 }
                                  bDay = mapping[bDay] !== undefined ? mapping[bDay] : -1
                                }
                                return bDay === dayIdx
                              })
                              .map((b: any) => {
                                const startHour = Number(b.start)
                                const offset = startHour >= 9 ? (startHour - 9) : 0
                                const span = Number(b.span) || 1.5
                                return (
                                  <div
                                    key={b.id}
                                    className={`absolute inset-x-0.5 rounded-lg p-1 overflow-hidden text-[8px] leading-tight font-extrabold border border-white/25 dark:border-white/5 shadow-sm ${
                                      b.color || "bg-blue-100"
                                    } ${b.textColor || "text-blue-700"}`}
                                    style={{
                                      top: `calc(${offset} * var(--mini-row-h) + 1px)`,
                                      height: `calc(${span} * var(--mini-row-h) - 2px)`
                                    }}
                                    title={`${b.name} (${b.professor})`}
                                  >
                                    <p className="truncate">{b.name}</p>
                                    <p className="truncate opacity-75">{b.professor}</p>
                                  </div>
                                )
                              })}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <ul className="space-y-2.5 border-t border-border pt-4">
                    {displayReasons.filter(r => r && r.title).map((r, i) => {
                      const Icon = reasonIconMap[r.icon] ?? Sparkles
                      return (
                        <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                          <Icon className="h-4 w-4 text-[#3182f6] shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold text-foreground mr-1">{r.title}:</span>
                            {r.desc}
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                  {onOpenSchedule && (
                    <button
                      type="button"
                      onClick={onOpenSchedule}
                      className="w-full mt-3 py-2.5 rounded-xl text-xs font-bold bg-[#3182f6] text-white hover:bg-[#1b64da] active:scale-95 transition-all cursor-pointer shadow-sm text-center flex items-center justify-center gap-1.5"
                    >
                      <Sparkles className="h-4 w-4" />
                      <span>추천 시간표 확인하러 가기</span>
                    </button>
                  )}
                </motion.div>
              ) : null}
            </AnimatePresence>

          </div>

          {/* Recommended course list */}
          {simDone && (
            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="ml-9.5 space-y-3"
            >
              <p className="text-xs font-semibold text-muted-foreground">추천 과목 목록</p>
              <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
                {coursesToRender.map((course) => {
                  const isAdded = customBlocks.some(b => b.name.trim().toLowerCase() === course.name.trim().toLowerCase())
                  return (
                    <div
                      key={course.id}
                      onClick={() => handleSelect(course)}
                      className="w-full rounded-2xl bg-card border border-border p-4.5 text-left shadow-sm transition-all hover:bg-secondary hover:border-transparent hover:shadow-md flex flex-col justify-between cursor-pointer"
                    >
                      <div className="flex items-start justify-between gap-2.5 w-full">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-foreground truncate">{course.name}</span>
                            {course.retake ? (
                              <span className="flex items-center gap-0.5 rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] font-semibold text-destructive shrink-0">
                                <RotateCcw className="h-3 w-3" />
                                재수강
                              </span>
                            ) : null}
                          </div>
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
                              : course.time || "시간 미정"

                            return (
                              <p className="text-xs text-muted-foreground mt-1.5 font-medium leading-relaxed">
                                🕒 {timeText} · {course.professor || "미지정"}교수 ({course.credit}학점)
                              </p>
                            )
                          })()}
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-base font-bold text-[#3182f6]">{course.match}%</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">적합도</p>
                        </div>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-1.5">
                        {course.tags.map((t) => (
                          <span
                            key={t}
                            className={`rounded px-2.5 py-0.5 text-[10px] font-bold ${tagStyle[t] ?? "bg-secondary text-muted-foreground"}`}
                          >
                            {t}
                          </span>
                        ))}
                      </div>

                      {/* [신규] 개별 추가/추가됨 액션 버튼 */}
                      <div className="mt-4 pt-3 border-t border-border/40 flex justify-end">
                        {isAdded ? (
                          <button
                            type="button"
                            disabled
                            className="w-full py-2 px-4 rounded-xl text-[10px] font-extrabold bg-[#3182f6]/10 text-[#3182f6] border border-[#3182f6]/20 cursor-not-allowed text-center"
                          >
                            ✓ 시간표에 추가됨
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={(e) => handleAddToSchedule(course, e)}
                            className="w-full py-2 px-4 rounded-xl text-[10px] font-extrabold bg-[#3182f6] text-white hover:bg-[#1b64da] active:scale-95 transition-all text-center cursor-pointer shadow-sm"
                          >
                            + 시간표에 추가
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Input bar */}
      <form onSubmit={handleSendMessage} className="border-t border-border bg-card px-4 py-3.5 shrink-0 shadow-lg">
        <div className="mx-auto w-full max-w-4xl flex items-center gap-2 rounded-full bg-secondary px-4.5 py-2.5 border border-transparent focus-within:border-primary/25 transition-all">
          <input
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            placeholder="수강 조건을 입력하세요 (예: 금요일 공강 해줘, 전공 필수 추천)"
            aria-label="추천 조건 입력"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="flex h-8.5 w-8.5 items-center justify-center rounded-full bg-[#3182f6] text-white transition-opacity disabled:opacity-50 cursor-pointer"
            aria-label="메시지 전송"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Retake warning modal (TDS Dialog Style) */}
      <AnimatePresence>
        {retakeCourse && (
          <div
            className="absolute inset-0 z-30 flex items-end md:items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            onClick={() => setRetakeCourse(null)}
          >
            <motion.div
              initial={{ opacity: 0, y: 50, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.95 }}
              className="w-full max-w-md rounded-[2.5rem] bg-card p-6 shadow-xl border border-border"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-start justify-between">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
                  <AlertTriangle className="h-6.5 w-6.5 text-destructive" />
                </span>
                <button
                  onClick={() => setRetakeCourse(null)}
                  aria-label="닫기"
                  className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  <X className="h-5.5 w-5.5" />
                </button>
              </div>
              <h3 className="text-lg font-bold text-foreground">재수강 과목 선택 확인</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                <span className="font-bold text-foreground">{retakeCourse.name}</span>은(는) 재수강
                과목입니다. 수강 시 <span className="font-semibold text-destructive">이전 취득 학점은 포기
                처리됩니다.</span> 계속하시겠어요?
              </p>
              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => setRetakeCourse(null)}
                  className="flex-1 rounded-2xl bg-secondary py-3.5 text-[15px] font-semibold text-secondary-foreground hover:opacity-90 h-[48px] cursor-pointer"
                >
                  취소
                </button>
                <button
                  onClick={() => setRetakeCourse(null)}
                  className="flex-1 rounded-2xl bg-destructive py-3.5 text-[15px] font-semibold text-white hover:opacity-90 h-[48px] cursor-pointer"
                >
                  이해했어요
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 융합/특화 전공 간편 설정 모달 (Toss UI 스타일) */}
      <AnimatePresence>
        {showEasySetting && (
          <div
            className="absolute inset-0 z-40 flex items-end md:items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            onClick={() => setShowEasySetting(false)}
          >
            <motion.div
              initial={{ opacity: 0, y: 50, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.95 }}
              className="w-full max-w-md rounded-[2.5rem] bg-card p-6 shadow-2xl border border-border"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-center justify-between border-b border-border pb-3">
                <h3 className="text-lg font-bold text-foreground">AI 전공/트랙 설정</h3>
                <button
                  onClick={() => setShowEasySetting(false)}
                  className="rounded-full p-1 hover:bg-secondary transition-colors"
                >
                  <X className="h-5.5 w-5.5 text-muted-foreground" />
                </button>
              </div>

              <div className="space-y-4">
                {/* 융합전공 */}
                <div>
                  <label className="text-xs font-bold text-muted-foreground block mb-1">융합전공 선택</label>
                  <div className="relative">
                    <select
                      value={easyConv}
                      onChange={(e) => {
                        const val = e.target.value
                        setEasyConv(val)
                        if (val !== "") {
                          setEasySpec("")
                        }
                      }}
                      className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3 text-sm text-foreground appearance-none cursor-pointer"
                    >
                      <option value="">선택 안 함 (일반 전공)</option>
                      {CONVERGENCE_MAJORS.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                      <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>

                {/* 특화트랙 */}
                <div>
                  <label className="text-xs font-bold text-muted-foreground block mb-1">특화트랙 선택</label>
                  <div className="relative">
                    <select
                      value={easySpec}
                      onChange={(e) => {
                        const val = e.target.value
                        setEasySpec(val)
                        if (val !== "") {
                          setEasyConv("")
                        }
                      }}
                      className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3 text-sm text-foreground appearance-none cursor-pointer"
                    >
                      <option value="">선택 안 함 (일반 트랙)</option>
                      {SPECIALIZED_TRACKS.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                      <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => setShowEasySetting(false)}
                  className="flex-1 rounded-2xl bg-secondary py-3 text-sm font-semibold text-secondary-foreground hover:opacity-90 h-[44px]"
                >
                  취소
                </button>
                <button
                  onClick={handleSaveEasy}
                  className="flex-1 rounded-2xl bg-primary py-3 text-sm font-semibold text-white hover:bg-primary-hover h-[44px]"
                >
                  저장하기
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ChatBubble({ role, children }: { role: "ai" | "user"; children: React.ReactNode }) {
  const isUser = role === "user"
  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} items-start gap-2.5`}
    >
      {!isUser && (
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="h-4 w-4 text-primary" />
        </span>
      )}
      <div 
        className={`max-w-[80%] rounded-2xl leading-relaxed shadow-sm px-4 py-3 text-sm font-medium ${
          isUser 
            ? "rounded-tr-sm bg-[#3182f6] text-white" 
            : "rounded-tl-sm bg-card border border-border text-foreground"
        }`}
      >
        {children}
      </div>
    </motion.div>
  )
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-secondary p-3 text-center border border-transparent">
      <p className="text-[15px] font-bold text-foreground">{value}</p>
      <p className="text-[10px] text-muted-foreground mt-0.5 font-semibold">{label}</p>
    </div>
  )
}
