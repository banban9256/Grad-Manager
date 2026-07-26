import type {
  AiCourse,
  AiFilterChip,
  ChatSimSummary,
  CreditCategory,
  KeywordChip,
  NoticeItem,
  QuickMenu,
  RecommendedCourse,
  ScheduleBlock,
  ScheduleReason,
} from "@/data/types"

export type UserInfo = {
  name: string
  university: string
  department: string
  track: string
  studentId: string
  semester: string
  mileage: number
  overallProgress: number
  remainingCredits: number
  totalRequired: number
  earnedCredits: number
  completedCourses: string[]
  completedCoursesDetail?: Record<string, string>
}

export type PastelColor = {
  bg: string
  text: string
  bar: string
}

export type DigitalTwin = {
  name: string
  progress: number
  remainingCredits: number
  aiProbability: number
  expectedGraduation: string
  completedCourses: number
  majorCourses: number
  liberalCourses: number
  scenarioCount: number
  scenarioStatus: string
}

export type GradManagerData = {
  logout?: () => void
  refreshData?: () => Promise<void>
  addInterestKeyword?: (text: string) => Promise<void>
  removeInterestKeyword?: (text: string) => Promise<void>
  updateCompletedCourses?: (studentId: string, completedCourses: string[], targetSemester?: string) => Promise<{ success: boolean; completed_credits: number; completed_courses_count: number }>
  messages?: any[]
  setMessages?: React.Dispatch<React.SetStateAction<any[]>>
  simulatedSchedule?: any
  resetSimulation?: () => void
  allCourses?: any[]
  notifyEnabled?: boolean
  setNotifyEnabled?: React.Dispatch<React.SetStateAction<boolean>>
  selectedSemester?: string
  setSelectedSemester?: React.Dispatch<React.SetStateAction<string>>
  semesters?: string[]
  user: {
    userInfo: UserInfo
    creditCategories: CreditCategory[]
    quickMenus: QuickMenu[]
  }
  schedule: {
    scheduleDays: string[]
    scheduleHours: number[]
    scheduleBlocks: ScheduleBlock[]
    scheduleReasons: ScheduleReason[]
    pastelPalette: PastelColor[]
  }
  notice: {
    interestKeywords: KeywordChip[]
    urgentNotice: NoticeItem
    academicCalendar: NoticeItem[]
  }
  chat: {
    recommendedCourses: RecommendedCourse[]
    chatSimSummary: ChatSimSummary
  }
  digitalTwin: DigitalTwin
  aiRecommendation: {
    aiFilters: AiFilterChip[]
    aiCourses: AiCourse[]
  }
}

