"use client"

import { useEffect, useState, useMemo, useCallback, useRef } from "react"
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
  ChevronDown,
  X,
  Search,
  Plus,
  Trash2,
  Award,
  Layers,
  BookMarked,
  Sparkles,
  Minus,
  FileUp,
  FileCheck,
  FileText,
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { useGradData } from "./grad-data-provider"
import { useToast } from "./toast"
import { 
  updateProfile, 
  changePassword, 
  getStudentCourseHistory, 
  addStudentCourseHistory, 
  addCustomStudentCourseHistory,
  updateStudentCourseHistory, 
  deleteStudentCourseHistory,
  getStudentGraduationSummary,
  searchCourseOfferings,
  uploadTranscriptPDF,
  confirmTranscriptCourses,
} from "@/lib/api"
import { DEPARTMENTS, CONVERGENCE_MAJORS, SPECIALIZED_TRACKS } from "@/lib/constants"
import { AcademicProfileSettings } from "./AcademicProfileSettings"

// 학기 선택 드롭다운용 23-1 ~ 26-2 전체 학기 목록 (계절학기 포함)
const SEMESTER_OPTIONS = [
  "2026-2학기",
  "2026-여름계절",
  "2026-1학기",
  "2025-겨울계절",
  "2025-2학기",
  "2025-여름계절",
  "2025-1학기",
  "2024-겨울계절",
  "2024-2학기",
  "2024-여름계절",
  "2024-1학기",
  "2023-겨울계절",
  "2023-2학기",
  "2023-여름계절",
  "2023-1학기",
]

// 성적별 평점 환산 테이블
const GRADE_POINTS: Record<string, number> = {
  "A+": 4.5,
  "A0": 4.0,
  "B+": 3.5,
  "B0": 3.0,
  "C+": 2.5,
  "C0": 2.0,
  "D+": 1.5,
  "D0": 1.0,
  "F": 0.0
}

// 학기 평점 계산 헬퍼 함수
const calculateSemesterGPA = (items: any[]) => {
  let totalPoints = 0
  let totalCredits = 0

  items.forEach((item) => {
    const grade = item.grade || "A+"
    const credit = Number(item.earned_credit !== undefined && item.earned_credit !== null && item.earned_credit !== '' ? item.earned_credit : (item.credit !== undefined && item.credit !== null && item.credit !== '' ? item.credit : 3))

    if (grade === "P" || grade === "NP") return

    const point = GRADE_POINTS[grade] !== undefined ? GRADE_POINTS[grade] : 4.5
    totalPoints += point * credit
    totalCredits += credit
  })

  if (totalCredits === 0) return "0.00"
  return (totalPoints / totalCredits).toFixed(2)
}

