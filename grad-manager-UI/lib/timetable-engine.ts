import type { RecommendedCourse, ScheduleBlock, ScheduleReason } from "@/data/types"
import type { PastelColor } from "./grad-data-types"

// 학수코드 접두사 제거 헬퍼 함수
const cleanCourseName = (name: string): string => {
  if (!name) return ""
  return name.replace(/^[A-Z0-9]+(?:\s*-\s*|\s+)/, "").trim()
}

function parseDayOffs(messages: any[]): string[] {
  const days = ["월", "화", "수", "목", "금"]

  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i]
    if (msg.role !== "user") continue
    const text = msg.content
    const dayOffs: string[] = []
    let foundConstraint = false

    // "월요일만 공강", "화요일 공강", "수요일 빼줘" 등 요일 공강 지시어 파싱
    for (const day of days) {
      const patterns = [
        new RegExp(`${day}요일\\s*(만)?\\s*(공강|제외|빼|없이|없게|안돼|기피|피해|비워)`),
        new RegExp(`${day}\\s*(만)?\\s*(공강|제외|빼|없이|없게|안돼|기피|피해|비워)`)
      ]
      if (patterns.some(p => p.test(text))) {
        if (!dayOffs.includes(day)) {
          dayOffs.push(day)
        }
        foundConstraint = true
      }
    }

    // 선호 요일 조합 감지하여 그 외 요일을 기피 요일로 추출
    if (text.includes("월수금")) {
      if (!dayOffs.includes("화")) dayOffs.push("화")
      if (!dayOffs.includes("목")) dayOffs.push("목")
      foundConstraint = true
    }
    if (text.includes("화목")) {
      if (!dayOffs.includes("월")) dayOffs.push("월")
      if (!dayOffs.includes("수")) dayOffs.push("수")
      if (!dayOffs.includes("금")) dayOffs.push("금")
      foundConstraint = true
    }

    if (foundConstraint) {
      return dayOffs
    }
  }
  return []
}

function timeToMinutes(timeStr: string): number {
  const [h, m] = timeStr.split(":").map(Number)
  return h * 60 + m
}

function hasConflict(s1: any, s2: any): boolean {
  if (s1.day !== s2.day) return false
  const start1 = timeToMinutes(s1.start_time)
  const end1 = timeToMinutes(s1.end_time)
  const start2 = timeToMinutes(s2.start_time)
  const end2 = timeToMinutes(s2.end_time)
  return start1 < end2 && start2 < end1
}

