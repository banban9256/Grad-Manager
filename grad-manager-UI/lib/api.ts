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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

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
  history?: Array<{ role: "user" | "assistant"; content: string }>
): Promise<{ message: string; simulated_timetable?: any }> {
  const res = await apiFetch("/api/v1/chatbot/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, history }),
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

export async function searchCourseOfferings(query: string): Promise<any[]> {
  const res = await apiFetch(`/api/v1/timetable/mock-courses?q=${encodeURIComponent(query)}`)
  if (!res.ok) {
    throw new Error("과목 검색에 실패했습니다.")
  }
  const data = await res.json()
  return data.data || []
}

export async function updateCompletedCourses(
  studentId: string,
  completedCourses: string[]
): Promise<{ success: boolean; completed_credits: number; completed_courses_count: number }> {
  const res = await apiFetch("/api/v1/graduation/courses", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId, completedCourses }),
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
  mileage?: number
): Promise<{ success: boolean }> {
  const res = await apiFetch("/api/v1/auth/profile", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, studentId, department, mileage }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.detail || errorData.error || "프로필 수정에 실패했습니다.")
  }
  return await res.json()
}
