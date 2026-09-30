"""
app/config.py — 설정값 모음  [1주차에 채움]

역할
    여러 파일이 함께 쓰는 경로와 상수를 한 곳에 모은다.
    학기가 바뀌거나 DB 위치를 옮길 때는 이 파일만 고치면 된다.
    Flask는 app.config.from_object(config)로 이 파일의 "대문자 변수"만 설정으로 읽는다.

채울 상수 (경로는 문자열 대신 pathlib.Path 사용 → 어느 폴더에서 실행해도 같은 파일을 가리킨다)

    BASE_DIR          backend 폴더의 절대 경로
                          Path(__file__).resolve().parent.parent
    DB_PATH           BASE_DIR / "data" / "processed" / "sugang.db"
    RAW_DIR           BASE_DIR / "data" / "raw"          (CSV가 있는 곳)
    FRONTEND_DIR      BASE_DIR.parent / "frontend"       (Flask가 화면 파일을 내보낼 폴더)

    CURRENT_SEMESTER  "2026-2"
                          화면 헤더 "2026-2학기 기준", 과목 검색·담기 대상 학기.
                          offerings.csv의 semester 값과 같아야 과목이 보인다.

    SECRET_KEY        세션 쿠키 서명용 문자열
                          os.environ.get("SECRET_KEY", "dev-only-change-me")
                          발표용 PC에서는 환경변수로 아무 긴 문자열을 넣어 둔다.
    PERMANENT_SESSION_LIFETIME
                      timedelta(days=180)  → 브라우저를 껐다 켜도 내 시간표가 유지되는 기간

    CATEGORIES        ["전공필수", "전공선택", "교양"]
                          course.category의 CHECK, 과목 찾기 필터 체크박스와 같은 값
    TIMETABLE_DAYS    ["월", "화", "수", "목", "금"]
    TIMETABLE_START   "09:00"
    TIMETABLE_END     "19:00"
                          화면 시간표 격자의 범위. import_csv.py가 범위 밖 수업을 경고할 때도 쓴다.

주의
    - 이 파일에는 함수나 Flask 코드를 넣지 않는다. scripts/*.py도 이 파일을 import한다.
    - 비밀번호·개인 키 같은 진짜 비밀 값은 코드에 적지 말고 환경변수로 받는다.
"""
import os
from datetime import timedelta
from pathlib import Path

# ── 경로 ─────────────────────────────────────────────
# 이 파일 위치(backend/app/config.py)에서 두 단계 위 = backend 폴더
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "sugang.db"
RAW_DIR = BASE_DIR / "data" / "raw"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# ── 학기 ─────────────────────────────────────────────
# 화면 헤더 "2026-2학기 기준", 검색·담기 대상 학기. offerings.csv의 semester와 같아야 한다.
CURRENT_SEMESTER = "2026-2"

# ── 세션 (로그인 없이 브라우저마다 내 시간표 구분) ─────────
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
PERMANENT_SESSION_LIFETIME = timedelta(days=180)

# ── 화면·데이터 규칙 ─────────────────────────────────
CATEGORIES = ["전공필수", "전공선택", "교양"]
TIMETABLE_DAYS = ["월", "화", "수", "목", "금"]
TIMETABLE_START = "09:00"
TIMETABLE_END = "19:00"