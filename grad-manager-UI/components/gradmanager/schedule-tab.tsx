"use client"

import { useState, useEffect, useMemo, useRef } from "react"
import { 
  BrainCircuit, 
  CalendarOff, 
  Clock, 
  GraduationCap, 
  Sparkles, 
  X, 
  Plus, 
  Trash2,
  Check,
  Search,
  Loader2,
  type LucideIcon 
} from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { motion, AnimatePresence } from "framer-motion"
import { saveUserSchedule, getUserSchedule, searchCourseOfferings } from "@/lib/api"

const reasonIconMap: Record<string, LucideIcon> = {
  CalendarOff,
  BrainCircuit,
  GraduationCap,
  Clock,
  Sparkles,
}

// 학기 선택용 상수 정의 (23-1 ~ 26-2 및 계절학기)
const SEMESTER_OPTIONS = [
  "2026-2학기",
]

const ROW_H = 52 // px per hour row

// 학수코드 접두사 제거 헬퍼 함수
const cleanCourseName = (name: string): string => {
  if (!name) return ""
  return name.replace(/^[A-Z0-9]+(?:\s*-\s*|\s+)/, "").trim()
}

const FALLBACK_SCHEDULE_BLOCKS = [
  { id: "s1", name: "머신러닝", day: 0, start: 1, span: 2, room: "율곡관 302", colorIndex: 0 },
  { id: "s2", name: "머신러닝", day: 2, start: 0, span: 2, room: "율곡관 302", colorIndex: 0 },
  { id: "s3", name: "데이터베이스", day: 1, start: 4, span: 2, room: "만우관 111", colorIndex: 1 },
  { id: "s4", name: "데이터베이스", day: 3, start: 4, span: 2, room: "만우관 111", colorIndex: 1 },
  { id: "s5", name: "융합캡스톤", day: 3, start: 6, span: 2, room: "장공관 210", colorIndex: 2 },
  { id: "s6", name: "확률과 통계", day: 0, start: 4, span: 2, room: "필헌관 405", colorIndex: 3 },
  { id: "s7", name: "확률과 통계", day: 2, start: 4, span: 2, room: "필헌관 405", colorIndex: 3 },
]

const validateBlocks = (blocks: any[]): boolean => {
  if (!Array.isArray(blocks) || blocks.length === 0) return false
  return blocks.every(b => (
    b &&
    typeof b.id === "string" &&
    typeof b.name === "string" &&
    (typeof b.day === "number" || typeof b.day === "string") &&
    typeof b.start === "number"
  ))
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

const timeToHoursValue = (timeStr: string): number => {
  if (!timeStr) return 9
  const [h, m] = timeStr.split(":").map(Number)
  return h + m / 60
}

// [신규] 결합 적재된 요일/시간 문자열("월,수", "09:30,09:30")을 개별 스케줄 구조로 정교하게 분할 및 쪼개기
const normalizeSchedules = (rawSchedules: any[]): any[] => {
  console.log("[AUDIT DEBUG] normalizeSchedules rawInput:", rawSchedules)
  const normalized: any[] = []
  if (!rawSchedules || rawSchedules.length === 0) {
    console.log("[AUDIT DEBUG] normalizeSchedules empty rawSchedules")
    return normalized
  }

  rawSchedules.forEach((s: any) => {
    const dayStr = String(s.day || "")
    const startStr = String(s.start_time || "")
    const endStr = String(s.end_time || "")
    const roomStr = String(s.classroom || s.room || "")

    // 요일(시작시간~종료시간) 패턴 검사용 정규식
    // 예: "금요일(16:00~17:15)", "화(11:00~12:15)"
    const bracketRegex = /([월화수목금토일])요일?\s*\(\s*(\d{2}:\d{2})\s*~\s*(\d{2}:\d{2})\s*\)/g
    const combinedStr = `${dayStr} ${startStr} ${endStr}`
    
    const matches: any[] = []
    let match
    while ((match = bracketRegex.exec(combinedStr)) !== null) {
      matches.push({
        day: match[1],
        start_time: match[2],
        end_time: match[3],
        classroom: roomStr || "미정",
        section: s.section || null,
        professor: s.professor || null,
        isDummy: s.isDummy || false
      })
    }

    if (matches.length > 0) {
      normalized.push(...matches)
      return
    }

    // 괄호식 패턴이 감지되지 않으면 기존의 콤마/슬래시 구분 파싱 로직 수행
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
        classroom: r,
        section: s.section || null,
        professor: s.professor || null,
        isDummy: s.isDummy || false
      })
    }
  })

  console.log("[AUDIT DEBUG] normalizeSchedules output:", normalized)
  return normalized
}

// [신규] 원시 개설 과목의 오염된 다중 일정 데이터(예: 여러 분반 일정이 하나로 뭉쳐져 있는 경우)를
// 데이터베이스에 등록된 실제 분반(section) 단위 기준으로 깔끔하게 1:1 분류하는 헬퍼 함수
const splitPollutedCourseToSections = (course: any): any[] => {
  const rawSchedules = course.schedules || []
  
  // [보완] schedules가 아예 없거나 빈 경우 가상 덤프 스케줄을 채워서 반환
  if (rawSchedules.length === 0) {
    const fallbackSchedule = {
      day: "월",
      start_time: "09:00",
      end_time: "10:30",
      classroom: course.room || "미정",
      section: course.section || "01",
      professor: course.professor || course.professor_name || "미정",
      isDummy: true
    }
    return [{
      ...course,
      schedules: [fallbackSchedule],
      time_slots: [["월", "09:00", "10:30"]]
    }]
  }

  // 개별 스케줄 목록 정규화
  const normalized = normalizeSchedules(rawSchedules)
  if (normalized.length === 0) {
    const fallbackSchedule = {
      day: "월",
      start_time: "09:00",
      end_time: "10:30",
      classroom: course.room || "미정",
      section: course.section || "01",
      professor: course.professor || course.professor_name || "미정",
      isDummy: true
    }
    return [{
      ...course,
      schedules: [fallbackSchedule],
      time_slots: [["월", "09:00", "10:30"]]
    }]
  }

  // schedules 내의 section 식별자 및 교수 정보 기준으로 복합 그룹화하여 분반 단위로 정밀 복원
  const groups: Record<string, any[]> = {}
  normalized.forEach((s: any) => {
    const secVal = s.section ? String(s.section).trim() : "01"
    const profVal = s.professor ? String(s.professor).trim() : "미정"
    const secKey = `${secVal}_${profVal}`
    if (!groups[secKey]) {
      groups[secKey] = []
    }
    groups[secKey].push(s)
  })

  const groupKeys = Object.keys(groups)
  if (groupKeys.length <= 1) {
    const secTimeSlots = normalized.map((s: any) => [s.day, s.start_time, s.end_time])
    const firstSlot = normalized[0] || {}
    const secVal = firstSlot.section ? String(firstSlot.section).trim() : "01"
    const profVal = firstSlot.professor || course.professor || "미정"
    
    const originalId = course.course_id || course.code || course.id || "SEC"
    const cleanOrigId = originalId.includes("-") ? originalId.split("-")[0] : originalId
    const newSecId = `${cleanOrigId}-${secVal}`

    return [{
      ...course,
      course_id: newSecId,
      code: newSecId,
      professor: profVal,
      schedules: normalized,
      time_slots: secTimeSlots
    }]
  }

  // 여러 분반(section/professor 조합)이 섞여 있는 경우 각각 독립된 분반 객체로 분할
  return groupKeys.map((secKey) => {
    const [secVal, profVal] = secKey.split("_")
    const originalId = course.course_id || course.code || course.id || "SEC"
    const cleanOrigId = originalId.includes("-") ? originalId.split("-")[0] : originalId
    const newSecId = `${cleanOrigId}-${secVal}`

    const secSchedules = groups[secKey]
    const secTimeSlots = secSchedules.map((s: any) => [s.day, s.start_time, s.end_time])

    return {
      ...course,
      course_id: newSecId,
      code: newSecId,
      professor: profVal, // 담당 교수 1:1 매핑
      schedules: secSchedules,
      time_slots: secTimeSlots // 연관 time_slots 1:1 매핑 보존
    }
  })
}


