"use client"

import { useState, useRef, useEffect } from "react"
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
}

export function ChatTab() {
  const { chat } = useGradData()
  const { chatSimSummary, recommendedCourses } = chat
  const [simLoading, setSimLoading] = useState(false)
  const [simDone, setSimDone] = useState(false)
  const [retakeCourse, setRetakeCourse] = useState<RecommendedCourse | null>(null)

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "ai",
      content: "안녕하세요! 원하는 수강 조건을 알려주세요. 예) “금요일 공강”, “전공 위주로”",
    },
  ])
  const [inputText, setInputText] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const runSimulation = () => {
    setSimLoading(true)
    setSimDone(false)
    setTimeout(() => {
      setSimLoading(false)
      setSimDone(true)
    }, 1000)
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim() || isLoading) return

    const userMsg: Message = {
      id: `msg-${Date.now()}-user`,
      role: "user",
      content: inputText,
    }

    setMessages((prev) => [...prev, userMsg])
    setInputText("")
    setIsLoading(true)

    try {
      const response = await sendChatMessage(userMsg.content)
      const aiMsg: Message = {
        id: `msg-${Date.now()}-ai`,
        role: "ai",
        content: response,
      }
      setMessages((prev) => [...prev, aiMsg])
      setSimDone(true)
    } catch (err) {
      const errMsg: Message = {
        id: `msg-${Date.now()}-err`,
        role: "ai",
        content: "분석을 처리하는 중 오류가 발생했습니다. 다시 시도해 주세요.",
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelect = (course: RecommendedCourse) => {
    if (course.retake) setRetakeCourse(course)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border bg-card px-4 py-4 shrink-0">
        <div className="mx-auto w-full max-w-4xl">
          <h1 className="flex items-center gap-2 text-lg font-bold text-foreground">
            <Sparkles className="h-5 w-5 text-primary" />
            AI 수강 추천
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">조건을 말씀하시면 시간표를 설계해 드립니다</p>
        </div>
      </div>

      {/* Chat scroll area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto bg-background">
        <div className="mx-auto w-full max-w-4xl space-y-4 px-4 py-4">
          {messages.map((msg) => (
            <ChatBubble key={msg.id} role={msg.role}>
              {msg.content}
            </ChatBubble>
          ))}

          {isLoading && (
            <div className="flex items-start gap-2.5">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="h-4 w-4 text-primary" />
              </span>
              <div className="flex items-center gap-2 max-w-[80%] rounded-2xl rounded-tl-sm bg-secondary px-4 py-3 text-sm text-muted-foreground shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>분석하는 중…</span>
              </div>
            </div>
          )}

          {/* Simulation summary card */}
          <div className="ml-9.5">
            {simLoading ? (
              <div className="flex items-center gap-3 rounded-2xl bg-card border border-border p-5 shadow-sm">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">시뮬레이션을 실행하는 중…</span>
              </div>
            ) : simDone ? (
              <div className="rounded-2xl border border-border bg-card p-4.5 shadow-sm">
                <div className="mb-3.5 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-[15px] font-bold text-foreground">
                    <CheckCircle2 className="h-4.5 w-4.5 text-primary" />
                    추천 시간표 시뮬레이션
                  </span>
                  <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-primary">
                    적합도 {chatSimSummary.avgMatch}%
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2.5">
                  <SummaryStat label="공강일" value={chatSimSummary.freeDay} />
                  <SummaryStat label="총 학점" value={`${chatSimSummary.totalCredits}학점`} />
                  <SummaryStat label="과목 수" value={`${chatSimSummary.courseCount}개`} />
                </div>
                <ul className="mt-4 space-y-2">
                  {chatSimSummary.reasons.map((r, i) => {
                    const Icon = reasonIconMap[r.icon] ?? Sparkles
                    return (
                      <li key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Icon className="h-4 w-4 text-primary" />
                        {r.text}
                      </li>
                    )
                  })}
                </ul>
              </div>
            ) : null}

            <button
              onClick={runSimulation}
              disabled={simLoading}
              className="mt-3.5 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-4 text-[17px] font-semibold text-white shadow-sm transition-colors hover:bg-primary-hover disabled:opacity-60 h-[56px]"
            >
              <Sparkles className="h-5 w-5" />
              AI 시뮬레이션 실행
            </button>
          </div>

          {/* Recommended course list */}
          {simDone && (
            <div className="ml-9.5 space-y-3">
              <p className="text-xs font-semibold text-muted-foreground">추천 과목 목록</p>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {recommendedCourses.map((course) => (
                  <button
                    key={course.id}
                    onClick={() => handleSelect(course)}
                    className="w-full rounded-2xl bg-card border border-border p-4 text-left shadow-sm transition-all hover:bg-secondary hover:border-transparent flex flex-col justify-between"
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
                        <p className="text-xs text-muted-foreground mt-1">
                          {course.professor} · {course.credit}학점 · {course.time}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="text-base font-bold text-primary">{course.match}%</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5">적합도</p>
                      </div>
                    </div>
                    <div className="mt-3.5 flex flex-wrap gap-1.5">
                      {course.tags.map((t) => (
                        <span
                          key={t}
                          className={`rounded px-2 py-0.5 text-[10px] font-bold ${tagStyle[t] ?? "bg-secondary text-muted-foreground"}`}
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input bar */}
      <form onSubmit={handleSendMessage} className="border-t border-border bg-card px-4 py-3.5 shrink-0">
        <div className="mx-auto w-full max-w-4xl flex items-center gap-2 rounded-full bg-secondary px-4.5 py-2.5">
          <input
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            placeholder="수강 조건을 입력하세요 (예: 금요일 공강)"
            aria-label="추천 조건 입력"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="flex h-8.5 w-8.5 items-center justify-center rounded-full bg-primary text-white transition-opacity disabled:opacity-50"
            aria-label="메시지 전송"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Retake warning modal (TDS Dialog Style) */}
      {retakeCourse ? (
        <div
          className="absolute inset-0 z-20 flex items-end md:items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setRetakeCourse(null)}
        >
          <div
            className="w-full max-w-md rounded-[2rem] bg-card p-6 shadow-xl border border-border"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
                <AlertTriangle className="h-6.5 w-6.5 text-destructive" />
              </span>
              <button
                onClick={() => setRetakeCourse(null)}
                aria-label="닫기"
                className="text-muted-foreground hover:text-foreground transition-colors"
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
                className="flex-1 rounded-2xl bg-secondary py-3.5 text-[15px] font-semibold text-secondary-foreground hover:opacity-90 h-[48px]"
              >
                취소
              </button>
              <button
                onClick={() => setRetakeCourse(null)}
                className="flex-1 rounded-2xl bg-destructive py-3.5 text-[15px] font-semibold text-white hover:opacity-90 h-[48px]"
              >
                이해했어요
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function ChatBubble({ role, children }: { role: "ai" | "user"; children: React.ReactNode }) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm font-medium">
          {children}
        </div>
      </div>
    )
  }
  return (
    <div className="flex items-start gap-2.5">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Sparkles className="h-4 w-4 text-primary" />
      </span>
      <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-secondary px-4 py-2.5 text-sm leading-relaxed text-foreground shadow-sm">
        {children}
      </div>
    </div>
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
