import type { GradManagerData, UserInfo, DigitalTwin, PastelColor } from "./grad-data-types"
import type {
  RecommendedCourse,
  CreditCategory,
  QuickMenu,
  ScheduleBlock,
  ScheduleReason,
  KeywordChip,
  NoticeItem,
  AiFilterChip,
  AiCourse,
} from "@/data/types"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

// Authorization JWT token injector helper for API readiness
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("token") : null
  const headers = {
    ...options.headers as Record<string, string>,
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
  }
  const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`
  return fetch(fullUrl, { ...options, headers })
}

export async function loginUser(studentId: string, password: string): Promise<{ token: string; user: UserInfo }> {
  const res = await apiFetch("/api/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId, password }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "로그인에 실패했습니다.")
  }
  return await res.json()
}

export async function getGradData(): Promise<GradManagerData> {
  const res = await apiFetch("/api/v1/graduation/summary")
  if (!res.ok) {
    throw new Error("데이터를 불러오지 못했습니다.")
  }
  return (await res.json()) as GradManagerData
}

export async function getUserData(): Promise<{
  userInfo: UserInfo
  creditCategories: CreditCategory[]
  quickMenus: QuickMenu[]
}> {
  const data = await getGradData()
  return {
    userInfo: data.user.userInfo,
    creditCategories: data.user.creditCategories,
    quickMenus: data.user.quickMenus,
  }
}

export async function getRecommendations(): Promise<{
  scheduleDays: string[]
  scheduleHours: number[]
  scheduleBlocks: ScheduleBlock[]
  scheduleReasons: ScheduleReason[]
  pastelPalette: PastelColor[]
}> {
  const res = await apiFetch("/api/v1/timetable/recommend")
  if (!res.ok) {
    throw new Error("시간표 추천을 불러오지 못했습니다.")
  }
  return await res.json()
}

export async function getNoticeData(): Promise<{
  interestKeywords: KeywordChip[]
  urgentNotice: NoticeItem
  academicCalendar: NoticeItem[]
}> {
  const res = await apiFetch("/api/v1/notices/alerts")
  if (!res.ok) {
    throw new Error("공지 데이터를 불러오지 못했습니다.")
  }
  return await res.json()
}

export async function getDigitalTwinData(): Promise<DigitalTwin> {
  const data = await getGradData()
  return data.digitalTwin
}

export async function getAiRecommendationData(): Promise<{
  aiFilters: AiFilterChip[]
  aiCourses: AiCourse[]
}> {
  const data = await getGradData()
  return data.aiRecommendation
}

export async function sendChatMessage(
  message: string,
  history?: Array<{ role: "user" | "assistant"; content: string }>,
  semester?: string,
  department?: string
): Promise<{ message: string; simulated_timetable?: any }> {
  let convergenceMajor = ""
  let specializedTrack = ""
  
  if (typeof window !== "undefined") {
    const studentId = sessionStorage.getItem("active_student_id")
    const prefKey = studentId ? `grad_major_preferences_${studentId}` : "grad_major_preferences"
    const stored = sessionStorage.getItem(prefKey)
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        convergenceMajor = parsed.convergenceMajor || ""
        specializedTrack = parsed.specializedTrack || ""
      } catch (e) {
        console.error("sessionStorage grad_major_preferences 파싱 실패:", e)
      }
    }
  }

  const res = await apiFetch("/api/v1/chatbot/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ 
      message, 
      history, 
      convergenceMajor, 
      specializedTrack,
      semester,
      department
    }),
  })
  if (!res.ok) {
    throw new Error("메시지 전송에 실패했습니다.")
  }
  return await res.json()
}

export async function registerUser(
  studentId: string,
  password: string,
  name: string,
  department: string
): Promise<{ message: string }> {
  const res = await apiFetch("/api/v1/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId, password, name, department }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "회원가입에 실패했습니다.")
  }
  return await res.json()
}

export async function searchCourseOfferings(query: string, semester?: string): Promise<any[]> {
  const semParam = semester ? `&semester=${encodeURIComponent(semester)}` : ""
  const res = await apiFetch(`/api/v1/timetable/mock-courses?q=${encodeURIComponent(query)}${semParam}`)
  if (!res.ok) {
    throw new Error("과목 검색에 실패했습니다.")
  }
  const data = await res.json()
  return data.data || []
}

export async function updateCompletedCourses(
  studentId: string,
  completedCourses: string[],
  targetSemester?: string
): Promise<{ success: boolean; completed_credits: number; completed_courses_count: number }> {
  const res = await apiFetch("/api/v1/graduation/courses", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId, completedCourses, targetSemester }),
  })
  if (!res.ok) {
    throw new Error("기수강 과목 업데이트에 실패했습니다.")
  }
  return await res.json()
}

export async function updateProfile(
  name: string,
  studentId: string,
  department: string,
  mileage?: number,
  currentSemester?: number,
  majorTracks?: string[]
): Promise<{ success: boolean }> {
  const res = await apiFetch("/api/v1/auth/profile", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      studentId,
      department,
      mileage,
      current_semester: currentSemester,
      major_tracks: majorTracks,
    }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "프로필 수정에 실패했습니다.")
  }
  return await res.json()
}

export async function saveUserSchedule(studentId: string | number, scheduleBlocks: any[], semester?: string): Promise<{ success: boolean }> {
  const res = await apiFetch("/api/v1/timetable/schedule", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId: String(studentId), scheduleBlocks, semester }),
  })
  if (!res.ok) {
    throw new Error("시간표 블록 저장에 실패했습니다.")
  }
  return await res.json()
}

export async function getUserSchedule(studentId: string, semester?: string): Promise<any[]> {
  const semParam = semester ? `&semester=${encodeURIComponent(semester)}` : ""
  const res = await apiFetch(`/api/v1/timetable/schedule?studentId=${studentId}${semParam}`)
  if (!res.ok) {
    throw new Error("시간표 블록 조회에 실패했습니다.")
  }
  const data = await res.json()
  return data.scheduleBlocks || []
}

export async function changePassword(
  studentId: string,
  currentPassword: string,
  newPassword: string
): Promise<{ success: boolean; message?: string }> {
  const res = await apiFetch("/api/v1/auth/change-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId, currentPassword, newPassword }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "비밀번호 변경에 실패했습니다.")
  }
  return await res.json()
}

export async function addStudentCourseHistory(
  studentId: number,
  courseId: number | string,
  semesterTaken: string,
  grade: string,
  isRetake: boolean = false,
  customCourseName?: string,
  credits?: number,
  courseType?: string
): Promise<{ status: string; message: string; history_id: number }> {
  const res = await apiFetch("/api/v1/students/history", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      student_id: studentId,
      course_id: courseId,
      semester_taken: semesterTaken,
      grade: grade,
      is_retake: isRetake,
      custom_course_name: customCourseName,
      credits: credits,
      course_type: courseType,
    }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "수강 이력 등록에 실패했습니다.")
  }
  return await res.json()
}

export async function addCustomStudentCourseHistory(
  studentId: number,
  customCourseName: string,
  credits: number,
  courseType: string,
  semesterTaken: string,
  grade: string,
  isRetake: boolean = false
): Promise<{ status: string; message: string; history_id: number; course_code: string }> {
  const res = await apiFetch("/api/v1/students/history", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      student_id: studentId,
      custom_course_name: customCourseName,
      credits: credits,
      course_type: courseType,
      semester_taken: semesterTaken,
      grade: grade,
      is_retake: isRetake,
    }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "커스텀 수강 이력 등록에 실패했습니다.")
  }
  return await res.json()
}

export async function getStudentGraduationSummary(
  studentId: number
): Promise<{
  status: string
  student_id: number
  total_required_credits: number
  total_completed_credits: number
  total_remaining_credits: number
  major_completed_credits: number
  general_completed_credits: number
}> {
  const res = await apiFetch(`/api/v1/students/${studentId}/graduation-summary`)
  if (!res.ok) {
    throw new Error("학생 졸업 진단 요약 조회에 실패했습니다.")
  }
  return await res.json()
}

export async function getStudentCourseHistory(
  studentId: number
): Promise<{
  status: string
  data: Array<{
    history_id: number
    student_id: number
    course_id: number
    course_name: string
    course_code: string
    semester_taken: string
    grade: string
    earned_credit: number
    is_retake: boolean
    year?: string
    semester?: string
  }>
}> {
  const res = await apiFetch(`/api/v1/students/${studentId}/history`)
  if (!res.ok) {
    throw new Error("수강 이력 조회에 실패했습니다.")
  }
  return await res.json()
}

export async function updateStudentCourseHistory(
  historyId: number,
  semesterTaken?: string,
  grade?: string,
  courseName?: string,
  earnedCredit?: number,
  isRetake?: boolean,
  courseId?: number | string,
  courseType?: string
): Promise<{ status: string; message: string }> {
  const res = await apiFetch(`/api/v1/students/history/${historyId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      semester_taken: semesterTaken,
      grade: grade,
      course_name: courseName,
      earned_credit: earnedCredit,
      is_retake: isRetake,
      course_id: courseId,
      course_type: courseType,
    }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "수강 이력 수정에 실패했습니다.")
  }
  return await res.json()
}

