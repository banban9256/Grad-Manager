"use client"

import { createContext, useContext, useEffect, useState, useMemo } from "react"
import { GraduationCap, Loader2 } from "lucide-react"
import type { GradManagerData } from "@/lib/grad-data-types"
import { getGradData, updateCompletedCourses as apiUpdateCompletedCourses, getSemesterList } from "@/lib/api"
import { ToastProvider } from "./toast"
import { LoginPage } from "./login-page"
import { SignUpPage } from "./signup-page"
import { generateTimetableFromChat } from "@/lib/timetable-engine"

const GradDataContext = createContext<GradManagerData | null>(null)

export function GradDataProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<GradManagerData | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [authState, setAuthState] = useState<"login" | "signup">("login")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 기수강 완료 과목 목록 전역 상태
  const [completedCourses, setCompletedCourses] = useState<string[]>([])

  // 관심 키워드 전역 상태 관리
  const [interestKeywords, setInterestKeywords] = useState<any[]>([])

  // 알림 토글 스위치 전역 상태
  const [notifyEnabled, setNotifyEnabled] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("grad_notify_enabled")
      return saved !== null ? saved === "true" : true
    }
    return true
  })

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("grad_notify_enabled", String(notifyEnabled))
    }
  }, [notifyEnabled])

  // 전체 과목 풀 전역 상태
  const [allCourses, setAllCourses] = useState<any[]>([])

  // 챗봇 메시지 전역 상태 관리
  const [messages, setMessages] = useState<any[]>([
    {
      id: "welcome",
      role: "ai",
      content: "안녕하세요! 원하는 수강 조건을 알려주세요. 예) “금요일 공강”, “전공 필수 과목 위주로 추천해줘”",
    },
  ])

  // 시뮬레이션 적용 시간표 전역 상태
  const [simulatedSchedule, setSimulatedSchedule] = useState<any>(null)

  const studentId = data?.user?.userInfo?.studentId

  const [semesters, setSemesters] = useState<string[]>([
    "2026-2학기", "2026-1학기", "2025-2학기", "2025-1학기",
    "2024-2학기", "2024-1학기", "2023-2학기", "2023-1학기",
    "2022-2학기", "2022-1학기", "2021-2학기", "2021-1학기"
  ])

  // 학기 관리 상태 신설 (마지막 조회 학기 복원 지원)
  const getSavedSemester = (id: string) => {
    if (typeof window !== "undefined" && id) {
      const lastSem = localStorage.getItem(`grad_last_viewed_semester_${id}`)
      if (lastSem) return lastSem
    }
    return "2026-1학기"
  }

  const [selectedSemester, setSelectedSemester] = useState<string>(() => getSavedSemester(studentId || "20210001"))

  // 학기 동적 로드 이펙트
  useEffect(() => {
    let isMounted = true
    getSemesterList().then((list) => {
      if (isMounted && list && list.length > 0) {
        setSemesters(list)
        const saved = getSavedSemester(studentId || "20210001")
        if (saved && list.includes(saved)) {
          setSelectedSemester(saved)
        } else {
          setSelectedSemester(list[0])
        }
      }
    }).catch((err) => {
      console.error("학기 목록 로드 실패:", err)
    })
    return () => {
      isMounted = false
    }
  }, [studentId])

  // 로그인 성공이나 data 로드 시 completedCourses 및 로컬 스토리지 동기화
  useEffect(() => {
    if (studentId) {
      const localKey = `grad_completed_courses_${studentId}`
      if (data?.user?.userInfo?.completedCourses) {
        // 백엔드 API의 최신 completedCourses 데이터를 최우선적으로 전역 상태 및 스토리지 캐시에 덮어쓰기
        setCompletedCourses(data.user.userInfo.completedCourses)
        localStorage.setItem(localKey, JSON.stringify(data.user.userInfo.completedCourses))
        sessionStorage.setItem(localKey, JSON.stringify(data.user.userInfo.completedCourses))
      } else {
        const localCached = localStorage.getItem(localKey)
        if (localCached) {
          try {
            setCompletedCourses(JSON.parse(localCached))
          } catch (e) {
            console.error("완료 과목 로컬 캐시 파싱 실패:", e)
          }
        }
      }
    } else {
      setCompletedCourses([])
    }
  }, [data, studentId])

  useEffect(() => {
    if (typeof window !== "undefined" && studentId) {
      const stored = sessionStorage.getItem(`grad_chatbot_messages_${studentId}`)
      if (stored) {
        try {
          setMessages(JSON.parse(stored))
        } catch (e) {
          console.error("챗봇 메시지 파싱 실패:", e)
        }
      } else {
        setMessages([
          {
            id: "welcome",
            role: "ai",
            content: "안녕하세요! 원하는 수강 조건을 알려주세요. 예) “금요일 공강”, “전공 필수 과목 위주로 추천해줘”",
          },
        ])
      }
    }
  }, [studentId])

  // 컴포넌트 마운트 및 선택 학기 변경 시 개설 과목 풀 로딩
  useEffect(() => {
    async function loadAllCourses() {
      try {
        const { searchCourseOfferings } = await import("@/lib/api")
        const courses = await searchCourseOfferings("", selectedSemester)
        setAllCourses(courses)
      } catch (err) {
        console.error("개설 과목 목록 로딩 실패:", err)
      }
    }
    if (isLoggedIn && selectedSemester) {
      loadAllCourses()
    }
  }, [isLoggedIn, selectedSemester])

  // 메시지 혹은 과목 풀 업데이트 시 시뮬레이션 엔진 실행
  useEffect(() => {
    if (!studentId) return

    const messagesKey = `grad_chatbot_messages_${studentId}`
    const simulatedTimetableKey = `grad_simulated_timetable_${studentId}_${selectedSemester}`
    const simulationAppliedKey = `chatbot_simulation_applied_${studentId}_${selectedSemester}`
    const aiRecommendedTimetableKey = `grad_manager_ai_recommended_timetable_${studentId}_${selectedSemester}`

    if (typeof window !== "undefined") {
      sessionStorage.setItem(messagesKey, JSON.stringify(messages))
    }
    if (messages.length > 0 && allCourses.length > 0) {
      const result = generateTimetableFromChat(messages, allCourses)
      setSimulatedSchedule(result)
      if (result) {
        if (typeof window !== "undefined") {
          sessionStorage.setItem(simulatedTimetableKey, JSON.stringify(result))
          sessionStorage.setItem(simulationAppliedKey, "true")
          // AI 추천 시간표를 localStorage에 영구 보존
          localStorage.setItem(aiRecommendedTimetableKey, JSON.stringify(result))
        }
      } else {
        if (typeof window !== "undefined") {
          sessionStorage.removeItem(simulatedTimetableKey)
          sessionStorage.removeItem(simulationAppliedKey)
        }
      }
    } else {
      // 메시지가 비었을 경우 로컬 스토리지 백업 복원 시도
      if (typeof window !== "undefined") {
        const cached = localStorage.getItem(aiRecommendedTimetableKey)
        if (cached) {
          try {
            setSimulatedSchedule(JSON.parse(cached))
          } catch {}
        } else {
          setSimulatedSchedule(null)
        }
      } else {
        setSimulatedSchedule(null)
      }
    }
  }, [messages, allCourses, studentId, selectedSemester])

  // 챗봇 시뮬레이션 초기화 액션
  const resetSimulation = () => {
    setMessages([
      {
        id: "welcome",
        role: "ai",
        content: "안녕하세요! 원하는 수강 조건을 알려주세요. 예) “금요일 공강”, “전공 필수 과목 위주로 추천해줘”",
      },
    ])
    setSimulatedSchedule(null)
    if (typeof window !== "undefined" && studentId) {
      sessionStorage.removeItem(`grad_chatbot_messages_${studentId}`)
      sessionStorage.removeItem(`grad_simulated_timetable_${studentId}_${selectedSemester}`)
      sessionStorage.removeItem(`chatbot_simulation_applied_${studentId}_${selectedSemester}`)
      sessionStorage.removeItem(`chatbot_simulation_data_${studentId}`)
      localStorage.removeItem(`grad_manager_ai_recommended_timetable_${studentId}_${selectedSemester}`)
    }
  }

  useEffect(() => {
    if (!studentId) return

    const keywordsKey = `grad_manager_keywords_${studentId}`

    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(keywordsKey)
      if (stored) {
        try {
          const parsed = JSON.parse(stored)
          if (Array.isArray(parsed)) {
            setInterestKeywords(parsed.map((kw, idx) => ({ id: idx, text: kw, active: true })))
            return
          }
        } catch (e) {
          console.error("localStorage 키워드 파싱 실패:", e)
        }
      }
    }

    if (data?.notice?.interestKeywords) {
      setInterestKeywords(data.notice.interestKeywords)
      if (typeof window !== "undefined") {
        localStorage.setItem(keywordsKey, JSON.stringify(data.notice.interestKeywords.map((k) => k.label || k.text)))
      }
    } else {
      setInterestKeywords([])
    }
  }, [data, studentId])

  const updateKeywordsOnServer = async (updatedKeywords: string[]) => {
    if (!data?.user?.userInfo?.studentId) return
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    const token = sessionStorage.getItem("token")
    await fetch(`${API_BASE_URL}/api/v1/notices/keywords`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        studentId: data.user.userInfo.studentId,
        keywords: updatedKeywords,
      }),
    })
  }

  const addInterestKeyword = async (text: string) => {
    const currentTexts = interestKeywords.map((k) => k.label || k.text)
    if (currentTexts.includes(text)) return
    
    // UI 및 localStorage 즉시 업데이트
    const newKeywordObj = { id: interestKeywords.length, text, active: true }
    const nextKeywords = [...interestKeywords, newKeywordObj]
    setInterestKeywords(nextKeywords)
    if (typeof window !== "undefined" && studentId) {
      localStorage.setItem(`grad_manager_keywords_${studentId}`, JSON.stringify(nextKeywords.map((k) => k.label || k.text)))
    }
    
    try {
      await updateKeywordsOnServer(nextKeywords.map((k) => k.text))
      await refreshData()
    } catch (err) {
      console.error("서버 키워드 싱크 실패 (로컬 스토리지 데이터 유지):", err)
    }
  }

  const removeInterestKeyword = async (text: string) => {
    const nextKeywords = interestKeywords.filter((k) => (k.label || k.text) !== text)
    setInterestKeywords(nextKeywords)
    if (typeof window !== "undefined" && studentId) {
      localStorage.setItem(`grad_manager_keywords_${studentId}`, JSON.stringify(nextKeywords.map((k) => k.label || k.text)))
    }
    
    try {
      await updateKeywordsOnServer(nextKeywords.map((k) => k.label || k.text))
      await refreshData()
    } catch (err) {
      console.error("서버 키워드 싱크 실패 (로컬 스토리지 데이터 유지):", err)
    }
  }

  // Check login session on mount
  useEffect(() => {
    const token = sessionStorage.getItem("token")
    if (token) {
      setIsLoggedIn(true)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const json = await getGradData()
      setData(json)
    } catch (err: any) {
      setError(err.message || "데이터를 불러오지 못했습니다.")
    } finally {
      setLoading(false)
    }
  }

  // Fetch grad manager data when logged in
  useEffect(() => {
    if (!isLoggedIn) return
    fetchData()
  }, [isLoggedIn])

  const refreshData = async () => {
    try {
      const json = await getGradData()
      setData(json)
      if (json?.user?.userInfo?.studentId && json.user.userInfo.completedCourses) {
        const localKey = `grad_completed_courses_${json.user.userInfo.studentId}`
        localStorage.setItem(localKey, JSON.stringify(json.user.userInfo.completedCourses))
        sessionStorage.setItem(localKey, JSON.stringify(json.user.userInfo.completedCourses))
        setCompletedCourses(json.user.userInfo.completedCourses)
      }
    } catch (err: any) {
      setError(err.message || "데이터 새로고침에 실패했습니다.")
    }
  }

  const updateCompletedCourses = async (studentId: string, completedCoursesList: string[], targetSemester?: string) => {
    // 1. 전역 상태 및 로컬 스토리지 즉시 업데이트
    setCompletedCourses(completedCoursesList)
    const localKey = `grad_completed_courses_${studentId}`
    if (typeof window !== "undefined") {
      localStorage.setItem(localKey, JSON.stringify(completedCoursesList))
      sessionStorage.setItem(localKey, JSON.stringify(completedCoursesList))
    }

    // 2. 백엔드 API 연동
    const result = await apiUpdateCompletedCourses(studentId, completedCoursesList, targetSemester)

    // 3. 백엔드 갱신
    await refreshData()
    return result
  }

  const login = (token: string, user: any) => {
    sessionStorage.setItem("token", token)
    if (user?.studentId) {
      sessionStorage.setItem("active_student_id", user.studentId)
    }
    setIsLoggedIn(true)
  }

  const logout = () => {
    if (typeof window !== "undefined") {
      // 모든 sessionStorage 제거
      sessionStorage.clear()
      
      // localStorage에서 유저 캐시 데이터들 제거
      const keysToRemove: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && (key.startsWith("grad_") || key.startsWith("chatbot_") || key.startsWith("schedule_"))) {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach(k => localStorage.removeItem(k))
    }
    setIsLoggedIn(false)
    setData(null)
    setInterestKeywords([])
    setMessages([
      {
        id: "welcome",
        role: "ai",
        content: "안녕하세요! 원하는 수강 조건을 알려주세요. 예) “금요일 공강”, “전공 필수 과목 위주로 추천해줘”",
      },
    ])
    setSimulatedSchedule(null)
  }

  // 기수강 완료 과목 리스트를 기반으로 클라이언트 단에서 실시간 학점 및 카테고리 진행률 계산 헬퍼 함수
  const calculateGradSummary = (
    completedCoursesList: string[],
    allCoursesList: any[],
    totalRequired: number = 130
  ) => {
    const categoryGoals: Record<string, number> = {
      "전공필수": 18,
      "전공선택": 45,
      "교양필수": 14,
      "교양선택": 20,
      "계열공통": 12,
    }

    const categoryEarned: Record<string, number> = {
      "전공필수": 0,
      "전공선택": 0,
      "교양필수": 0,
      "교양선택": 0,
      "계열공통": 0,
      "일반선택": 0,
    }

    const courseMap = new Map<string, { category: string; credit: number }>()
    if (allCoursesList && allCoursesList.length > 0) {
      allCoursesList.forEach((c: any) => {
        const code = String(c.course_code || c.code || c.course_id || "")
        if (code && !courseMap.has(code)) {
          courseMap.set(code, {
            category: c.category || "일반선택",
            credit: Number(c.credits || c.credit || 3)
          })
        }
      })
    }

    let totalEarned = 0
    completedCoursesList.forEach((code) => {
      const course = courseMap.get(code)
      const credit = course ? course.credit : 3
      const cat = course ? course.category : "일반선택"

      totalEarned += credit
      const normalizedCat = ["전공필수", "전공선택", "교양필수", "교양선택", "계열공통"].includes(cat)
        ? cat
        : "일반선택"
      
      categoryEarned[normalizedCat] += credit
    })

    const categoryKeys: Record<string, string> = {
      "전공필수": "major_req",
      "전공선택": "major_sel",
      "교양필수": "liberal_req",
      "교양선택": "liberal_sel",
      "계열공통": "core_common",
      "일반선택": "general_sel"
    }

    const categoryTones: Record<string, string> = {
      "전공필수": "chart-1",
      "전공선택": "chart-2",
      "교양필수": "chart-3",
      "교양선택": "chart-1",
      "계열공통": "chart-2",
      "일반선택": "chart-3"
    }

    const creditCategories = Object.keys(categoryGoals).map((cat) => ({
      key: categoryKeys[cat] || "etc",
      label: cat,
      current: categoryEarned[cat],
      required: categoryGoals[cat],
      tone: categoryTones[cat] || "chart-1"
    }))

    creditCategories.push({
      key: "general_sel",
      label: "일반선택",
      current: categoryEarned["일반선택"],
      required: 21,
      tone: "chart-3"
    })

    return {
      earnedCredits: totalEarned,
      remainingCredits: Math.max(0, totalRequired - totalEarned),
      overallProgress: totalRequired > 0 ? Math.min(100, Math.round((totalEarned / totalRequired) * 100)) : 0,
      creditCategories
    }
  }

  // 클라이언트 계산 오버라이드 억제 및 제거

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-navy p-0 sm:p-6">
        <div className="flex h-screen w-full max-w-[420px] flex-col items-center justify-center bg-background shadow-2xl sm:h-[860px] sm:rounded-[2.5rem] sm:border-8 sm:border-navy">
          <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
            <GraduationCap className="h-7 w-7" />
          </span>
          <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden />
          <p className="mt-4 text-sm font-medium text-foreground">GradManager 불러오는 중…</p>
          <p className="mt-1 text-xs text-muted-foreground">졸업 데이터를 준비하고 있어요</p>
        </div>
      </main>
    )
  }

  if (!isLoggedIn) {
    if (authState === "signup") {
      return (
        <SignUpPage
          onSignUpSuccess={() => setAuthState("login")}
          onGoToLogin={() => setAuthState("login")}
        />
      )
    }
    return (
      <LoginPage
        onLoginSuccess={login}
        onGoToSignUp={() => setAuthState("signup")}
      />
    )
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-navy p-6">
        <div className="max-w-sm rounded-2xl bg-card p-6 text-center shadow-lg">
          <p className="text-sm font-semibold text-destructive">데이터 로드 실패</p>
          <p className="mt-2 text-xs text-muted-foreground">{error ?? "알 수 없는 오류"}</p>
          <button
            onClick={logout}
            className="mt-4 w-full rounded-xl bg-destructive px-4 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90"
          >
            로그인 화면으로 돌아가기
          </button>
        </div>
      </main>
    )
  }

  // Inject logout, refresh, and keyword actions to Context
  const contextValue: GradManagerData = {
    ...data,
    logout,
    refreshData,
    addInterestKeyword,
    removeInterestKeyword,
    updateCompletedCourses,
    messages,
    setMessages,
    simulatedSchedule,
    resetSimulation,
    allCourses,
    notifyEnabled,
    setNotifyEnabled,
    selectedSemester,
    setSelectedSemester,
    semesters,
    user: data?.user || { userInfo: {} as any, creditCategories: [], quickMenus: [] },
    notice: data?.notice ? {
      ...data.notice,
      interestKeywords,
    } : { interestKeywords: [], urgentNotice: {} as any, academicCalendar: [] },
  }

  return (
    <GradDataContext.Provider value={contextValue}>
      <ToastProvider>{children}</ToastProvider>
    </GradDataContext.Provider>
  )
}

export function useGradData() {
  const ctx = useContext(GradDataContext)
  if (!ctx) throw new Error("useGradData must be used within GradDataProvider")
  return ctx
}
