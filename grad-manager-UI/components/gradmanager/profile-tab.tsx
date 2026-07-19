"use client"

import { useEffect, useState } from "react"
import {
  User,
  GraduationCap,
  BookOpen,
  Bell,
  Moon,
  Tag,
  LogOut,
  Edit2,
  Check,
  Loader2,
  ChevronRight,
} from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { updateProfile } from "@/lib/api"

export function ProfileTab() {
  const { user, logout } = useGradData()
  const { showToast } = useToast()
  const { userInfo } = user

  // Editable Profile States
  const [isEditing, setIsEditing] = useState(false)
  const [name, setName] = useState(userInfo.name)
  const [studentId, setStudentId] = useState(userInfo.studentId)
  const [department, setDepartment] = useState(userInfo.department)
  const [saveLoading, setSaveLoading] = useState(false)

  // Settings states
  const [notifyEnabled, setNotifyEnabled] = useState(true)
  const [darkTheme, setDarkTheme] = useState(false)

  // Initial dark theme check
  useEffect(() => {
    if (typeof window !== "undefined") {
      setDarkTheme(document.documentElement.classList.contains("dark"))
    }
  }, [])

  const handleToggleDarkMode = (enabled: boolean) => {
    setDarkTheme(enabled)
    if (enabled) {
      document.documentElement.classList.add("dark")
    } else {
      document.documentElement.classList.remove("dark")
    }
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !studentId.trim() || !department.trim()) {
      showToast("모든 프로필 필드를 입력해 주세요.")
      return
    }

    setSaveLoading(true)
    try {
      await updateProfile(name, studentId, department)
      showToast("정보가 수정되었습니다.")
      setIsEditing(false)
    } catch (err: any) {
      showToast(err.message || "정보 수정에 실패했습니다.")
    } finally {
      setSaveLoading(false)
    }
  }

  return (
    <div className="space-y-6 px-4 pb-6 pt-5 md:max-w-4xl md:mx-auto md:px-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">마이페이지 &amp; 설정</h1>
        <p className="text-sm text-muted-foreground">개인정보 확인 및 환경설정을 관리하세요</p>
      </div>

      {/* Profile Section */}
      <section className="rounded-3xl bg-card p-5 shadow-sm border border-border">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">내 프로필 정보</h2>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-1 text-xs font-bold text-primary hover:underline"
            >
              <Edit2 className="h-3.5 w-3.5" />
              수정
            </button>
          )}
        </div>

        {isEditing ? (
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">성명</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">학번</label>
                <input
                  type="text"
                  required
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">소속 학과</label>
                <input
                  type="text"
                  required
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setName(userInfo.name)
                  setStudentId(userInfo.studentId)
                  setDepartment(userInfo.department)
                  setIsEditing(false)
                }}
                className="flex-1 rounded-xl bg-secondary py-2.5 text-xs font-bold text-secondary-foreground"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={saveLoading}
                className="flex-1 rounded-xl bg-primary py-2.5 text-xs font-bold text-primary-foreground flex items-center justify-center gap-1.5"
              >
                {saveLoading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    저장 중…
                  </>
                ) : (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    저장
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-3.5">
            <ProfileInfoRow Icon={User} label="이름" value={name} />
            <ProfileInfoRow Icon={GraduationCap} label="학번" value={studentId} />
            <ProfileInfoRow Icon={BookOpen} label="학과" value={department} />
          </div>
        )}
      </section>

      {/* Settings Section */}
      <section className="rounded-3xl bg-card p-5 shadow-sm border border-border space-y-4">
        <h2 className="text-sm font-semibold text-foreground">환경설정</h2>

        <div className="space-y-1">
          {/* Notifications switch */}
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Bell className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">알림 설정</p>
                <p className="text-[11px] text-muted-foreground">졸업 요건 분석 및 공지 알림 수신</p>
              </div>
            </div>
            <button
              onClick={() => setNotifyEnabled(!notifyEnabled)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                notifyEnabled ? "bg-primary" : "bg-muted"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  notifyEnabled ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Dark theme switch */}
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-500/10 text-purple-500">
                <Moon className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">다크 모드</p>
                <p className="text-[11px] text-muted-foreground">어두운 테마 스킨 적용</p>
              </div>
            </div>
            <button
              onClick={() => handleToggleDarkMode(!darkTheme)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                darkTheme ? "bg-primary" : "bg-muted"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  darkTheme ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Notice keyword management */}
          <button
            onClick={() => showToast("준비 중인 기능입니다.")}
            className="w-full flex items-center justify-between py-2 text-left hover:bg-accent/50 rounded-xl px-1 -mx-1"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-500/10 text-teal-500">
                <Tag className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">공지사항 키워드 관리</p>
                <p className="text-[11px] text-muted-foreground">학사 알림 키워드 등록/해제</p>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>
      </section>

      {/* Logout Action Button */}
      <div className="pt-2">
        <button
          onClick={logout}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-destructive/10 hover:bg-destructive/20 py-3.5 text-sm font-bold text-destructive transition-colors shadow-sm"
        >
          <LogOut className="h-4.5 w-4.5" />
          안전하게 로그아웃
        </button>
      </div>
    </div>
  )
}

function ProfileInfoRow({
  Icon,
  label,
  value,
}: {
  Icon: typeof User
  label: string;
  value: string
}) {
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-secondary text-secondary-foreground">
        <Icon className="h-4.5 w-4.5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] text-muted-foreground">{label}</p>
        <p className="text-sm font-bold text-foreground truncate">{value}</p>
      </div>
    </div>
  )
}
