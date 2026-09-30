"""
tests/conftest.py — 테스트 공용 준비물(픽스처)  [1주차 시작 → 2주차, 3주차에 추가]

pytest가 하는 일
    tests/ 안의 test_로 시작하는 파일에서 test_로 시작하는 함수를 찾아 실행한다.
    테스트 함수의 인자 이름이 이 파일의 @pytest.fixture 함수 이름과 같으면, 그 결과를 자동으로 넣어 준다.
        def test_something(db):   ← 아래 db 픽스처가 만든 연결이 들어온다

실행 (backend 폴더에서)
    python -m pytest                       전체
    python -m pytest tests/test_overlap.py 파일 하나
    "python -m"으로 실행해야 backend 폴더가 import 경로에 들어가서 app, scripts를 불러올 수 있다.

중요한 약속
    실제 data/processed/sugang.db는 절대 건드리지 않는다.
    테스트마다 pytest가 주는 임시 폴더(tmp_path)에 새 DB를 만들어 쓰고, 끝나면 자동으로 버려진다.

채울 픽스처

    [1주차]
    db_path(tmp_path) -> Path
        path = tmp_path / "test.db"
        app.db.connect(path)로 연결 → scripts.init_db.create_tables(conn) → close → path 반환

    db(db_path) -> sqlite3.Connection
        conn = app.db.connect(db_path)
        yield conn        ← 테스트가 이 연결을 쓴다
        conn.close()      ← 테스트가 끝나면 실행

    [2주차]
    sample_raw_dir(tmp_path) -> Path
        tmp_path / "raw" 폴더에 작은 courses.csv, offerings.csv, reviews.csv를 써 넣고 폴더 경로를 돌려준다.
        (파일 내용은 이 함수 안에 문자열로 적는다. encoding="utf-8")
        반드시 들어가야 하는 경우 — 뒤의 테스트들이 이 데이터를 전제로 한다
            · 시간이 겹치는 과목 한 쌍        (예: 기계학습 화·목 11-12 / 데이터시각화 화·목 11-12)
            · 같은 교수가 맡은 같은 과목의 분반 두 개
                                               (예: 데이터베이스 이OO 01반 월·수 10-11 / 02반 화·목 15-16)
            · 강의평이 없는 과목 하나          (평균 평점 None, 최소 평점 필터에서 빠지는지 확인용)
            · 시간 미정 과목 하나              (day_time 빈칸)
            · 이수구분 3종류가 모두 한 번 이상

    seeded_db_path(db_path, sample_raw_dir) -> Path
        db_path에 scripts.import_csv.import_all(conn, sample_raw_dir, "2026-09-20", "2026-2")로
        샘플을 넣은 뒤(연결은 닫고) 경로를 돌려준다.

    [3주차]
    app(seeded_db_path) -> Flask
        create_app({"TESTING": True, "DB_PATH": str(seeded_db_path), "CURRENT_SEMESTER": "2026-2"})

    client(app) -> FlaskClient
        return app.test_client()
        서버를 켜지 않고도 client.get("/api/courses"), client.post("/api/cart", json={...})로 API를 부를 수 있다.
        test_client() 하나 = 브라우저 하나 (쿠키를 따로 가진다).
"""
import textwrap
import pytest
from app.db import connect

SEMESTER = "2026-2"
CAPTURED_AT = "2026-09-20"

# ── 샘플 CSV ───────────────────────────────────────────
# 테스트가 전제로 하는 경우가 모두 들어 있다. 바꿀 때는 test_*.py의 기대값도 같이 확인할 것.
#   · 시간 겹침:        기계학습(CSE401) ↔ 데이터시각화(CSE403)  화·목 11:00-12:00
#   · 같은 교수 분반 2개: 데이터베이스(CSE402) 이OO 01반 월·수 / 02반 화·목
#   · 강의평 없음:      글쓰기와소통(GEN101), 캡스톤디자인(CSE405)
#   · 시간 미정:        캡스톤디자인(CSE405) day_time 빈칸, 교수 미정
#   · 이수구분 3종류, 학점 2·3, 학과 2개(컴퓨터공학과 여러 번 등장)
#   · 평균 평점: CSE401 4.5 / CSE402 3.5 / CSE403 4.0 / CSE404 5.0
SAMPLE_COURSES = """\
department_name,course_code,course_name,credit,category
컴퓨터공학과,CSE401,기계학습,3,전공선택
컴퓨터공학과,CSE402,데이터베이스,3,전공필수
컴퓨터공학과,CSE403,데이터시각화,3,전공선택
컴퓨터공학과,CSE404,실용머신러닝,3,전공선택
컴퓨터공학과,CSE405,캡스톤디자인,3,전공필수
교양학부,GEN101,글쓰기와소통,2,교양
"""

SAMPLE_OFFERINGS = """\
semester,course_code,section,professor_name,day_time,classroom
2026-2,CSE401,01,김OO,"화11:00-12:00,목11:00-12:00",IT융합관 210
2026-2,CSE402,01,이OO,"월10:00-11:00,수10:00-11:00",공학관 301
2026-2,CSE402,02,이OO,"화15:00-16:00,목15:00-16:00",공학관 301
2026-2,CSE403,01,박OO,"화11:00-12:00,목11:00-12:00",공학관 502
2026-2,CSE404,01,김OO,"월12:00-13:00,수12:00-13:00",공학관 512
2026-2,CSE405,01,미정,,
2026-2,GEN101,01,최OO,금09:00-11:00,인문관 101
"""

SAMPLE_REVIEWS = """\
course_code,professor_name,taken_semester,rating,comment
CSE401,김OO,2026-1,5,과제가 많지만 실습 위주라 남는 게 많아요.
CSE401,김OO,2025-2,4,선형대수 기초가 없으면 초반이 힘들 수 있어요.
CSE402,이OO,2025-2,4,설계 과제가 실무에 가까워서 도움이 됐어요.
CSE402,이OO,2025-1,3,"시험 범위가 넓어서 시간 투자가 꽤 필요해요."
CSE403,박OO,2025-2,4,시각화 도구를 여러 개 써 볼 수 있어서 좋았어요.
CSE404,김OO,2026-1,5,실제 데이터로 프로젝트를 해서 재미있었어요.
"""

@pytest.fixture
def db_path(tmp_path):
    """테이블만 있는 빈 임시 DB 파일 경로."""
    from scripts.init_db import create_tables

    path = tmp_path / "test.db"
    conn = connect(path)
    create_tables(conn)
    conn.close()
    return path


@pytest.fixture
def db(db_path):
    """빈 임시 DB 연결. 테스트가 끝나면 닫는다."""
    conn = connect(db_path)
    yield conn
    conn.close()
