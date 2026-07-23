"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "motion/react"
import {
  AlertTriangle,
  BrainCircuit,
  CalendarOff,
  CheckCircle2,
  GraduationCap,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  X,
  type LucideIcon,
} from "lucide-react"
import type { RecommendedCourse } from "@/data/types"
import { useGradData } from "./grad-data-provider"
import { sendChatMessage } from "@/lib/api"

const reasonIconMap: Record<string, LucideIcon> = {
  CalendarOff,
  BrainCircuit,
  GraduationCap,
}

const tagStyle: Record<string, string> = {
  필수: "bg-[#e8f3ff] text-[#1b64da] dark:bg-[#1b2d45] dark:text-[#5592f2]",
  "관심사 매칭": "bg-[#daf2ee] text-[#008f80] dark:bg-[#183531] dark:text-[#00caab]",
  "특화전공 인정": "bg-[#fff3f5] text-[#d6284a] dark:bg-[#381e25] dark:text-[#ff6b8b]",
}

type Message = {
  id: string
  role: "ai" | "user"
  content: string
  displayedContent?: string
}

function TypewriterText({ text, onComplete }: { text: string; onComplete?: () => void }) {
  const [displayed, setDisplayed] = useState("")
  const indexRef = useRef(0)

  useEffect(() => {
    indexRef.current = 0
    setDisplayed("")

    const interval = setInterval(() => {
      if (indexRef.current < text.length) {
        setDisplayed(text.slice(0, indexRef.current + 1))
        indexRef.current++
      } else {
        clearInterval(interval)
        onComplete?.()
      }
    }, 18)

    return () => clearInterval(interval)
  }, [text, onComplete])

  return (
    <span>
      {displayed}
      {indexRef.current < text.length && (
        <span className="inline-block w-[2px] h-4 bg-primary/70 animate-pulse ml-0.5 align-text-bottom" />
      )}
    </span>
  )
}



const dayStringToNum = (dayVal: any): number => {
  if (typeof dayVal === "number") return dayVal
  if (typeof dayVal !== "string") return -1
  
  const clean = dayVal.trim().toUpperCase()
  const mapping: Record<string, number> = {
    "월": 0, "화": 1, "수": 2, "목": 3, "금": 4,
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4,
    "MONDAY": 0, "TUESDAY": 1, "WEDNESDAY": 2, "THURSDAY": 3, "FRIDAY": 4
  }
  return mapping[clean] !== undefined ? mapping[clean] : -1
}

