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
        <h1 className="text-2xl font-bold text-foreground">마이페이지 &amp; 설정</h1>
        <p className="text-sm text-muted-foreground mt-0.5">개인정보 확인 및 환경설정을 관리하세요</p>
      </div>

      {/* Profile Section */}
      <section className="rounded-3xl bg-card p-5 shadow-sm border border-border">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-muted-foreground">내 프로필 정보</h2>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-1 text-xs font-bold text-primary hover:underline transition-colors"
            >
              <Edit2 className="h-3.5 w-3.5" />
              수정
            </button>
          )}
        </div>

        {isEditing ? (
          <form onSubmit={handleSaveProfile} className="space-y-4.5">
            <div className="space-y-3.5">
              <div>
                <label className="text-[11px] font-bold text-muted-foreground block mb-1">성명</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3 text-sm text-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-muted-foreground block mb-1">학번</label>
                <input
                  type="text"
                  required
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3 text-sm text-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-muted-foreground block mb-1">소속 학과</label>
                <input
                  type="text"
                  required
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3 text-sm text-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <div className="flex gap-2.5 pt-1.5">
              <button
                type="button"
                onClick={() => {
                  setName(userInfo.name)
                  setStudentId(userInfo.studentId)
                  setDepartment(userInfo.department)
                  setIsEditing(false)
                }}
                className="flex-1 rounded-2xl bg-secondary py-3.5 text-[15px] font-semibold text-secondary-foreground hover:opacity-90 h-[48px]"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={saveLoading}
                className="flex-1 rounded-2xl bg-primary py-3.5 text-[15px] font-semibold text-white hover:bg-primary-hover flex items-center justify-center gap-1.5 h-[48px] disabled:opacity-50"
              >
                {saveLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    저장 중…
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    저장
                  </>
                )}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <ProfileInfoRow Icon={User} label="이름" value={name} />
            <ProfileInfoRow Icon={GraduationCap} label="학번" value={studentId} />
            <ProfileInfoRow Icon={BookOpen} label="학과" value={department} />
          </div>
        )}
      </section>

      {/* Settings Section */}
      <section className="rounded-3xl bg-card p-5 shadow-sm border border-border space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">환경설정</h2>

        <div className="space-y-2">
          {/* Notifications switch */}
          <div className="flex items-center justify-between py-1.5">
            <div className="flex items-center gap-3">
              <span className="flex h-9.5 w-9.5 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Bell className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">알림 설정</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">졸업 요건 분석 및 공지 알림 수신</p>
              </div>
            </div>
            <button
              onClick={() => setNotifyEnabled(!notifyEnabled)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                notifyEnabled ? "bg-primary" : "bg-[#e5e8eb] dark:bg-[#2c3746]"
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
          <div className="flex items-center justify-between py-1.5">
            <div className="flex items-center gap-3">
              <span className="flex h-9.5 w-9.5 items-center justify-center rounded-xl bg-[#8f5cf0]/10 text-[#8f5cf0]">
                <Moon className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">다크 모드</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">어두운 테마 스킨 적용</p>
              </div>
            </div>
            <button
              onClick={() => handleToggleDarkMode(!darkTheme)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                darkTheme ? "bg-primary" : "bg-[#e5e8eb] dark:bg-[#2c3746]"
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
            className="w-full flex items-center justify-between py-1.5 text-left hover:bg-secondary rounded-2xl px-2.5 -mx-2.5 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-9.5 w-9.5 items-center justify-center rounded-xl bg-[#00b5a3]/10 text-[#00b5a3]">
                <Tag className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">공지사항 키워드 관리</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">학사 알림 키워드 등록/해제</p>
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
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#fff3f5] dark:bg-[#381e25] hover:bg-opacity-80 py-4 text-[17px] font-bold text-[#d6284a] dark:text-[#ff6b8b] transition-all shadow-sm h-[56px]"
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
    <div className="flex items-center gap-3.5 py-1">
      <span className="flex h-9.5 w-9.5 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
        <Icon className="h-4.5 w-4.5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] text-muted-foreground font-semibold">{label}</p>
        <p className="text-sm font-bold text-foreground truncate mt-0.5">{value}</p>
      </div>
    </div>
  )
}
