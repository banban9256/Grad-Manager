"use client"

import { useEffect, useState, useRef, useCallback } from "react"
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
  X,
  Search,
  Plus,
  Trophy,
  Minus,
} from "lucide-react"
import { motion, AnimatePresence } from "motion/react"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { updateProfile, searchCourseOfferings, updateCompletedCourses, registerUser } from "@/lib/api"
import { DEPARTMENTS } from "@/lib/constants"

// 백엔드 notices API 호출용 함수 추가 (lib/api.ts에 없거나 직접 호출하기 위해 로컬 래퍼 작성 가능)
import { getNoticeData } from "@/lib/api"

export function ProfileTab() {
  const { user, notice, logout, refreshData, addInterestKeyword, removeInterestKeyword } = useGradData()
  const { showToast } = useToast()
  const { userInfo } = user

  const [isEditing, setIsEditing] = useState(false)
  const [name, setName] = useState(userInfo.name)
  const [studentId, setStudentId] = useState(userInfo.studentId)
  const [department, setDepartment] = useState(userInfo.department)
  const [mileage, setMileage] = useState(userInfo.mileage)
  const [saveLoading, setSaveLoading] = useState(false)

  useEffect(() => {
    setName(userInfo.name)
    setStudentId(userInfo.studentId)
    setDepartment(userInfo.department)
    setMileage(userInfo.mileage)
  }, [userInfo])

  const [notifyEnabled, setNotifyEnabled] = useState(true)
  const [darkTheme, setDarkTheme] = useState(false)

  // 기수강 과목 관련 상태
  const [completedList, setCompletedList] = useState<string[]>(userInfo.completedCourses || [])
  const [searchTerm, setSearchTerm] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [updatingCourses, setUpdatingCourses] = useState(false)

  // 키워드 관리 모달 관련 상태
  const [showKeywordModal, setShowKeywordModal] = useState(false)
  const [keywordInput, setKeywordInput] = useState("")
  const [updatingKeywords, setUpdatingKeywords] = useState(false)

  useEffect(() => {
    if (typeof window !== "undefined") {
      setDarkTheme(document.documentElement.classList.contains("dark"))
    }
  }, [])

  // 디바운스 과목 검색 구현
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  useEffect(() => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)

    if (searchTerm.trim().length < 1) {
      setSearchResults([])
      return
    }

    setSearchLoading(true)
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const results = await searchCourseOfferings(searchTerm)
        setSearchResults(results.slice(0, 8))
      } catch {
        setSearchResults([])
      } finally {
        setSearchLoading(false)
      }
    }, 300)

    return () => {
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    }
  }, [searchTerm])

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

    if (mileage % 25 !== 0) {
      showToast("마일리지는 25점 단위로만 수정 가능합니다.")
      return
    }

    setSaveLoading(true)
    try {
      await updateProfile(name, studentId, department, mileage)
      if (refreshData) await refreshData()
      showToast("정보가 수정되었습니다.")
      setIsEditing(false)
    } catch (err: any) {
      showToast(err.message || "정보 수정에 실패했습니다.")
    } finally {
      setSaveLoading(false)
    }
  }

  // 기수강 과목 추가
  const handleAddCourse = async (courseId: string) => {
    if (completedList.includes(courseId)) {
      showToast("이미 이수한 과목입니다.")
      return
    }
    const updated = [...completedList, courseId]
    setCompletedList(updated)
    setSearchTerm("")
    setSearchResults([])
    
    setUpdatingCourses(true)
    try {
      await updateCompletedCourses(userInfo.studentId, updated)
      if (refreshData) await refreshData()
      showToast("기수강 과목이 추가되었습니다.")
    } catch (err: any) {
      showToast(err.message || "과목 추가 처리에 실패했습니다.")
      setCompletedList(completedList) // 롤백
    } finally {
      setUpdatingCourses(false)
    }
  }

  // 기수강 과목 삭제
  const handleRemoveCourse = async (courseId: string) => {
    const updated = completedList.filter(id => id !== courseId)
    setCompletedList(updated)
    
    setUpdatingCourses(true)
    try {
      await updateCompletedCourses(userInfo.studentId, updated)
      if (refreshData) await refreshData()
      showToast("기수강 과목이 목록에서 제외되었습니다.")
    } catch (err: any) {
      showToast(err.message || "과목 제거 처리에 실패했습니다.")
      setCompletedList(completedList) // 롤백
    } finally {
      setUpdatingCourses(false)
    }
  }

  // 알림 키워드 추가
  const handleAddKeyword = async () => {
    const trimmed = keywordInput.trim()
    if (!trimmed) return
    const currentKeywords = (notice?.interestKeywords || []).map((k: any) => k.label || k.text)
    if (currentKeywords.includes(trimmed)) {
      showToast("이미 등록된 키워드입니다.")
      return
    }

    setUpdatingKeywords(true)
    try {
      if (addInterestKeyword) {
        await addInterestKeyword(trimmed)
        showToast("알림 키워드가 등록되었습니다.")
      }
      setKeywordInput("")
    } catch {
      showToast("키워드 등록에 실패했습니다.")
    } finally {
      setUpdatingKeywords(false)
    }
  }



  // 알림 키워드 삭제
  const handleRemoveKeyword = async (keyword: string) => {
    setUpdatingKeywords(true)
    try {
      if (removeInterestKeyword) {
        await removeInterestKeyword(keyword)
        showToast("알림 키워드가 삭제되었습니다.")
      }
    } catch {
      showToast("키워드 삭제에 실패했습니다.")
    } finally {
      setUpdatingKeywords(false)
    }
  }

  return (
    <div className="space-y-6 px-4 pb-12 pt-5 md:max-w-4xl md:mx-auto md:px-6 relative">
      <div>
        <h1 className="text-2xl font-bold text-foreground">마이페이지 &amp; 설정</h1>
        <p className="text-sm text-muted-foreground mt-0.5">개인정보 확인 및 환경설정을 관리하세요</p>
      </div>

      {/* 1. 내 프로필 정보 섹션 */}
      <motion.section 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl bg-card p-5 shadow-sm border border-border"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-muted-foreground">내 프로필 정보</h2>
          {!isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-1 text-xs font-bold text-primary hover:underline transition-colors cursor-pointer"
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
                <div className="relative">
                  <select
                    required
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full rounded-2xl border border-transparent bg-secondary px-4 py-3.5 pr-10 text-sm text-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary appearance-none cursor-pointer"
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
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4">
                    <svg className="h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>
              <div>
                <label className="text-[11px] font-bold text-muted-foreground block mb-1">누적 마일리지 (25점 단위)</label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setMileage((prev) => Math.max(0, prev - 25))}
                    className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-foreground hover:bg-muted active:scale-95 transition-all select-none cursor-pointer"
                  >
                    <Minus className="h-4 w-4" />
                  </button>
                  <input
                    type="number"
                    required
                    value={mileage}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) || 0
                      setMileage(val)
                    }}
                    step={25}
                    min={0}
                    className="flex-1 rounded-2xl border border-transparent bg-secondary px-4 py-3 text-sm text-foreground text-center font-bold transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <button
                    type="button"
                    onClick={() => setMileage((prev) => prev + 25)}
                    className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary text-foreground hover:bg-muted active:scale-95 transition-all select-none cursor-pointer"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex gap-2.5 pt-1.5">
              <button
                type="button"
                onClick={() => {
                  setName(userInfo.name)
                  setStudentId(userInfo.studentId)
                  setDepartment(userInfo.department)
                  setMileage(userInfo.mileage)
                  setIsEditing(false)
                }}
                className="flex-1 rounded-2xl bg-secondary py-3.5 text-[15px] font-semibold text-secondary-foreground hover:opacity-90 h-[48px] cursor-pointer"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={saveLoading}
                className="flex-1 rounded-2xl bg-primary py-3.5 text-[15px] font-semibold text-white hover:bg-primary-hover flex items-center justify-center gap-1.5 h-[48px] disabled:opacity-50 cursor-pointer"
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
            <ProfileInfoRow Icon={User} label="이름" value={userInfo.name} />
            <ProfileInfoRow Icon={GraduationCap} label="학번" value={userInfo.studentId} />
            <ProfileInfoRow Icon={BookOpen} label="학과" value={userInfo.department} />
            <ProfileInfoRow Icon={Trophy} label="누적 마일리지" value={`${userInfo.mileage.toLocaleString()}P`} />
          </div>
        )}
      </motion.section>

      {/* 2. 기수강 과목 선택 섹션 */}
      <motion.section 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="rounded-3xl bg-card p-5 shadow-sm border border-border space-y-4"
      >
        <div>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground">기수강 과목 선택</h2>
            {updatingCourses && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">이미 이수한 과목을 검색해서 추가하거나 삭제할 수 있습니다.</p>
        </div>

        <div className="relative">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4.5">
            {searchLoading ? (
              <Loader2 className="h-4.5 w-4.5 animate-spin text-muted-foreground" />
            ) : (
              <Search className="h-4.5 w-4.5 text-muted-foreground" />
            )}
          </div>
          <input
            type="text"
            placeholder="과목 코드 또는 과목명 검색 (예: 운영체제, UNIV101)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-2xl border border-transparent bg-secondary py-3.5 pl-11 pr-4.5 text-sm text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          />

          <AnimatePresence>
            {searchResults.length > 0 && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="absolute z-10 mt-2 w-full max-h-60 overflow-y-auto rounded-2xl bg-card border border-border shadow-xl p-2 space-y-1"
              >
                {searchResults.map((course) => (
                  <button
                    key={course.course_id}
                    onClick={() => handleAddCourse(course.course_id)}
                    className="w-full flex items-center justify-between rounded-xl px-4 py-3 text-left text-sm hover:bg-[#f2f4f6] dark:hover:bg-[#212836] transition-colors cursor-pointer"
                  >
                    <div>
                      <p className="font-bold text-foreground">{course.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{course.course_id} · {course.credit}학점</p>
                    </div>
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary hover:bg-primary hover:text-white transition-colors">
                      <Plus className="h-4 w-4" />
                    </span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-bold text-muted-foreground">내가 이수한 과목 ({completedList.length}개)</p>
          {completedList.length === 0 ? (
            <div className="rounded-2xl border-2 border-dashed border-border py-8 text-center">
              <p className="text-xs text-muted-foreground">등록된 기수강 과목이 없습니다.<br />위 검색창에서 과목을 검색하여 추가해보세요.</p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto p-1 border border-[#f2f4f6] dark:border-[#212836] rounded-2xl bg-secondary/30">
              {completedList.map((courseId) => (
                <motion.div
                  key={courseId}
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.9, opacity: 0 }}
                  className="flex items-center gap-1.5 rounded-full bg-secondary hover:bg-secondary/80 px-3.5 py-1.5 text-xs font-bold text-foreground border border-border shadow-sm"
                >
                  <span>
                    {`[${courseId}] ${userInfo.completedCoursesDetail?.[courseId] || "기수강 과목"}`}
                  </span>
                  <button
                    onClick={() => handleRemoveCourse(courseId)}
                    disabled={updatingCourses}
                    className="text-muted-foreground hover:text-destructive transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </motion.section>

      {/* 3. Toss 스타일 환경설정 섹션 */}
      <motion.section 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="rounded-3xl bg-card p-5 shadow-sm border border-border"
      >
        <h2 className="text-sm font-semibold text-muted-foreground mb-4">환경설정</h2>

        <div className="divide-y divide-[#f2f4f6] dark:divide-[#212836]">
          {/* 알림 설정 */}
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3.5">
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
                notifyEnabled ? "bg-[#3182f6]" : "bg-[#e5e8eb] dark:bg-[#2c3746]"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition-transform duration-200 ease-in-out ${
                  notifyEnabled ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* 다크 모드 */}
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3.5">
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
                darkTheme ? "bg-[#3182f6]" : "bg-[#e5e8eb] dark:bg-[#2c3746]"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition-transform duration-200 ease-in-out ${
                  darkTheme ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* 공지사항 키워드 관리 */}
          <button
            onClick={() => setShowKeywordModal(true)}
            className="w-full flex items-center justify-between py-4 text-left hover:bg-[#f2f4f6]/50 dark:hover:bg-[#212836]/30 px-1 -mx-1 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3.5">
              <span className="flex h-9.5 w-9.5 items-center justify-center rounded-xl bg-[#00b5a3]/10 text-[#00b5a3]">
                <Tag className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">공지사항 키워드 관리</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">학사 알림 키워드 등록/해제</p>
              </div>
            </div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <span className="text-xs bg-secondary px-2 py-0.5 rounded-full font-semibold">{(notice?.interestKeywords || []).length}개</span>
              <ChevronRight className="h-5 w-5" />
            </div>
          </button>
        </div>
      </motion.section>

      {/* 로그아웃 버튼 */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="pt-2"
      >
        <button
          onClick={logout}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#fff3f5] dark:bg-[#381e25] hover:bg-opacity-80 py-4 text-[17px] font-bold text-[#d6284a] dark:text-[#ff6b8b] transition-all shadow-sm h-[56px] cursor-pointer"
        >
          <LogOut className="h-4.5 w-4.5" />
          안전하게 로그아웃
        </button>
      </motion.div>

      {/* Toss-inspired 키워드 관리 모달 (AnimatePresence) */}
      <AnimatePresence>
        {showKeywordModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* 배경 블러 페이드 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowKeywordModal(false)}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            />

            {/* 모달 창 슬라이드 업 */}
            <motion.div
              initial={{ opacity: 0, y: 50, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 350, damping: 28 }}
              className="relative w-full max-w-md overflow-hidden rounded-[2rem] bg-card p-6 shadow-2xl border border-border"
            >
              <div className="flex items-center justify-between border-b border-border pb-4">
                <div>
                  <h3 className="text-lg font-bold text-foreground">학사 알림 키워드 관리</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">선택한 키워드가 포함된 공지를 실시간 감지합니다</p>
                </div>
                <button
                  onClick={() => setShowKeywordModal(false)}
                  className="rounded-full p-1.5 text-muted-foreground hover:bg-secondary transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* 키워드 등록 인풋 */}
              <div className="mt-5 flex gap-2">
                <input
                  type="text"
                  placeholder="예: 장학, 인턴, 수강신청"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      handleAddKeyword()
                    }
                  }}
                  className="flex-1 rounded-2xl border border-transparent bg-secondary px-4 py-3 text-sm text-foreground placeholder-muted-foreground transition-all focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  onClick={handleAddKeyword}
                  disabled={updatingKeywords}
                  className="rounded-2xl bg-primary px-5 font-bold text-white hover:bg-primary-hover transition-colors disabled:opacity-50 flex items-center justify-center cursor-pointer"
                >
                  추가
                </button>
              </div>

              {/* 등록된 키워드 칩 리스트 */}
              <div className="mt-6 space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-muted-foreground">
                  <span>알림 키워드 목록 ({(notice?.interestKeywords || []).length}개)</span>
                  {updatingKeywords && <Loader2 className="h-3 w-3 animate-spin text-primary" />}
                </div>

                {(notice?.interestKeywords || []).length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border py-8 text-center text-xs text-muted-foreground bg-secondary/10">
                    등록된 알림 키워드가 없습니다.
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2 py-1 max-h-40 overflow-y-auto">
                    {(notice?.interestKeywords || []).map((k: any) => {
                      const kw = k.label || k.text
                      return (
                        <motion.div
                          key={kw}
                          initial={{ scale: 0.8, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0.8, opacity: 0 }}
                          className="flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-3.5 py-1.5 text-xs font-bold text-primary"
                        >
                          <span>{kw}</span>
                          <button
                            onClick={() => handleRemoveKeyword(kw)}
                            disabled={updatingKeywords}
                            className="hover:text-destructive transition-colors cursor-pointer disabled:opacity-50"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </motion.div>
                      )
                    })}
                  </div>
                )}
              </div>

              <div className="mt-8">
                <button
                  onClick={() => setShowKeywordModal(false)}
                  className="w-full rounded-2xl bg-secondary py-3.5 text-[15px] font-bold text-foreground hover:bg-opacity-80 transition-colors cursor-pointer"
                >
                  닫기
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ProfileInfoRow({
  Icon,
  label,
  value,
}: {
  Icon: typeof User
  label: string
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
