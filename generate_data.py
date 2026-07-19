# -*- coding: utf-8 -*-
"""
GradManager - DB 데이터 생성 스크립트
XML 시간표 파싱 + 학사일정 + 졸업요건 + programs CSV 생성
"""
import csv
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, date

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

NS = {"ns": "http://www.nexacroplatform.com/platform/dataset"}

# ============================================================
# 1. XML 시간표 데이터 파싱
# ============================================================

# 사용자가 제공한 XML 문자열 (26-1 개설강의 시간표)
XML_DATA = r'''<?xml version="1.0" encoding="UTF-8"?>
<Root xmlns="http://www.nexacroplatform.com/platform/dataset">
<Parameters>
<Parameter id="JSON_RETURN_MESSAGE" type="string">[{"RETURN_DATA":"{ ... }"}]</Parameter>
<Parameter id="ErrorCode" type="string">0</Parameter>
<Parameter id="ErrorMsg" type="string">정상적으로 처리되었습니다.</Parameter>
</Parameters>
<Dataset id="output1">
<ColumnInfo>
<Column id="ESTB_SBJT_CD" type="string" size="32"/>
<Column id="ESTB_SBJT_NM" type="string" size="32"/>
<Column id="SHYR" type="string" size="32"/>
<Column id="SMST_GBCD" type="string" size="32"/>
<Column id="COURSE_CD" type="string" size="32"/>
<Column id="COURSE_NM" type="string" size="32"/>
<Column id="CLAS" type="string" size="32"/>
<Column id="COPL_GBNM" type="string" size="32"/>
<Column id="LISTAGG_GRADE" type="string" size="32"/>
<Column id="PNT" type="string" size="32"/>
<Column id="LISTAGG_TEHIN" type="string" size="32"/>
<Column id="LISTAGG_ROOM" type="string" size="32"/>
<Column id="LISTAGG_PESN_GEND_NM" type="string" size="32"/>
<Column id="PESN_NO" type="string" size="32"/>
<Column id="INWON" type="string" size="32"/>
<Column id="NOTE" type="string" size="32"/>
<Column id="MMDIST_GBNM" type="string" size="32"/>
<Column id="PLAN_YN" type="bigdecimal" size="16"/>
<Column id="BUID_NM" type="string" size="32"/>
<Column id="CYBER_GBCD" type="string" size="32"/>
<Column id="NOW_DEPT_CD" type="string" size="32"/>
<Column id="NOW_DEPT_NM" type="string" size="32"/>
</ColumnInfo>
<Rows>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY042</Col><Col id="COURSE_NM">영화로배우는한국어와한국문화</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1, 2, 3, 4</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">금요일(16:00~17:15), 금요일(17:30~18:45)</Col><Col id="LISTAGG_ROOM">3308, 3308</Col><Col id="LISTAGG_PESN_GEND_NM">PANG LI</Col><Col id="PESN_NO">20120123</Col><Col id="INWON">8/15</Col><Col id="NOTE">외국인학생 전용강의 / 신설(2024.11.27)</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY043</Col><Col id="COURSE_NM">외국인을위한한국세계유산탐방</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">금요일(13:00~14:15), 금요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">3308, 3308</Col><Col id="LISTAGG_PESN_GEND_NM">PANG LI</Col><Col id="PESN_NO">20120123</Col><Col id="INWON">15/15</Col><Col id="NOTE">외국인학생 전용강의 / 신설(2024.11.27)</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY044</Col><Col id="COURSE_NM">응급처치와생존수영</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">2</Col><Col id="LISTAGG_TEHIN">화요일(13:00~14:40)</Col><Col id="LISTAGG_ROOM">10205</Col><Col id="LISTAGG_PESN_GEND_NM">정예수</Col><Col id="PESN_NO">20208014</Col><Col id="INWON">15/25</Col><Col id="NOTE">집중이수제과목 / 외국인학생 전용강의 / 신설(2024.11.27)</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY045</Col><Col id="COURSE_NM">고급심화한국어문법1</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1, 2, 3, 4</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">금요일(13:00~14:15), 금요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">3412, 3412</Col><Col id="LISTAGG_PESN_GEND_NM">김연숙</Col><Col id="PESN_NO">20250133</Col><Col id="INWON">15/15</Col><Col id="NOTE">외국인학생 전용 강의 / TOPIK 4급 읽기,문법,쓰기</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY046</Col><Col id="COURSE_NM">고급심화한국어회화1</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1, 2, 3, 4</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">월요일(13:00~14:15), 수요일(13:00~14:15)</Col><Col id="LISTAGG_ROOM">3408, 3408</Col><Col id="LISTAGG_PESN_GEND_NM">신남미</Col><Col id="PESN_NO">20250143</Col><Col id="INWON">18/18</Col><Col id="NOTE">외국인학생 전용강의 / TOPIK 4급 듣기, 말하기</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY130</Col><Col id="COURSE_NM">고급한국어회화2</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">월요일(14:30~15:45), 수요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">3408, 3408</Col><Col id="LISTAGG_PESN_GEND_NM">신남미</Col><Col id="PESN_NO">20250143</Col><Col id="INWON">15/15</Col><Col id="NOTE">외국인학생 전용강의 / TOPIK 4급 듣기, 말하기</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY133</Col><Col id="COURSE_NM">소통의기술</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">화요일(09:30~10:45), 목요일(11:00~12:15)</Col><Col id="LISTAGG_ROOM">3505, 3505</Col><Col id="LISTAGG_PESN_GEND_NM">정예수</Col><Col id="PESN_NO">20208014</Col><Col id="INWON">24/25</Col><Col id="NOTE">외국인학생 전용강의</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY134</Col><Col id="COURSE_NM">K-POP실습</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">월요일(11:00~12:15), 수요일(09:30~10:45)</Col><Col id="LISTAGG_ROOM">10203, 10203</Col><Col id="LISTAGG_PESN_GEND_NM">강형모</Col><Col id="PESN_NO">20230137</Col><Col id="INWON">14/15</Col><Col id="NOTE">외국인학생 전용강의</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">*KY142</Col><Col id="COURSE_NM">컴퓨터기초1</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1, 2, 3, 4</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">금요일(09:30~10:45), 금요일(11:00~12:15)</Col><Col id="LISTAGG_ROOM">20404, 20404</Col><Col id="LISTAGG_PESN_GEND_NM">김시윤</Col><Col id="PESN_NO">20260025</Col><Col id="INWON">25/25</Col><Col id="NOTE">외국인학생 전용강의/신설(25.11.27)</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY100</Col><Col id="COURSE_NM">채플</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1, 2</Col><Col id="PNT">(1)</Col><Col id="LISTAGG_TEHIN">월요일(17:30~18:20), 수요일(16:00~16:50)</Col><Col id="LISTAGG_ROOM">4105, 4105</Col><Col id="LISTAGG_PESN_GEND_NM">김광연, 나현기, 한경미</Col><Col id="PESN_NO">20240162</Col><Col id="INWON">5/100</Col><Col id="NOTE">~22학번 신학대학 2~4학년 복학생(대예배실에서 채플 진행)</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY101</Col><Col id="COURSE_NM">채플</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1, 2</Col><Col id="PNT">.5</Col><Col id="LISTAGG_TEHIN">월요일(14:30~15:20)</Col><Col id="LISTAGG_ROOM">채플실</Col><Col id="LISTAGG_PESN_GEND_NM">김광연, 나현기, 한경미</Col><Col id="PESN_NO">20240162</Col><Col id="INWON">578/580</Col><Col id="NOTE">첨단융합(수리,응통,금융공학,빅데이터융합),AI·SW계열(컴공, 소웨융, IT영상콘텐츠), AI시스템반도체</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY101</Col><Col id="COURSE_NM">채플</Col><Col id="CLAS">B</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1, 2</Col><Col id="PNT">.5</Col><Col id="LISTAGG_TEHIN">수요일(14:30~15:20)</Col><Col id="LISTAGG_ROOM">채플실</Col><Col id="LISTAGG_PESN_GEND_NM">김광연, 나현기, 한경미</Col><Col id="PESN_NO">20240162</Col><Col id="INWON">541/550</Col><Col id="NOTE">인문융합(한국어,종교,철학,문예,한국사),문화콘텐츠(독일어,영미,중문콘,디영문콘,일본),자유전공</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY201</Col><Col id="COURSE_NM">채플</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1, 2</Col><Col id="PNT">.5</Col><Col id="LISTAGG_TEHIN">월요일(16:00~16:50)</Col><Col id="LISTAGG_ROOM">채플실</Col><Col id="LISTAGG_PESN_GEND_NM">김광연, 나현기, 한경미</Col><Col id="PESN_NO">20240162</Col><Col id="INWON">577/580</Col><Col id="NOTE">경영계열(경영,IT경영,글비), 미디어계열(미영), 휴먼서비스계열(사회학과,사복,재활,심아), 특수체육학계열(특체)</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY201</Col><Col id="COURSE_NM">채플</Col><Col id="CLAS">B</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1, 2</Col><Col id="PNT">.5</Col><Col id="LISTAGG_TEHIN">수요일(16:00~16:50)</Col><Col id="LISTAGG_ROOM">채플실</Col><Col id="LISTAGG_PESN_GEND_NM">김광연, 나현기, 한경미</Col><Col id="PESN_NO">20240162</Col><Col id="INWON">577/580</Col><Col id="NOTE">글로벌융합(중국,동아시아,국경,경제,경제금융,국관,글인,공공인재)</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY217</Col><Col id="COURSE_NM">성서의세계</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">2, 3, 4</Col><Col id="PNT">2</Col><Col id="LISTAGG_TEHIN">화요일(17:30~19:10)</Col><Col id="LISTAGG_ROOM">18420</Col><Col id="LISTAGG_PESN_GEND_NM">이수연</Col><Col id="PESN_NO">20250019</Col><Col id="INWON">58/90</Col><Col id="NOTE">교필과목/2,3,4학년 성서관련 과목 미이수자</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY241</Col><Col id="COURSE_NM">노벨상으로보는과학의역사</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">화요일(13:00~14:15), 화요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">18418, 18418</Col><Col id="LISTAGG_PESN_GEND_NM">정태성</Col><Col id="PESN_NO">20080106</Col><Col id="INWON">49/50</Col><Col id="NOTE"></Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY245</Col><Col id="COURSE_NM">수재수학:수포자를위한재미있는수학</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">화요일(13:00~14:15), 화요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">18520, 18520</Col><Col id="LISTAGG_PESN_GEND_NM">나경욱</Col><Col id="PESN_NO">20080158</Col><Col id="INWON">47/50</Col><Col id="NOTE"></Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY286</Col><Col id="COURSE_NM">서양사의이해</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">금요일(13:00~14:15), 금요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">18211, 18211</Col><Col id="LISTAGG_PESN_GEND_NM">이시연</Col><Col id="PESN_NO">20250154</Col><Col id="INWON">44/90</Col><Col id="NOTE"></Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY304</Col><Col id="COURSE_NM">채플</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">2, 3, 4</Col><Col id="PNT">(1)</Col><Col id="LISTAGG_TEHIN">월요일(17:30~18:20)</Col><Col id="LISTAGG_ROOM">채플실</Col><Col id="LISTAGG_PESN_GEND_NM">김광연, 나현기, 한경미</Col><Col id="PESN_NO">20240162</Col><Col id="INWON">48/200</Col><Col id="NOTE">신학대학 2~4학년 수강(복수전공자 포함), P/NP</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY309</Col><Col id="COURSE_NM">생활속의실용금융</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">금요일(13:00~14:15), 금요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">18212, 18212</Col><Col id="LISTAGG_PESN_GEND_NM">장순택</Col><Col id="PESN_NO">20240159</Col><Col id="INWON">45/50</Col><Col id="NOTE">학생 전원 교재 지급</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY313</Col><Col id="COURSE_NM">기독교와문화</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">2</Col><Col id="LISTAGG_TEHIN">금요일(13:00~14:40)</Col><Col id="LISTAGG_ROOM">7215</Col><Col id="LISTAGG_PESN_GEND_NM">나현기</Col><Col id="PESN_NO">20180057</Col><Col id="INWON">85/90</Col><Col id="NOTE">교필과목/기독교과목</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY313</Col><Col id="COURSE_NM">기독교와문화</Col><Col id="CLAS">B</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">2</Col><Col id="LISTAGG_TEHIN">화요일(11:00~12:40)</Col><Col id="LISTAGG_ROOM">18420</Col><Col id="LISTAGG_PESN_GEND_NM">이수연</Col><Col id="PESN_NO">20250019</Col><Col id="INWON">90/90</Col><Col id="NOTE">교필과목/기독교과목</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY313</Col><Col id="COURSE_NM">기독교와문화</Col><Col id="CLAS">C</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">2</Col><Col id="LISTAGG_TEHIN">목요일(13:00~14:40)</Col><Col id="LISTAGG_ROOM">18420</Col><Col id="LISTAGG_PESN_GEND_NM">진형섭</Col><Col id="PESN_NO">20209150</Col><Col id="INWON">90/90</Col><Col id="NOTE">교필과목/기독교과목</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY313</Col><Col id="COURSE_NM">기독교와문화</Col><Col id="CLAS">D</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">2</Col><Col id="LISTAGG_TEHIN">수요일(11:00~12:40)</Col><Col id="LISTAGG_ROOM">18420</Col><Col id="LISTAGG_PESN_GEND_NM">진형섭</Col><Col id="PESN_NO">20209150</Col><Col id="INWON">90/90</Col><Col id="NOTE">교필과목/기독교과목</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY313</Col><Col id="COURSE_NM">기독교와문화</Col><Col id="CLAS">E</Col><Col id="COPL_GBNM">교양필수</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">2</Col><Col id="LISTAGG_TEHIN">금요일(17:30~19:10)</Col><Col id="LISTAGG_ROOM">7215</Col><Col id="LISTAGG_PESN_GEND_NM">나현기</Col><Col id="PESN_NO">20180057</Col><Col id="INWON">35/80</Col><Col id="NOTE">교필과목/기독교과목</Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY419</Col><Col id="COURSE_NM">현대사회와복지</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">화요일(11:00~12:15), 목요일(09:30~10:45)</Col><Col id="LISTAGG_ROOM">18519, 18519</Col><Col id="LISTAGG_PESN_GEND_NM">주경희</Col><Col id="PESN_NO">20180047</Col><Col id="INWON">45/90</Col><Col id="NOTE"></Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY471</Col><Col id="COURSE_NM">논리와비판적사고</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">화요일(09:30~10:45), 목요일(11:00~12:15)</Col><Col id="LISTAGG_ROOM">18212, 18212</Col><Col id="LISTAGG_PESN_GEND_NM">조현진</Col><Col id="PESN_NO">20250167</Col><Col id="INWON">27/80</Col><Col id="NOTE"></Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
<Row><Col id="ESTB_SBJT_CD">400000</Col><Col id="ESTB_SBJT_NM">교양과정</Col><Col id="SHYR">2026</Col><Col id="SMST_GBCD">1</Col><Col id="COURSE_CD">KY472</Col><Col id="COURSE_NM">생활법률</Col><Col id="CLAS">A</Col><Col id="COPL_GBNM">교양선택</Col><Col id="LISTAGG_GRADE">1</Col><Col id="PNT">3</Col><Col id="LISTAGG_TEHIN">화요일(13:00~14:15), 화요일(14:30~15:45)</Col><Col id="LISTAGG_ROOM">18211, 18211</Col><Col id="LISTAGG_PESN_GEND_NM">유영국</Col><Col id="PESN_NO">20240072</Col><Col id="INWON">90/90</Col><Col id="NOTE"></Col><Col id="MMDIST_GBNM"></Col><Col id="PLAN_YN">1</Col><Col id="BUID_NM"></Col><Col id="CYBER_GBCD">대면</Col><Col id="NOW_DEPT_CD"></Col><Col id="NOW_DEPT_NM"></Col></Row>
</Rows>
</Dataset>
</Root>'''


