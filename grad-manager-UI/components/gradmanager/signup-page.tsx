"use client"

import { useState } from "react"
import { GraduationCap, Loader2, Lock, User, BookOpen, UserCheck } from "lucide-react"
import { registerUser } from "@/lib/api"

export function SignUpPage({
  onSignUpSuccess,
  onGoToLogin,
}: {
  onSignUpSuccess: () => void
  onGoToLogin: () => void
}) {
  const [studentId, setStudentId] = useState("")
  const [name, setName] = useState("")
  const [department, setDepartment] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!studentId.trim() || !name.trim() || !department.trim() || !password.trim()) {
      setError("모든 필드를 입력해 주세요.")
      return
    }

    setError(null)
    setSuccessMsg(null)
    setLoading(true)

    try {
      const res = await registerUser(studentId, password, name, department)
      setSuccessMsg(res.message || "회원가입이 완료되었습니다!")
      setTimeout(() => {
        onSignUpSuccess()
      }, 1500)
    } catch (err: any) {
      setError(err.message || "회원가입 중 오류가 발생했습니다.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8">
      {/* Container Card */}
      <div className="w-full max-w-md space-y-8 rounded-[2rem] bg-card p-8 border border-border sm:shadow-lg transition-all duration-300">
        {/* Header Icon & Title */}
        <div className="flex flex-col items-center justify-center text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
            <GraduationCap className="h-8 w-8" />
          </span>
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
            GradManager 가입
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            신규 학생 계정을 등록하고 졸업 플랜을 확인하세요
          </p>
        </div>

        {/* Signup Form */}
        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-3.5 text-center text-xs font-semibold text-destructive">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-50/50 p-3.5 text-center text-xs font-semibold text-emerald-600 dark:text-emerald-400 dark:bg-emerald-950/20">
              {successMsg}
              <p className="mt-1 text-[10px] opacity-85">잠시 후 로그인 페이지로 이동합니다...</p>
            </div>
          )}

          <div className="space-y-4">
            {/* Student ID */}
            <div className="relative">
              <label htmlFor="signup-student-id" className="sr-only">학번</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <User className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                id="signup-student-id"
                name="studentId"
                type="text"
                required
                disabled={loading}
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                className="block w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-11 pr-4 text-sm text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="학번 (예: 2022115001)"
              />
            </div>

            {/* Name */}
            <div className="relative">
              <label htmlFor="signup-name" className="sr-only">이름</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <UserCheck className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                id="signup-name"
                name="name"
                type="text"
                required
                disabled={loading}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="block w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-11 pr-4 text-sm text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="성명 (예: 김한신)"
              />
            </div>

            {/* Department */}
            <div className="relative">
              <label htmlFor="signup-dept" className="sr-only">소속 학과</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <BookOpen className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                id="signup-dept"
                name="department"
                type="text"
                required
                disabled={loading}
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="block w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-11 pr-4 text-sm text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="소속 학과 (예: AI.SW학과)"
              />
            </div>

            {/* Password */}
            <div className="relative">
              <label htmlFor="signup-password" className="sr-only">비밀번호</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
                <Lock className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                id="signup-password"
                name="password"
                type="password"
                required
                disabled={loading}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-11 pr-4 text-sm text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="비밀번호"
              />
            </div>
          </div>

          {/* Submit Button */}
          <div>
            <button
              type="submit"
              disabled={loading}
              className="group relative flex w-full justify-center items-center rounded-2xl bg-primary py-4 text-[17px] font-semibold text-white shadow-sm transition-all hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 h-[56px]"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin text-white" />
                  가입 요청 중…
                </span>
              ) : (
                "회원가입"
              )}
            </button>
          </div>

          {/* Link to Login */}
          <div className="text-center mt-4">
            <button
              type="button"
              onClick={onGoToLogin}
              className="text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
            >
              이미 계정이 있으신가요? <span className="text-primary hover:underline ml-1">로그인</span>
            </button>
          </div>
        </form>
      </div>
    </main>
  )
}
