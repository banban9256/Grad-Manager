// Shared domain types for GradManager mock data

export type CreditCategory = {
  key: string
  label: string
  current: number
  required: number
  tone: string // tailwind chart token
}

export type QuickMenu = {
  key: string
  label: string
  icon: string // lucide icon name
}

export type CourseTag = "필수" | "관심사 매칭" | "특화전공 인정"

export type RecommendedCourse = {
  id: string
  name: string
  code: string
  credit: number
  match: number // 적합도 %
  tags: CourseTag[]
  retake: boolean
  professor: string
  time: string
}

export type ChatSimSummary = {
  freeDay: string
  totalCredits: number
  courseCount: number
  avgMatch: number
  reasons: { icon: string; text: string }[]
}

export type ScheduleBlock = {
  id: string
  name: string
  day: number // 0=월 ... 4=금
  start: number // 시작 교시 인덱스
  span: number
  room: string
  colorIndex: number
}

export type ScheduleReason = {
  icon: string
  title: string
  desc: string
}

export type KeywordChip = { key: string; label: string; urgent?: boolean }

export type NoticeItem = {
  id: string
  date: string
  title: string
  desc: string
  type: "urgent" | "warning" | "info"
  keyword?: string
}

export type AiFilterChip = { key: string; label: string; addOnly?: boolean }

export type AiCourseColor = "violet" | "pink" | "teal"

export type AiCourse = {
  id: string
  name: string
  code: string
  credit: number
  match: number
  tags: string[]
  reason: string
  color: AiCourseColor
}