export function ProfileTab() {
  const { user, notice, logout, allCourses, refreshData, addInterestKeyword, removeInterestKeyword, updateCompletedCourses, semesters = [] } = useGradData()
  const { showToast } = useToast()
  const { userInfo } = user

  const [showHistoryForm, setShowHistoryForm] = useState(false)
  const [mileage, setMileage] = useState(userInfo.mileage)

  // 융합/특화전공 상태 관리
  const [convergenceMajor, setConvergenceMajor] = useState<string>("")
  const [specializedTrack, setSpecializedTrack] = useState<string>("")

  // 수강 이력 관리 데이터 목록 상태
  const [historyList, setHistoryList] = useState<any[]>([])
  const [isHistoryLoading, setIsHistoryLoading] = useState(false)

  // 체크박스 기반 벌크 일괄 선택 상태
  const [showAddForm, setShowAddForm] = useState(false)
  const [checkedCourses, setCheckedCourses] = useState<string[]>([])
  const [courseSearchQuery, setCourseSearchQuery] = useState("")
  const [filterCourseType, setFilterCourseType] = useState<string>("전체")

  // 모달 내 개설 과목 목록 관리 상태
  const [modalCourses, setModalCourses] = useState<any[]>([])
  const [isModalCoursesLoading, setIsModalCoursesLoading] = useState(false)



  // 직접 입력(Custom Input) 상태들
  const [addFormTab, setAddFormTab] = useState<"search" | "custom">("search")
  const [customCourseName, setCustomCourseName] = useState("")
  const [customCredits, setCustomCredits] = useState("3")
  const [customCourseType, setCustomCourseType] = useState("전공선택")
  const [customSemester, setCustomSemester] = useState("2025-1학기")
  const [customGrade, setCustomGrade] = useState("A+")
  const [isCustomSubmitting, setIsCustomSubmitting] = useState(false)
  const [bulkTargetSemester, setBulkTargetSemester] = useState("2026-1학기")
  const [customIsRetake, setCustomIsRetake] = useState(false)

  // 모달 오픈 시 혹은 대상 학기(bulkTargetSemester) 변경 시 개설 과목 비동기 로딩
  useEffect(() => {
    if (!showAddForm) return

    let isMounted = true
    async function fetchModalCourses() {
      setIsModalCoursesLoading(true)
      try {
        const courses = await searchCourseOfferings("", bulkTargetSemester)
        if (isMounted) {
          setModalCourses(courses)
        }
      } catch (err) {
        console.error("모달 내 개설 과목 목록 로드 실패:", err)
      } finally {
        if (isMounted) {
          setIsModalCoursesLoading(false)
        }
      }
    }
    fetchModalCourses()
    return () => {
      isMounted = false
    }
  }, [showAddForm, bulkTargetSemester])

  // 인라인 편집 상태 (개별 학기/성적 튜닝용)
  const [editingHistoryId, setEditingHistoryId] = useState<number | null>(null)
  const [editSemester, setEditSemester] = useState("")
  const [editGrade, setEditGrade] = useState("")
  const [editCourseName, setEditCourseName] = useState("")
  const [editCredits, setEditCredits] = useState("3")
  const [editIsRetake, setEditIsRetake] = useState(false)
  const [editCourseType, setEditCourseType] = useState("전공선택")

  // 학기별 아코디언 상태
  const [collapsedSemesters, setCollapsedSemesters] = useState<Record<string, boolean>>({})
  const toggleSemesterCollapse = useCallback((semester: string) => {
    setCollapsedSemesters(prev => ({
      ...prev,
      [semester]: !prev[semester]
    }))
  }, [])

  // PDF 업로드 상태
  const [showPdfUpload, setShowPdfUpload] = useState(false)
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [isPdfUploading, setIsPdfUploading] = useState(false)
  const [isPdfSaving, setIsPdfSaving] = useState(false)
  const [pdfParsedCourses, setPdfParsedCourses] = useState<any[]>([])
  const [pdfUploadMessage, setPdfUploadMessage] = useState("")
  const pdfInputRef = useRef<HTMLInputElement>(null)

  // 실시간 학점 요약 데이터 보관
  const [gradSummary, setGradSummary] = useState<any>(null)

  const fetchGradSummary = async (sId: string) => {
    try {
      const summary = await getStudentGraduationSummary(Number(sId))
      setGradSummary(summary)
    } catch (e) {
      console.error(e)
    }
  }

  // 수강 이력 백엔드 조회 함수
  const loadCourseHistory = async () => {
    if (!userInfo?.studentId) return
    setIsHistoryLoading(true)
    try {
      const res = await getStudentCourseHistory(Number(userInfo.studentId))
      if (res.status === "success") {
        setHistoryList(res.data || [])
      }
    } catch (e: any) {
      console.error(e)
    } finally {
      setIsHistoryLoading(false)
    }
  }

  // 초기 마운트 및 정보 로딩
  useEffect(() => {
    setMileage(userInfo.mileage)
    if (userInfo?.studentId) {
      loadCourseHistory()
      fetchGradSummary(userInfo.studentId)
    }
  }, [userInfo])

  // PDF 업로드 핸들러
  const handlePdfUpload = async () => {
    if (!pdfFile) return
    setIsPdfUploading(true)
    setPdfUploadMessage("")
    try {
      const result = await uploadTranscriptPDF(pdfFile)
      setPdfParsedCourses(result.courses)
      setPdfUploadMessage(result.message)
    } catch (e: any) {
      setPdfUploadMessage(e.message || "PDF 업로드에 실패했습니다.")
    } finally {
      setIsPdfUploading(false)
    }
  }

  const handlePdfConfirmSave = async () => {
    if (pdfParsedCourses.length === 0) return
    setIsPdfSaving(true)
    try {
      const coursesToSave = pdfParsedCourses.map(c => ({
        courseName: c.courseName,
        courseCode: c.courseCode,
        courseType: c.courseType,
        credits: c.credits,
        grade: c.grade,
        semester: c.semester,
      }))
      const result = await confirmTranscriptCourses(coursesToSave)
      showToast(result.message || "과목이 저장되었습니다.")
      setShowPdfUpload(false)
      setPdfFile(null)
      setPdfParsedCourses([])
      setPdfUploadMessage("")
      loadCourseHistory()
      if (userInfo?.studentId) {
        fetchGradSummary(userInfo.studentId)
      }
    } catch (e: any) {
      showToast(e.message || "저장에 실패했습니다.")
    } finally {
      setIsPdfSaving(false)
    }
  }



  useEffect(() => {
    if (userInfo) {
      const tracks = userInfo.track ? userInfo.track.split(", ") : []
      const conv = CONVERGENCE_MAJORS.find(m => tracks.includes(m)) || ""
      const spec = SPECIALIZED_TRACKS.find(t => tracks.includes(t)) || ""
      setConvergenceMajor(conv)
      setSpecializedTrack(spec)
    }
  }, [showHistoryForm, userInfo])

  const { notifyEnabled = true, setNotifyEnabled = () => {} } = useGradData()
  const [darkTheme, setDarkTheme] = useState(false)

  // 키워드 관리 모달 관련 상태
  const [showKeywordModal, setShowKeywordModal] = useState(false)
  const [keywordInput, setKeywordInput] = useState("")
  const [updatingKeywords, setUpdatingKeywords] = useState(false)

  // 비밀번호 변경 모달 관련 상태
  const [isOpenPasswordModal, setIsOpenPasswordModal] = useState(false)
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false)

  const handlePasswordChange = async () => {
    if (!newPassword || newPassword.trim().length < 4) {
      showToast("새 비밀번호는 최소 4자리 이상 입력해 주세요.")
      return
    }
    if (newPassword !== confirmPassword) {
      showToast("새 비밀번호와 확인 비밀번호가 일치하지 않습니다.")
      return
    }
    
    setIsPasswordSubmitting(true)
    try {
      await changePassword(userInfo.studentId, currentPassword, newPassword)
      showToast("비밀번호가 성공적으로 변경되었습니다.")
      setIsOpenPasswordModal(false)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch (err: any) {
      showToast(err.message || "비밀번호 변경에 실패했습니다.")
    } finally {
      setIsPasswordSubmitting(false)
    }
  }

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

  // 학수코드/과목 리스트 가공 (중복 코드 배제)
  const processedCourses = useMemo(() => {
    const sourceCourses = showAddForm ? modalCourses : (allCourses || [])
    const defaultList = sourceCourses.map((c: any) => ({
      id: String(c.course_id || c.code || c.id || ""),
      code: String(c.course_code || c.code || c.course_id || ""),
      name: c.title || c.name || "과목명 미정",
      category: c.category || "일반선택",
      credit: c.credits || c.credit || 3
    }))
    const seen = new Set<string>()
    const uniqueList: any[] = []
    for (const course of defaultList) {
      if (course.code && !seen.has(course.code)) {
        seen.add(course.code)
        uniqueList.push(course)
      }
    }
    return uniqueList
  }, [allCourses, modalCourses, showAddForm])

  // 검색 쿼리 및 이수 구분에 필터링된 과목 리스트
  const filteredSearchCourses = useMemo(() => {
    let result = processedCourses

    if (filterCourseType !== "전체") {
      result = result.filter(c => c.category === filterCourseType)
    }

    const q = courseSearchQuery.trim().toLowerCase()
    if (q) {
      result = result.filter(c => 
        c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
      )
    }
    return result
  }, [processedCourses, courseSearchQuery, filterCourseType])

  // 가장 최신 학기 계산 (최근 이력 우선, 없으면 2026-1학기 기본값)
  const latestSemester = useMemo(() => {
    if (!historyList || historyList.length === 0) {
      return "2026-1학기"
    }
    const semesters = historyList.map((h: any) => h.semester_taken).filter(Boolean)
    if (semesters.length === 0) return "2026-1학기"
    return [...semesters].sort().reverse()[0]
  }, [historyList])

  // 최신 학기가 식별되었을 때 직접 입력 학기 및 벌크 입력 학기 상태 업데이트
  useEffect(() => {
    if (latestSemester) {
      setCustomSemester(latestSemester)
      setBulkTargetSemester(latestSemester)
    }
  }, [latestSemester])

  // 기수강 정보 기반 가상 이력 병합 계산
  const computedHistoryList = useMemo(() => {
    const baseList = historyList || []

    // --- [재수강 포기(Forfeit) 규칙 계산 적용] ---
    const n = baseList.length
    const parent = Array.from({ length: n }, (_, i) => i)

    const find = (i: number): number => {
      if (parent[i] === i) return i
      parent[i] = find(parent[i])
      return parent[i]
    }

    const union = (i: number, j: number) => {
      const rootI = find(i)
      const rootJ = find(j)
      if (rootI !== rootJ) {
        parent[rootI] = rootJ
      }
    }

    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const codeI = baseList[i].course_code
        const codeJ = baseList[j].course_code
        const nameI = baseList[i].course_name || baseList[i].name
        const nameJ = baseList[j].course_name || baseList[j].name

        const condCode = codeI && codeJ && codeI === codeJ
        const condName = nameI && nameJ && nameI === nameJ

        if (condCode || condName) {
          union(i, j)
        }
      }
    }

    const groups: Record<number, any[]> = {}
    for (let i = 0; i < n; i++) {
      const root = find(i)
      if (!groups[root]) groups[root] = []
      groups[root].push(baseList[i])
    }

    const forfeitedHistoryIds = new Set<number>()
    Object.values(groups).forEach(instances => {
      const hasRetake = instances.some(inst => inst.is_retake)
      if (hasRetake && instances.length > 1) {
        // 학기 정렬 (올림차순 정렬 후, 가장 최근 학기를 제외한 나머지를 포기 처리)
        const sorted = [...instances].sort((a, b) => {
          const getSemScore = (sem: string) => {
            if (!sem) return 0
            const m = sem.match(/(\d+)-(\d)학기/)
            if (!m) return 0
            return Number(m[1]) * 10 + Number(m[2])
          }
          return getSemScore(a.semester_taken) - getSemScore(b.semester_taken)
        })
        // 마지막 항목(가장 최근 학기)만 살리고, 이전 모든 인스턴스의 ID를 포기 목록에 추가
        for (let i = 0; i < sorted.length - 1; i++) {
          if (sorted[i].history_id !== undefined) {
            forfeitedHistoryIds.add(sorted[i].history_id)
          }
        }
      }
    })

    return baseList.map(h => ({
      ...h,
      is_forfeited: forfeitedHistoryIds.has(h.history_id)
    }))
  }, [historyList])



  // 학기 및 연도별 수강 이력 그룹핑 계산
  const groupedHistory = useMemo(() => {
    const groups: Record<string, any[]> = {}
    
    computedHistoryList.forEach(item => {
      const sem = item.semester_taken || "미정 학기"
      if (!groups[sem]) {
        groups[sem] = []
      }
      groups[sem].push(item)
    })
    
    // 학기 문자열 내림차순 정렬 (최근 학기 우선) 후 평점 사전 계산 탑재
    const sortedSemesters = Object.keys(groups).sort().reverse()
    return sortedSemesters.map(sem => {
      const items = groups[sem]
      let totalPoints = 0
      let totalCredits = 0
      items.forEach((item) => {
        const grade = item.grade || "A+"
        const credit = Number(item.earned_credit !== undefined && item.earned_credit !== null && item.earned_credit !== '' ? item.earned_credit : (item.credit !== undefined && item.credit !== null && item.credit !== '' ? item.credit : 3))
        // 재수강에 의해 포기된(forfeited) 이전 학점/성적은 학기 평점 계산에서도 완벽하게 포기 처리
        if (grade === "P" || grade === "NP" || item.is_forfeited) return
        const point = GRADE_POINTS[grade] !== undefined ? GRADE_POINTS[grade] : 4.5
        totalPoints += point * credit
        totalCredits += credit
      })
      const gpa = totalCredits === 0 ? "0.00" : (totalPoints / totalCredits).toFixed(2)
      return {
        semester: sem,
        items,
        gpa
      }
    })
  }, [computedHistoryList])

  // 대시보드 갱신 학점 적용 계산
  const currentEarnedCredits = useMemo(() => {
    let total = 0
    computedHistoryList.forEach(item => {
      // F학점이거나 재수강에 의해 포기된(forfeited) 경우 학점 합산에서 제외
      if (item.grade === "F" || item.is_forfeited) return

      const course = (allCourses || []).find((c: any) => 
        String(c.course_code || c.code || c.course_id || "") === item.course_code
      )
      const creditVal = course ? Number(course.credits !== undefined && course.credits !== null && course.credits !== '' ? course.credits : (course.credit !== undefined && course.credit !== null && course.credit !== '' ? course.credit : 3)) : 3
      total += creditVal
    })
    return total
  }, [computedHistoryList, allCourses])

  // 전체 학기 총 평점 (Cumulative GPA) 계산
  const cumulativeGPA = useMemo(() => {
    let totalPoints = 0
    let totalCredits = 0

    computedHistoryList.forEach((item: any) => {
      // 재수강에 의해 포기된(forfeited) 이전 수강 내역은 전체 총 평점(GPA) 계산에서 완벽하게 제외
      if (item.is_forfeited) return

      const grade = item.grade || "A+"
      
      const course = (allCourses || []).find((c: any) => 
        String(c.course_code || c.code || c.course_id || "") === item.course_code
      )
      const credit = course ? Number(course.credits !== undefined && course.credits !== null && course.credits !== '' ? course.credits : (course.credit !== undefined && course.credit !== null && course.credit !== '' ? course.credit : 3)) : 3

      if (grade === "P" || grade === "NP") return

      const point = GRADE_POINTS[grade] !== undefined ? GRADE_POINTS[grade] : 4.5
      totalPoints += point * credit
      totalCredits += credit
    })

    if (totalCredits === 0) return "0.00"
    return (totalPoints / totalCredits).toFixed(2)
  }, [computedHistoryList, allCourses])

  // 체크박스 토글 핸들러
  const handleToggleCourse = useCallback((code: string) => {
    setCheckedCourses(prev => {
      const index = prev.indexOf(code)
      if (index !== -1) {
        // 이미 선택된 항목인 경우, 중복 허용을 위해 1개 인스턴스만 splice 제거
        const next = [...prev]
        next.splice(index, 1)
        return next
      } else {
        // 새로 추가하는 경우 뒤에 append
        return [...prev, code]
      }
    })
  }, [])

  // 벌크 수강 이력 일괄 저장 핸들러
  const handleBulkSave = useCallback(async () => {
    if (checkedCourses.length === 0) {
      showToast("선택된 과목이 없습니다.")
      return
    }

    setIsHistoryLoading(true)
    try {
      // 신규 과목 각각에 대해 POST API(개별 수강 기록 추가)를 병렬 실행하여 기존 DB 레코드를 온전히 보존
      await Promise.all(
        checkedCourses.map(async (code) => {
          const course = processedCourses.find(c => c.code === code)
          const courseIdOrCode = course ? course.id : code
          const creditVal = (course && course.credit !== undefined && course.credit !== null && course.credit !== "") ? Number(course.credit) : 3

          await addStudentCourseHistory(
            Number(userInfo.studentId),
            courseIdOrCode,
            bulkTargetSemester,
            "A+",
            false,
            undefined,
            creditVal
          )
        })
      )

      showToast("선택한 과목들이 성공적으로 수강 이력에 추가되었습니다.")
      setCheckedCourses([])
      setShowAddForm(false)
      await loadCourseHistory()
      await fetchGradSummary(userInfo.studentId)
      if (refreshData) await refreshData()
    } catch (e: any) {
      showToast(e.message || "과목 일괄 저장에 실패했습니다.")
    } finally {
      setIsHistoryLoading(false)
    }
  }, [checkedCourses, processedCourses, userInfo.studentId, bulkTargetSemester, loadCourseHistory, fetchGradSummary, refreshData, showToast])

  // 커스텀 직접 입력 과목 저장 핸들러
  const handleCustomSave = useCallback(async () => {
    if (!customCourseName.trim()) {
      showToast("과목명을 입력해 주세요.")
      return
    }

    setIsCustomSubmitting(true)
    setIsHistoryLoading(true)
    try {
      const res = await addCustomStudentCourseHistory(
        Number(userInfo.studentId),
        customCourseName.trim(),
        Number(customCredits),
        customCourseType,
        customSemester,
        customGrade,
        customIsRetake
      )

      if (res.status === "success") {
        showToast("커스텀 과목이 수강 이력에 성공적으로 추가되었습니다.")
        setCustomCourseName("")
        setCustomCredits("3")
        setCustomCourseType("전공선택")
        setCustomIsRetake(false)
        setShowAddForm(false)
        
        await loadCourseHistory()
        await fetchGradSummary(userInfo.studentId)
        if (refreshData) await refreshData()
      }
    } catch (e: any) {
      showToast(e.message || "커스텀 과목 추가에 실패했습니다.")
    } finally {
      setIsCustomSubmitting(false)
      setIsHistoryLoading(false)
    }
  }, [customCourseName, customCredits, customCourseType, customSemester, customGrade, customIsRetake, userInfo.studentId, loadCourseHistory, fetchGradSummary, refreshData, showToast])

  // 개별 수강 이력 수정 핸들러
  const handleUpdateHistory = useCallback(async (historyId: number) => {
    setIsHistoryLoading(true)
    try {
      if (historyId < 0) {
        const item = computedHistoryList.find(h => h.history_id === historyId)
        if (!item) throw new Error("과목 정보를 찾을 수 없습니다.")

        let cId: any = item.course_id
        if (typeof cId === "string" && !isNaN(Number(cId)) && cId.trim() !== "") {
          cId = Number(cId)
        }

        await addStudentCourseHistory(
          Number(userInfo.studentId),
          cId,
          editSemester,
          editGrade,
          editIsRetake,
          editCourseName,
          Number(editCredits)
        )
      } else {
        await updateStudentCourseHistory(
          historyId,
          editSemester,
          editGrade,
          editCourseName,
          Number(editCredits),
          editIsRetake,
          undefined,
          editCourseType
        )
      }
      
      showToast("수강 정보가 저장되었습니다.")
      setEditingHistoryId(null)
      await loadCourseHistory()
      await fetchGradSummary(userInfo.studentId)
      if (refreshData) await refreshData()
    } catch (e: any) {
      showToast(e.message || "수강 정보 저장에 실패했습니다.")
    } finally {
      setIsHistoryLoading(false)
    }
  }, [computedHistoryList, editSemester, editGrade, editCourseName, editCredits, editIsRetake, editCourseType, userInfo.studentId, loadCourseHistory, fetchGradSummary, refreshData, showToast])

  // 개별 수강 이력 삭제 핸들러
  const handleDeleteHistory = useCallback(async (historyId: number) => {
    if (!confirm("정말 이 수강 기록을 삭제하시겠습니까?")) return

    const targetItem = computedHistoryList.find(h => h.history_id === historyId)
    if (!targetItem) {
      showToast("삭제할 과목 정보를 찾을 수 없습니다.")
      return
    }

    setIsHistoryLoading(true)
    try {
      if (historyId >= 0) {
        await deleteStudentCourseHistory(historyId)
      }
      showToast("수강 기록이 삭제되었습니다.")
      await loadCourseHistory()
      await fetchGradSummary(userInfo.studentId)
      if (refreshData) await refreshData()
    } catch (e: any) {
      showToast(e.message || "수강 기록 삭제에 실패했습니다.")
    } finally {
      setIsHistoryLoading(false)
    }
  }, [computedHistoryList, userInfo.studentId, loadCourseHistory, fetchGradSummary, refreshData, showToast])

  // 학기 전체 삭제 핸들러
  const handleDeleteSemester = useCallback(async (semester: string, items: any[]) => {
    if (!confirm(`정말 ${semester}의 모든 수강 기록을 삭제하시겠습니까?`)) return

    setIsHistoryLoading(true)
    try {
      const dbHistoryIds = items.filter(item => item.history_id >= 0).map(item => item.history_id)
      if (dbHistoryIds.length > 0) {
        await Promise.all(dbHistoryIds.map(id => deleteStudentCourseHistory(id)))
      }

      showToast(`${semester}의 모든 수강 기록이 삭제되었습니다.`)
      await loadCourseHistory()
      await fetchGradSummary(userInfo.studentId)
      if (refreshData) await refreshData()
    } catch (e: any) {
      showToast(e.message || "학기 일괄 삭제에 실패했습니다.")
    } finally {
      setIsHistoryLoading(false)
    }
  }, [userInfo.studentId, loadCourseHistory, fetchGradSummary, refreshData, showToast])

  if (showHistoryForm) {
    return (
      <AcademicProfileSettings
        onBack={() => setShowHistoryForm(false)}
        onSubmitSuccess={() => setShowHistoryForm(false)}
      />
    )
  }

  return (
    <div className="space-y-6 px-4 pb-12 pt-5 md:max-w-4xl md:mx-auto md:px-6 relative">
      <div>
        <h1 className="text-2xl font-bold text-foreground">마이페이지 &amp; 설정</h1>
        <p className="text-sm text-muted-foreground mt-0.5">개인정보 확인 및 환경설정을 관리하세요</p>
      </div>

      {/* 종합 학사 정보 요약 카드 */}
      <motion.section 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl bg-card p-6 shadow-sm border border-border space-y-6"
      >
        <div className="flex items-center justify-between border-b border-border/60 pb-4">
          <div className="space-y-1">
            <h2 className="text-sm font-bold text-muted-foreground flex items-center gap-2">
              <GraduationCap className="h-4.5 w-4.5 text-[#3182f6]" />
              종합 학사 정보
            </h2>
            <p className="text-[11px] text-muted-foreground">현재 설정된 학적 및 이수 요약입니다.</p>
          </div>
          <button
            onClick={() => setShowHistoryForm(true)}
            className="flex items-center gap-1.5 bg-[#3182f6]/10 text-[#3182f6] text-xs font-bold px-4 py-2.5 rounded-2xl hover:bg-[#3182f6]/20 transition-all cursor-pointer"
          >
            <Edit2 className="h-3.5 w-3.5" />
            <span>편집</span>
          </button>
        </div>

        {/* 세부 학사정보 그리드 */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-4">
          <ProfileInfoRow Icon={User} label="이름" value={userInfo.name} />
          <ProfileInfoRow Icon={GraduationCap} label="학번" value={userInfo.studentId} />
          <ProfileInfoRow Icon={BookOpen} label="소속 학과" value={userInfo.department} />
          <ProfileInfoRow Icon={Layers} label="선택 학년" value={userInfo.semester ? `${Math.min(4, Math.max(1, Math.ceil(parseInt(userInfo.semester) / 2)))}학년 (${userInfo.semester})` : "1학년 (1학기)"} />
          <ProfileInfoRow Icon={BookMarked} label="융합전공" value={convergenceMajor || "선택 안 함 (일반 전공)"} />
          <ProfileInfoRow Icon={Award} label="특성화트랙" value={specializedTrack || "선택 안 함 (일반 트랙)"} />
        </div>

        {/* 학점 이수 현황 */}
        <div className="pt-4.5 border-t border-border/60 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-secondary/40 rounded-2xl p-4 flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="text-[10px] text-muted-foreground font-bold">기수강 이수 학점</span>
              <p className="text-sm font-bold text-foreground">총 {currentEarnedCredits} / {userInfo.totalRequired || 130} 학점</p>
            </div>
            <span className="text-[11px] bg-[#3182f6]/10 text-[#3182f6] px-2.5 py-1 rounded-xl font-bold">
              진척도 {Math.round((currentEarnedCredits / (userInfo.totalRequired || 130)) * 100)}%
            </span>
          </div>

          {/* 누적 마일리지 */}
          <div className="bg-secondary/40 rounded-2xl p-4 flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="text-[10px] text-muted-foreground font-bold">누적 마일리지</span>
              <p className="text-sm font-bold text-foreground">{(mileage || 0).toLocaleString()} P</p>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={async () => {
                  const newMileage = Math.max(0, mileage - 25)
                  setMileage(newMileage)
                  try {
                    await updateProfile(userInfo.name, userInfo.studentId, userInfo.department, newMileage)
                    if (refreshData) await refreshData()
                    showToast("마일리지가 성공적으로 차감되었습니다.")
                  } catch {
                    showToast("마일리지 수정에 실패했습니다.")
                  }
                }}
                className="flex h-8 w-8 items-center justify-center rounded-xl bg-card border border-border text-foreground hover:bg-muted active:scale-95 transition-all select-none cursor-pointer"
              >
                <Minus className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={async () => {
                  const newMileage = mileage + 25
                  setMileage(newMileage)
                  try {
                    await updateProfile(userInfo.name, userInfo.studentId, userInfo.department, newMileage)
                    if (refreshData) await refreshData()
                    showToast("마일리지가 성공적으로 추가되었습니다.")
                  } catch {
                    showToast("마일리지 수정에 실패했습니다.")
                  }
                }}
                className="flex h-8 w-8 items-center justify-center rounded-xl bg-card border border-border text-foreground hover:bg-muted active:scale-95 transition-all select-none cursor-pointer"
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* 전체 학기 총 평점 (Cumulative GPA) */}
          <div className="bg-secondary/40 rounded-2xl p-4 flex items-center justify-between col-span-1">
            <div className="space-y-0.5">
              <span className="text-[10px] text-muted-foreground font-bold">전체 학기 총 평점</span>
              <p className="text-sm font-bold text-foreground">{cumulativeGPA} / 4.5</p>
            </div>
            <span className={`text-[11px] px-2.5 py-1 rounded-xl font-bold select-none ${
              Number(cumulativeGPA) >= 4.0 
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" 
                : Number(cumulativeGPA) >= 3.5 
                  ? "bg-blue-500/10 text-blue-600 dark:text-blue-400" 
                  : Number(cumulativeGPA) >= 3.0 
                    ? "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400" 
                    : "bg-red-500/10 text-red-600 dark:text-red-400"
            }`}>
              {Number(cumulativeGPA) >= 4.0 
                ? "최우수" 
                : Number(cumulativeGPA) >= 3.5 
                  ? "우수" 
                  : Number(cumulativeGPA) >= 3.0 
                    ? "양호" 
                    : "관리 요망"}
            </span>
          </div>
        </div>
      </motion.section>

      {/* 기이수 과목 관리 전용 카드 섹션 (벌크 체크박스 일괄 저장 복원) */}
      <motion.section 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="rounded-3xl bg-card p-6 shadow-sm border border-border space-y-6"
      >
        <div className="flex items-center justify-between border-b border-border/60 pb-4">
          <div className="space-y-1">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
              <BookMarked className="h-4.5 w-4.5 text-[#3182f6]" />
              기이수과목 이력 관리
            </h2>
            <p className="text-[11px] text-muted-foreground">이수한 과목들을 일괄 선택하여 졸업 학점에 즉시 반영합니다.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setShowPdfUpload(!showPdfUpload)
                setPdfFile(null)
                setPdfParsedCourses([])
                setPdfUploadMessage("")
              }}
              className="flex items-center gap-1 bg-emerald-500 text-white text-xs font-bold px-4 py-2.5 rounded-2xl hover:bg-emerald-600 transition-all cursor-pointer shadow-sm shadow-emerald-500/10"
            >
              <FileUp className="h-4 w-4" />
              <span>성적 PDF 첨부</span>
            </button>
            <button
              onClick={() => {
                setCheckedCourses([])
                setShowAddForm(!showAddForm)
              }}
              className="flex items-center gap-1 bg-[#3182f6] text-white text-xs font-bold px-4 py-2.5 rounded-2xl hover:bg-[#1b64da] transition-all cursor-pointer shadow-sm shadow-[#3182f6]/10"
            >
              <Plus className="h-4 w-4" />
              <span>수강기록 설정</span>
            </button>
          </div>
        </div>

        {/* PDF 업로드 섹션 */}
        <AnimatePresence>
          {showPdfUpload && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden rounded-2xl bg-emerald-500/5 border border-emerald-500/15"
            >
              <div className="p-5 space-y-4">
                {/* 파일 선택 영역 */}
                {pdfParsedCourses.length === 0 && (
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5 text-emerald-600" />
                      성적확인서 PDF 업로드
                    </h3>
                    <p className="text-[11px] text-muted-foreground">
                      학교에서 발급받은 성적확인서 PDF 파일을 업로드하면, AI가 자동으로 과목 정보를 추출합니다.
                    </p>
                    <div
                      onClick={() => pdfInputRef.current?.click()}
                      onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
                      onDrop={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        const files = e.dataTransfer.files
                        if (files?.[0]) {
                          const f = files[0]
                          if (f.type === "application/pdf" || f.name.endsWith(".pdf")) {
                            setPdfFile(f)
                          } else {
                            showToast("PDF 파일만 업로드 가능합니다.")
                          }
                        }
                      }}
                      className={`flex flex-col items-center justify-center gap-2 p-8 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
                        pdfFile
                          ? "border-emerald-500 bg-emerald-500/10"
                          : "border-border hover:border-emerald-400 hover:bg-emerald-500/5"
                      }`}
                    >
                      <input
                        ref={pdfInputRef}
                        type="file"
                        accept=".pdf,application/pdf"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0]
                          if (f) {
                            if (f.type !== "application/pdf" && !f.name.endsWith(".pdf")) {
                              showToast("PDF 파일만 업로드 가능합니다.")
                              return
                            }
                            setPdfFile(f)
                          }
                        }}
                      />
                      {pdfFile ? (
                        <>
                          <FileCheck className="h-8 w-8 text-emerald-600" />
                          <span className="text-xs font-bold text-emerald-700">{pdfFile.name}</span>
                          <span className="text-[10px] text-muted-foreground">
                            {(pdfFile.size / 1024).toFixed(1)}KB · 클릭하여 파일 변경
                          </span>
                        </>
                      ) : (
                        <>
                          <FileUp className="h-8 w-8 text-muted-foreground" />
                          <span className="text-xs font-bold text-foreground">PDF 파일을 여기에 드래그하거나 클릭하여 선택</span>
                          <span className="text-[10px] text-muted-foreground">성적확인서 · 학업성적증명서 (최대 10MB)</span>
                        </>
                      )}
                    </div>
                    {pdfFile && (
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => { setPdfFile(null); pdfInputRef.current && (pdfInputRef.current.value = "") }}
                          className="px-4 py-2.5 rounded-xl text-xs font-bold bg-secondary text-foreground hover:bg-muted cursor-pointer"
                        >
                          취소
                        </button>
                        <button
                          onClick={handlePdfUpload}
                          disabled={isPdfUploading}
                          className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 cursor-pointer shadow-sm shadow-emerald-500/10"
                        >
                          {isPdfUploading ? (
                            <><Loader2 className="h-3.5 w-3.5 animate-spin" /> AI 분석 중...</>
                          ) : (
                            <><FileUp className="h-3.5 w-3.5" /> 업로드 및 분석</>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* 업로드 메시지 */}
                {pdfUploadMessage && pdfParsedCourses.length === 0 && (
                  <div className="text-xs text-red-600 bg-red-500/10 rounded-xl p-3">
                    {pdfUploadMessage}
                  </div>
                )}

                {/* 추출된 과목 결과 테이블 */}
                {pdfParsedCourses.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                        <FileCheck className="h-3.5 w-3.5 text-emerald-600" />
                        추출된 과목 목록 ({pdfParsedCourses.length}개)
                      </h3>
                      <span className="text-[10px] text-muted-foreground">
                        DB 매칭: {pdfParsedCourses.filter(c => c.dbMatched).length}개
                      </span>
                    </div>

                    <div className="max-h-[350px] overflow-y-auto rounded-xl border border-border">
                      <table className="w-full text-xs">
                        <thead className="sticky top-0 bg-card border-b border-border">
                          <tr className="text-left">
                            <th className="px-3 py-2 font-bold text-muted-foreground">과목명</th>
                            <th className="px-3 py-2 font-bold text-muted-foreground">이수구분</th>
                            <th className="px-3 py-2 font-bold text-muted-foreground text-center">학점</th>
                            <th className="px-3 py-2 font-bold text-muted-foreground text-center">성적</th>
                            <th className="px-3 py-2 font-bold text-muted-foreground">학기</th>
                            <th className="px-3 py-2 font-bold text-muted-foreground text-center">매칭</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/50">
                          {pdfParsedCourses.map((c, idx) => (
                            <tr key={idx} className="hover:bg-secondary/30">
                              <td className="px-3 py-2">
                                <span className="font-bold text-foreground">{c.courseName}</span>
                                {c.courseCode && (
                                  <span className="ml-1.5 text-[9px] text-muted-foreground font-mono">{c.courseCode}</span>
                                )}
                              </td>
                              <td className="px-3 py-2">
                                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                  c.courseType.includes("전공") ? "bg-blue-500/10 text-blue-600" :
                                  c.courseType.includes("교양") ? "bg-purple-500/10 text-purple-600" :
                                  "bg-gray-500/10 text-gray-600"
                                }`}>
                                  {c.courseType}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-center font-mono">{c.credits}</td>
                              <td className="px-3 py-2 text-center">
                                <span className={`font-bold ${
                                  c.grade.startsWith("A") ? "text-emerald-600" :
                                  c.grade.startsWith("B") ? "text-blue-600" :
                                  c.grade === "F" ? "text-red-600" : "text-foreground"
                                }`}>
                                  {c.grade}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-[10px] text-muted-foreground">{c.semester}</td>
                              <td className="px-3 py-2 text-center">
                                {c.dbMatched ? (
                                  <span className="text-[9px] font-bold text-emerald-600 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                                    DB 매칭
                                  </span>
                                ) : (
                                  <span className="text-[9px] font-bold text-amber-600 bg-amber-500/10 px-1.5 py-0.5 rounded">
                                    신규 등록
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="flex justify-end gap-2 pt-2 border-t border-border/40">
                      <button
                        onClick={() => { setPdfParsedCourses([]); setPdfFile(null); setPdfUploadMessage(""); pdfInputRef.current && (pdfInputRef.current.value = "") }}
                        className="px-4 py-2.5 rounded-xl text-xs font-bold bg-secondary text-foreground hover:bg-muted cursor-pointer"
                      >
                        취소
                      </button>
                      <button
                        onClick={handlePdfConfirmSave}
                        disabled={isPdfSaving}
                        className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 cursor-pointer shadow-sm shadow-emerald-500/10"
                      >
                        {isPdfSaving ? (
                          <><Loader2 className="h-3.5 w-3.5 animate-spin" /> 저장 중...</>
                        ) : (
                          <><Check className="h-3.5 w-3.5" /> 저장하기</>
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* [복원] 체크박스 기반 이수과목 일괄 설정 보드 */}
        <AnimatePresence>
          {showAddForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden p-5 rounded-2xl bg-[#3182f6]/5 border border-[#3182f6]/15 space-y-4"
            >
              {/* 탭 헤더 */}
              <div className="flex border-b border-border/40 pb-2">
                <button
                  type="button"
                  onClick={() => setAddFormTab("search")}
                  className={`flex-1 pb-2 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                    addFormTab === "search"
                      ? "border-[#3182f6] text-[#3182f6]"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  과목 검색 선택
                </button>
                <button
                  type="button"
                  onClick={() => setAddFormTab("custom")}
                  className={`flex-1 pb-2 text-xs font-bold border-b-2 transition-all cursor-pointer ${
                    addFormTab === "custom"
                      ? "border-[#3182f6] text-[#3182f6]"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  직접 입력 (커스텀 과목)
                </button>
              </div>

              {addFormTab === "search" ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-[#3182f6]" />
                      이수 완료 과목 체크박스 일괄 설정 (체크 시 반영)
                    </h3>
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground font-bold shrink-0">대상 학기:</span>
                        <select
                          value={bulkTargetSemester}
                          onChange={(e) => setBulkTargetSemester(e.target.value)}
                          className="rounded-lg bg-card border border-border px-1.5 py-0.5 text-[10px] text-foreground focus:outline-none cursor-pointer"
                        >
                          {(semesters.length > 0 ? semesters : SEMESTER_OPTIONS).map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      </div>
                      <span className="text-[10px] bg-[#3182f6]/15 text-[#3182f6] px-2 py-0.5 rounded-md font-bold shrink-0">
                        선택됨: {checkedCourses.length}개
                      </span>
                    </div>
                  </div>

                  {/* 검색창 & 이수구분 필터 */}
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-3.5 w-3.5 text-muted-foreground" />
                      </div>
                      <input
                        type="text"
                        placeholder="과목명 또는 학수코드 검색..."
                        value={courseSearchQuery}
                        onChange={(e) => setCourseSearchQuery(e.target.value)}
                        className="w-full rounded-xl bg-card border border-border pl-8.5 pr-4 py-2.5 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6]"
                      />
                    </div>
                    <select
                      value={filterCourseType}
                      onChange={(e) => setFilterCourseType(e.target.value)}
                      className="rounded-xl bg-card border border-border px-3 py-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6] cursor-pointer"
                    >
                      {["전체", "전공필수", "전공선택", "교양필수", "교양선택", "계열공통", "특화전공 전선", "융합전공 전선", "일반선택"].map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>

                  {/* 스크롤블 체크박스 그리드 */}
                  <div className="max-h-[300px] overflow-y-auto pr-1.5 grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {isModalCoursesLoading ? (
                      <div className="col-span-full text-center py-12 space-y-2">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto text-[#3182f6]" />
                        <span className="text-xs text-muted-foreground block">선택 학기 개설 과목 불러오는 중...</span>
                      </div>
                    ) : filteredSearchCourses.length === 0 ? (
                      <div className="col-span-full text-center py-8 text-xs text-muted-foreground">
                        검색 결과와 일치하는 개설 과목이 없습니다.
                      </div>
                    ) : (
                      filteredSearchCourses.map((c) => {
                        const isAlreadySaved = historyList.some((h: any) => h.course_code === c.code)
                        const isChecked = checkedCourses.includes(c.code)
                        return (
                          <div
                            key={c.code}
                            onClick={() => handleToggleCourse(c.code)}
                            className={`rounded-xl border p-3 flex items-center gap-3 transition-all select-none text-left cursor-pointer ${
                              isChecked 
                                ? "bg-card border-[#3182f6] shadow-sm shadow-[#3182f6]/5" 
                                : "bg-card border-border/80 hover:bg-secondary/40"
                            }`}
                          >
                            <div className={`h-4.5 w-4.5 rounded flex items-center justify-center border transition-all ${
                              isChecked 
                                ? "bg-[#3182f6] border-[#3182f6] text-white" 
                                : "border-border bg-background"
                            }`}>
                              {isChecked && <Check className="h-3 w-3 stroke-[3]" />}
                            </div>
                            
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between gap-2">
                                <p className="text-xs font-bold text-foreground truncate">{c.name}</p>
                                {isAlreadySaved && (
                                  <span className="text-[8px] font-bold text-[#3182f6] bg-[#3182f6]/10 px-1.5 py-0.5 rounded-md shrink-0">
                                    이수 완료
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-[9px] text-muted-foreground font-mono">{c.code}</span>
                                <span className="text-[9px] text-[#3182f6] font-bold">{c.category} ({c.credit}학점)</span>
                              </div>
                            </div>
                          </div>
                        )
                      })
                    )}
                  </div>

                  {/* 저장 및 취소 버튼 */}
                  <div className="flex justify-end gap-2 pt-2 border-t border-border/40">
                    <button
                      type="button"
                      onClick={() => {
                        setShowAddForm(false)
                        setCourseSearchQuery("")
                      }}
                      className="px-4 py-2.5 rounded-xl text-xs font-bold bg-secondary text-foreground hover:bg-muted cursor-pointer"
                    >
                      취소
                    </button>
                    <button
                      type="button"
                      onClick={handleBulkSave}
                      className="px-5 py-2.5 rounded-xl text-xs font-bold bg-[#3182f6] text-white hover:bg-[#1b64da] cursor-pointer shadow-sm shadow-[#3182f6]/10"
                    >
                      변경사항 일괄 저장하기
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-[#3182f6]" />
                      개설 과목 풀에 없는 커스텀 과목 직접 추가
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-muted-foreground">과목명</label>
                      <input
                        type="text"
                        placeholder="예: 실용 AI 프로젝트"
                        value={customCourseName}
                        onChange={(e) => setCustomCourseName(e.target.value)}
                        className="w-full rounded-xl bg-card border border-border px-3.5 py-2.5 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6]"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-muted-foreground">학점</label>
                      <select
                        value={customCredits}
                        onChange={(e) => setCustomCredits(e.target.value)}
                        className="w-full rounded-xl bg-card border border-border px-3.5 py-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6] cursor-pointer"
                      >
                        {["0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4"].map((c) => (
                          <option key={c} value={c}>{c}학점</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-muted-foreground">이수 구분</label>
                      <select
                        value={customCourseType}
                        onChange={(e) => setCustomCourseType(e.target.value)}
                        className="w-full rounded-xl bg-card border border-border px-3.5 py-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6] cursor-pointer"
                      >
                        {["전공필수", "전공선택", "교양필수", "교양선택", "계열공통", "특화전공 전선", "융합전공 전선", "일반선택"].map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-muted-foreground">수강 학기</label>
                      <select
                        value={customSemester}
                        onChange={(e) => setCustomSemester(e.target.value)}
                        className="w-full rounded-xl bg-card border border-border px-3.5 py-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6] cursor-pointer"
                      >
                        {(semesters.length > 0 ? semesters : SEMESTER_OPTIONS).map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-muted-foreground">성적</label>
                      <select
                        value={customGrade}
                        onChange={(e) => setCustomGrade(e.target.value)}
                        className="w-full rounded-xl bg-card border border-border px-3.5 py-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-[#3182f6] cursor-pointer"
                      >
                        {["A+", "A0", "B+", "B0", "C+", "C0", "D+", "D0", "F", "P", "NP"].map((g) => (
                          <option key={g} value={g}>{g}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-1 pb-2">
                    <label className="flex items-center gap-2 text-xs font-bold text-muted-foreground select-none cursor-pointer">
                      <input
                        type="checkbox"
                        checked={customIsRetake}
                        onChange={(e) => setCustomIsRetake(e.target.checked)}
                        className="rounded border-border text-[#3182f6] focus:ring-[#3182f6] h-4 w-4 cursor-pointer"
                      />
                      <span>이 과목은 재수강 과목입니다 (이전 학기 동일 과목의 성적이 포기 처리됩니다)</span>
                    </label>
                  </div>

                  {/* 직접입력 폼 하단 버튼 */}
                  <div className="flex justify-end gap-2 pt-2 border-t border-border/40">
                    <button
                      type="button"
                      onClick={() => {
                        setShowAddForm(false);
                        setCustomCourseName("");
                      }}
                      className="px-4 py-2.5 rounded-xl text-xs font-bold bg-secondary text-foreground hover:bg-muted cursor-pointer"
                    >
                      취소
                    </button>
                    <button
                      type="button"
                      onClick={handleCustomSave}
                      disabled={isCustomSubmitting || !customCourseName.trim()}
                      className="px-5 py-2.5 rounded-xl text-xs font-bold bg-[#3182f6] text-white hover:bg-[#1b64da] disabled:opacity-50 cursor-pointer shadow-sm shadow-[#3182f6]/10"
                    >
                      {isCustomSubmitting ? "저장 중..." : "커스텀 과목 추가"}
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>


        {/* 학기별 그룹화된 리스트 뷰 */}
        {isHistoryLoading ? (
          <div className="py-12 flex justify-center items-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : groupedHistory.length === 0 ? (
          <div className="rounded-2xl border-2 border-dashed border-border py-12 text-center text-xs text-muted-foreground bg-secondary/15">
            등록된 수강 이력이 없습니다.<br />우측 상단의 [수강기록 설정] 버튼을 눌러 완료한 과목들을 일괄 추가해 주세요.
          </div>
        ) : (
          <div className="space-y-5">
            {groupedHistory.map(({ semester, items, gpa }) => {
              const isCollapsed = !!collapsedSemesters[semester]
              return (
                <div key={semester} className="space-y-2.5">
                  <div 
                    className="flex items-center justify-between border-b border-border/40 pb-1.5 cursor-pointer select-none group"
                    onClick={() => toggleSemesterCollapse(semester)}
                  >
                    <div className="flex items-center gap-2">
                      {isCollapsed ? (
                        <ChevronRight className="h-4 w-4 text-muted-foreground/80 hover:text-muted-foreground transition-transform" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground/80 hover:text-muted-foreground transition-transform" />
                      )}
                      <h3 className="text-xs font-bold text-muted-foreground border-l-2 border-[#3182f6] pl-2">{semester}</h3>
                      <span className="text-[10px] font-bold text-[#3182f6] bg-[#3182f6]/10 px-2 py-0.5 rounded-md select-none">
                        학기 평점: {gpa}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteSemester(semester, items)
                      }}
                      className="flex items-center gap-1 text-[10px] text-destructive hover:bg-destructive/10 px-2 py-1 rounded-xl transition-all cursor-pointer font-bold select-none"
                    >
                      <Trash2 className="h-3 w-3" />
                      <span>학기 전체 삭제</span>
                    </button>
                  </div>
                  
                  {!isCollapsed && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {items.map((item) => {
                    const isEditing = editingHistoryId === item.history_id

                    return (
                      <div
                        key={item.history_id}
                        className={`rounded-2xl border p-4.5 transition-all flex items-center justify-between ${
                          isEditing ? "bg-[#3182f6]/5 border-[#3182f6]" : "bg-secondary/20 border-border"
                        }`}
                      >
                        <div className="space-y-1 truncate pr-4 flex-1">
                          {isEditing ? (
                            <div className="flex flex-col gap-2 w-full pt-1.5" onClick={(e) => e.stopPropagation()}>
                              <div className="flex gap-1.5 items-center w-full">
                                <input
                                  type="text"
                                  value={editCourseName}
                                  onChange={(e) => setEditCourseName(e.target.value)}
                                  className="rounded-lg bg-card border border-border px-2 py-1 text-xs text-foreground focus:outline-none flex-1 font-bold"
                                  placeholder="과목명 수정"
                                />
                                <select
                                  value={editCredits}
                                  onChange={(e) => setEditCredits(e.target.value)}
                                  className="rounded-lg bg-card border border-border px-2 py-1 text-[10px] text-foreground focus:outline-none cursor-pointer shrink-0"
                                >
                                  {["0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4"].map((c) => (
                                    <option key={c} value={c}>{c}학점</option>
                                  ))}
                                </select>
                              </div>
                              <div className="flex gap-2 items-center flex-wrap">
                                <select
                                  value={editSemester}
                                  onChange={(e) => setEditSemester(e.target.value)}
                                  className="rounded-lg bg-card border border-border px-2 py-1 text-[10px] text-foreground focus:outline-none cursor-pointer"
                                >
                                  {(semesters.length > 0 ? semesters : SEMESTER_OPTIONS).map((s) => (
                                    <option key={s} value={s}>{s}</option>
                                  ))}
                                </select>
                                <select
                                  value={editGrade}
                                  onChange={(e) => setEditGrade(e.target.value)}
                                  className="rounded-lg bg-card border border-border px-2 py-1 text-[10px] text-foreground focus:outline-none cursor-pointer"
                                >
                                  {["A+", "A0", "B+", "B0", "C+", "C0", "D+", "D0", "F", "P", "NP"].map((g) => (
                                    <option key={g} value={g}>{g}</option>
                                  ))}
                                </select>
                                <select
                                  value={editCourseType}
                                  onChange={(e) => setEditCourseType(e.target.value)}
                                  className="rounded-lg bg-card border border-border px-2 py-1 text-[10px] text-foreground focus:outline-none cursor-pointer"
                                >
                                  {["전공필수", "전공선택", "교양필수", "교양선택", "계열공통", "특화전공 전선", "융합전공 전선", "일반선택"].map((ct) => (
                                    <option key={ct} value={ct}>{ct}</option>
                                  ))}
                                </select>
                                <label 
                                  className="flex items-center gap-1 text-[10px] text-muted-foreground select-none cursor-pointer shrink-0"
                                  title="재수강 선택 시, 동일 과목(코드/이름)의 이전 수강 이력 학점과 성적은 졸업 사정 및 GPA 계산에서 제외(포기)됩니다."
                                >
                                  <input
                                    type="checkbox"
                                    checked={editIsRetake}
                                    onChange={(e) => setEditIsRetake(e.target.checked)}
                                    className="rounded border-border text-[#3182f6] focus:ring-[#3182f6] h-3.5 w-3.5 cursor-pointer"
                                  />
                                  <span className="underline decoration-dotted decoration-muted-foreground cursor-help">재수강</span>
                                </label>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="flex items-center gap-2 flex-wrap">
                                <p className={`text-sm font-bold truncate ${
                                  item.is_forfeited 
                                    ? "line-through text-muted-foreground/60 decoration-1" 
                                    : "text-foreground"
                                }`}>
                                  {item.course_name}
                                </p>
                                {item.is_retake && (
                                  <span className="text-[8px] font-bold text-[#ff9800] bg-[#ff9800]/10 px-1.5 py-0.5 rounded-md select-none shrink-0">
                                    재수강
                                  </span>
                                )}
                                {item.is_forfeited && (
                                  <span 
                                    className="text-[8px] font-bold text-muted-foreground bg-secondary px-1.5 py-0.5 rounded-md select-none shrink-0 cursor-help"
                                    title="재수강 과목 수강으로 인해 이 과목의 취득 학점과 성적은 전체 합계 및 GPA에서 포기 처리되었습니다."
                                  >
                                    학점포기됨
                                  </span>
                                )}
                              </div>
                              
                              <div className="flex items-center gap-2 pt-0.5">
                                <span className="text-[10px] font-bold text-muted-foreground select-none">
                                  {item.earned_credit !== undefined && item.earned_credit !== null && item.earned_credit !== '' ? item.earned_credit : 3}학점
                                </span>
                                <span className="text-[10px] font-bold text-muted-foreground bg-secondary/85 px-1.5 py-0.5 rounded-md select-none shrink-0">
                                  {item.course_type || "일반선택"}
                                </span>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full select-none ${
                                  item.grade === "F" ? "bg-red-100 text-red-600" : "bg-[#3182f6]/10 text-[#3182f6]"
                                }`}>
                                  {item.grade}
                                </span>
                              </div>
                            </>
                          )}
                        </div>

                        {/* 개별 CRUD 수정 및 삭제 버튼 묶음 */}
                        <div className="flex items-center gap-1.5 shrink-0">
                          {isEditing ? (
                            <>
                              <button
                                onClick={() => handleUpdateHistory(item.history_id)}
                                className="p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/20 rounded-xl cursor-pointer"
                              >
                                <Check className="h-4.5 w-4.5" />
                              </button>
                              <button
                                onClick={() => setEditingHistoryId(null)}
                                className="p-1.5 text-muted-foreground hover:bg-muted rounded-xl cursor-pointer"
                              >
                                <X className="h-4.5 w-4.5" />
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => {
                                  setEditingHistoryId(item.history_id)
                                  setEditSemester(item.semester_taken)
                                  setEditGrade(item.grade)
                                  setEditCourseName(item.course_name)
                                  setEditCredits(String(item.earned_credit !== undefined && item.earned_credit !== null && item.earned_credit !== '' ? item.earned_credit : 3))
                                  setEditIsRetake(!!item.is_retake)
                                  setEditCourseType(item.course_type || "전공선택")
                                }}
                                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-xl cursor-pointer"
                              >
                                <Edit2 className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => handleDeleteHistory(item.history_id)}
                                className="p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/5 rounded-xl cursor-pointer"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
              </div>
            )})}
          </div>
        )}
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

          {/* 비밀번호 변경 */}
          <button
            onClick={() => setIsOpenPasswordModal(true)}
            className="w-full flex items-center justify-between py-4 text-left hover:bg-[#f2f4f6]/50 dark:hover:bg-[#212836]/30 px-1 -mx-1 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3.5">
              <span className="flex h-9.5 w-9.5 items-center justify-center rounded-xl bg-[#d6284a]/10 text-[#d6284a]">
                <Edit2 className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-sm font-bold text-foreground">비밀번호 변경</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">가상 로그인 계정 비밀번호 수정</p>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
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

      {/* Toss-inspired 키워드 관리 모달 */}
      <AnimatePresence>
        {showKeywordModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowKeywordModal(false)}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            />
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

      {/* 비밀번호 변경 모달 */}
      <AnimatePresence>
        {isOpenPasswordModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                if (!isPasswordSubmitting) setIsOpenPasswordModal(false)
              }}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, y: 50, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 350, damping: 28 }}
              className="relative w-full max-w-sm rounded-[2rem] bg-card p-6 shadow-2xl border border-border space-y-4"
            >
              <div className="flex items-center justify-between border-b border-border pb-3">
                <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                  <span>🔒 비밀번호 변경</span>
                </h3>
                <button
                  type="button"
                  onClick={() => setIsOpenPasswordModal(false)}
                  disabled={isPasswordSubmitting}
                  className="rounded-full p-1.5 text-muted-foreground hover:bg-secondary transition-colors cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-3.5 pt-1.5">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-muted-foreground">현재 비밀번호</label>
                  <input
                    type="password"
                    placeholder="현재 비밀번호를 입력하세요"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    disabled={isPasswordSubmitting}
                    className="w-full rounded-xl border border-transparent bg-secondary px-3.5 py-2.5 text-xs text-foreground placeholder-muted-foreground focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-muted-foreground">새 비밀번호</label>
                  <input
                    type="password"
                    placeholder="새 비밀번호를 입력하세요 (4자리 이상)"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    disabled={isPasswordSubmitting}
                    className="w-full rounded-xl border border-transparent bg-secondary px-3.5 py-2.5 text-xs text-foreground placeholder-muted-foreground focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-muted-foreground">새 비밀번호 확인</label>
                  <input
                    type="password"
                    placeholder="새 비밀번호를 다시 입력하세요"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    disabled={isPasswordSubmitting}
                    className="w-full rounded-xl border border-transparent bg-secondary px-3.5 py-2.5 text-xs text-foreground placeholder-muted-foreground focus:border-primary focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsOpenPasswordModal(false)}
                  disabled={isPasswordSubmitting}
                  className="flex-1 py-3 rounded-xl text-xs font-bold bg-secondary text-foreground hover:bg-muted transition-all cursor-pointer text-center"
                >
                  취소
                </button>
                <button
                  type="button"
                  onClick={handlePasswordChange}
                  disabled={isPasswordSubmitting || !currentPassword || !newPassword || !confirmPassword}
                  className="flex-1 py-3 rounded-xl text-xs font-bold bg-[#3182f6] text-white hover:bg-[#1b64da] active:scale-[0.98] transition-all cursor-pointer disabled:bg-secondary disabled:text-muted-foreground/50 disabled:cursor-not-allowed text-center"
                >
                  {isPasswordSubmitting ? "변경 중..." : "변경 완료"}
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
