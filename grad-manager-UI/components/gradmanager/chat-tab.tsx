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
  필수: "bg-primary/10 text-primary",
  "관심사 매칭": "bg-emerald-100 text-emerald-700",
  "특화전공 인정": "bg-amber-100 text-amber-700",
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
      <div className="border-b border-border bg-card px-4 py-3">
        <div className="mx-auto w-full max-w-4xl">
          <h1 className="flex items-center gap-2 text-lg font-bold text-foreground">
            <Sparkles className="h-5 w-5 text-primary" />
            AI 수강 추천
          </h1>
          <p className="text-xs text-muted-foreground">조건을 말하면 시간표를 설계해 드려요</p>
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
            <div className="flex items-start gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="h-4 w-4 text-primary" />
              </span>
              <div className="flex items-center gap-2 max-w-[80%] rounded-2xl rounded-tl-sm bg-card px-4 py-2.5 text-sm text-muted-foreground shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span>분석하는 중…</span>
              </div>
            </div>
          )}

          {/* Simulation summary card */}
          <div className="ml-9">
            {simLoading ? (
              <div className="flex items-center gap-3 rounded-2xl bg-card p-5 shadow-sm">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">시뮬레이션을 실행하는 중…</span>
              </div>
            ) : simDone ? (
              <div className="rounded-2xl border border-primary/20 bg-card p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-sm font-bold text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                    추천 시간표 시뮬레이션
                  </span>
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                    적합도 {chatSimSummary.avgMatch}%
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <SummaryStat label="공강일" value={chatSimSummary.freeDay} />
                  <SummaryStat label="총 학점" value={`${chatSimSummary.totalCredits}학점`} />
                  <SummaryStat label="과목 수" value={`${chatSimSummary.courseCount}개`} />
                </div>
                <ul className="mt-3 space-y-1.5">
                  {chatSimSummary.reasons.map((r, i) => {
                    const Icon = reasonIconMap[r.icon] ?? Sparkles
                    return (
                      <li key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Icon className="h-3.5 w-3.5 text-primary" />
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
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3 text-sm font-semibold text-primary-foreground shadow-sm transition-opacity disabled:opacity-60"
            >
              <Sparkles className="h-4 w-4" />
              AI 시뮬레이션 실행
            </button>
          </div>

          {/* Recommended course list */}
          {simDone && (
            <div className="ml-9 space-y-2.5">
              <p className="text-xs font-semibold text-muted-foreground">추천 과목 목록</p>
              <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
                {recommendedCourses.map((course) => (
                  <button
                    key={course.id}
                    onClick={() => handleSelect(course)}
                    className="w-full rounded-2xl bg-card p-3.5 text-left shadow-sm transition-colors hover:bg-accent flex flex-col justify-between"
                  >
                    <div className="flex items-start justify-between gap-2 w-full">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm font-bold text-foreground">{course.name}</span>
                          {course.retake ? (
                            <span className="flex items-center gap-0.5 rounded-full bg-destructive/10 px-1.5 py-0.5 text-[10px] font-semibold text-destructive">
                              <RotateCcw className="h-3 w-3" />
                              재수강
                            </span>
                          ) : null}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {course.professor} · {course.credit}학점 · {course.time}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="text-base font-bold text-primary">{course.match}%</p>
                        <p className="text-[10px] text-muted-foreground">적합도</p>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {course.tags.map((t) => (
                        <span
                          key={t}
                          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${tagStyle[t] ?? "bg-muted text-muted-foreground"}`}
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
      <form onSubmit={handleSendMessage} className="border-t border-border bg-card px-4 py-3 shrink-0">
        <div className="mx-auto w-full max-w-4xl flex items-center gap-2 rounded-full bg-muted px-4 py-2.5">
          <input
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            placeholder="조건을 입력하세요…"
            aria-label="추천 조건 입력"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground transition-opacity disabled:opacity-50"
            aria-label="메시지 전송"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Retake warning modal */}
      {retakeCourse ? (
        <div
          className="absolute inset-0 z-20 flex items-end md:items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setRetakeCourse(null)}
        >
          <div
            className="w-full max-w-md rounded-3xl bg-card p-5 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-start justify-between">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-destructive/10">
                <AlertTriangle className="h-6 w-6 text-destructive" />
              </span>
              <button
                onClick={() => setRetakeCourse(null)}
                aria-label="닫기"
                className="text-muted-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <h3 className="text-base font-bold text-foreground">재수강 과목 선택 확인</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              <span className="font-semibold text-foreground">{retakeCourse.name}</span>은(는) 재수강
              과목입니다. 수강 시 <span className="font-semibold text-destructive">이전 학점은 포기
              처리됩니다.</span> 계속하시겠어요?
            </p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => setRetakeCourse(null)}
                className="flex-1 rounded-2xl bg-muted py-3 text-sm font-semibold text-secondary-foreground"
              >
                취소
              </button>
              <button
                onClick={() => setRetakeCourse(null)}
                className="flex-1 rounded-2xl bg-destructive py-3 text-sm font-semibold text-white"
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
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
          {children}
        </div>
      </div>
    )
  }
  return (
    <div className="flex items-start gap-2">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Sparkles className="h-4 w-4 text-primary" />
      </span>
      <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-card px-4 py-2.5 text-sm leading-relaxed text-foreground shadow-sm">
        {children}
      </div>
    </div>
  )
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted p-2.5 text-center">
      <p className="text-sm font-bold text-foreground">{value}</p>
      <p className="text-[10px] text-muted-foreground">{label}</p>
    </div>
  )
}