export function ChatTab({ onOpenSchedule }: { onOpenSchedule?: () => void }) {
  const { chat, refreshData, schedule, messages = [], setMessages, simulatedSchedule } = useGradData()
  const { recommendedCourses } = chat

  const localSimData = simulatedSchedule
  const simDone = localSimData !== null
  const simLoading = false // Real-time calculation on client

  // 동적 통계 데이터 실시간 계산
  let freeDayText = "공강 없음"
  let courseCount = 0
  let totalCreditsText = "0"
  let displayReasons: any[] = []

  if (localSimData) {
    const blocks = localSimData.scheduleBlocks || []
    const days = localSimData.scheduleDays || ["월", "화", "수", "목", "금"]
    const actDays = new Set(blocks.map((b: any) => dayStringToNum(b.day)))
    const freeD = days.filter((_, idx) => !actDays.has(idx))
    freeDayText = freeD.length > 0 ? `${freeD.join(", ")} 공강` : "공강 없음"

    const uniqueC = Array.from(new Set(blocks.map((b: any) => b.name)))
    courseCount = uniqueC.length
    totalCreditsText = localSimData.totalCredits !== undefined ? String(localSimData.totalCredits) : String(courseCount * 3)
    displayReasons = localSimData.scheduleReasons || []
  } else {
    // 디폴트 밸런스 시간표 정보 적용
    const blocks = schedule?.scheduleBlocks || []
    const days = schedule?.scheduleDays || ["월", "화", "수", "목", "금"]
    const actDays = new Set(blocks.map((b: any) => dayStringToNum(b.day)))
    const freeD = days.filter((_, idx) => !actDays.has(idx))
    freeDayText = freeD.length > 0 ? `${freeD.join(", ")} 공강` : "공강 없음"

    const uniqueC = Array.from(new Set(blocks.map((b: any) => b.name)))
    courseCount = uniqueC.length
    totalCreditsText = String(courseCount * 3)
    displayReasons = schedule?.scheduleReasons || []
  }

  const [retakeCourse, setRetakeCourse] = useState<RecommendedCourse | null>(null)
  const [inputText, setInputText] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim() || isLoading) return

    const userMsg: Message = {
      id: `msg-${Date.now()}-user`,
      role: "user",
      content: inputText,
    }

    if (setMessages) {
      setMessages((prev) => [...prev, userMsg])
    }
    setInputText("")
    setIsLoading(true)

    try {
      const formattedHistory = messages
        .filter((m) => m.id !== "welcome")
        .map((m) => ({
          role: m.role === "user" ? ("user" as const) : ("assistant" as const),
          content: m.content,
        }))
      
      const chatResult = await sendChatMessage(userMsg.content, formattedHistory)
      
      const aiMsg: Message = {
        id: `msg-${Date.now()}-ai`,
        role: "ai",
        content: chatResult.message,
      }
      if (setMessages) {
        setMessages((prev) => [...prev, aiMsg])
      }
    } catch (err) {
      const errMsg: Message = {
        id: `msg-${Date.now()}-err`,
        role: "ai",
        content: "분석을 처리하는 중 오류가 발생했습니다. 다시 시도해 주세요.",
      }
      if (setMessages) {
        setMessages((prev) => [...prev, errMsg])
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelect = (course: RecommendedCourse) => {
    if (course.retake) setRetakeCourse(course)
  }

  const coursesToRender = localSimData && localSimData.courses ? localSimData.courses : recommendedCourses

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card px-4 py-4 shrink-0 shadow-sm">
        <div className="mx-auto w-full max-w-4xl">
          <h1 className="flex items-center gap-2 text-lg font-bold text-foreground">
            <Sparkles className="h-5 w-5 text-primary" />
            AI 수강 추천 &amp; 상담
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">조건을 말씀하시면 최적의 과목과 시간표를 추천해 드립니다</p>
        </div>
      </div>

      {/* Chat scroll area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto bg-[#f9fafb] dark:bg-[#0f151c] px-4 py-6">
        <div className="mx-auto w-full max-w-4xl space-y-6">
          <AnimatePresence>
            {messages.map((msg) => (
              <ChatBubble key={msg.id} role={msg.role}>
                {msg.content}
              </ChatBubble>
            ))}
          </AnimatePresence>

          {isLoading && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-2.5"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="h-4 w-4 text-primary" />
              </span>
              <div className="flex items-center gap-2 max-w-[80%] rounded-2xl rounded-tl-sm bg-card border border-border px-4 py-3 text-sm text-muted-foreground shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>답변을 생성하고 있어요…</span>
              </div>
            </motion.div>
          )}

          {/* Simulation summary card */}
          <div className="ml-9.5">
            <AnimatePresence mode="wait">
              {simLoading ? (
                <motion.div 
                  key="sim-loading"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex items-center gap-3 rounded-2xl bg-card border border-border p-5 shadow-sm"
                >
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">시뮬레이션을 실행하는 중…</span>
                </motion.div>
              ) : simDone ? (
                <motion.div 
                  key="sim-done"
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-2xl border border-border bg-card p-5 shadow-md shadow-primary/5 hover:shadow-lg transition-all duration-300"
                >
                  <div className="mb-4 flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-[15px] font-bold text-foreground">
                      <CheckCircle2 className="h-4.5 w-4.5 text-[#3182f6]" />
                      추천 시간표 시뮬레이션
                    </span>
                    <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                      적합도 {localSimData ? 100 : 95}%
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <SummaryStat label="공강일" value={freeDayText} />
                    <SummaryStat label="총 학점" value={`${totalCreditsText}학점`} />
                    <SummaryStat label="과목 수" value={`${courseCount}개`} />
                  </div>
                  <ul className="mt-4.5 space-y-2.5 border-t border-border pt-4">
                    {displayReasons.filter(r => r && r.title).map((r, i) => {
                      const Icon = reasonIconMap[r.icon] ?? Sparkles
                      return (
                        <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                          <Icon className="h-4 w-4 text-[#3182f6] shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold text-foreground mr-1">{r.title}:</span>
                            {r.desc}
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                </motion.div>
              ) : null}
            </AnimatePresence>

          </div>

          {/* Recommended course list */}
          {simDone && (
            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="ml-9.5 space-y-3"
            >
              <p className="text-xs font-semibold text-muted-foreground">추천 과목 목록</p>
              <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2">
                {coursesToRender.map((course) => (
                  <button
                    key={course.id}
                    onClick={() => handleSelect(course)}
                    className="w-full rounded-2xl bg-card border border-border p-4.5 text-left shadow-sm transition-all hover:bg-secondary hover:border-transparent hover:shadow-md flex flex-col justify-between cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-2.5 w-full">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-foreground truncate">{course.name}</span>
                          {course.retake ? (
                            <span className="flex items-center gap-0.5 rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] font-semibold text-destructive shrink-0">
                              <RotateCcw className="h-3 w-3" />
                              재수강
                            </span>
                          ) : null}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1.5">
                          {course.professor} · {course.credit}학점 · {course.time}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="text-base font-bold text-[#3182f6]">{course.match}%</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5">적합도</p>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {course.tags.map((t) => (
                        <span
                          key={t}
                          className={`rounded px-2.5 py-0.5 text-[10px] font-bold ${tagStyle[t] ?? "bg-secondary text-muted-foreground"}`}
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Input bar */}
      <form onSubmit={handleSendMessage} className="border-t border-border bg-card px-4 py-3.5 shrink-0 shadow-lg">
        <div className="mx-auto w-full max-w-4xl flex items-center gap-2 rounded-full bg-secondary px-4.5 py-2.5 border border-transparent focus-within:border-primary/25 transition-all">
          <input
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            placeholder="수강 조건을 입력하세요 (예: 금요일 공강 해줘, 전공 필수 추천)"
            aria-label="추천 조건 입력"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="flex h-8.5 w-8.5 items-center justify-center rounded-full bg-[#3182f6] text-white transition-opacity disabled:opacity-50 cursor-pointer"
            aria-label="메시지 전송"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Retake warning modal (TDS Dialog Style) */}
      <AnimatePresence>
        {retakeCourse && (
          <div
            className="absolute inset-0 z-30 flex items-end md:items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            onClick={() => setRetakeCourse(null)}
          >
            <motion.div
              initial={{ opacity: 0, y: 50, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.95 }}
              className="w-full max-w-md rounded-[2.5rem] bg-card p-6 shadow-xl border border-border"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-start justify-between">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
                  <AlertTriangle className="h-6.5 w-6.5 text-destructive" />
                </span>
                <button
                  onClick={() => setRetakeCourse(null)}
                  aria-label="닫기"
                  className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  <X className="h-5.5 w-5.5" />
                </button>
              </div>
              <h3 className="text-lg font-bold text-foreground">재수강 과목 선택 확인</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                <span className="font-bold text-foreground">{retakeCourse.name}</span>은(는) 재수강
                과목입니다. 수강 시 <span className="font-semibold text-destructive">이전 취득 학점은 포기
                처리됩니다.</span> 계속하시겠어요?
              </p>
              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => setRetakeCourse(null)}
                  className="flex-1 rounded-2xl bg-secondary py-3.5 text-[15px] font-semibold text-secondary-foreground hover:opacity-90 h-[48px] cursor-pointer"
                >
                  취소
                </button>
                <button
                  onClick={() => setRetakeCourse(null)}
                  className="flex-1 rounded-2xl bg-destructive py-3.5 text-[15px] font-semibold text-white hover:opacity-90 h-[48px] cursor-pointer"
                >
                  이해했어요
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

function ChatBubble({ role, children }: { role: "ai" | "user"; children: React.ReactNode }) {
  const isUser = role === "user"
  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} items-start gap-2.5`}
    >
      {!isUser && (
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="h-4 w-4 text-primary" />
        </span>
      )}
      <div 
        className={`max-w-[80%] rounded-2xl leading-relaxed shadow-sm px-4 py-3 text-sm font-medium ${
          isUser 
            ? "rounded-tr-sm bg-[#3182f6] text-white" 
            : "rounded-tl-sm bg-card border border-border text-foreground"
        }`}
      >
        {children}
      </div>
    </motion.div>
  )
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-secondary p-3 text-center border border-transparent">
      <p className="text-[15px] font-bold text-foreground">{value}</p>
      <p className="text-[10px] text-muted-foreground mt-0.5 font-semibold">{label}</p>
    </div>
  )
}
