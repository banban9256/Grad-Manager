import time
import requests
import pandas as pd

# =====================================
# 설정
# =====================================

YEAR = "2026"
SEMESTER = "2"

BASE_URL = "https://sugang.hs.ac.kr/course/comm/search"

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://sugang.hs.ac.kr/course/subject",
    "X-Requested-With": "XMLHttpRequest",
}

COOKIES = {
    "JSESSIONID": "MNoFZaoc2voCa1JvXhPN2ZAkrGxUA5jytmcNuRk0kKOuFcRpTzxWW80HMn9dXFu7.amV1c19kb21haW4vaHN1c3VnMDI=",
    "SCOUTER": "zm55ppltk1jf2"
}

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)

# =====================================
# 1. 학과 목록 가져오기
# =====================================

major_params = {
    "SHYR": YEAR,
    "SMST_GBCD": SEMESTER,
    "GBCD": "Major"
}

r = session.get(BASE_URL, params=major_params)

if r.status_code != 200:
    print("학과목록 조회 실패")
    exit()

major_json = r.json()

major_list = major_json.get("searchList", [])

print(f"학과 수 : {len(major_list)}")

# =====================================
# 2. 학과별 강의 수집
# =====================================

all_rows = []

for idx, major in enumerate(major_list, start=1):

    major_code = major["CODE"]
    major_name = major["NAME"]

    print(f"[{idx}/{len(major_list)}] {major_name}")

    params = {
        "SHYR": YEAR,
        "SMST_GBCD": SEMESTER,
        "GBCD": "Lecture",
        "MAJOR_CD": major_code,
        "ISU_GB": "",
        "HAKYUN": "",
        "NAME": "",
        "PROF": ""
    }

    try:

        res = session.get(BASE_URL, params=params)

        if res.status_code != 200:
            print("   실패")
            continue

        data = res.json()

        lectures = data.get("searchList", [])

        print(f"   {len(lectures)}개")

        for lec in lectures:

            all_rows.append({
                "학과코드": lec.get("MAJOR_CD"),
                "학과명": major_name,
                "과목코드": lec.get("CODE"),
                "과목명": lec.get("NAME"),
                "학년": lec.get("HAKYUN"),
                "이수구분": lec.get("ISU_GB"),
                "학년도": lec.get("SHYR"),
                "학기": lec.get("SMST_GBCD"),
            })

        time.sleep(0.1)

    except Exception as e:
        print(e)

# =====================================
# 3. 저장
# =====================================

df = pd.DataFrame(all_rows)

df.drop_duplicates(inplace=True)

print()
print("총 강의 수 :", len(df))

df.to_csv(
    "전체강의목록.csv",
    index=False,
    encoding="utf-8-sig"
)

print("저장 완료!")