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

// Authorization JWT token injector helper for API readiness
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("token") : null
  const headers = {
    ...options.headers,
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
  }
  return fetch(url, { ...options, headers })
}

export async function loginUser(studentId: string, password: string): Promise<{ token: string; user: UserInfo }> {
  const res = await apiFetch("/api/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId, password }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.error || "로그인에 실패했습니다.")
  }
  return await res.json()
}

export async function getGradData(): Promise<GradManagerData> {
  const res = await apiFetch("/api/grad-data")
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
  const res = await apiFetch("/api/user")
  if (!res.ok) {
    throw new Error("유저 정보를 불러오지 못했습니다.")
  }
  return await res.json()
}

export async function getRecommendations(): Promise<{
  scheduleDays: string[]
  scheduleHours: number[]
  scheduleBlocks: ScheduleBlock[]
  scheduleReasons: ScheduleReason[]
  pastelPalette: PastelColor[]
}> {
  const res = await apiFetch("/api/recommendations")
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
  const res = await apiFetch("/api/notice")
  if (!res.ok) {
    throw new Error("공지 데이터를 불러오지 못했습니다.")
  }
  return await res.json()
}

export async function getDigitalTwinData(): Promise<DigitalTwin> {
  const res = await apiFetch("/api/digital-twin")
  if (!res.ok) {
    throw new Error("디지털 트윈 데이터를 불러오지 못했습니다.")
  }
  return (await res.json()) as DigitalTwin
}

export async function getAiRecommendationData(): Promise<{
  aiFilters: AiFilterChip[]
  aiCourses: AiCourse[]
}> {
  const res = await apiFetch("/api/ai-recommendation")
  if (!res.ok) {
    throw new Error("AI 추천 데이터를 불러오지 못했습니다.")
  }
  return await res.json()
}

export async function sendChatMessage(message: string): Promise<string> {
  const res = await apiFetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) {
    throw new Error("메시지 전송에 실패했습니다.")
  }
  const data = await res.json()
  return data.message
}

export async function registerUser(
  studentId: string,
  password: string,
  name: string,
  department: string
): Promise<{ message: string }> {
  const res = await apiFetch("/api/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ studentId, password, name, department }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.error || "회원가입에 실패했습니다.")
  }
  return await res.json()
}

export async function updateProfile(
  name: string,
  studentId: string,
  department: string
): Promise<{ success: boolean }> {
  const res = await apiFetch("/api/user/profile", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, studentId, department }),
  })
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(errorData.error || "프로필 정보 수정에 실패했습니다.")
  }
  return await res.json()
}