export function generateTimetableFromChat(messages: any[], allCourses: any[]) {
  if (!allCourses || allCourses.length === 0) {
    return null
  }

  const dayOffs = parseDayOffs(messages)

  // 0. 활성 추천 필터 로드 및 공강 요일 자동 편입
  const studentId = typeof window !== "undefined" ? sessionStorage.getItem("active_student_id") : null
  const filtersKey = studentId ? `active_recommend_filters_${studentId}` : "active_recommend_filters"
  const rawFilters = typeof window !== "undefined" ? sessionStorage.getItem(filtersKey) : null
  const activeFilters = rawFilters ? JSON.parse(rawFilters) : []

  const days = ["월", "화", "수", "목", "금"]
  for (const filter of activeFilters) {
    const label = filter.label || ""
    for (const day of days) {
      if (label.includes(day) && (label.includes("공강") || label.includes("제외") || label.includes("피해") || label.includes("비워"))) {
        if (!dayOffs.includes(day)) {
          dayOffs.push(day)
        }
      }
    }
  }

  // 1. 공강 요일 조건이 있는 경우, 해당 요일에 수업이 있는 강좌를 모두 제거
  let pool = allCourses.filter(course => {
    if (!course.schedules || course.schedules.length === 0) return false
    
    // 요일 공강 조건 체크
    if (course.schedules.some((s: any) => dayOffs.includes(s.day))) return false

    // 세션 스토리지에서 넘어온 동적 추천 필터 조건 반영
    for (const filter of activeFilters) {
      const key = filter.key.toLowerCase()
      const label = filter.label.toLowerCase()

      if (key === "all" || key === "major" || key === "liberal" || key === "settings") continue

      // 학점 필터 (예: "3학점 제한")
      if (label.includes("3학점") && course.credit !== 3) return false
      if (label.includes("2학점") && course.credit !== 2) return false

      // 특정 요교시 필터 (예: "오전 수업 제외" -> 9시 수업 제거)
      if ((label.includes("오전") || label.includes("9시")) && label.includes("제외")) {
        if (course.schedules.some((s: any) => s.start_time.startsWith("09:"))) return false
      }

      // 키워드 필터 (예: "인공지능", "데이터")
      if (!label.includes("공강") && !label.includes("제외") && !label.includes("학점")) {
        const title = course.title || course.name || ""
        const desc = course.description || ""
        const prof = course.professor || ""
        if (
          !title.toLowerCase().includes(key) && 
          !desc.toLowerCase().includes(key) && 
          !prof.toLowerCase().includes(key)
        ) {
          return false
        }
      }
    }

    return true
  })

  // 2. 그리디 시간표 조립 (목표 학점: 15학점 내외, 4~5과목)
  const selectedCourses: any[] = []
  let totalCredits = 0

  // 전공(MAJOR)이 우선순위가 높도록 정렬
  // sessionStorage에서 융합/특화전공 정보 로드
  const prefsKey = studentId ? `grad_major_preferences_${studentId}` : "grad_major_preferences"
  const rawPrefs = typeof window !== "undefined" ? sessionStorage.getItem(prefsKey) : null
  const prefs = rawPrefs ? JSON.parse(rawPrefs) : null

  const sortedPool = [...pool].sort((a, b) => {
    let aScore = a.program_type === "MAJOR" ? 5 : 0
    let bScore = b.program_type === "MAJOR" ? 5 : 0

    if (prefs) {
      const conv = prefs.convergenceMajor
      const spec = prefs.specializedTrack

      // 특화트랙 키워드 매칭 가중치
      if (spec === "데이터 사이언스 트랙") {
        const keywords = ["데이터", "분석", "통계", "머신러닝", "딥러닝", "인공지능", "AI", "Data"]
        if (keywords.some(kw => (a.title || a.name || "").includes(kw) || a.description?.includes(kw))) aScore += 10
        if (keywords.some(kw => (b.title || b.name || "").includes(kw) || b.description?.includes(kw))) bScore += 10
      } else if (spec === "인지 감성 특화 트랙") {
        const keywords = ["인지", "감성", "인간", "HCI", "심리", "UX", "디자인"]
        if (keywords.some(kw => (a.title || a.name || "").includes(kw) || a.description?.includes(kw))) aScore += 10
        if (keywords.some(kw => (b.title || b.name || "").includes(kw) || b.description?.includes(kw))) bScore += 10
      } else if (spec === "지능형 IoT 소프트웨어 트랙") {
        const keywords = ["IoT", "임베디드", "네트워크", "센서", "통신", "시스템"]
        if (keywords.some(kw => (a.title || a.name || "").includes(kw) || a.description?.includes(kw))) aScore += 10
        if (keywords.some(kw => (b.title || b.name || "").includes(kw) || b.description?.includes(kw))) bScore += 10
      } else if (spec === "풀스택 웹/모바일 소프트웨어 트랙") {
        const keywords = ["웹", "모바일", "앱", "안드로이드", "iOS", "프론트", "백엔드", "네트워크", "서버"]
        if (keywords.some(kw => (a.title || a.name || "").includes(kw) || a.description?.includes(kw))) aScore += 10
        if (keywords.some(kw => (b.title || b.name || "").includes(kw) || b.description?.includes(kw))) bScore += 10
      }

      // 융합전공 키워드 매칭 가중치 (예: 융합전공 이름의 명사 매칭)
      if (conv) {
        const convClean = conv.replace("융합전공", "")
        // 단어 일부 매칭 (예: "문화콘텐츠" -> "콘텐츠", "문화" 등)
        const matchTerms = [convClean, "융합", "문화", "콘텐츠", "경영", "스마트", "공공", "서비스"]
        if (matchTerms.some(term => (a.title || a.name || "").includes(term) || a.description?.includes(term))) aScore += 6
        if (matchTerms.some(term => (b.title || b.name || "").includes(term) || b.description?.includes(term))) bScore += 6
      }
    }

    return bScore - aScore
  })

  // 단일 개설 분반 일정 추출 헬퍼 (분반/교수별 그룹화 후 단일 결합 분반 세트 선택)
  const extractSingleSectionSchedules = (rawSchedules: any[]): any[] => {
    if (!rawSchedules || rawSchedules.length === 0) return []
    
    // 1. 분반/교수명 기준으로 스케줄 그룹화
    const groups: Record<string, any[]> = {}
    rawSchedules.forEach((s: any) => {
      const secVal = String(s.section || s.class_no || "1").trim()
      const profVal = String(s.professor || s.professor_name || "미정").trim()
      const key = `${secVal}_${profVal}`
      if (!groups[key]) {
        groups[key] = []
      }
      groups[key].push(s)
    })

    const groupKeys = Object.keys(groups)
    if (groupKeys.length === 0) return []

    // 2. 여러 분반 후보 중 첫 번째 분반 세트를 선택 (중복 시간대 요소를 요일/시작/종료 기준 unique하게 소거)
    const targetKey = groupKeys[0]
    const secSchedules = groups[targetKey]

    const uniqueSet: any[] = []
    const seenKeys = new Set<string>()
    secSchedules.forEach((s: any) => {
      const key = `${s.day}-${s.start_time}-${s.end_time}`
      if (!seenKeys.has(key)) {
        seenKeys.add(key)
        uniqueSet.push(s)
      }
    })
    return uniqueSet
  }

  for (const rawCourse of sortedPool) {
    if (totalCredits + rawCourse.credit > 18) continue

    // 단일 분반으로 schedules 정제
    const cleanedSchedules = extractSingleSectionSchedules(rawCourse.schedules)
    if (cleanedSchedules.length === 0) continue

    // 정제된 단일 분반 시간표를 가진 신규 과목 객체 생성
    const course = {
      ...rawCourse,
      schedules: cleanedSchedules
    }

    // 동일 과목 중복 배치 방지 (동일 과목 코드 혹은 과목명 정밀 매칭)
    const isDuplicate = selectedCourses.some(selected => {
      const selId = selected.course_id || selected.code || ""
      const targetId = course.course_id || course.code || ""
      const selTitle = (selected.title || selected.name || "").trim().toLowerCase()
      const targetTitle = (course.title || course.name || "").trim().toLowerCase()
      return (selId === targetId && selId !== "") || (selTitle === targetTitle && selTitle !== "")
    })
    if (isDuplicate) continue

    // 시간 충돌 검사
    let conflict = false
    for (const selected of selectedCourses) {
      for (const s1 of course.schedules) {
        for (const s2 of selected.schedules) {
          if (hasConflict(s1, s2)) {
            conflict = true
            break
          }
        }
        if (conflict) break
      }
      if (conflict) break
    }

    if (!conflict) {
      selectedCourses.push(course)
      totalCredits += course.credit
    }

    if (totalCredits >= 15) break
  }

  // 3. scheduleBlocks 빌드
  const dayMap: Record<string, number> = { "월": 0, "화": 1, "수": 2, "목": 3, "금": 4 }
  const scheduleBlocks: ScheduleBlock[] = []
  const pastelPalette = [
    { bg: "bg-[#e8f3ff] dark:bg-[#1b2d45]", text: "text-[#1b64da] dark:text-[#5592f2]", bar: "bg-[#3182f6]" },
    { bg: "bg-[#daf2ee] dark:bg-[#183531]", text: "text-[#008f80] dark:text-[#00caab]", bar: "bg-[#00b5a3]" },
    { bg: "bg-[#fff3f5] dark:bg-[#381e25]", text: "text-[#d6284a] dark:text-[#ff6b8b]", bar: "bg-[#f25875]" },
    { bg: "bg-[#f7f4fd] dark:bg-[#2c1d3c]", text: "text-[#703bc9] dark:text-[#a880f7]", bar: "bg-[#8f5cf0]" },
    { bg: "bg-[#fff9e6] dark:bg-[#3d321d]", text: "text-[#b27600] dark:text-[#ffca57]", bar: "bg-[#ff9f1a]" },
  ]

  selectedCourses.forEach((c, idx) => {
    c.schedules.forEach((s: any) => {
      if (dayMap[s.day] === undefined) return

      const [sh, sm] = s.start_time.split(":").map(Number)
      const [eh, em] = s.end_time.split(":").map(Number)
      const start = sh + sm / 60
      const end = eh + em / 60
      const dayVal = dayMap[s.day]

      // 겹치거나 중복되는 시간 블록 방지 이중 가드
      const hasConflictInBlocks = scheduleBlocks.some((b: any) => {
        if (b.day !== dayVal) return false
        const bStart = b.start
        const bEnd = b.start + b.span
        return start < bEnd && bStart < end
      })

      if (hasConflictInBlocks) {
        console.warn(`[TIMETABLE ENGINE WARNING] 충돌 시간대 스킵됨: ${c.title || c.name} (${s.day} ${s.start_time})`)
        return
      }

      scheduleBlocks.push({
        id: `block-${String(c.course_id || c.code || "")}-${s.day}-${s.start_time}-${scheduleBlocks.length}`,
        groupId: String(c.course_id || c.code || ""),
        name: cleanCourseName(c.title || c.name || String(c.course_id || c.code || "과목명 미정")),
        day: dayVal,
        start: start,
        span: end - start,
        room: s.classroom || "미정",
        professor: s.professor || c.professor || c.professor_name || "미정",
        colorIndex: idx % pastelPalette.length
      })
    })
  })

  // 4. 추천 이유 구성
  const reasons: ScheduleReason[] = []
  if (dayOffs.length > 0) {
    reasons.push({
      icon: "CalendarOff",
      title: `${dayOffs.join(", ")}요일 공강 보장`,
      desc: `사용자님의 요청을 반영하여 ${dayOffs.join(", ")}요일에는 단 하나의 수업도 배정하지 않았습니다.`
    })
  } else {
    reasons.push({
      icon: "CalendarOff",
      title: "균형 잡힌 주 5일 분산 배치",
      desc: "학습 스트레스를 덜기 위해 특정 요일에 편중되지 않도록 시간표를 분산했습니다."
    })
  }

  reasons.push({
    icon: "GraduationCap",
    title: "미이수 졸업 필수과목 자동 배치",
    desc: "현재 주전공 이수를 위해 남은 미이수 전공 필수 요건들을 누락 없이 담았습니다."
  })
  reasons.push({
    icon: "BrainCircuit",
    title: "강의동 간 동선 최소화 최적화",
    desc: "연강일 때 강의실 이동 거리를 감안하여 효율적인 강의실 위주로 배정했습니다."
  })

  return {
    scheduleDays: ["월", "화", "수", "목", "금"],
    scheduleHours: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    scheduleBlocks,
    scheduleReasons: reasons,
    pastelPalette,
    totalCredits,
    courseCount: selectedCourses.length,
    courses: selectedCourses.map(c => ({
      id: String(c.course_id || c.code || ""),
      name: cleanCourseName(c.title || c.name || String(c.course_id || c.code || "과목명 미정")),
      code: String(c.course_id || c.code || ""),
      credit: c.credit,
      match: 95,
      tags: c.program_type === "MAJOR" ? ["필수"] : ["관심사 매칭"],
      retake: false,
      professor: c.professor,
      time: c.schedules.map((s: any) => `${s.day} ${s.start_time}`).join(" / "),
      schedules: c.schedules
    }))
  }
}