def parse_credit(raw: str) -> float:
    """Parse credit like '(1)', '.5', '3' to float."""
    raw = raw.strip().strip("()")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def parse_time_range(time_str: str):
    """Parse '금요일(16:00~17:15)' into (day_kr, start, end)."""
    m = re.match(r"(\S+요일)\((\d{2}:\d{2})~(\d{2}:\d{2})\)", time_str.strip())
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None, None, None


DAY_MAP = {
    "월요일": "월",
    "화요일": "화",
    "수요일": "수",
    "목요일": "목",
    "금요일": "금",
    "토요일": "토",
}


def parse_schedule(raw: str):
    """Parse LISTAGG_TEHIN into list of (day, start, end)."""
    entries = []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for part in parts:
        day, start, end = parse_time_range(part)
        if day:
            entries.append((DAY_MAP.get(day, day), start, end))
    return entries


def parse_rooms(raw: str):
    return [r.strip() for r in raw.split(",") if r.strip()]


def parse_grades(raw: str):
    """Parse '1, 2, 3, 4' -> '1,2,3,4'"""
    return ",".join(g.strip() for g in raw.split(",") if g.strip())


# ============================================================
# Step 1: Parse XML → rows
# ============================================================

root = ET.fromstring(XML_DATA)
dataset = root.find("ns:Dataset[@id='output1']", NS)
rows_data = []
for row_el in dataset.find("ns:Rows", NS).findall("ns:Row", NS):
    cols = {}
    for col_el in row_el.findall("ns:Col", NS):
        cols[col_el.get("id")] = (col_el.text or "").strip()
    rows_data.append(cols)

