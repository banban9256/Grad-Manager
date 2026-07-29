from fastapi import APIRouter, Header, HTTPException, Query
from typing import Optional, List, Any
from pydantic import BaseModel

from backend.core.data.students import get_student, save_student
from backend.core.data.csv_loader import load_courses
from backend.core.scheduler import generate_timetable

router = APIRouter()

def get_student_from_token(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="인증 토큰이 없습니다. 로그인 후 이용해주세요.")
    try:
        token = authorization.split(" ")[1]
        student_id = token.replace("mock-jwt-token-", "")
        student = get_student(student_id)
        if not student:
            raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        return student
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

@router.get("/recommend", summary="실제 조건부 시간표 추천 API")
def get_recommendations(authorization: Optional[str] = Header(None)):
    student = get_student_from_token(authorization)
    schedules = generate_timetable(student, max_schedules=1)
    
    schedule_blocks = []
    schedule_reasons = []
    
    pastel_palette = [
        {"bg": "bg-[#e8f3ff]", "text": "text-[#1b64da]", "bar": "bg-[#3182f6]"},
        {"bg": "bg-[#daf2ee]", "text": "text-[#008f80]", "bar": "bg-[#00b5a3]"},
        {"bg": "bg-[#fff3f5]", "text": "text-[#d6284a]", "bar": "bg-[#f04452]"},
        {"bg": "bg-[#f4edff]", "text": "text-[#6b31f6]", "bar": "bg-[#8f5cf0]"},
        {"bg": "bg-[#fffae8]", "text": "text-[#b08b00]", "bar": "bg-[#ffc900]"}
    ]
    
    day_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4}
    
    if schedules:
        sched = schedules[0]
        for idx, c in enumerate(sched["courses"]):
            color = pastel_palette[idx % len(pastel_palette)]
            for d, start, end in c.get("time_slots", []):
                if d in day_map:
                    try:
                        sh, sm = map(int, start.split(":"))
                        eh, em = map(int, end.split(":"))
                        start_h = sh + sm / 60
                        end_h = eh + em / 60
                        
                        schedule_blocks.append({
                          "id": f"block-{c['code']}-{d}-{start}-{end}",
                          "name": c["name"],
                          "professor": c["professor"],
                          "day": day_map[d],
                          "start": start_h,
                          "end": end_h,
                          "color": color["bg"],
                          "textColor": color["text"]
                        })
                    except Exception:
                        pass
                        
        schedule_reasons = [
            {"icon": "GraduationCap", "title": "미이수한 졸업 필수과목 자동 배정", "desc": "졸업 요건을 충족하기 위해 미이수 필수 과목을 자동으로 배정했습니다."},
            {"icon": "CalendarOff", "title": "선호 요일 최적 배정 완료", "desc": "사용자의 선호 요일을 반영하여 최적의 시간표를 구성했습니다."},
            {"icon": "Check", "title": "강의실 간 거리 제외", "desc": "사용자 요청에 따라 강의실 간 거리를 계산에서 배제하고 추천 과목들로만 배정했습니다."}
        ]

        # 각 과목별 상세 추천 사유 생성
        _TRACK_NAMES = {
            "AS001": "AI.SW개론", "AS002": "C언어", "AS003": "공학설계입문",
            "AS004": "AI·SW수학", "AS005": "문제해결형프로그래밍", "AS006": "웹프로그래밍",
            "AS007": "자료구조", "AS008": "자바프로그래밍", "AS009": "논리회로",
            "AS010": "데이터통신", "AS011": "운영체제", "AS012": "데이터베이스",
        }
        _TYPE_REASONS = {
            "전공필수": "졸업을 위한 전공 필수 과목으로, 반드시 이수해야 합니다.",
            "전공선택": "전공 역량을 강화하는 선택 과목으로, 관심 분야 심화에 적합합니다.",
            "교양필수": "졸업을 위한 교양 필수 과목으로, 기초 소양 함양에 필요합니다.",
            "교양선택": "학문적 시야를 넓히는 교양 선택 과목입니다.",
            "계열공통": "AISW 계열 공통 과목으로, 전공 기초 역량 강화에 필수적입니다.",
        }
        _TRACK_KEYWORDS = {
            "앰비언트": ["앰비언트", "IoT", "센서", "임베디드", "통신"],
            "데이터 사이언스": ["데이터", "분석", "통계", "머신러닝", "딥러닝"],
            "인지 감성": ["인지", "감성", "HCI", "심리", "UX"],
        }

        seen_course_codes = set()
        for c in sched.get("courses", []):
            code = c.get("code", "")
            if code in seen_course_codes:
                continue
            seen_course_codes.add(code)

            course_name = c.get("name", "")
            course_type = c.get("type", "")
            credits = c.get("credits", 3)

            reason_desc = ""
            if code in _TRACK_NAMES:
                reason_desc = f"계열 공통 과목({code})으로, AISW 전공 기초 역량을 갖추기 위한 필수 과목입니다."
            elif course_type in _TYPE_REASONS:
                reason_desc = _TYPE_REASONS[course_type]
            else:
                specialized_track = student.get("specialized_track", "")
                if specialized_track:
                    for track_name, keywords in _TRACK_KEYWORDS.items():
                        if track_name in specialized_track:
                            if any(kw in course_name for kw in keywords):
                                reason_desc = f"특화트랙({specialized_track}) 관련 과목으로, 트랙 전문성 강화에 기여합니다."
                                break
                if not reason_desc:
                    if credits >= 3:
                        reason_desc = f"{credits}학점 과목으로, 졸업 학점 요건 충족에 기여합니다."
                    else:
                        reason_desc = f"추가 역량 개발을 위한 과목입니다."

            schedule_reasons.append({
                "icon": "Sparkles",
                "title": f"{course_name} ({code})",
                "desc": reason_desc
            })
    else:
        schedule_reasons = [{"icon": "AlertTriangle", "title": "추천 시간표 없음", "desc": "추천 조건에 맞는 조합이 존재하지 않습니다."}]

    return {
        "scheduleDays": ["월", "화", "수", "목", "금"],
        "scheduleHours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "scheduleBlocks": schedule_blocks,
        "scheduleReasons": schedule_reasons,
        "pastelPalette": pastel_palette[:3]
    }

