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

// 시간표 파스텔 팔레트 (TDS Style)
export const pastelPalette = [
  { bg: "bg-[#e8f3ff] dark:bg-[#1b2d45]", text: "text-[#1b64da] dark:text-[#5592f2]", bar: "bg-[#3182f6]" }, // Toss Blue
  { bg: "bg-[#daf2ee] dark:bg-[#183531]", text: "text-[#008f80] dark:text-[#00caab]", bar: "bg-[#00b5a3]" }, // Toss Mint (Teal)
  { bg: "bg-[#fff3f5] dark:bg-[#381e25]", text: "text-[#d6284a] dark:text-[#ff6b8b]", bar: "bg-[#f25875]" }, // Toss Pink
  { bg: "bg-[#f7f4fd] dark:bg-[#2c1d3c]", text: "text-[#703bc9] dark:text-[#a880f7]", bar: "bg-[#8f5cf0]" }, // Toss Violet
  { bg: "bg-[#fff9e6] dark:bg-[#3d321d]", text: "text-[#b27600] dark:text-[#ffca57]", bar: "bg-[#ff9f1a]" }, // Toss Orange
]