print(f"Parsed {len(rows_data)} rows from XML.")

# ============================================================
# Step 2: Build courses, course_offerings, course_schedules
# ============================================================

courses_map = {}  # course_code -> {course_id, ...}
offerings = []
schedules = []
course_id_counter = 1
offering_id_counter = 1

for rd in rows_data:
    code = rd.get("COURSE_CD", "")
    name = rd.get("COURSE_NM", "")
    credit = parse_credit(rd.get("PNT", "0"))
    category = rd.get("COPL_GBNM", "")
    section = rd.get("CLAS", "")
    professor = rd.get("LISTAGG_PESN_GEND_NM", "")
    schedule_raw = rd.get("LISTAGG_TEHIN", "")
    rooms_raw = rd.get("LISTAGG_ROOM", "")
    note = rd.get("NOTE", "")
    dept_name = rd.get("ESTB_SBJT_NM", "")
    capacity_raw = rd.get("INWON", "")
    cyber = rd.get("CYBER_GBCD", "")

    # courses table
    if code not in courses_map:
        courses_map[code] = {
            "course_id": course_id_counter,
            "course_code": code,
            "course_name": name,
            "credit": credit,
            "description": note,
            "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
        }
        course_id_counter += 1

    cid = courses_map[code]["course_id"]

    # course_offerings
    offering_id = offering_id_counter
    offering_id_counter += 1
    offerings.append({
        "offering_id": offering_id,
        "course_id": cid,
        "academic_year": 2026,
        "semester": "1",
        "section": section,
        "professor_name": professor,
        "syllabus_url": "",
    })

    # course_schedules
    sched_entries = parse_schedule(schedule_raw)
    room_entries = parse_rooms(rooms_raw)
    for i, (day, start, end) in enumerate(sched_entries):
        room = room_entries[i] if i < len(room_entries) else ""
        schedules.append({
            "schedule_id": len(schedules) + 1,
            "offering_id": offering_id,
            "day_of_week": day,
            "start_time": f"{start}:00",
            "end_time": f"{end}:00",
            "classroom": room,
        })


