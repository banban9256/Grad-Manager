// AI 추천(챗봇) 탭 — 추천 과목 / 시뮬레이션 요약 mock data
import type { ChatSimSummary, RecommendedCourse } from "./types"

export const recommendedCourses: RecommendedCourse[] = [
  {
    id: "c1",
    name: "머신러닝",
    code: "AISW3021",
    credit: 3,
    match: 96,
    tags: ["필수", "관심사 매칭"],
    retake: false,
    professor: "이정민",
    time: "월 10:30 / 수 09:00",
  },
  {
    id: "c2",
    name: "데이터베이스 시스템",
    code: "AISW2044",
    credit: 3,
    match: 91,
    tags: ["필수", "특화전공 인정"],
    retake: false,
    professor: "박서준",
    time: "화 13:00 / 목 13:00",
  },
  {
    id: "c3",
    name: "빅데이터 융합캡스톤",
    code: "CONV3110",
    credit: 3,
    match: 88,
    tags: ["특화전공 인정", "관심사 매칭"],
    retake: false,
    professor: "최유나",
    time: "목 15:00",
  },
  {
    id: "c4",
    name: "확률과 통계",
    code: "MATH2010",
    credit: 3,
    match: 74,
    tags: ["관심사 매칭"],
    retake: true,
    professor: "정하늘",
    time: "월 13:00 / 수 13:00",
  },
]

export const chatSimSummary: ChatSimSummary = {
  freeDay: "금요일",
  totalCredits: 12,
  courseCount: 4,
  avgMatch: 89,
  reasons: [
    { icon: "CalendarOff", text: "금요일 공강 유지" },
    { icon: "BrainCircuit", text: "AI/데이터 관심분야 매칭" },
    { icon: "GraduationCap", text: "졸업요건(전공 6학점) 충족" },
  ],
}

// 챗봇 과목 태그 색상
export const chatTagStyle: Record<string, string> = {
  필수: "bg-primary/10 text-primary",
  "관심사 매칭": "bg-emerald-100 text-emerald-700",
  "특화전공 인정": "bg-amber-100 text-amber-700",
}
