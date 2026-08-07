// 알림 탭 — 관심 키워드 / 긴급 공지 / 학사 일정 mock data
import type { KeywordChip, NoticeItem } from "./types"

export const interestKeywords: KeywordChip[] = [
  { key: "special", label: "특화", urgent: true },
  { key: "scholarship", label: "장학금" },
  { key: "internship", label: "인턴십" },
  { key: "contest", label: "공모전" },
  { key: "capstone", label: "캡스톤" },
  { key: "exchange", label: "교환학생" },
]

export const urgentNotice: NoticeItem = {
  id: "n0",
  date: "D-2",
  title: "[특화전공] 융합트랙 신청 마감 임박",
  desc: "특화(융합)전공 이수 신청이 12월 19일 18시에 마감됩니다. 미신청 시 이번 학기 인정 불가.",
  type: "urgent",
  keyword: "특화",
}

export const academicCalendar: NoticeItem[] = [
  {
    id: "n1",
    date: "12월 20일",
    title: "기말 강의 평가 시작",
    desc: "미완료 시 성적 조회 불가. 전 과목 평가를 완료해 주세요.",
    type: "warning",
  },
  {
    id: "n2",
    date: "12월 23일",
    title: "겨울 계절학기 수강신청",
    desc: "재수강 및 학점 보충 대상자는 신청 기간을 확인하세요.",
    type: "info",
  },
  {
    id: "n3",
    date: "12월 26일",
    title: "기말고사 기간 종료",
    desc: "성적 입력 마감은 1월 3일까지입니다.",
    type: "info",
  },
  {
    id: "n4",
    date: "1월 6일",
    title: "성적 공시 및 이의신청",
    desc: "성적 확인 후 3일 이내 이의신청 가능합니다.",
    type: "info",
  },
]