# ============================================================
# Step 3: Write CSV files
# ============================================================

def write_csv(filename, fieldnames, rows):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written: {filename} ({len(rows)} rows)")


# 3-1. courses.csv
write_csv("courses.csv", [
    "course_id", "course_code", "course_name", "credit",
    "theory_hours", "practice_hours", "course_description", "source_url"
], [
    {
        "course_id": c["course_id"],
        "course_code": c["course_code"],
        "course_name": c["course_name"],
        "credit": c["credit"],
        "theory_hours": "",
        "practice_hours": "",
        "course_description": c["description"],
        "source_url": c["source_url"],
    } for c in courses_map.values()
])

# 3-2. course_offerings.csv
write_csv("course_offerings.csv", [
    "offering_id", "course_id", "academic_year", "semester",
    "section", "professor_name", "syllabus_url"
], offerings)

# 3-3. course_schedules.csv
write_csv("course_schedules.csv", [
    "schedule_id", "offering_id", "day_of_week", "start_time",
    "end_time", "classroom"
], schedules)


# ============================================================
# Step 4: Programs (전공과정)
# ============================================================

# AISW 관련 전공 + 특화전공 + 융합전공
programs = [
    {
        "program_id": 1,
        "program_name": "AI·SW학 전공",
        "program_type": "MAJOR",
        "required_credits": 36,
        "effective_from_year": 2023,
        "effective_to_year": None,
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "program_id": 2,
        "program_name": "컴퓨터공학부",
        "program_type": "MAJOR",
        "required_credits": 36,
        "effective_from_year": 2023,
        "effective_to_year": None,
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "program_id": 3,
        "program_name": "소프트웨어융합학부",
        "program_type": "MAJOR",
        "required_credits": 36,
        "effective_from_year": 2023,
        "effective_to_year": None,
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "program_id": 4,
        "program_name": "IT영상콘텐츠학과",
        "program_type": "MAJOR",
        "required_credits": 36,
        "effective_from_year": 2023,
        "effective_to_year": None,
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    # 특화전공
    {
        "program_id": 5,
        "program_name": "인지감성컴퓨팅 특화전공",
        "program_type": "SPECIALIZED",
        "required_credits": 21,
        "effective_from_year": 2025,
        "effective_to_year": None,
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "program_id": 6,
        "program_name": "앰비언트컴퓨팅 특화전공",
        "program_type": "SPECIALIZED",
        "required_credits": 21,
        "effective_from_year": 2025,
        "effective_to_year": None,
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    # 융합전공 (참여학과 기반)
    {
        "program_id": 7,
        "program_name": "AI SW 융합 전공",
        "program_type": "CONVERGENCE",
        "required_credits": 21,
        "effective_from_year": 2023,
        "effective_to_year": None,
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
]

write_csv("programs.csv", [
    "program_id", "program_name", "program_type", "required_credits",
    "effective_from_year", "effective_to_year", "source_url"
], programs)


# ============================================================
# Step 5: Graduation Requirements
# ============================================================

grad_requirements = [
    {
        "requirement_id": 1,
        "admission_year": 2023,
        "program_id": None,
        "requirement_category": "총 이수학점",
        "required_credits": 130,
        "requirement_text": "교양+계열공통+전공+타전공 합계 130학점 이상",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 2,
        "admission_year": 2023,
        "program_id": None,
        "requirement_category": "교양 최소학점",
        "required_credits": 35,
        "requirement_text": "교양 최소 35학점 이상 이수 필요. 미충족 시 졸업 불가",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 3,
        "admission_year": 2023,
        "program_id": None,
        "requirement_category": "교양 최대학점(인정한도)",
        "required_credits": 45,
        "requirement_text": "교양 최대 45학점까지 인정. 초과 시 교양 외 과목에서 학점 추가 필요",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 4,
        "admission_year": 2023,
        "program_id": None,
        "requirement_category": "계열공통",
        "required_credits": 36,
        "requirement_text": "AI SW 계열공통 36학점 이수 필요",
        "source_url": "https://hsctis.hs.ac.kr/commons/file/view/UG_GRDTH/files/dcd1b2a9-04e8-4ced-86bc-13c6c9bd4f47.pdf",
    },
    {
        "requirement_id": 5,
        "admission_year": 2023,
        "program_id": 1,
        "requirement_category": "전공(전공필수+전공선택)",
        "required_credits": 24,
        "requirement_text": "AI·SW학 전공 전필+전선 합계 최소 24학점 이상",
        "source_url": "https://hsctis.hs.ac.kr/commons/file/view/UG_GRDTH/files/dcd1b2a9-04e8-4ced-86bc-13c6c9bd4f47.pdf",
    },
    {
        "requirement_id": 6,
        "admission_year": 2023,
        "program_id": 5,
        "requirement_category": "특화전공",
        "required_credits": 21,
        "requirement_text": "인지감성컴퓨팅 특화전공: 전필 9학점 + 전선 12학점 = 21학점 이상",
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "requirement_id": 7,
        "admission_year": 2023,
        "program_id": 6,
        "requirement_category": "특화전공",
        "required_credits": 21,
        "requirement_text": "앰비언트컴퓨팅 특화전공: 전필 9학점 + 전선 12학점 = 21학점 이상",
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "requirement_id": 8,
        "admission_year": 2023,
        "program_id": None,
        "requirement_category": "기독교 관련 교양필수",
        "required_credits": None,
        "requirement_text": "기독교와문화(A) 또는 성서의세계(A) 1과목 이상 이수 필수",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 9,
        "admission_year": 2023,
        "program_id": None,
        "requirement_category": "채플",
        "required_credits": None,
        "requirement_text": "채플 매 �기 0.5학점(또는 1학점) 이수. 총 8학기 이상 수강",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 10,
        "admission_year": 2023,
        "program_id": None,
        "requirement_category": "타전공",
        "required_credits": None,
        "requirement_text": "타전공 이수는 필수사항이 아니나, 이수 시 추가 학점 인정 가능",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 11,
        "admission_year": 2024,
        "program_id": None,
        "requirement_category": "총 이수학점",
        "required_credits": 130,
        "requirement_text": "교양+계열공통+전공+타전공 합계 130학점 이상",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 12,
        "admission_year": 2024,
        "program_id": None,
        "requirement_category": "교양 최소학점",
        "required_credits": 35,
        "requirement_text": "교양 최소 35학점 이상 이수 필요. 미충족 시 졸업 불가",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 13,
        "admission_year": 2024,
        "program_id": None,
        "requirement_category": "교양 최대학점(인정한도)",
        "required_credits": 45,
        "requirement_text": "교양 최대 45학점까지 인정. 초과 시 교양 외 과목에서 학점 추가 필요",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 14,
        "admission_year": 2024,
        "program_id": None,
        "requirement_category": "계열공통",
        "required_credits": 36,
        "requirement_text": "AI SW 계열공통 36학점 이수 필요",
        "source_url": "https://hsctis.hs.ac.kr/commons/file/view/UG_GRDTH/files/dcd1b2a9-04e8-4ced-86bc-13c6c9bd4f47.pdf",
    },
    {
        "requirement_id": 15,
        "admission_year": 2024,
        "program_id": 1,
        "requirement_category": "전공(전공필수+전공선택)",
        "required_credits": 24,
        "requirement_text": "AI·SW학 전공 전필+전선 합계 최소 24학점 이상",
        "source_url": "https://hsctis.hs.ac.kr/commons/file/view/UG_GRDTH/files/dcd1b2a9-04e8-4ced-86bc-13c6c9bd4f47.pdf",
    },
    {
        "requirement_id": 16,
        "admission_year": 2024,
        "program_id": 5,
        "requirement_category": "특화전공",
        "required_credits": 21,
        "requirement_text": "인지감성컴퓨팅 특화전공: 전필 9학점 + 전선 12학점 = 21학점 이상",
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "requirement_id": 17,
        "admission_year": 2024,
        "program_id": 6,
        "requirement_category": "특화전공",
        "required_credits": 21,
        "requirement_text": "앰비언트컴퓨팅 특화전공: 전필 9학점 + 전선 12학점 = 21학점 이상",
        "source_url": "https://swuniv.hs.ac.kr/02/02.php",
    },
    {
        "requirement_id": 18,
        "admission_year": 2024,
        "program_id": None,
        "requirement_category": "기독교 관련 교양필수",
        "required_credits": None,
        "requirement_text": "기독교와문화(A) 또는 성서의세계(A) 1과목 이상 이수 필수",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 19,
        "admission_year": 2024,
        "program_id": None,
        "requirement_category": "채플",
        "required_credits": None,
        "requirement_text": "채플 매 �기 0.5학점(또는 1학점) 이수. 총 8학기 이상 수강",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
    {
        "requirement_id": 20,
        "admission_year": 2024,
        "program_id": None,
        "requirement_category": "타전공",
        "required_credits": None,
        "requirement_text": "타전공 이수는 필수사항이 아니나, 이수 시 추가 학점 인정 가능",
        "source_url": "https://www.hs.ac.kr/kor/4935/subview.do",
    },
]

write_csv("graduation_requirements.csv", [
    "requirement_id", "admission_year", "program_id",
    "requirement_category", "required_credits", "requirement_text", "source_url"
], grad_requirements)


# ============================================================
# Step 6: Academic Events (학사일정)
# ============================================================

academic_events = [
    {
        "event_id": 1, "academic_year": 2026, "semester": "2",
        "event_name": "2026-2학기 수강신청",
        "event_type": "COURSE_REGISTRATION",
        "start_date": "2026-08-04", "end_date": "2026-08-08",
        "is_mandatory": True,
        "description": "2026학년도 2학기 수강신청 기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 2, "academic_year": 2026, "semester": "2",
        "event_name": "2026-2학기 수강신청 변경기간",
        "event_type": "COURSE_REGISTRATION",
        "start_date": "2026-08-25", "end_date": "2026-08-27",
        "is_mandatory": False,
        "description": "수강신청 정정기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 3, "academic_year": 2026, "semester": "2",
        "event_name": "2026-2학기 등록금 납부",
        "event_type": "TUITION_PAYMENT",
        "start_date": "2026-08-11", "end_date": "2026-08-13",
        "is_mandatory": True,
        "description": "2026학년도 2학기 등록금 납부 기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 4, "academic_year": 2026, "semester": "1",
        "event_name": "2026-1학기 기말 강의평가",
        "event_type": "FINAL_COURSE_EVALUATION",
        "start_date": "2026-06-02", "end_date": "2026-06-12",
        "is_mandatory": True,
        "description": "기말 강의평가 기간. 미이수 시 성적 열람 불가",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 5, "academic_year": 2026, "semester": "1",
        "event_name": "2026-1학기 기말고사",
        "event_type": "EXAM",
        "start_date": "2026-06-16", "end_date": "2026-06-22",
        "is_mandatory": True,
        "description": "기말고사 기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 6, "academic_year": 2026, "semester": "1",
        "event_name": "2026-1학기 성적조회",
        "event_type": "GRADE_INQUIRY",
        "start_date": "2026-06-30", "end_date": "2026-07-03",
        "is_mandatory": True,
        "description": "1학기 성적 조회 기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 7, "academic_year": 2026, "semester": "1",
        "event_name": "2026-1학기 성적정정",
        "event_type": "GRADE_INQUIRY",
        "start_date": "2026-07-03", "end_date": "2026-07-04",
        "is_mandatory": False,
        "description": "성적 정정 신청 기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 8, "academic_year": 2026, "semester": "",
        "event_name": "2026-2학기 융합/특화전공 신청",
        "event_type": "PRE_REGISTRATION",
        "start_date": "2026-07-14", "end_date": "2026-07-25",
        "is_mandatory": False,
        "description": "2026-2학기 융합/특화전공 신청 안내",
        "source_url": "https://swuniv.hs.ac.kr/07_01",
    },
    {
        "event_id": 9, "academic_year": 2026, "semester": "1",
        "event_name": "2026-1학기 휴학신청",
        "event_type": "ADMINISTRATIVE",
        "start_date": "2026-03-02", "end_date": "2026-03-13",
        "is_mandatory": False,
        "description": "휴학신청 기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
    {
        "event_id": 10, "academic_year": 2026, "semester": "2",
        "event_name": "2026-2학기 복학신청",
        "event_type": "ADMINISTRATIVE",
        "start_date": "2026-08-04", "end_date": "2026-08-08",
        "is_mandatory": False,
        "description": "복학신청 기간",
        "source_url": "https://www.hs.ac.kr/kor/4837/subview.do",
    },
]

write_csv("academic_events.csv", [
    "event_id", "academic_year", "semester", "event_name", "event_type",
    "start_date", "end_date", "is_mandatory", "description", "source_url"
], academic_events)


# ============================================================
# Step 7: Notices (SW공지사항)
# ============================================================

notices = [
    {
        "notice_id": 1,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[공지] 2026-2학기 융합/특화전공 신청 안내",
        "category": "학사",
        "posted_date": "2026-07-15",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 2,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[공지] AI아트코딩과윤리 멘토링 신청안내",
        "category": "행사",
        "posted_date": "2026-03-19",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 3,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[홍보] ACPC 2026 (AWS x Codetree) 전국 대학생/대학원생 프로그래밍 경진대회 개최 안내",
        "category": "행사",
        "posted_date": "2026-07-16",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 4,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[안내] 2026년 관광데이터 활용 공모전 웹·앱 구현 부문 모집 안내 (~7/21까지)",
        "category": "행사",
        "posted_date": "2026-07-15",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 5,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[공지] 2026 SW중심대학 학생 주도형 아이디어 공모전 결과 발표 일정 변경 안내",
        "category": "학사",
        "posted_date": "2026-07-07",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 6,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[공지] 2026년도 1학기 SW포인트(소중한 포인트) 신청 안내",
        "category": "장학",
        "posted_date": "2026-06-30",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 7,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[안내] 2026 상반기 교재개발 사업 안내 (접수기한 연장)",
        "category": "학사",
        "posted_date": "2026-06-24",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 8,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[홍보] 2026년 코디세이 올인원 교육 과정",
        "category": "행사",
        "posted_date": "2026-06-19",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 9,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[공지] 2026 SW중심대학 디지털경진대회 학교 대표 선발 안내",
        "category": "행사",
        "posted_date": "2026-06-08",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 10,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[공지] 2026-1학기 SW융합/특화전공 장학금 신청 안내",
        "category": "장학",
        "posted_date": "2026-06-04",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 11,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[안내] (양식 변경) 2026 한일 브릿지 아이디어톤 참가자 모집",
        "category": "행사",
        "posted_date": "2026-06-04",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
    {
        "notice_id": 12,
        "source_board": "SW중심대학사업단 공지사항",
        "title": "[공지] 제1차 한신 AISW 알고리즘 공개 경진대회 결과 안내",
        "category": "행사",
        "posted_date": "2026-06-02",
        "notice_url": "https://swuniv.hs.ac.kr/07_01",
        "content": None,
    },
]

write_csv("notices.csv", [
    "notice_id", "source_board", "title", "category",
    "posted_date", "notice_url", "content"
], notices)


# ============================================================
# Step 8: Empty reference tables (초기 빈 테이블)
# ============================================================

write_csv("student_course_history.csv", [
    "history_id", "student_id", "course_id", "academic_year",
    "semester", "earned_credit", "completion_status", "is_retake",
    "attempt_no", "original_history_id", "credit_counted"
], [])

write_csv("curriculum_courses.csv", [
    "curriculum_course_id", "curriculum_year", "course_id",
    "recommended_grade", "semester", "completion_type",
    "is_required", "note"
], [])

write_csv("program_courses.csv", [
    "program_course_id", "program_id", "course_id",
    "effective_year", "recognition_credit", "is_required", "note"
], [])

write_csv("course_keywords.csv", [
    "keyword_id", "offering_id", "keyword", "keyword_source",
    "confidence_score", "keyword_category", "weight", "source_text"
], [])

write_csv("student_programs.csv", [
    "student_program_id", "student_id", "program_id",
    "program_role", "selected_year", "completion_status", "created_at"
], [])

write_csv("user_interests.csv", [
    "user_interest_id", "user_id", "interest_type",
    "keyword", "created_at"
], [])

write_csv("course_recommendations.csv", [
    "recommendation_id", "student_id", "offering_id",
    "match_score", "reason", "generated_at"
], [])

write_csv("chat_sessions.csv", [
    "session_id", "user_id", "created_at", "updated_at"
], [])

write_csv("chat_messages.csv", [
    "message_id", "session_id", "sender_type",
    "message_text", "created_at"
], [])

write_csv("students.csv", [
    "student_id", "user_id", "student_number",
    "admission_year", "current_grade"
], [])

write_csv("users.csv", [
    "user_id", "login_id", "password_hash", "role"
], [])


# ============================================================
# Summary
# ============================================================

print("\n" + "=" * 60)
print("=== GradManager CSV 생성 완료 ===")
print(f"출력 경로: {OUTPUT_DIR}")
print(f"과목 수: {len(courses_map)}")
print(f"개설강좌 수: {len(offerings)}")
print(f"강의시간 항목 수: {len(schedules)}")
print(f"전공과정 수: {len(programs)}")
print(f"졸업요건 수: {len(grad_requirements)}")
print(f"학사일정 수: {len(academic_events)}")
print(f"공지사항 수: {len(notices)}")
print("=" * 60)