export async function deleteStudentCourseHistory(
  historyId: number
): Promise<{ status: string; message: string }> {
  const res = await apiFetch(`/api/v1/students/history/${historyId}`, {
    method: "DELETE",
  })
  if (!res.ok) {
    throw new Error("수강 이력 삭제에 실패했습니다.")
  }
  return await res.json()
}

export async function getSemesterList(): Promise<string[]> {
  const res = await apiFetch("/api/v1/timetable/semesters")
  if (!res.ok) {
    throw new Error("학기 목록 조회에 실패했습니다.")
  }
  const data = await res.json()
  return data.semesters || []
}

export async function uploadTranscriptPDF(file: File): Promise<{
  success: boolean
  studentInfo: any
  courses: Array<{
    courseName: string
    courseCode: string
    courseType: string
    credits: number
    grade: string
    semester: string
    matchConfidence: string
    dbMatched: boolean
    dbName: string
  }>
  totalExtracted: number
  totalMatched: number
  message: string
}> {
  const formData = new FormData()
  formData.append("file", file)

  const token = typeof window !== "undefined" ? sessionStorage.getItem("token") : null
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${API_BASE_URL}/api/v1/transcript/upload`, {
    method: "POST",
    headers,
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || "PDF 업로드에 실패했습니다.")
  }
  return await res.json()
}

export async function confirmTranscriptCourses(
  courses: Array<{
    courseName: string
    courseCode: string
    courseType: string
    credits: number
    grade: string
    semester: string
  }>
): Promise<{ success: boolean; savedCount: number; skippedCount: number; totalCredits: number; message: string }> {
  const res = await apiFetch("/api/v1/transcript/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ courses }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || "과목 저장에 실패했습니다.")
  }
  return await res.json()
}
