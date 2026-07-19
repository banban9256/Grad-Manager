"use client"

import { createContext, useContext, useEffect, useState } from "react"
import { GraduationCap, Loader2 } from "lucide-react"
import type { GradManagerData } from "@/lib/grad-data-types"
import { getGradData } from "@/lib/api"
import { ToastProvider } from "./toast"
import { LoginPage } from "./login-page"
import { SignUpPage } from "./signup-page"

const GradDataContext = createContext<GradManagerData | null>(null)

export function GradDataProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<GradManagerData | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [authState, setAuthState] = useState<"login" | "signup">("login")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Check login session on mount
  useEffect(() => {
    const token = sessionStorage.getItem("token")
    if (token) {
      setIsLoggedIn(true)
    } else {
      setLoading(false)
    }
  }, [])

  // Fetch grad manager data when logged in
  useEffect(() => {
    if (!isLoggedIn) return

    let cancelled = false
    setLoading(true)
    setError(null)

    getGradData()
      .then((json) => {
        if (!cancelled) {
          setData(json)
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [isLoggedIn])

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

  // Inject logout method to Context
  const contextValue: GradManagerData = {
    ...data,
    logout,
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