@router.get("/mock-courses", summary="실제 개설 과목 목록 반환 (검색 지원)")
def get_all_courses(
    q: Optional[str] = Query(None, description="과목명 또는 코드 검색"),
    semester: Optional[str] = Query(None, description="개설 학기 필터 (예: 2024-2학기)")
):
    courses_db = load_courses()
    data = []
    
    target_year = None
    target_sem = None
    if semester and "-" in semester:
        parts = semester.split("-", 1)
        target_year = parts[0]
        target_sem = parts[1]
    
    for code, info in courses_db.items():
        if q:
            if q.lower() not in info["name"].lower() and q.lower() not in code.lower():
                continue
                
        # semester 필터링: 해당 과목의 offerings 중 target_year와 target_sem에 매칭되는 것이 있는지 확인
        if target_year and target_sem:
            offerings = info.get("offerings", [])
            # 개설 정보(분반)가 등록되어 있는 과목의 경우에만 학기 필터를 엄격하게 적용
            if len(offerings) > 0:
                has_matching_offering = False
                for o in offerings:
                    if str(o.get("academic_year")) == target_year and o.get("semester") == target_sem:
                        has_matching_offering = True
                        break
                if not has_matching_offering:
                    continue

        # API 응답 포맷 맞춤
        schedules = []
        for o in info.get("offerings", []):
            if target_year and target_sem:
                # 개설 정보가 존재하는 경우, 해당 학기의 일정만 필터링하여 응답
                if str(o.get("academic_year")) != target_year or o.get("semester") != target_sem:
                    continue
            sec_val = o.get("section") or "01"
            prof_val = o.get("professor") or info.get("professor") or "미정"
            for d, start, end in o.get("time_slots", []):
                schedules.append({
                    "day": d,
                    "start_time": start,
                    "end_time": end,
                    "classroom": o.get("classrooms", ["미정"])[0] if o.get("classrooms") else "미정",
                    "section": sec_val,
                    "professor": prof_val
                })
                
        data.append({
            "offering_id": info.get("offerings", [{}])[0].get("offering_id", 0) if info.get("offerings") else 0,
            "course_id": code,
            "title": info["name"],
            "credit": float(info["credits"]),
            "category": info["category"],
            "program_type": "MAJOR" if "전공" in info["category"] else "LIBERAL",
            "professor": info.get("professor", "교수"),
            "schedules": schedules,
            "keywords": [info["category"], info.get("department", "AISW")]
        })
        
    return {
        "status": "success",
        "data": data  # 필터링된 결과 반환
    }

class ScheduleBlocksUpdateRequest(BaseModel):
    studentId: str
    semester: Optional[str] = None
    scheduleBlocks: List[Any]

@router.post("/schedule", summary="사용자 커스텀 시간표 블록 저장 API")
def save_user_schedule(req: ScheduleBlocksUpdateRequest):
    student = get_student(req.studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
    
    target_sem = req.semester or "2026-2학기"
    blocks_store = student.get("custom_schedule_blocks", {})
    if isinstance(blocks_store, list):
        blocks_store = {"2026-2학기": blocks_store}
        
    blocks_store[target_sem] = req.scheduleBlocks
    student["custom_schedule_blocks"] = blocks_store
    
    save_student(req.studentId, student)
    return {"success": True, "count": len(req.scheduleBlocks)}

@router.get("/schedule", summary="사용자 커스텀 시간표 블록 조회 API")
def get_user_schedule(studentId: str, semester: Optional[str] = Query(None)):
    student = get_student(studentId)
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        
    target_sem = semester or "2026-2학기"
    blocks_store = student.get("custom_schedule_blocks", {})
    if isinstance(blocks_store, list):
        if target_sem == "2026-2학기":
            blocks = blocks_store
        else:
            blocks = []
    else:
        blocks = blocks_store.get(target_sem, [])
        
    return {
        "success": True,
        "scheduleBlocks": blocks
    }

@router.get("/semesters", summary="전체 개설된 고유 학기 목록 조회 API")
def get_semesters():
    from backend.core.data.courses import get_all_semesters
    return {
        "status": "success",
        "semesters": get_all_semesters()
    }