import { http, HttpResponse, delay } from "msw"

let tempRegisteredUser: any = null
let tempProfileUser: any = null

async function fetchLocalJson() {
  const res = await fetch("/data/grad-manager.json")
  if (!res.ok) {
    throw new Error("Local JSON fetch failed")
  }
  const data = await res.json()
  if (tempProfileUser) {
    data.user.userInfo.name = tempProfileUser.name
    data.user.userInfo.studentId = tempProfileUser.studentId
    data.user.userInfo.department = tempProfileUser.department
  }
  return data
}

export const handlers = [
  http.get("/api/grad-data", async () => {
    await delay(1500)
    try {
      const data = await fetchLocalJson()
      return HttpResponse.json(data)
    } catch (err) {
      return HttpResponse.json({ error: "Failed to load data" }, { status: 500 })
    }
  }),

  http.get("/api/user", async () => {
    await delay(1500)
    try {
      const data = await fetchLocalJson()
      return HttpResponse.json(data.user)
    } catch (err) {
      return HttpResponse.json({ error: "Failed to load user info" }, { status: 500 })
    }
  }),

  http.get("/api/recommendations", async () => {
    await delay(1500)
    try {
      const data = await fetchLocalJson()
      return HttpResponse.json(data.schedule)
    } catch (err) {
      return HttpResponse.json({ error: "Failed to load schedule" }, { status: 500 })
    }
  }),

  http.get("/api/notice", async () => {
    await delay(1500)
    try {
      const data = await fetchLocalJson()
      return HttpResponse.json(data.notice)
    } catch (err) {
      return HttpResponse.json({ error: "Failed to load notices" }, { status: 500 })
    }
  }),

  http.get("/api/digital-twin", async () => {
    await delay(1500)
    try {
      const data = await fetchLocalJson()
      return HttpResponse.json(data.digitalTwin)
    } catch (err) {
      return HttpResponse.json({ error: "Failed to load digital twin" }, { status: 500 })
    }
  }),

  http.get("/api/ai-recommendation", async () => {
    await delay(1500)
    try {
      const data = await fetchLocalJson()
      return HttpResponse.json(data.aiRecommendation)
    } catch (err) {
      return HttpResponse.json({ error: "Failed to load ai recommendations" }, { status: 500 })
    }
  }),

  http.post("/api/chat", async () => {
    await delay(1500)
    return HttpResponse.json({
      message: "요청하신 조건에 맞춘 분석이 완료되었습니다. 추천 시간표를 확인해 보세요.",
    })
  }),

  http.post("/api/login", async ({ request }) => {
    await delay(1500)
    try {
      const body = (await request.json()) as any
      const { studentId, password } = body

      if (!studentId || !password) {
        return HttpResponse.json({ error: "학번과 비밀번호를 모두 입력해 주세요." }, { status: 400 })
      }

      const fullData = await fetchLocalJson()
      const userInfo = tempRegisteredUser && tempRegisteredUser.studentId === studentId
        ? {
            ...fullData.user.userInfo,
            name: tempRegisteredUser.name,
            department: tempRegisteredUser.department,
          }
        : fullData.user.userInfo

      return HttpResponse.json({
        token: "mock-jwt-token-12345",
        user: userInfo,
      })
    } catch (err) {
      return HttpResponse.json({ error: "로그인 처리 중 오류 발생" }, { status: 500 })
    }
  }),

  http.post("/api/register", async ({ request }) => {
    await delay(1500)
    try {
      const body = (await request.json()) as any
      const { studentId, password, name, department } = body

      if (!studentId || !password || !name || !department) {
        return HttpResponse.json({ error: "모든 필드를 입력해 주세요." }, { status: 400 })
      }

      tempRegisteredUser = { studentId, password, name, department }

      return HttpResponse.json({
        message: "회원가입이 정상적으로 완료되었습니다.",
      })
    } catch (err) {
      return HttpResponse.json({ error: "회원가입 처리 중 오류 발생" }, { status: 500 })
    }
  }),

  http.put("/api/user/profile", async ({ request }) => {
    await delay(1500)
    try {
      const body = (await request.json()) as any
      const { name, studentId, department } = body

      if (!name || !studentId || !department) {
        return HttpResponse.json({ error: "모든 필드를 입력해 주세요." }, { status: 400 })
      }

      tempProfileUser = { name, studentId, department }
      tempRegisteredUser = { ...tempRegisteredUser, name, studentId, department }

      return HttpResponse.json({ success: true })
    } catch (err) {
      return HttpResponse.json({ error: "프로필 수정 처리 실패" }, { status: 500 })
    }
  }),
]
