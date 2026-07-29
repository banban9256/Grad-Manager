import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# =========================================================
# 1. 학과 코드 자동 추출
# =========================================================
select_html = """
<select name="sch_dept" id="sch_dept">
<option value="400000"># 교양과정  [400000]</option><option value="427100">AI·SW계열  [427100]</option><option value="427200">AI·SW학  [427200]</option><option value="427300">AI시스템반도체학  [427300]</option><option value="406150">AI융합시니어라이프케어  [406150]</option><option value="406140">AI융합장애인라이프케어  [406140]</option><option value="424120">IT경영학  [424120]</option><option value="411010">IT경영학과  [411010]</option><option value="419020">IT영상콘텐츠학과  [419020]</option><option value="416010">IT콘텐츠학과  [416010]</option><option value="422210">K-문화예술학  [422210]</option><option value="422110">K-문화예술학계열  [422110]</option><option value="427140">XR콘텐츠  [427140]</option><option value="404040">e-비즈니스학과  [404040]</option><option value="424100">경영·미디어계열  [424100]</option><option value="424200">경영계열  [424200]</option><option value="424110">경영학  [424110]</option><option value="404030">경영학과  [404030]</option><option value="423160">경제금융학  [423160]</option><option value="423300">경제통상·국제·공공인재융합계열  [423300]</option><option value="423100">경제통상·국제지역계열  [423100]</option><option value="423140">경제학  [423140]</option><option value="404010">경제학과  [404010]</option><option value="423220">공공인재빅데이터융합학  [423220]</option><option value="418010">공공인재학부  [418010]</option><option value="406120">공직역량개발PEPD  [406120]</option><option value="403041">광고홍보학과  [403041]</option><option value="402070">국사학과  [402070]</option><option value="402010">국어국문학과  [402010]</option><option value="423130">국제경제학  [423130]</option><option value="404020">국제경제학과  [404020]</option><option value="423170">국제관계학  [423170]</option><option value="418021">국제관계학  [418021]</option><option value="403950">국제관계학부  [403950]</option><option value="423200">글로벌·공공인재융합계열  [423200]</option><option value="424130">글로벌비즈니스학  [424130]</option><option value="403960">글로벌비즈니스학부  [403960]</option><option value="423400">글로벌융합계열  [423400]</option><option value="423000">글로벌융합대학  [423000]</option><option value="423210">글로벌인재학  [423210]</option><option value="418020">글로벌인재학부  [418020]</option><option value="427170">금융공학  [427170]</option><option value="401021">기독교교육학  [401021]</option><option value="401020">기독교교육학과  [401020]</option><option value="427130">데이터사이언스  [427130]</option><option value="402030">독어독문학과  [402030]</option><option value="402032">독어독문화학  [402032]</option><option value="402033">독어독문화학과  [402033]</option><option value="422140">독일어문화학  [422140]</option><option value="402962">독일어문화학과  [402962]</option><option value="402960">독일어문화학부  [402960]</option><option value="406030">동북아국제통상학  [406030]</option><option value="423150">동아시아통상학  [423150]</option><option value="402090">디지털문화콘텐츠  [402090]</option><option value="402095">디지털문화콘텐츠학  [402095]</option><option value="402094">디지털문화콘텐츠학과  [402094]</option><option value="422200">디지털영상문화콘텐츠학  [422200]</option><option value="402096">디지털영상문화콘텐츠학과  [402096]</option><option value="406090">마이크로전공  [406090]</option><option value="422160">문예창작학  [422160]</option><option value="402081">문예창작학과  [402081]</option><option value="422120">문화콘텐츠계열  [422120]</option><option value="424300">미디어계열  [424300]</option><option value="403970">미디어영상광고학부  [403970]</option><option value="424140">미디어영상광고홍보학  [424140]</option><option value="403980">미디어영상광고홍보학부  [403980]</option><option value="427180">빅데이터융합학  [427180]</option><option value="403021">사회복지학  [403021]</option><option value="403020">사회복지학과  [403020]</option><option value="425110">사회학  [425110]</option><option value="403011">사회학과  [403011]</option><option value="427110">소프트웨어  [427110]</option><option value="405971">소프트웨어융합학  [405971]</option><option value="405970">소프트웨어융합학부  [405970]</option><option value="426110">수리금융학  [426110]</option><option value="405011">수리금융학과  [405011]</option><option value="405010">수학과  [405010]</option><option value="401011">신학  [401011]</option><option value="422100">신학·인문융합계열  [422100]</option><option value="401010">신학과  [401010]</option><option value="401910">신학부  [401910]</option><option value="425140">심리·아동학  [425140]</option><option value="403990">심리·아동학부  [403990]</option><option value="422150">영미문화학  [422150]</option><option value="402021">영미문화학과  [402021]</option><option value="402100">영상문화학  [402100]</option><option value="402020">영어영문학과  [402020]</option><option value="426120">응용통계학  [426120]</option><option value="405021">응용통계학과  [405021]</option><option value="426100">이공계융합계열  [426100]</option><option value="427120">인공지능  [427120]</option><option value="402980">인문콘텐츠학부  [402980]</option><option value="403071">일본지역학과  [403071]</option><option value="423120">일본학  [423120]</option><option value="403072">일본학과  [403072]</option><option value="403992">임상심리  [403992]</option><option value="428100">자유전공학부  [428100]</option><option value="425130">재활상담학  [425130]</option><option value="403032">재활상담학과  [403032]</option><option value="403031">재활학  [403031]</option><option value="403030">재활학과  [403030]</option><option value="405020">정보통계학과  [405020]</option><option value="405960">정보통신학부  [405960]</option><option value="402060">종교문화학  [402060]</option><option value="402061">종교문화학과  [402061]</option><option value="419010">중국어문화영상융합학과  [419010]</option><option value="422190">중국어문화콘텐츠학  [422190]</option><option value="402043">중국어문화학과  [402043]</option><option value="402970">중국어문화학부  [402970]</option><option value="403061">중국지역학과  [403061]</option><option value="423110">중국학  [423110]</option><option value="403062">중국학과  [403062]</option><option value="427150">지능형IoT  [427150]</option><option value="402051">철학  [402051]</option><option value="402050">철학과  [402050]</option><option value="427400">첨단융합계열  [427400]</option><option value="405941">컴퓨터공학  [405941]</option><option value="405940">컴퓨터공학부  [405940]</option><option value="425210">특수체육학  [425210]</option><option value="425200">특수체육학계열  [425200]</option><option value="405061">특수체육학과  [405061]</option><option value="406100">평생교육학·HRD  [406100]</option><option value="409010">학점교류  [409010]</option><option value="422180">한국사학  [422180]</option><option value="402071">한국사학과  [402071]</option><option value="422170">한국어문학  [422170]</option><option value="406130">한류와아시아문화콘텐츠융합인재  [406130]</option><option value="402044">한중문화콘텐츠학과  [402044]</option><option value="402042">한중문화콘텐츠학과  [402042]</option><option value="427160">휴먼머신인터랙션  [427160]</option><option value="425100">휴먼서비스계열  [425100]</option><option value="427130 ">  [427130 ]</option>
</select>
"""

