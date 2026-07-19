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
    <main className="flex min-h-screen items-center justify-center bg-navy px-4 py-12 sm:px-6 lg:px-8">
      {/* Container Card */}
      <div className="w-full max-w-md space-y-8 rounded-3xl border border-white/10 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-md">
        {/* Header Icon & Title */}
        <div className="flex flex-col items-center justify-center text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
            <GraduationCap className="h-8 w-8" />
          </span>
          <h2 className="mt-6 text-3xl font-extrabold tracking-tight text-white">
            GradManager 가입
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            신규 학생 계정을 등록하고 졸업 플랜을 확인하세요
          </p>
        </div>

        {/* Signup Form */}
        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-center text-xs font-semibold text-destructive">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-center text-xs font-semibold text-emerald-400">
              {successMsg}
              <p className="mt-1 text-[10px] text-emerald-400/80">잠시 후 로그인 페이지로 이동합니다...</p>
            </div>
          )}

          <div className="space-y-3.5 rounded-md shadow-sm">
            {/* Student ID */}
            <div className="relative">
              <label htmlFor="signup-student-id" className="sr-only">학번</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <User className="h-5 w-5 text-slate-500" />
              </div>
              <input
                id="signup-student-id"
                name="studentId"
                type="text"
                required
                disabled={loading}
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                className="block w-full rounded-2xl border border-white/10 bg-white/5 py-3.5 pl-10 pr-3 text-sm text-white placeholder-slate-500 focus:border-primary focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="학번 (예: 2022115001)"
              />
            </div>

            {/* Name */}
            <div className="relative">
              <label htmlFor="signup-name" className="sr-only">이름</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <UserCheck className="h-5 w-5 text-slate-500" />
              </div>
              <input
                id="signup-name"
                name="name"
                type="text"
                required
                disabled={loading}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="block w-full rounded-2xl border border-white/10 bg-white/5 py-3.5 pl-10 pr-3 text-sm text-white placeholder-slate-500 focus:border-primary focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="성명 (예: 김한신)"
              />
            </div>

            {/* Department */}
            <div className="relative">
              <label htmlFor="signup-dept" className="sr-only">소속 학과</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <BookOpen className="h-5 w-5 text-slate-500" />
              </div>
              <input
                id="signup-dept"
                name="department"
                type="text"
                required
                disabled={loading}
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="block w-full rounded-2xl border border-white/10 bg-white/5 py-3.5 pl-10 pr-3 text-sm text-white placeholder-slate-500 focus:border-primary focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="소속 학과 (예: AI.SW학과)"
              />
            </div>

            {/* Password */}
            <div className="relative">
              <label htmlFor="signup-password" className="sr-only">비밀번호</label>
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <Lock className="h-5 w-5 text-slate-500" />
              </div>
              <input
                id="signup-password"
                name="password"
                type="password"
                required
                disabled={loading}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full rounded-2xl border border-white/10 bg-white/5 py-3.5 pl-10 pr-3 text-sm text-white placeholder-slate-500 focus:border-primary focus:bg-white/10 focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="비밀번호"
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
              className="text-xs font-semibold text-slate-400 hover:text-white transition-colors"
            >
              이미 계정이 있으신가요? <span className="text-primary underline">로그인</span>
            </button>
          </div>
        </form>
      </div>
    </main>
  )
}
