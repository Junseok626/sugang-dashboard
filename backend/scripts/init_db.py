"""
scripts/init_db.py — 빈 DB 파일과 테이블 만들기  [1주차에 채움]

실행 (backend 폴더에서)
    python -m scripts.init_db            없는 테이블만 새로 만든다. 이미 있는 데이터는 그대로.
    python -m scripts.init_db --reset    sugang.db를 지우고 처음부터 만든다. (담은 과목·강의평도 사라짐)

채울 것

    SCHEMA_SQL: str
        "스키마 구조.md" §4의 테이블 8개를 CREATE TABLE IF NOT EXISTS 문으로 옮겨 적은 문자열 하나.
        표에 적힌 제약(NOT NULL, UNIQUE, CHECK, DEFAULT, FOREIGN KEY ... ON DELETE CASCADE)과
        각 표 아래의 테이블 제약·인덱스(CREATE INDEX IF NOT EXISTS ...)까지 빠짐없이 옮긴다.
        컬럼 옆에 -- 주석으로 한 줄 설명을 달아 둔다.

        예) department
            CREATE TABLE IF NOT EXISTS department (
                department_id INTEGER PRIMARY KEY,   -- 학과 번호 (자동 증가)
                name          TEXT NOT NULL UNIQUE   -- 학과명, 예: 컴퓨터공학과
            );

        적는 순서: 다른 테이블이 참조하는 쪽을 먼저
            department → course → professor → course_offering → offering_slot → review → cart_item → data_source

    create_tables(conn) -> None
        conn.executescript(SCHEMA_SQL) 후 conn.commit()
        tests/conftest.py도 이 함수로 테스트용 임시 DB를 만든다.

    main() -> None
        1. argparse로 --reset 옵션 읽기 (action="store_true")
        2. --reset이면 config.DB_PATH 파일 삭제 (파일이 없으면 그냥 넘어감: unlink(missing_ok=True))
        3. DB_PATH가 들어갈 폴더가 없으면 만들기: DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        4. app.db.connect(DB_PATH)로 연결 → create_tables(conn) → conn.close()
        5. 만들어진 테이블 이름 출력
               SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name
           출력 예)  테이블 8개 준비 완료: cart_item, course, course_offering, data_source, ...

    if __name__ == "__main__":
        main()

완료 확인
    - python -m scripts.init_db 를 두 번 실행해도 오류가 없다.
    - backend/data/processed/sugang.db 파일이 생기고, git status에는 보이지 않는다 (.gitignore).
    - DB Browser for SQLite로 열면 8개 테이블이 보인다.
    - python -m pytest tests/test_init_db.py 통과
"""

"""
scripts/init_db.py — 빈 DB 파일과 테이블 만들기

실행 (backend 폴더에서)
    python -m scripts.init_db            없는 테이블만 새로 만든다. 이미 있는 데이터는 그대로.
    python -m scripts.init_db --reset    sugang.db를 지우고 처음부터 만든다. (담은 과목·강의평도 사라짐)

테이블 설계는 "스키마 구조.md" §4.
"""
import argparse

from app.config import DB_PATH
from app.db import connect

