"use client"

import { createContext, useContext, useEffect, useState } from "react"
import { GraduationCap, Loader2 } from "lucide-react"
import type { GradManagerData } from "@/lib/grad-data-types"
import { getGradData } from "@/lib/api"
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

  // 관심 키워드 전역 상태 관리
  const [interestKeywords, setInterestKeywords] = useState<any[]>([])

  // 전체 과목 풀 전역 상태
  const [allCourses, setAllCourses] = useState<any[]>([])

  // 챗봇 메시지 전역 상태 관리
  const [messages, setMessages] = useState<any[]>(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("grad_chatbot_messages")
      if (stored) {
        try {
          return JSON.parse(stored)
        } catch (e) {
          console.error("챗봇 메시지 파싱 실패:", e)
        }
      }
    }
    return [
      {
        id: "welcome",
        role: "ai",
        content: "안녕하세요! 원하는 수강 조건을 알려주세요. 예) “금요일 공강”, “전공 필수 과목 위주로 추천해줘”",
      },
    ]
  })

  // 시뮬레이션 적용 시간표 전역 상태
  const [simulatedSchedule, setSimulatedSchedule] = useState<any>(null)

  // 컴포넌트 마운트 시 전체 개설 과목 풀 로딩
  useEffect(() => {
    async function loadAllCourses() {
      try {
        const { searchCourseOfferings } = await import("@/lib/api")
        const courses = await searchCourseOfferings("")
        setAllCourses(courses)
      } catch (err) {
        console.error("전체 개설 과목 목록 로딩 실패:", err)
      }
    }
    if (isLoggedIn) {
      loadAllCourses()
    }
  }, [isLoggedIn])

  // 메시지 혹은 과목 풀 업데이트 시 시뮬레이션 엔진 실행
  useEffect(() => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("grad_chatbot_messages", JSON.stringify(messages))
    }
    if (messages.length > 0 && allCourses.length > 0) {
      const result = generateTimetableFromChat(messages, allCourses)
      setSimulatedSchedule(result)
      if (result) {
        if (typeof window !== "undefined") {
          sessionStorage.setItem("grad_simulated_timetable", JSON.stringify(result))
          sessionStorage.setItem("chatbot_simulation_applied", "true")
        }
      } else {
        if (typeof window !== "undefined") {
          sessionStorage.removeItem("grad_simulated_timetable")
          sessionStorage.removeItem("chatbot_simulation_applied")
        }
      }
    } else {
      setSimulatedSchedule(null)
    }
  }, [messages, allCourses])

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
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("grad_chatbot_messages")
      sessionStorage.removeItem("grad_simulated_timetable")
      sessionStorage.removeItem("chatbot_simulation_applied")
      sessionStorage.removeItem("chatbot_simulation_data")
    }
  }

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("grad_manager_keywords")
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
        localStorage.setItem("grad_manager_keywords", JSON.stringify(data.notice.interestKeywords.map((k) => k.label || k.text)))
      }
    }
  }, [data])

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
    if (typeof window !== "undefined") {
      localStorage.setItem("grad_manager_keywords", JSON.stringify(nextKeywords.map((k) => k.label || k.text)))
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
    if (typeof window !== "undefined") {
      localStorage.setItem("grad_manager_keywords", JSON.stringify(nextKeywords.map((k) => k.label || k.text)))
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
    } catch (err: any) {
      setError(err.message || "데이터 새로고침에 실패했습니다.")
    }
  }

  const login = (token: string, user: any) => {
    sessionStorage.setItem("token", token)
    setIsLoggedIn(true)
  }

  const logout = () => {
    sessionStorage.removeItem("token")
    setIsLoggedIn(false)
    setData(null)
  }

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
    messages,
    setMessages,
    simulatedSchedule,
    resetSimulation,
    allCourses,
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