export function ScheduleTab() {
  const { 
    schedule, 
    refreshData, 
    simulatedSchedule, 
    resetSimulation, 
    allCourses, 
    user,
    selectedSemester = "2026-2학기",
    setSelectedSemester,
    semesters = []
  } = useGradData()
  const { showToast } = useToast()

  const studentId = user?.userInfo?.studentId || "20210001"

  const [displayFilter, setDisplayFilter] = useState<"room" | "professor" | "both" | "name">(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("grad_timetable_display_filter")
      if (stored === "room" || stored === "professor" || stored === "both" || stored === "name") {
        return stored
      }
    }
    return "both"
  })

  const handleDisplayFilterChange = (filter: "room" | "professor" | "both" | "name") => {
    setDisplayFilter(filter)
    if (typeof window !== "undefined") {
      localStorage.setItem("grad_timetable_display_filter", filter)
    }
  }

  useEffect(() => {
    // 탭 진입 시 최신 개인화 시간표 갱신 호출
    if (refreshData) {
      refreshData()
    }
  }, [])

  const hasSimulatedSchedule = simulatedSchedule !== null
  // AI 추천 시간표가 있을 경우 scheduleReasons(과목별 추천 사유)를 우선 사용
  const activeSchedule = simulatedSchedule?.scheduleReasons
    ? { ...schedule, scheduleReasons: simulatedSchedule.scheduleReasons }
    : schedule

  // 호버된 분반(groupId) 상태 관리
  const [hoveredGroupId, setHoveredGroupId] = useState<string | null>(null)

  // 학기 변경 시 localStorage 갱신 및 전역 상태 갱신 처리
  const handleSemesterChange = (newSem: string) => {
    if (setSelectedSemester) {
      setSelectedSemester(newSem)
    }
    if (typeof window !== "undefined") {
      localStorage.setItem(`grad_last_viewed_semester_${studentId}`, newSem)
    }
  }

  // 0학점 과목 상태 관리 (진로와상담 등)
  const [zeroCreditCourses, setZeroCreditCourses] = useState<any[]>(() => {
    if (typeof window !== "undefined") {
      const activeSem = localStorage.getItem(`grad_last_viewed_semester_${studentId}`) || "2026-2학기"
      const key = `grad_zero_credit_courses_${studentId}_${activeSem}`
      const storedLocal = localStorage.getItem(key)
      const storedSession = sessionStorage.getItem(key)
      if (storedLocal) {
        try {
          const parsed = JSON.parse(storedLocal)
          if (Array.isArray(parsed)) return parsed
        } catch (e) {}
      }
      if (storedSession) {
        try {
          const parsed = JSON.parse(storedSession)
          if (Array.isArray(parsed)) return parsed
        } catch (e) {}
      }
    }
    return []
  })

  useEffect(() => {
    if (typeof window !== "undefined") {
      const key = `grad_zero_credit_courses_${studentId}_${selectedSemester}`
      const stored = localStorage.getItem(key) || sessionStorage.getItem(key)
      if (stored) {
        try {
          setZeroCreditCourses(JSON.parse(stored))
          return
        } catch (e) {}
      }
      setZeroCreditCourses([])
    }
  }, [studentId, selectedSemester])

  // 수동 커스텀 시간표 상태
  const [customBlocks, setCustomBlocks] = useState<any[]>(() => {
    if (typeof window !== "undefined") {
      const activeSem = localStorage.getItem(`grad_last_viewed_semester_${studentId}`) || "2026-2학기"
      const scheduleClearedKey = `grad_schedule_cleared_${studentId}_${activeSem}`
      const scheduleBlocksKey = `grad_custom_schedule_blocks_${studentId}_${activeSem}`
      const isCleared = localStorage.getItem(scheduleClearedKey) === "true" ||
                        sessionStorage.getItem(scheduleClearedKey) === "true"
      if (isCleared) return []

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
      
      if (localBlocks.length > 0 && validateBlocks(localBlocks)) return localBlocks
      if (sessionBlocks.length > 0 && validateBlocks(sessionBlocks)) return sessionBlocks
    }
    return []
  })

  // 프리뷰로 화면에 그릴 블록 선택 (기본적으로 항상 진짜 내 시간표 출력)
  const blocksToRender = customBlocks

  // 추가 및 수정 모달 상태
  const [isOpenModal, setIsOpenModal] = useState(false)
  const [modalMode, setModalMode] = useState<"add" | "edit">("add")
  const [targetBlockId, setTargetBlockId] = useState<string | null>(null)

  // 모달 입력 폼 필드 상태
  const [courseName, setCourseName] = useState("")
  const [courseDay, setCourseDay] = useState("월")
  const [startHour, setStartHour] = useState(9)
  const [spanHours, setSpanHours] = useState(1.5)
  const [room, setRoom] = useState("")
  const [professor, setProfessor] = useState("")
  const [colorIndex, setColorIndex] = useState(0)

  // 과목 검색 선택기 모달 상태
  const [isOpenPicker, setIsOpenPicker] = useState(false)
  const [pickerSearch, setPickerSearch] = useState("")
  const [pickerChecked, setPickerChecked] = useState<string[]>([]) 
  const [expandedCourse, setExpandedCourse] = useState<string | null>(null) 
  const [pickerCategory, setPickerCategory] = useState<string>("all") 

  // 모달 내 실시간 개설 과목 관리 상태
  const [pickerCourses, setPickerCourses] = useState<any[]>([])
  const [isPickerLoading, setIsPickerLoading] = useState(false)

  // 과목 선택기 모달 오픈 시 혹은 선택된 학기 변경 시 개설 과목 비동기 로딩
  useEffect(() => {
    if (!isOpenPicker) return

    let isMounted = true
    async function loadPickerCourses() {
      setIsPickerLoading(true)
      try {
        const courses = await searchCourseOfferings("", selectedSemester)
        if (isMounted) {
          setPickerCourses(courses)
        }
      } catch (err) {
        console.error("시간표 추가 모달 내 개설 과목 로드 실패:", err)
      } finally {
        if (isMounted) {
          setIsPickerLoading(false)
        }
      }
    }
    loadPickerCourses()
    return () => {
      isMounted = false
    }
  }, [isOpenPicker, selectedSemester])

  // ── [보완] 시간표 로컬 캐시 유실 대응 및 백엔드 DB 연동 로직 ──
  useEffect(() => {
    const scheduleBlocksKey = `grad_custom_schedule_blocks_${studentId}_${selectedSemester}`
    const scheduleClearedKey = `grad_schedule_cleared_${studentId}_${selectedSemester}`
    // 1. 로컬 캐시 조회
    const storedLocal = localStorage.getItem(scheduleBlocksKey)
    const storedSession = sessionStorage.getItem(scheduleBlocksKey)
    const cleared = localStorage.getItem(scheduleClearedKey) || sessionStorage.getItem(scheduleClearedKey)
    
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
    
    // 캐시가 비어있지 않은 경우 캐시 복원 적용
    if (activeStored.length > 0 && validateBlocks(activeStored)) {
      const seen = new Set()
      const cleanBlocks = activeStored.filter((b: any) => {
        const key = String(b.id || "").trim()
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
      setCustomBlocks(cleanBlocks)
      localStorage.setItem(scheduleBlocksKey, JSON.stringify(cleanBlocks))
      sessionStorage.setItem(scheduleBlocksKey, JSON.stringify(cleanBlocks))
      return
    }

    // 만약 사용자가 명시적으로 시간표를 싹 비운 상태("cleared")라면 백엔드 조킵하고 빈 채로 둠
    if (cleared === "true") {
      setCustomBlocks([])
      return
    }

    // 2. 캐시가 비어있는 경우 백엔드 DB에서 시간표 조회하여 복원
    const activeStudentId = studentId || "20210001"
    getUserSchedule(activeStudentId, selectedSemester).then((dbBlocks) => {
      if (dbBlocks && dbBlocks.length > 0 && validateBlocks(dbBlocks)) {
        setCustomBlocks(dbBlocks)
        localStorage.setItem(scheduleBlocksKey, JSON.stringify(dbBlocks))
        sessionStorage.setItem(scheduleBlocksKey, JSON.stringify(dbBlocks))
      } else {
        // 백엔드에도 없는 경우 신규 빈 시간표로 초기 설정 (더미 주입 차단)
        setCustomBlocks([])
        localStorage.setItem(scheduleBlocksKey, JSON.stringify([]))
        sessionStorage.setItem(scheduleBlocksKey, JSON.stringify([]))
      }
    }).catch((err) => {
      console.error("[BACKEND LOAD ERROR] getUserSchedule failed:", err)
      // 에러 시에도 빈 시간표 초기화
      setCustomBlocks([])
    })
  }, [schedule, studentId, selectedSemester])

  // 로컬/세션 스토리지 보존 동기화 헬퍼 (React 로컬 상태 갱신에 의한 즉각 리렌더링 트리거)
  const saveBlocks = (nextBlocks: any[]) => {
    setCustomBlocks(nextBlocks)
    const scheduleBlocksKey = `grad_custom_schedule_blocks_${studentId}_${selectedSemester}`
    const scheduleClearedKey = `grad_schedule_cleared_${studentId}_${selectedSemester}`
    if (typeof window !== "undefined") {
      if (nextBlocks.length === 0) {
        localStorage.removeItem(scheduleBlocksKey)
        sessionStorage.removeItem(scheduleBlocksKey)
        localStorage.setItem(scheduleClearedKey, "true")
        sessionStorage.setItem(scheduleClearedKey, "true")
      } else {
        localStorage.setItem(scheduleBlocksKey, JSON.stringify(nextBlocks))
        sessionStorage.setItem(scheduleBlocksKey, JSON.stringify(nextBlocks))
        localStorage.removeItem(scheduleClearedKey)
        sessionStorage.removeItem(scheduleClearedKey)
      }
    }
    // 백엔드 DB 저장 연동
    const activeStudentId = studentId || "20210001"
    saveUserSchedule(activeStudentId, nextBlocks, selectedSemester).catch((err) => {
      console.error("[BACKEND SAVE ERROR] saveUserSchedule failed:", err)
    })
  }

  // AI 프리뷰 적용 (체크 V 클릭 시 전체 적용)
  const handleApplyAiTimetable = () => {
    if (simulatedSchedule?.scheduleBlocks) {
      saveBlocks(simulatedSchedule.scheduleBlocks)
      
      // 0학점 과목 적용
      if (simulatedSchedule.zero_credit_courses) {
        setZeroCreditCourses(simulatedSchedule.zero_credit_courses)
        const key = `grad_zero_credit_courses_${studentId}_${selectedSemester}`
        if (typeof window !== "undefined") {
          localStorage.setItem(key, JSON.stringify(simulatedSchedule.zero_credit_courses))
          sessionStorage.setItem(key, JSON.stringify(simulatedSchedule.zero_credit_courses))
        }
      } else {
        setZeroCreditCourses([])
        const key = `grad_zero_credit_courses_${studentId}_${selectedSemester}`
        if (typeof window !== "undefined") {
          localStorage.removeItem(key)
          sessionStorage.removeItem(key)
        }
      }

      showToast("AI 추천 시간표가 현재 내 시간표로 성공적으로 반영되었습니다!")
      
      if (resetSimulation) {
        resetSimulation()
      }
      if (typeof window !== "undefined") {
        const aiTimetableKey = `grad_manager_ai_recommended_timetable_${studentId}_${selectedSemester}`
        localStorage.removeItem(aiTimetableKey)
        sessionStorage.removeItem(aiTimetableKey)
      }
    }
  }

  // 배너 닫기 및 프리뷰 취소 시 이전 customBlocks 그대로 복귀
  const handleCloseBanner = () => {
    if (resetSimulation) {
      resetSimulation()
    }
    if (typeof window !== "undefined") {
      const aiTimetableKey = `grad_manager_ai_recommended_timetable_${studentId}_${selectedSemester}`
      localStorage.removeItem(aiTimetableKey)
      sessionStorage.removeItem(aiTimetableKey)
    }
    showToast("AI 추천 시간표 미리보기를 취소하고 이전 시간표로 복원했습니다.")
  }

  // 시간표 전체 초기화 핸들러
  const handleClearAll = () => {
    const isConfirmed = window.confirm("정말 시간표를 전부 비우시겠습니까?")
    if (isConfirmed) {
      // 로컬 갱신, 로컬스토리지 정리, 백엔드 API 연동을 saveBlocks([])를 통해 일괄 처리
      saveBlocks([])
      
      // 0학점 과목 초기화
      setZeroCreditCourses([])
      const key = `grad_zero_credit_courses_${studentId}_${selectedSemester}`
      if (typeof window !== "undefined") {
        localStorage.removeItem(key)
        sessionStorage.removeItem(key)
      }
      
      // AI 프리뷰/추천 임시 저장 데이터도 별도 삭제 처리
      if (typeof window !== "undefined") {
        const aiTimetableKey = `grad_manager_ai_recommended_timetable_${studentId}_${selectedSemester}`
        localStorage.removeItem(aiTimetableKey)
        sessionStorage.removeItem(aiTimetableKey)
      }
      
      showToast("시간표가 초기화되었습니다.")
    }
  }



  const { pastelPalette, scheduleDays, scheduleHours, scheduleReasons } = activeSchedule

  // 수동 편집된 blocks 기준 동적 통계 데이터 계산
  const uniqueCourses = Array.from(new Set(customBlocks.map((b) => b.name)))
  const courseCount = uniqueCourses.length

  const prefsFreeDays = (activeSchedule as any)?.preferences?.freeDays
  const activeDays = new Set(customBlocks.map((b) => dayStringToNum(b.day)))
  const freeDays = Array.isArray(prefsFreeDays)
    ? prefsFreeDays
    : scheduleDays.filter((_, idx) => !activeDays.has(idx))
  const freeDayText = freeDays.length > 0 ? `${freeDays.join(", ")} 공강` : "공강 없음"

  const dynamicReasons = scheduleReasons || []

  // 직접 추가 모달 오픈 핸들러
  const openAddModal = () => {
    setModalMode("add")
    setTargetBlockId(null)
    setCourseName("")
    setCourseDay("월")
    setStartHour(9)
    setSpanHours(1.5)
    setRoom("")
    setProfessor("")
    setColorIndex(customBlocks.length % (pastelPalette?.length || 5))
    setIsOpenModal(true)
  }

  // 기존 강좌 수정 모달 오픈 핸들러
  const openEditModal = (b: any) => {
    setModalMode("edit")
    setTargetBlockId(b.id)
    setCourseName(b.name)
    
    let dayStr = "월"
    if (typeof b.day === "number") {
      const mapping = ["월", "화", "수", "목", "금"]
      dayStr = mapping[b.day] || "월"
    } else if (typeof b.day === "string") {
      dayStr = b.day
    }
    setCourseDay(dayStr)

    setStartHour(b.start !== undefined ? Number(b.start) : 9)
    const spanVal = b.span !== undefined ? Number(b.span) : (b.end !== undefined ? (Number(b.end) - Number(b.start)) : 1.5)
    setSpanHours(spanVal)
    setRoom(b.room || "")
    setProfessor(b.professor || "")
    setColorIndex(b.colorIndex !== undefined ? Number(b.colorIndex) : 0)
    setIsOpenModal(true)
  }

  // 모달 폼 전송 저장 핸들러
  const handleSaveBlock = () => {
    if (!courseName.trim()) {
      showToast("과목 이름을 입력해 주세요.")
      return
    }

    // 동일 과목 중복 기입 차단 가드
    const normalizedName = courseName.trim().toLowerCase()
    const isNameDuplicate = customBlocks.some((b) => {
      if (modalMode === "edit" && b.id === targetBlockId) return false
      return b.name.trim().toLowerCase() === normalizedName
    })

    if (isNameDuplicate) {
      showToast("이미 시간표에 동일한 이름의 과목이 존재합니다.")
      return
    }

    if (modalMode === "add") {
      const newBlock = {
        id: `custom-block-${Date.now()}`,
        name: cleanCourseName(courseName.trim()),
        day: courseDay,
        start: Number(startHour),
        span: Number(spanHours),
        room: room.trim(),
        professor: professor.trim(),
        colorIndex: Number(colorIndex)
      }
      const next = [...customBlocks, newBlock]
      saveBlocks(next)
      setIsOpenModal(false)
      showToast(`'${cleanCourseName(courseName.trim())}' 강좌가 추가되었습니다.`)
    } else {
      const next = customBlocks.map((b) => {
        if (b.id === targetBlockId) {
          return {
            ...b,
            name: cleanCourseName(courseName.trim()),
            day: courseDay,
            start: Number(startHour),
            span: Number(spanHours),
            room: room.trim(),
            professor: professor.trim(),
            colorIndex: Number(colorIndex)
          }
        }
        return b
      })
      saveBlocks(next)
      setIsOpenModal(false)
      showToast("강좌 정보가 갱신되었습니다.")
    }
  }

  // 모달 폼 강좌 삭제 핸들러 (분반 그룹 단위 일괄 원자적 삭제)
  const handleDeleteBlock = () => {
    if (!targetBlockId) return
    const targetBlock = customBlocks.find(b => b.id === targetBlockId)
    if (!targetBlock) return

    let next = []
    if (targetBlock.groupId) {
      next = customBlocks.filter(b => b.groupId !== targetBlock.groupId)
    } else {
      next = customBlocks.filter(b => b.id !== targetBlockId)
    }

    saveBlocks(next)
    setIsOpenModal(false)
    showToast(`'${targetBlock.name}' 과목 및 연동된 모든 분반 일정이 시간표에서 일괄 삭제되었습니다.`)
  }

  // 시간표 상의 시간 충돌 검사 로직
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

  // [신규] 검색된 과목들을 과목명 기준으로 그룹화 (동일 교과목의 여러 개설 분반들을 묶어서 노출)
  const groupedCourses = useMemo(() => {
    if (!pickerCourses) return []
    
    // 1. 카테고리 필터링 (전체 선택 시 전공필수, 전공선택, 교양필수, 교양선택, 계열공통, 일반선택을 기본 포함)
    let filteredList = pickerCourses
    if (pickerCategory === "major") {
      filteredList = pickerCourses.filter(c => c.category === "전공필수" || c.category === "전공선택" || c.category === "계열공통")
    } else if (pickerCategory === "liberal") {
      filteredList = pickerCourses.filter(c => (c.category && c.category.includes("교양")) || c.category === "일반선택")
    } else {
      // pickerCategory === "all" 일 때 모든 카테고리(전공필수, 전공선택, 교양필수, 교양선택, 계열공통, 일반선택 등)를 유실 없이 포함
      filteredList = pickerCourses.filter(c => c)
    }

    // 2. 검색어 필터링
    const query = pickerSearch.trim().toLowerCase()
    const list = query 
      ? filteredList.filter(c => {
          const name = (c.title || c.name || "").toLowerCase()
          const code = (c.course_id || c.code || "").toLowerCase()
          const prof = (c.professor || c.professor_name || "").toLowerCase()
          const category = (c.category || "").toLowerCase()
          return name.includes(query) || code.includes(query) || prof.includes(query) || category.includes(query)
        })
      : filteredList

    // 각 과목(course) 객체를 안전한 단일 시간대 분반 리스트로 쪼개어 평탄화
    const expandedList: any[] = []
    list.forEach(c => {
      expandedList.push(...splitPollutedCourseToSections(c))
    })

    // 학수번호(접미사 제거한 오리지널 course_id 또는 code) 기준으로 그룹핑하여 동일 교과목 하위에 모든 분반들이 모이도록 보장
    const groups: Record<string, any[]> = {}
    expandedList.forEach(c => {
      const fullCid = String(c.course_id || c.code || "미정")
      const cid = fullCid.includes("-") ? fullCid.split("-")[0] : fullCid
      const courseTitle = c.title || c.name || "과목명 미정"
      const key = courseTitle.includes(cid) ? courseTitle : `${cid} - ${courseTitle}`
      if (!groups[key]) {
        groups[key] = []
      }
      groups[key].push(c)
    })

    // 모든 그룹 노출
    return Object.entries(groups).map(([courseName, sections]) => {
      return {
        courseName,
        sections: sections
      }
    })
  }, [pickerCourses, pickerSearch, pickerCategory])

  return (
    <div className="space-y-4 px-2 pb-4 pt-3.5 md:space-y-6 md:px-6 md:pb-6 md:pt-5 md:max-w-6xl md:mx-auto relative">
      {/* 헤더 및 추가/선택 버튼들 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 text-left">
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-foreground">추천 시간표</h1>
            <p className="text-xs md:text-sm text-muted-foreground mt-0.5">{freeDayText} · 총 {courseCount}개 과목 추천</p>
          </div>
          {/* 학기 선택기 드롭다운 추가 */}
          <div className="flex items-center gap-1.5 shrink-0 bg-secondary/40 px-3 py-1.8 rounded-xl border border-border/50">
            <span className="text-[10px] font-black text-muted-foreground shrink-0">학기 선택:</span>
            <select
              value={selectedSemester}
              onChange={(e) => handleSemesterChange(e.target.value)}
              disabled
              className="rounded-lg bg-card border border-border px-2 py-1 text-[10px] text-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6] cursor-not-allowed font-bold opacity-80"
            >
              {(semesters.length > 0 ? semesters : SEMESTER_OPTIONS).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
        
        {/* 보기 옵션 및 제어 버튼 그룹 */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3.5 w-full md:w-auto">
          {/* 보기 옵션 필터 */}
          <div className="flex items-center gap-1.5 text-xs shrink-0">
            <span className="text-muted-foreground font-semibold">보기 옵션:</span>
            <div className="flex rounded-xl bg-[#f2f4f6] dark:bg-[#212836] p-0.5 border border-border/10 shadow-inner">
              {(["both", "room", "professor", "name"] as const).map((opt) => {
                const active = displayFilter === opt
                const label = {
                  both: "전체",
                  room: "강의실",
                  professor: "교수명",
                  name: "과목명"
                }[opt]
                return (
                  <button
                    key={opt}
                    onClick={() => handleDisplayFilterChange(opt)}
                    className={`px-2.5 py-1.5 rounded-lg text-[10px] md:text-xs font-black transition-all cursor-pointer ${
                      active
                        ? "bg-white dark:bg-[#0f151c] text-[#3182f6] shadow-sm"
                        : "text-[#4e5968] dark:text-[#b0b8c1] hover:text-foreground"
                    }`}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1.5 w-full sm:flex sm:w-auto sm:gap-2">
            {/* 대화 바탕으로 불러오기 버튼 */}
            <button
              onClick={handleApplyAiTimetable}
              disabled={!hasSimulatedSchedule}
              className={`flex items-center justify-center gap-1 text-[10px] md:text-xs font-bold px-2.5 py-2 md:px-4 md:py-2.5 rounded-xl md:rounded-2xl transition-all cursor-pointer shadow-sm ${
                hasSimulatedSchedule
                  ? "bg-[#3182f6] hover:bg-[#1b64da] text-white active:scale-98 animate-pulse shadow-md shadow-[#3182f6]/20 font-black"
                  : "bg-secondary text-muted-foreground opacity-50 cursor-not-allowed font-medium"
              }`}
            >
              <Sparkles className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span>대화 바탕으로 불러오기</span>
            </button>
            <button
              onClick={handleClearAll}
              className="flex items-center justify-center gap-1 bg-destructive/10 text-destructive text-[10px] md:text-xs font-bold px-2 py-2 md:px-4 md:py-2.5 rounded-xl md:rounded-2xl hover:bg-destructive/20 active:scale-98 transition-all cursor-pointer shadow-sm"
            >
              <Trash2 className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span>초기화</span>
            </button>
            <button
              onClick={() => {
                setPickerSearch("")
                setPickerChecked([])
                setIsOpenPicker(true)
              }}
              className="flex items-center justify-center gap-1 bg-[#3182f6]/10 text-[#3182f6] text-[10px] md:text-xs font-bold px-2 py-2 md:px-4 md:py-2.5 rounded-xl md:rounded-2xl hover:bg-[#3182f6]/20 active:scale-98 transition-all cursor-pointer shadow-sm shadow-[#3182f6]/5"
            >
              <Search className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span>검색 추가</span>
            </button>
            <button
              onClick={openAddModal}
              className="flex items-center justify-center gap-1 bg-[#3182f6]/10 text-[#3182f6] text-[10px] md:text-xs font-bold px-2 py-2 md:px-4 md:py-2.5 rounded-xl md:rounded-2xl hover:bg-[#3182f6]/20 active:scale-98 transition-all cursor-pointer shadow-sm shadow-[#3182f6]/5"
            >
              <Plus className="h-3.5 w-3.5 md:h-4 md:w-4" />
              <span>직접 추가</span>
            </button>
          </div>
        </div>
      </div>

      {/* Timetable grid */}
      <section className="rounded-[20px] md:rounded-[24px] bg-card border border-border p-1.5 md:p-4.5 shadow-[0_8px_30px_rgba(0,0,0,0.02)] transition-all overflow-x-auto">
        <div className="grid grid-cols-[28px_repeat(5,1fr)] md:grid-cols-[36px_repeat(5,1fr)] min-w-[320px] md:min-w-0 w-full [--row-h:36px] md:[--row-h:52px]">
          {/* header row */}
          <div />
          {scheduleDays.map((d, i) => (
            <div
              key={d}
              className="pb-1.5 md:pb-4.5 text-center flex items-center justify-center"
            >
              <span className="bg-secondary/60 text-secondary-foreground text-[9px] md:text-[11px] font-bold px-1.5 py-0.5 md:px-3 md:py-1.5 rounded-lg md:rounded-xl border border-border/10 shadow-sm select-none">
                {d}
              </span>
            </div>
          ))}

          {/* time label column */}
          <div className="relative pr-1 md:pr-2.5 pt-1 select-none flex flex-col justify-between">
            {scheduleHours.map((h) => (
              <div
                key={h}
                className="text-right text-[8px] md:text-[10px] text-muted-foreground/60 font-mono font-bold leading-none"
                style={{ height: "var(--row-h)" }}
              >
                {h}:00
              </div>
            ))}
          </div>

          {/* day columns */}
          {scheduleDays.map((day, dayIndex) => (
            <div
              key={day}
              className="relative border-l border-slate-100 dark:border-slate-800/60"
              style={{ height: `calc(var(--row-h) * ${scheduleHours.length})` }}
            >
              {/* hour gridlines */}
              {scheduleHours.map((h) => (
                <div key={h} className="border-b border-slate-100/80 dark:border-slate-800/40" style={{ height: "var(--row-h)" }} />
              ))}

              {/* subject blocks */}
              {blocksToRender
                .filter((b) => dayStringToNum(b.day) === dayIndex)
                .map((b) => {
                  const hasColorIndex = b.colorIndex !== undefined && b.colorIndex !== null
                  const c = hasColorIndex
                    ? pastelPalette[b.colorIndex % pastelPalette.length]
                    : {
                        bg: b.color || "bg-blue-100",
                        text: b.textColor || "text-blue-700",
                        bar: b.color || "bg-blue-500",
                      }

                  const safeC = c || { bg: "bg-blue-100", text: "text-blue-700", bar: "bg-blue-500" }

                  // 낙관적 업데이트 대응: start, span 수치 파싱 시 디폴트 값 바인딩 보장
                  const startHourRaw = b.start !== undefined ? Number(b.start) : 9
                  const startHour = isNaN(startHourRaw) ? 9 : startHourRaw
                  const startOffset = startHour >= 8 ? (startHour - scheduleHours[0]) : (startHour >= 0 ? startHour : 0)

                  const spanRaw = b.span !== undefined 
                    ? Number(b.span)
                    : (b.end !== undefined ? (Number(b.end) - startHour) : 1.5)
                  const span = isNaN(spanRaw) || spanRaw <= 0 ? 1.5 : spanRaw

                  const isHovered = hoveredGroupId && b.groupId === hoveredGroupId

                  const getCourseDisplayTitle = (block: any) => {
                    if (block.name && block.name.trim() !== "") return block.name;
                    const lookupCode = block.code || block.course_id || block.id;
                    if (!lookupCode) return "알 수 없는 과목";
                    const found = allCourses?.find(c => {
                      const cid = String(lookupCode);
                      return String(c.course_id || "") === cid ||
                             String(c.code || "") === cid ||
                             String(c.id || "") === cid;
                    });
                    if (found) {
                      return found.title || found.name || found.course_id || found.code || "과목명 미정";
                    }
                    return String(lookupCode || "과목명 미정");
                  };
                  const displayTitle = getCourseDisplayTitle(b);

                  return (
                    <div
                      key={b.id}
                      onClick={() => openEditModal(b)}
                      onMouseEnter={() => b.groupId && setHoveredGroupId(b.groupId)}
                      onMouseLeave={() => setHoveredGroupId(null)}
                      className={`absolute inset-x-0.5 md:inset-x-1.5 overflow-hidden rounded-[8px] md:rounded-[16px] p-1.5 md:p-3 border transition-all duration-300 ease-out hover:scale-[1.03] hover:-translate-y-0.5 hover:shadow-lg hover:z-20 cursor-pointer ${
                        isHovered 
                          ? "border-[#3182f6] shadow-[0_0_12px_rgba(49,130,246,0.3)] scale-[1.02]" 
                          : "border-white/20 dark:border-white/5"
                      } ${safeC.bg}`}
                      style={{ 
                        top: `calc(${startOffset} * var(--row-h) + 2px)`, 
                        height: `calc(${span} * var(--row-h) - 4px)` 
                      }}
                      title="클릭하여 편집"
                    >
                      <div className="h-full flex flex-col justify-between">
                        <div>
                          <p className={`text-[8.5px] md:text-[11px] font-black leading-tight tracking-tight truncate md:whitespace-normal ${safeC.text}`}>{displayTitle}</p>
                        </div>
                        <div className="flex flex-col gap-0.5 mt-auto">
                          {span >= 1.2 && (displayFilter === "both" || displayFilter === "room") && b.room && (
                            <p className={`text-[7px] md:text-[9px] font-bold opacity-75 truncate ${safeC.text}`}>
                              📍 {b.room}
                            </p>
                          )}
                          {span >= 1.2 && (displayFilter === "both" || displayFilter === "professor") && (b.professor || b.professor_name) && (
                            <p className={`text-[7px] md:text-[9px] font-bold opacity-65 truncate ${safeC.text}`}>
                              👤 {b.professor || b.professor_name}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
            </div>
          ))}
        </div>
      </section>

      {/* 0학점 과목 (추가 이수 과목) 리스트 노출 영역 */}
      {zeroCreditCourses && zeroCreditCourses.length > 0 && (
        <div className="rounded-[20px] md:rounded-[24px] bg-secondary/20 border border-border/80 p-4.5 md:p-6 text-left shadow-sm space-y-2">
          <h3 className="text-xs md:text-sm font-bold text-foreground flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-[#3182f6]" />
            <span>추가 이수 과목 (시간외 0학점 과목)</span>
          </h3>
          <p className="text-[11px] md:text-xs text-muted-foreground leading-relaxed">
            시간표 그리드에 표시되지 않는 추가 과목(예: 진로와상담 등) 목록입니다.
          </p>
          <div className="flex flex-wrap gap-2 pt-1.5">
            {zeroCreditCourses.map((c, idx) => (
              <span 
                key={idx} 
                className="bg-card border border-border/60 text-foreground text-[10px] md:text-xs font-bold px-3 py-1.5 rounded-xl shadow-sm flex items-center gap-1.5 animate-fade-in"
              >
                🎓 {cleanCourseName(c.name)} ({c.code})
                {c.professor && c.professor !== "미정" && (
                  <span className="text-[9px] md:text-[10px] text-muted-foreground font-medium border-l border-border/80 pl-1.5">
                    {c.professor}
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}



      {/* 수동 추가 및 편집 모달 */}
      <AnimatePresence>
        {isOpenModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpenModal(false)}
              className="absolute inset-0 bg-black/45 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              className="relative w-full max-w-sm rounded-[24px] bg-card border border-border p-6 shadow-2xl z-10 space-y-4"
            >
              <div className="flex items-center justify-between border-b border-border/60 pb-3">
                <h3 className="text-base font-bold text-foreground">
                  {modalMode === "add" ? "시간표 직접 추가" : "강좌 상세 편집"}
                </h3>
                <button
                  onClick={() => setIsOpenModal(false)}
                  className="p-1 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-full cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* 폼 필드 입력 영역 */}
              <div className="space-y-3.5 text-xs">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-muted-foreground block">과목 이름</label>
                  <input
                    type="text"
                    placeholder="예: 클라우드 서비스 기초"
                    value={courseName}
                    onChange={(e) => setCourseName(e.target.value)}
                    className="w-full rounded-xl bg-secondary px-3 py-2.5 text-xs border border-transparent focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary font-bold"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-muted-foreground block">요일</label>
                    <select
                      value={courseDay}
                      onChange={(e) => setCourseDay(e.target.value)}
                      className="w-full rounded-xl bg-secondary px-3 py-2.5 text-xs border border-transparent focus:border-primary focus:bg-background focus:outline-none appearance-none cursor-pointer font-semibold"
                    >
                      {["월", "화", "수", "목", "금"].map(d => (
                        <option key={d} value={d}>{d}요일</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-muted-foreground block">시작 시간</label>
                    <select
                      value={startHour}
                      onChange={(e) => setStartHour(Number(e.target.value))}
                      className="w-full rounded-xl bg-secondary px-3 py-2.5 text-xs border border-transparent focus:border-primary focus:bg-background focus:outline-none appearance-none cursor-pointer font-semibold"
                    >
                      {scheduleHours.map(h => (
                        <option key={h} value={h}>{h}:00</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-muted-foreground block">수업 시간 (단위: 시간)</label>
                    <select
                      value={spanHours}
                      onChange={(e) => setSpanHours(Number(e.target.value))}
                      className="w-full rounded-xl bg-secondary px-3 py-2.5 text-xs border border-transparent focus:border-primary focus:bg-background focus:outline-none appearance-none cursor-pointer font-semibold"
                    >
                      <option value={1}>1시간 수업</option>
                      <option value={1.5}>1.5시간 수업</option>
                      <option value={2}>2시간 수업</option>
                      <option value={3}>3시간 수업</option>
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-muted-foreground block">테마 색상</label>
                    <div className="flex gap-1.5 py-1 justify-between">
                      {pastelPalette?.map((p, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setColorIndex(idx)}
                          className={`w-6 h-6 rounded-full border transition-all cursor-pointer shrink-0 relative flex items-center justify-center ${p.bg}`}
                          style={{
                            borderColor: colorIndex === idx ? "rgb(156 163 175 / 0.85)" : "transparent"
                          }}
                        >
                          {colorIndex === idx && <Check className={`h-3 w-3 ${p.text}`} />}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-muted-foreground block">강의실 (선택)</label>
                    <input
                      type="text"
                      placeholder="예: 율곡관 301호"
                      value={room}
                      onChange={(e) => setRoom(e.target.value)}
                      className="w-full rounded-xl bg-secondary px-3 py-2.5 text-xs border border-transparent focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-muted-foreground block">교수명 (선택)</label>
                    <input
                      type="text"
                      placeholder="예: 김한신 교수"
                      value={professor}
                      onChange={(e) => setProfessor(e.target.value)}
                      className="w-full rounded-xl bg-secondary px-3 py-2.5 text-xs border border-transparent focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              </div>

              {/* 하단 액션 버튼 그룹 */}
              <div className="flex gap-2 pt-3 border-t border-border/60 justify-end">
                {modalMode === "edit" && (
                  <button
                    type="button"
                    onClick={handleDeleteBlock}
                    className="mr-auto p-2.5 text-destructive bg-destructive/5 hover:bg-destructive/10 rounded-xl transition-all cursor-pointer flex items-center gap-1 text-xs font-bold"
                    title="시간표에서 삭제"
                  >
                    <Trash2 className="h-4 w-4" />
                    <span>삭제</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setIsOpenModal(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-bold bg-secondary text-foreground hover:bg-muted transition-all cursor-pointer"
                >
                  <Spacer />
                  <span>취소</span>
                </button>
                <button
                  type="button"
                  onClick={handleSaveBlock}
                  className="px-5 py-2.5 rounded-xl text-xs font-bold bg-[#3182f6] text-white hover:bg-[#1b64da] active:scale-95 transition-all cursor-pointer"
                >
                  저장
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 개설 강좌 데이터베이스 검색 선택 모달 */}
      <AnimatePresence>
        {isOpenPicker && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpenPicker(false)}
              className="absolute inset-0 bg-black/45 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              className="relative w-full max-w-md rounded-[24px] bg-card border border-border p-6 shadow-2xl z-10 max-h-[85vh] flex flex-col"
            >
              {/* 모달 헤더 */}
              <div className="flex items-center justify-between border-b border-border/60 pb-3 shrink-0">
                <div>
                  <h3 className="text-base font-bold text-foreground">개설 과목 목록에서 고르기</h3>
                  <p className="text-[11px] text-muted-foreground mt-0.5">원하는 과목을 찾아 요일/시간 분반별로 추가하세요.</p>
                </div>
                <button
                  onClick={() => setIsOpenPicker(false)}
                  className="p-1 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-full cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* 검색어 입력창 */}
              <div className="relative shrink-0 my-2">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-muted-foreground" />
                </div>
                <input
                  type="text"
                  placeholder="과목 이름, 교수명, 또는 과목코드 검색"
                  value={pickerSearch}
                  onChange={(e) => setPickerSearch(e.target.value)}
                  className="w-full rounded-xl border border-transparent bg-secondary py-2.5 pl-9 pr-8 text-xs text-foreground placeholder-muted-foreground focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary font-medium"
                />
                {pickerSearch && (
                  <button 
                    onClick={() => setPickerSearch("")}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* 필터 카테고리 칩 그룹 */}
              <div className="flex gap-1.5 overflow-x-auto pb-2 shrink-0 select-none scrollbar-hide">
                {[
                  { key: "all", label: "전체" },
                  { key: "major", label: "전공" },
                  { key: "liberal", label: "교양" }
                ].map((chip) => {
                  const isActive = pickerCategory === chip.key
                  return (
                    <button
                      key={chip.key}
                      onClick={() => setPickerCategory(chip.key)}
                      type="button"
                      className={`px-3.5 py-1.5 rounded-full text-[10px] font-bold transition-all shrink-0 cursor-pointer ${
                        isActive 
                          ? "bg-foreground text-background" 
                          : "bg-secondary text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {chip.label}
                    </button>
                  )
                })}
              </div>

              {/* 과목 리스트 아코디언 전개 스크롤 영역 */}
              <div className="flex-1 overflow-y-auto pr-1 space-y-2 select-none min-h-[260px] max-h-[60vh] pb-2">
                {isPickerLoading ? (
                  <div className="py-12 flex flex-col justify-center items-center gap-3 text-xs text-muted-foreground border border-dashed border-border rounded-2xl bg-secondary/10">
                    <Loader2 className="h-6 w-6 animate-spin text-[#3182f6]" />
                    <span>개설 과목 정보를 불러오는 중입니다...</span>
                  </div>
                ) : groupedCourses.length === 0 ? (
                  <div className="py-12 text-center text-xs text-muted-foreground border-2 border-dashed border-border rounded-2xl">
                    검색 조건에 맞는 개설 과목이 없습니다.
                  </div>
                ) : (
                  groupedCourses.map(({ courseName, sections }) => {
                    const isExpanded = expandedCourse === courseName
                    const sectionCount = sections.length

                    return (
                      <div 
                        key={courseName} 
                        className="space-y-1.5 rounded-2xl bg-secondary/30 border border-border/40 p-2.5 transition-all"
                      >
                        {/* 대표 과목명 및 아코디언 헤더 */}
                        <div 
                          onClick={() => setExpandedCourse(isExpanded ? null : courseName)}
                          className="flex items-center justify-between p-1.5 cursor-pointer hover:bg-secondary/40 rounded-xl transition-all"
                        >
                          <div className="flex-1 min-w-0 pr-3">
                            <p className="text-xs font-black text-foreground truncate text-left">{cleanCourseName(courseName)}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5 text-left">개설 분반: {sectionCount}개</p>
                          </div>
                          <span className="text-[10px] text-primary bg-primary/10 px-2.5 py-1.2 rounded-lg font-bold">
                            {isExpanded ? "닫기" : "분반 보기"}
                          </span>
                        </div>

                        {/* 분반 아코디언 바디 */}
                        {isExpanded && (
                          <div className="space-y-2 pt-2 border-t border-border/40">
                             {sections.map((sec) => {
                               const secId = String(sec.course_id || sec.code || "")
                               const rawSchedules = sec.schedules || []

                               // 결합된 원시 스케줄 데이터를 개별 청크로 분할 정규화
                               const normalizedSchedules = normalizeSchedules(rawSchedules)

                               // 요일/시작시간/종료시간 쌍 기준으로 schedules 중복 소거
                               const uniqueSchedules: any[] = []
                               const seenScheduleKeys = new Set<string>()
                               normalizedSchedules.forEach((s: any) => {
                                 const key = `${s.day}-${s.start_time}-${s.end_time}`
                                 if (!seenScheduleKeys.has(key)) {
                                   seenScheduleKeys.add(key)
                                   uniqueSchedules.push(s)
                                 }
                               })

                               const profName = sec.professor || sec.professor_name || "미지정"
                               const sectionName = secId.includes("-") ? `${secId.split("-")[1]}분반` : `${secId} 분반`

                               // 이미 이 분반 그룹의 블록들이 하나라도 시간표에 추가되어 있는지 판별
                               const isSectionAdded = customBlocks.some(b => 
                                 String(b.groupId) === String(secId) || 
                                 b.id.startsWith(`db-block-${String(secId)}`)
                               )

                               // 분반 일괄 추가 핸들러 (원자적 추가)
                               const handleAddSection = () => {
                                 console.log("[AUDIT DEBUG] handleAddSection invoked. secId:", secId)
                                 console.log("[AUDIT DEBUG] uniqueSchedules:", uniqueSchedules)
                                 if (isSectionAdded) {
                                   showToast(`이미 시간표에 등록된 분반입니다.`)
                                   return
                                 }

                                 // 1. 모든 요일 일정의 시간 충돌 검사 (가상 스케줄은 시간 충돌 검사 제외)
                                 const realSchedules = uniqueSchedules.filter(s => !s.isDummy)
                                 const conflictName = checkTimeConflict(realSchedules, customBlocks)
                                 if (conflictName) {
                                   showToast(`이 분반의 일정 중 일부가 기존 '${conflictName}'과 시간이 겹칩니다.`)
                                   return
                                 }

                                 // 2. 가상 스케줄(isDummy)이 아닌 진짜 강의 시간대(realSchedules)에 대해 개별 시간표 블록 1:1 매핑 생성
                                 // (만약 실 시간대가 비어 있다면 전체 uniqueSchedules를 폴백 활용)
                                 const targetSchedules = realSchedules.length > 0 ? realSchedules : uniqueSchedules
                                 const newBlocks = targetSchedules.map((s: any, sIdx: number) => {
                                   const start = timeToHoursValue(s.start_time)
                                   const end = timeToHoursValue(s.end_time)
                                   const slotRoom = s.classroom || sec.room || "미정"
                                   const stringSecId = String(secId)
                                   
                                   return {
                                     id: `db-block-${stringSecId}-${s.day}-${s.start_time}-${sIdx}`,
                                     groupId: stringSecId, // 분반 세트 ID 지정 (원자적 결합)
                                     name: cleanCourseName(courseName),
                                     day: s.day,
                                     start: start,
                                     span: end - start,
                                     room: slotRoom,
                                     professor: profName,
                                     colorIndex: (customBlocks.length) % (pastelPalette?.length || 5)
                                   }
                                 })

                                 const next = [...customBlocks, ...newBlocks]
                                 saveBlocks(next)
                                 setIsOpenPicker(false)
                                 showToast(`'${cleanCourseName(courseName)}' (${sectionName})이 시간표에 일괄 추가되었습니다.`)
                               }

                               return (
                                 <div 
                                   key={secId} 
                                   className="flex items-center justify-between p-3.5 bg-card border border-border/40 rounded-xl hover:shadow-sm transition-all gap-3"
                                 >
                                   <div className="flex-1 min-w-0 text-left">
                                     <div className="flex items-center gap-1.5">
                                       <span className="text-[9px] font-bold text-foreground bg-secondary px-1.5 py-0.5 rounded">{sectionName}</span>
                                       <span className="text-[9px] font-mono text-muted-foreground">{secId}</span>
                                     </div>
                                     <p className="text-[10px] text-muted-foreground/80 font-bold mt-1">
                                       👤 {profName}교수
                                     </p>
                                     <div className="mt-1.5 flex flex-wrap gap-1">
                                       {uniqueSchedules.map((s: any, sIdx: number) => {
                                         const isDummy = s.isDummy || false
                                         return (
                                           <span key={sIdx} className={`px-2 py-0.8 rounded-lg border inline-block font-bold shadow-[0_1px_3px_rgba(49,130,246,0.02)] text-[9px] text-left ${
                                             isDummy 
                                               ? "bg-destructive/5 text-destructive border-destructive/10" 
                                               : "bg-[#3182f6]/5 text-[#3182f6] border-[#3182f6]/10"
                                           }`}>
                                             {isDummy 
                                               ? "🕒 요일/시간 미정 (기본 월09:00 배정)" 
                                               : `🕒 ${s.day}요일 ${s.start_time} ~ ${s.end_time} ${s.classroom ? `(${s.classroom})` : ""}`}
                                           </span>
                                         )
                                       })}
                                     </div>
                                   </div>
                                   {isSectionAdded ? (
                                     <button
                                       disabled
                                       className="bg-[#3182f6]/10 text-[#3182f6] text-[10px] font-bold px-3 py-2 rounded-lg cursor-not-allowed shrink-0"
                                     >
                                       추가됨
                                     </button>
                                   ) : (
                                     <button
                                       onClick={handleAddSection}
                                       className="bg-[#3182f6] text-white text-[10px] font-bold px-3 py-2 rounded-lg hover:bg-[#1b64da] active:scale-95 transition-all cursor-pointer shrink-0"
                                     >
                                       추가
                                     </button>
                                   )}
                                 </div>
                               )
                             })}
                          </div>
                        )}
                      </div>
                    )
                  })
                )}
              </div>

              {/* 하단 패널 */}
              <div className="pt-3 border-t border-border/60 flex justify-end shrink-0">
                <button
                  type="button"
                  onClick={() => setIsOpenPicker(false)}
                  className="px-5 py-2.5 rounded-xl text-xs font-bold bg-secondary text-foreground hover:bg-muted transition-all cursor-pointer"
                >
                  닫기
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Spacer() {
  return null
}
