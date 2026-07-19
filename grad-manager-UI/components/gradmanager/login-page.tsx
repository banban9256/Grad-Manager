"use client"

import { useState } from "react"
import { GraduationCap, Loader2, Lock, User } from "lucide-react"
import { loginUser } from "@/lib/api"

export function LoginPage({
  onLoginSuccess,
  onGoToSignUp,
}: {
  onLoginSuccess: (token: string, user: any) => void
  onGoToSignUp: () => void
}) {
  const [studentId, setStudentId] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!studentId.trim() || !password.trim()) {
      setError("학번과 비밀번호를 모두 입력해 주세요.")
      return
    }

    setError(null)
    setLoading(true)

    try {
      const { token, user } = await loginUser(studentId, password)
      onLoginSuccess(token, user)
    } catch (err: any) {
      setError(err.message || "로그인 요청에 실패했습니다.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy px-4 py-12 sm:px-6 lg:px-8">
      {/* Container Card */}
      <div className="w-full max-w-md space-y-8 rounded-3xl border border-white/10 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-md">
        {/* Header Icon & Title */}
        <div className="flex flex-col items-center justify-center text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
            <GraduationCap className="h-8 w-8" />
          </span>
          <h2 className="mt-6 text-3xl font-extrabold tracking-tight text-white">
            GradManager
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            졸업을 부탁해 · 한신대 학사관리 시스템
          </p>
        </div>

        {/* Login Form */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-center text-xs font-semibold text-destructive">
              {error}
            </div>
          )}

          <div className="space-y-4 rounded-md shadow-sm">
            {/* Student ID input */}
            <div className="relative">
              <label htmlFor="student-id" className="sr-only">학번</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <User className="h-5 w-5 text-slate-500" />
              </div>
              <input
                id="student-id"
                name="studentId"
                type="text"
                required
                disabled={loading}
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                className="block w-full rounded-2xl border border-white/10 bg-white/5 py-3.5 pl-10 pr-3 text-sm text-white placeholder-slate-500 focus:border-primary focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="학번을 입력하세요 (예: 2022115xxx)"
              />
            </div>

            {/* Password input */}
            <div className="relative">
              <label htmlFor="password" className="sr-only">비밀번호</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <Lock className="h-5 w-5 text-slate-500" />
              </div>
              <input
                id="password"
                name="password"
                type="password"
                required
                disabled={loading}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full rounded-2xl border border-white/10 bg-white/5 py-3.5 pl-10 pr-3 text-sm text-white placeholder-slate-500 focus:border-primary focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="비밀번호를 입력하세요"
              />
            </div>
          </div>

          {/* Submit Button */}
          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative flex w-full justify-center rounded-2xl bg-primary py-3.5 text-sm font-bold text-white shadow-lg transition-all hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                  로그인 중…
                </span>
              ) : (
                "로그인"
              )}
            </button>
          </div>

          {/* Link to Signup */}
          <div className="text-center mt-4">
            <button
              type="button"
              onClick={onGoToSignUp}
              className="text-xs font-semibold text-slate-400 hover:text-white transition-colors"
            >
              아직 계정이 없으신가요? <span className="text-primary underline">회원가입</span>
            </button>
          </div>
        </form>
      </div>
    </main>
  )
}