soup_select = BeautifulSoup(select_html, 'html.parser')
dept_codes = [option['value'] for option in soup_select.find_all('option') if option.get('value')]

print(f"총 {len(dept_codes)}개의 학과 코드를 자동으로 찾았습니다!")

# =========================================================
# 2. 크롤링 세팅
# =========================================================
url = "https://sugang.hs.ac.kr/course/subject/list"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # 전달해주신 최신 쿠키 적용
    "Cookie": "_ga=GA1.3.1430624782.1775003570; _ga_5JG97MV41D=GS2.1.s1779375030$o2$g0$t1779375030$j60$l0$h0; _ga_QCJX2CD1HH=GS2.3.s1780673940$o25$g0$t1780673940$j60$l0$h0; SCOUTER=zm55ppltk1jf2; JSESSIONID=aTb9H3Ni9dzjwrXw7bBet8F6YGmPaRpetcYvhCoQS6EAGDyYT5UDPhfJ3w36TUlN.amV1c19kb21haW4vaHN1c3VnMDI=; NetFunnel_ID=" 
}

all_course_list = []

# =========================================================
# 3. 학과별 데이터 무한 수집
# =========================================================
for dept in dept_codes:
    print(f"[{dept}] 학과 데이터 수집 중...")
    
    # 캡처본에 있는 Payload의 진짜 Key 이름들 적용!
    payload = {
        "SHYR": "2026",
        "SMST_GBCD": "2",
        "ESTB_SBJT_CD": dept,    # 학과코드 변수가 들어갈 자리
        "COPL_GBCD": "",
        "FRMN_ESTB_GRADE": "",
        "CHRG_PESN_NO": "",
        "COURSE_CD": "",
        "CATEGORY": "0",
        "SCH_WEEK": "",
        "SCH_TIME": "",
        "SCH_TEXT": ""
    }
    
    # 서버에 요청 보내기
    response = requests.post(url, data=payload, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.select('.table-type01 tbody tr')
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 11:
            # 텍스트 추출 후 저장
            all_course_list.append({
                '학과코드': dept,
                '이수구분': cols[2].text.strip(),
                '학수번호': cols[4].text.strip(),
                '교과목명': cols[5].text.strip(),
                '학점': cols[6].text.strip(),
                '교수명': cols[7].text.strip(),
                '강의시간': cols[8].text.strip(),
                '강의실': cols[9].text.strip(),
                '수강인원/정원': cols[10].text.strip()
            })
            
    # 서버 부하 방지를 위해 1초 휴식
    time.sleep(1)

# =========================================================
# 4. 결과 정리 및 CSV 저장
# =========================================================
if all_course_list:
    df = pd.DataFrame(all_course_list)
    
    # 활용성을 높이기 위해 '수강인원'과 '정원'을 별도의 칼럼으로 쪼개기
    try:
        df[['수강인원', '정원']] = df['수강인원/정원'].str.split('/', expand=True)
        df = df.drop(columns=['수강인원/정원'])
    except Exception as e:
        print("인원수 데이터 분리 중 예외 발생:", e)
        
    df.to_csv('26전체강의목록_업데이트.csv', index=False, encoding='utf-8-sig')
    print(f"성공! 총 {len(all_course_list)}개의 강의 데이터를 '26전체강의목록_업데이트.csv'로 저장했습니다.")
else:
    print("가져온 데이터가 없습니다. Session 만료, 또는 변수명 확인 요망.")