# 다른 테이블이 참조하는 쪽을 먼저 만든다.
SCHEMA_SQL = """
-- 4-1. 학과
CREATE TABLE IF NOT EXISTS department (
    department_id INTEGER PRIMARY KEY,               -- 학과 번호 (자동 증가)
    name          TEXT NOT NULL UNIQUE               -- 학과명, 예: 컴퓨터공학과
);

-- 4-2. 과목 (학기와 상관없는 정보)
CREATE TABLE IF NOT EXISTS course (
    course_id     INTEGER PRIMARY KEY,               -- 과목 번호
    department_id INTEGER NOT NULL
                  REFERENCES department (department_id),  -- 개설 학과
    course_code   TEXT NOT NULL UNIQUE,              -- 학수번호, 예: CSE401
    course_name   TEXT NOT NULL,                     -- 과목명
    credit        INTEGER NOT NULL CHECK (credit >= 1),   -- 학점
    category      TEXT NOT NULL
                  CHECK (category IN ('전공필수', '전공선택', '교양'))  -- 이수구분 (필터 값과 같음)
);

-- 4-3. 교수
CREATE TABLE IF NOT EXISTS professor (
    professor_id  INTEGER PRIMARY KEY,               -- 교수 번호
    name          TEXT NOT NULL UNIQUE               -- 교수명 (같은 이름 = 같은 사람)
);

-- 4-4. 이번 학기 개설 과목 (분반). 검색 결과 한 줄 = 한 행
CREATE TABLE IF NOT EXISTS course_offering (
    offering_id   INTEGER PRIMARY KEY,               -- 개설 번호 (API: /api/courses/<offering_id>)
    course_id     INTEGER NOT NULL REFERENCES course (course_id),
    professor_id  INTEGER NOT NULL REFERENCES professor (professor_id),
    semester      TEXT NOT NULL,                     -- 예: 2026-2
    section       TEXT NOT NULL,                     -- 분반, 예: 01
    classroom     TEXT NOT NULL DEFAULT '',          -- 강의실 (모르면 빈 문자열)
    UNIQUE (semester, course_id, section)            -- CSV를 다시 넣어도 같은 분반은 하나
);
CREATE INDEX IF NOT EXISTS idx_offering_semester ON course_offering (semester);

-- 4-5. 수업 시간 한 칸 (요일 하나당 한 행)
CREATE TABLE IF NOT EXISTS offering_slot (
    slot_id       INTEGER PRIMARY KEY,
    offering_id   INTEGER NOT NULL
                  REFERENCES course_offering (offering_id) ON DELETE CASCADE,
    day           TEXT NOT NULL
                  CHECK (day IN ('월', '화', '수', '목', '금', '토', '일')),
    start_time    TEXT NOT NULL,                     -- 'HH:MM' 두 자리, 예: 09:00
    end_time      TEXT NOT NULL,
    CHECK (start_time < end_time)
);
CREATE INDEX IF NOT EXISTS idx_slot_offering ON offering_slot (offering_id);

-- 4-6. 강의평 (익명). 과목 + 교수 단위로 묶는다
CREATE TABLE IF NOT EXISTS review (
    review_id      INTEGER PRIMARY KEY,
    course_id      INTEGER NOT NULL REFERENCES course (course_id),
    professor_id   INTEGER NOT NULL REFERENCES professor (professor_id),
    rating         INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),  -- 별점
    comment        TEXT NOT NULL,                    -- 서술형 후기
    taken_semester TEXT NOT NULL,                    -- 작성자가 들은 학기, 예: 2026-1
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP   -- 작성 시각 (UTC)
);
CREATE INDEX IF NOT EXISTS idx_review_course_prof ON review (course_id, professor_id);

-- 4-7. 담은 과목 (내 시간표). 로그인 대신 세션 ID로 브라우저 구분
CREATE TABLE IF NOT EXISTS cart_item (
    cart_id       INTEGER PRIMARY KEY,
    session_id    TEXT NOT NULL,                     -- 서버가 쿠키에 넣어 둔 무작위 문자열
    offering_id   INTEGER NOT NULL
                  REFERENCES course_offering (offering_id) ON DELETE CASCADE,
    added_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,   -- 담은 순서·시간표 색 순서
    UNIQUE (session_id, offering_id)                 -- 같은 과목 두 번 담기 방지
);
CREATE INDEX IF NOT EXISTS idx_cart_session ON cart_item (session_id);

-- 4-8. CSV 반영 기록. 헤더 "최신 반영일" = offerings의 최근 captured_at
CREATE TABLE IF NOT EXISTS data_source (
    source_id     INTEGER PRIMARY KEY,
    data_type     TEXT NOT NULL
                  CHECK (data_type IN ('courses', 'offerings', 'reviews')),
    file_name     TEXT NOT NULL,                     -- 예: offerings.csv
    semester      TEXT,                              -- offerings일 때만, 나머지는 NULL
    row_count     INTEGER NOT NULL,                  -- 반영한 행 수
    captured_at   TEXT NOT NULL,                     -- 자료 기준일 'YYYY-MM-DD'
    imported_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP    -- DB에 넣은 시각
);
"""


def create_tables(conn):
    """SCHEMA_SQL을 실행해 테이블과 인덱스를 만든다. 이미 있으면 그대로 둔다."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="빈 DB와 테이블을 만든다.")
    parser.add_argument("--reset", action="store_true",
                        help="sugang.db를 지우고 처음부터 만든다 (담은 과목·강의평도 사라짐)")
    args = parser.parse_args()

    if args.reset:
        DB_PATH.unlink(missing_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = connect(DB_PATH)
    try:
        create_tables(conn)
        names = [row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master"
            " WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
    finally:
        conn.close()

    print(f"테이블 {len(names)}개 준비 완료: {', '.join(names)}")
    print(f"DB 파일: {DB_PATH}")


if __name__ == "__main__":
    main()