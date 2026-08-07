// 홈 탭 — 사용자 / 졸업요건 / 빠른 메뉴 mock data
import type { CreditCategory, QuickMenu } from "./types"

export const userInfo = {
  name: "김한신",
  university: "한신대학교",
  department: "AI.SW학과",
  track: "본전공 + 특화전공(융합)",
  studentId: "2022115xxx",
  semester: "3학년 2학기",
  mileage: 1280, // 누적 마일리지
  overallProgress: 72, // 총 졸업 진행률 (%)
  remainingCredits: 37, // 남은 이수 학점
  totalRequired: 132,
  earnedCredits: 95,
}

export const creditCategories: CreditCategory[] = [
  { key: "major", label: "전공", current: 48, required: 66, tone: "chart-1" },
  { key: "liberal", label: "교양", current: 30, required: 36, tone: "chart-2" },
  { key: "convergence", label: "특화(융합)", current: 17, required: 30, tone: "chart-3" },
]

export const quickMenus: QuickMenu[] = [
  { key: "recommend", label: "시간표 추천", icon: "Sparkles" },
  { key: "requirements", label: "졸업 요건", icon: "GraduationCap" },
  { key: "enroll", label: "수강신청", icon: "PencilLine" },
  { key: "grades", label: "성적 조회", icon: "BarChart3" },
  { key: "mileage", label: "마일리지", icon: "Trophy" },
  { key: "counsel", label: "학사 상담", icon: "MessageCircleQuestion" },
]
