"use client"

import { useEffect, useState } from "react"
import { 
  GraduationCap, 
  BookOpen, 
  Check, 
  ArrowLeft,
  Loader2,
  Layers,
  Award,
  Pencil,
  X
} from "lucide-react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { updateProfile } from "@/lib/api"
import { DEPARTMENTS, CONVERGENCE_MAJORS, SPECIALIZED_TRACKS } from "@/lib/constants"

interface AcademicProfileSettingsProps {
  onBack?: () => void
  onSubmitSuccess?: () => void
}

export function AcademicProfileSettings({ onBack, onSubmitSuccess }: AcademicProfileSettingsProps) {
  const { user, refreshData } = useGradData()
  const { showToast } = useToast()
  const { userInfo } = user

  // 입력 상태
  const [name, setName] = useState("")
  const [studentId, setStudentId] = useState(userInfo?.studentId || "")
  const [grade, setGrade] = useState<number>(() => {
    if (userInfo?.semester) {
      const sem = parseInt(userInfo.semester) || 1
      return Math.min(4, Math.max(1, Math.ceil(sem / 2)))
    }
    return 1
  })
  const [department, setDepartment] = useState(userInfo?.department || "")
  const [convergenceMajor, setConvergenceMajor] = useState<string>("")
  const [specializedTrack, setSpecializedTrack] = useState<string>("")
  const [semesterVal, setSemesterVal] = useState<string>("1학기")

  // 사용자 이름 인라인 편집 상태
  const [isEditingName, setIsEditingName] = useState(false)
  const [nameEditValue, setNameEditValue] = useState("")

  const [isSubmitting, setIsSubmitting] = useState(false)

  // 초기 유저 정보 로딩
  useEffect(() => {
    if (userInfo) {
      setName(userInfo.name || "학생")
      setStudentId(userInfo.studentId || "")
      setDepartment(userInfo.department || "")
      
      const semStr = userInfo.semester || "1학기"
      const match = semStr.match(/(\d)학년\s*(\d)학기/)
      if (match) {
        setGrade(parseInt(match[1]) || 1)
        setSemesterVal(`${match[2]}학기`)
      } else {
        const semNum = parseInt(semStr) || 1
        setGrade(Math.min(4, Math.max(1, Math.ceil(semNum / 2))))
        setSemesterVal(semNum % 2 === 1 ? "1학기" : "2학기")
      }

      const tracks = userInfo.track ? userInfo.track.split(", ") : []
      const conv = CONVERGENCE_MAJORS.find(m => tracks.includes(m)) || ""
      const spec = SPECIALIZED_TRACKS.find(t => tracks.includes(t)) || ""
      setConvergenceMajor(conv)
      setSpecializedTrack(spec)
    }
  }, [userInfo])

  // 이름 인라인 편집 핸들러
  const startNameEdit = () => {
    setIsEditingName(true)
    setNameEditValue(name)
  }

  const saveNameEdit = () => {
    if (!nameEditValue.trim()) {
      showToast("이름은 빈 칸으로 둘 수 없습니다.")
      return
    }
    setName(nameEditValue.trim())
    setIsEditingName(false)
  }

  const cancelNameEdit = () => {
    setIsEditingName(false)
  }

  // 최종 제출 (학적 정보 단일 저장)
  const handleSubmit = async () => {
    if (!studentId.trim()) {
      showToast("학번을 입력해 주세요.")
      return
    }
    if (!/^\d{4,10}$/.test(studentId)) {
      showToast("올바른 학번 형식(숫자 4~10자리)으로 입력해 주세요.")
      return
    }
    if (!department) {
      showToast("소속 학과를 선택해 주세요.")
      return
    }

    setIsSubmitting(true)
    try {
      const semNum = semesterVal === "1학기" ? 1 : 2
      const mappedSemester = (grade - 1) * 2 + semNum
      const semesterString = `${grade}학년 ${semesterVal}`
      const majorTracks = [`${department} 본전공`]
      if (convergenceMajor) majorTracks.push(convergenceMajor)
      if (specializedTrack) majorTracks.push(specializedTrack)

      if (typeof window !== "undefined") {
        sessionStorage.setItem(`grad_major_preferences_${studentId}`, JSON.stringify({
          convergenceMajor,
          specializedTrack
        }))
        sessionStorage.setItem(`grad_manager_semester_${studentId}`, semesterString)
      }

      await updateProfile(name, studentId, department, userInfo?.mileage || 0, mappedSemester, majorTracks)

      if (refreshData) {
        await refreshData()
      }

      showToast("학사 정보가 성공적으로 업데이트되었습니다.")
      if (onSubmitSuccess) {
        onSubmitSuccess()
      }
    } catch (error: any) {
      showToast(error.message || "정보 저장 중 오류가 발생했습니다.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const isValid = studentId.trim().length >= 4 && department !== ""

  return (
    <div className="flex flex-col min-h-screen bg-background md:max-w-xl md:mx-auto md:shadow-2xl md:border-x md:border-border transition-all duration-300 relative pb-[100px]">
      {/* 네비게이션 헤더 */}
      <header className="flex items-center justify-between px-6 py-4.5 border-b border-border/60 bg-card/90 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-3">
          {onBack && (
            <button 
              onClick={onBack} 
              className="p-1.5 -ml-1 rounded-full hover:bg-secondary transition-colors cursor-pointer"
            >
              <ArrowLeft className="h-5 w-5 text-foreground" />
            </button>
          )}
          <span className="text-lg font-bold text-foreground">종합 학사정보 설정</span>
        </div>
      </header>

      {/* 메인 폼 바디 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="space-y-6">
          {/* 타이틀 안내 및 이름 인라인 편집 */}
          <div className="space-y-1.5 min-h-[68px]">
            {isEditingName ? (
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="text"
                  value={nameEditValue}
                  onChange={(e) => setNameEditValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveNameEdit()
                    if (e.key === "Escape") cancelNameEdit()
                  }}
                  autoFocus
                  className="text-xl font-bold rounded-2xl bg-secondary px-3 py-1.5 border border-transparent focus:border-primary focus:bg-background focus:outline-none w-[160px]"
                />
                <button
                  type="button"
                  onClick={saveNameEdit}
                  className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-xl cursor-pointer"
                >
                  <Check className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  onClick={cancelNameEdit}
                  className="p-1.5 text-destructive hover:bg-destructive/5 rounded-xl cursor-pointer"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            ) : (
              <div className="flex items-start gap-1 justify-between w-full">
                <div className="space-y-1">
                  <h1 className="text-2xl font-bold tracking-tight text-foreground whitespace-pre-line leading-snug flex items-center gap-2">
                    <span>{name}님</span>
                    <button
                      type="button"
                      onClick={startNameEdit}
                      className="p-1 text-muted-foreground hover:text-foreground hover:bg-secondary/40 rounded-xl cursor-pointer"
                      title="이름 수정"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                  </h1>
                  <p className="text-xs text-muted-foreground">
                    입력하신 학과와 전공 설정에 기반하여 맞춤형 과목 추천을 가동합니다.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* 학번 입력 */}
          <div className="space-y-2">
            <label htmlFor="studentId" className="text-[11px] font-bold text-muted-foreground block">
              학번 (Student ID)
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4.5 flex items-center pointer-events-none">
                <GraduationCap className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                id="studentId"
                type="text"
                pattern="\d*"
                maxLength={10}
                placeholder="학번을 입력하세요 (예: 2022115001)"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value.replace(/[^0-9]/g, ""))}
                className="w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-12 pr-4.5 text-base text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary font-medium"
              />
            </div>
          </div>

          {/* 학년 선택 */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-muted-foreground block">
              학년 (Grade)
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[1, 2, 3, 4].map((g) => {
                const isSelected = grade === g
                return (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGrade(g)}
                    className={`py-3 rounded-2xl border text-sm font-bold transition-all cursor-pointer ${
                      isSelected
                        ? "bg-[#3182f6] border-[#3182f6] text-white shadow-sm"
                        : "bg-secondary border-transparent text-foreground hover:bg-muted"
                    }`}
                  >
                    {g}학년
                  </button>
                )
              })}
            </div>
          </div>

          {/* 학기 선택 */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-muted-foreground block">
              학기 (Semester)
            </label>
            <div className="grid grid-cols-2 gap-2">
              {["1학기", "2학기"].map((sem) => {
                const isSelected = semesterVal === sem
                return (
                  <button
                    key={sem}
                    type="button"
                    onClick={() => setSemesterVal(sem)}
                    className={`py-3 rounded-2xl border text-sm font-bold transition-all cursor-pointer ${
                      isSelected
                        ? "bg-[#3182f6] border-[#3182f6] text-white shadow-sm"
                        : "bg-secondary border-transparent text-foreground hover:bg-muted"
                    }`}
                  >
                    {sem}
                  </button>
                )
              })}
            </div>
          </div>

          {/* 소속 학과 선택 */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-muted-foreground block">
              소속 학과 (Department)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DEPARTMENTS.map((dept) => {
                const isSelected = department === dept
                return (
                  <button
                    key={dept}
                    type="button"
                    onClick={() => setDepartment(dept)}
                    className={`flex items-center justify-between rounded-2xl p-4 text-left border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-[#3182f6]/5 border-[#3182f6] text-[#3182f6] font-bold shadow-sm shadow-[#3182f6]/5"
                        : "bg-secondary border-transparent text-foreground hover:bg-muted font-medium"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 flex-1 min-w-0 mr-2">
                      <BookOpen className={`h-4.5 w-4.5 shrink-0 ${isSelected ? "text-[#3182f6]" : "text-muted-foreground"}`} />
                      <span className="text-[11px] sm:text-xs font-bold leading-tight whitespace-normal break-keep">{dept}</span>
                    </div>
                    {isSelected && (
                      <span className="flex h-4.5 w-4.5 items-center justify-center rounded-full bg-[#3182f6] text-white">
                        <Check className="h-2.5 w-2.5" />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {/* 융합전공 선택 */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-muted-foreground block flex items-center gap-1">
              <Layers className="h-3.5 w-3.5 text-muted-foreground" />
              융합전공 (Convergence Major)
            </label>
            <div className="relative">
              <select
                value={convergenceMajor}
                onChange={(e) => {
                  const val = e.target.value
                  setConvergenceMajor(val)
                  if (val !== "") {
                    setSpecializedTrack("")
                  }
                }}
                className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3.5 pr-10 text-sm text-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary appearance-none cursor-pointer font-medium"
              >
                <option value="">선택 안 함 (일반 전공)</option>
                {CONVERGENCE_MAJORS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          {/* 특성화트랙 선택 */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-muted-foreground block flex items-center gap-1">
              <Award className="h-3.5 w-3.5 text-muted-foreground" />
              특성화트랙 (Specialized Track)
            </label>
            <div className="relative">
              <select
                value={specializedTrack}
                onChange={(e) => {
                  const val = e.target.value
                  setSpecializedTrack(val)
                  if (val !== "") {
                    setConvergenceMajor("")
                  }
                }}
                className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3.5 pr-10 text-sm text-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary appearance-none cursor-pointer font-medium"
              >
                <option value="">선택 안 함 (일반 트랙)</option>
                {SPECIALIZED_TRACKS.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 하단 고정 저장 버튼 */}
      <footer className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-background via-background to-transparent border-t border-border/10">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting || !isValid}
          className={`w-full flex items-center justify-center gap-1.5 py-4.5 rounded-2xl text-[16px] font-bold transition-all shadow-md select-none h-[54px] cursor-pointer ${
            isValid
              ? "bg-[#3182f6] text-white hover:bg-[#1b64da] active:scale-[0.98]"
              : "bg-secondary text-muted-foreground/50 cursor-not-allowed"
          }`}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>학사정보 저장 중…</span>
            </>
          ) : (
            <>
              <Check className="h-5 w-5" />
              <span>학사정보 저장 완료</span>
            </>
          )}
        </button>
      </footer>
    </div>
  )
}
