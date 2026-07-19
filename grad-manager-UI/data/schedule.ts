// 시간표 탭 — 시간표 블록 / 추천 이유 / 파스텔 팔레트 mock data
import type { ScheduleBlock, ScheduleReason } from "./types"

export const scheduleDays = ["월", "화", "수", "목", "금"]
// 09:00 ~ 17:00 (1시간 단위, 8칸)
export const scheduleHours = [9, 10, 11, 12, 13, 14, 15, 16]

export const scheduleBlocks: ScheduleBlock[] = [
  { id: "s1", name: "머신러닝", day: 0, start: 1, span: 2, room: "율곡관 302", colorIndex: 0 },
  { id: "s2", name: "머신러닝", day: 2, start: 0, span: 2, room: "율곡관 302", colorIndex: 0 },
  { id: "s3", name: "데이터베이스", day: 1, start: 4, span: 2, room: "만우관 111", colorIndex: 1 },
  { id: "s4", name: "데이터베이스", day: 3, start: 4, span: 2, room: "만우관 111", colorIndex: 1 },
  { id: "s5", name: "융합캡스톤", day: 3, start: 6, span: 2, room: "장공관 210", colorIndex: 2 },
  { id: "s6", name: "확률과 통계", day: 0, start: 4, span: 2, room: "필헌관 405", colorIndex: 3 },
  { id: "s7", name: "확률과 통계", day: 2, start: 4, span: 2, room: "필헌관 405", colorIndex: 3 },
]

export const scheduleReasons: ScheduleReason[] = [
  { icon: "CalendarOff", title: "금요일 공강 유지", desc: "요청하신 금요일 전면 공강을 확보했어요." },
  { icon: "BrainCircuit", title: "AI/데이터 관심분야 매칭", desc: "관심 키워드와 87% 이상 일치하는 과목 위주로 편성." },
  { icon: "GraduationCap", title: "졸업요건 충족", desc: "전공 6학점 + 특화 3학점으로 남은 요건을 반영." },
  { icon: "Clock", title: "1교시 최소화", desc: "오전 9시 수업을 주 1회로 줄였어요." },
]

// 시간표 파스텔 팔레트
export const pastelPalette = [
  { bg: "bg-blue-100", text: "text-blue-700", bar: "bg-blue-500" },
  { bg: "bg-emerald-100", text: "text-emerald-700", bar: "bg-emerald-500" },
  { bg: "bg-amber-100", text: "text-amber-700", bar: "bg-amber-500" },
  { bg: "bg-rose-100", text: "text-rose-700", bar: "bg-rose-500" },
  { bg: "bg-violet-100", text: "text-violet-700", bar: "bg-violet-500" },
]
