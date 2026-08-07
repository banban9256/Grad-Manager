"use client"

import { useState } from "react"
import { motion } from "motion/react"
import { GraduationCap, Loader2, Lock, User, BookOpen, UserCheck } from "lucide-react"
import { registerUser } from "@/lib/api"
import { DEPARTMENTS } from "@/lib/constants"

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
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md space-y-8 rounded-[2rem] bg-card p-8 border border-border sm:shadow-lg"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="flex flex-col items-center justify-center text-center"
        >
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
            <GraduationCap className="h-8 w-8" />
          </span>
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
            GradManager 가입
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            신규 학생 계정을 등록하고 졸업 플랜을 확인하세요
          </p>
        </motion.div>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="rounded-xl border border-destructive/20 bg-destructive/5 p-3.5 text-center text-xs font-semibold text-destructive"
            >
              {error}
            </motion.div>
          )}

          {successMsg && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="rounded-xl border border-emerald-500/20 bg-emerald-50/50 p-3.5 text-center text-xs font-semibold text-emerald-600 dark:text-emerald-400 dark:bg-emerald-950/20"
            >
              {successMsg}
              <p className="mt-1 text-[10px] opacity-85">잠시 후 로그인 페이지로 이동합니다...</p>
            </motion.div>
          )}

          <div className="space-y-4">
            {[
              { id: "signup-student-id", icon: User, label: "학번", value: studentId, onChange: setStudentId, placeholder: "학번 (예: 2022115001)", delay: 0.25 },
              { id: "signup-name", icon: UserCheck, label: "이름", value: name, onChange: setName, placeholder: "성명 (예: 김한신)", delay: 0.32 },
              { id: "signup-dept", icon: BookOpen, label: "소속 학과", value: department, onChange: setDepartment, placeholder: "소속 학과 선택", delay: 0.39 },
              { id: "signup-password", icon: Lock, label: "비밀번호", value: password, onChange: setPassword, placeholder: "비밀번호", type: "password", delay: 0.46 },
            ].map((field) => (
              <motion.div
                key={field.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, delay: field.delay }}
                className="relative"
              >
                <label htmlFor={field.id} className="sr-only">{field.label}</label>
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 z-10">
                  <field.icon className="h-5 w-5 text-muted-foreground" />
                </div>
                {field.id === "signup-dept" ? (
                  <select
                    id={field.id}
                    name={field.id}
                    required
                    disabled={loading}
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    className="block w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-11 pr-10 text-sm text-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary appearance-none cursor-pointer"
                  >
                    <option value="" disabled hidden>
                      소속 학과 선택
                    </option>
                    {DEPARTMENTS.map((dept) => (
                      <option key={dept} value={dept}>
                        {dept}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={field.id}
                    name={field.id}
                    type={field.type || "text"}
                    required
                    disabled={loading}
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    className="block w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-11 pr-4 text-sm text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder={field.placeholder}
                  />
                )}
                {field.id === "signup-dept" && (
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                    <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                )}
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.55 }}
          >
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
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.65 }}
            className="text-center mt-4"
          >
            <button
              type="button"
              onClick={onGoToLogin}
              className="text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors"
            >
              이미 계정이 있으신가요? <span className="text-primary hover:underline ml-1">로그인</span>
            </button>
          </motion.div>
        </form>
      </motion.div>
    </main>
  )
}
