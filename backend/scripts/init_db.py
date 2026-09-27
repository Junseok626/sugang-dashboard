"""
scripts/init_db.py

data/processed/sugang.db 에 7개 테이블 스키마를 생성한다.
이미 존재하는 테이블은 건드리지 않는다 (CREATE TABLE IF NOT EXISTS).

실행:
    python scripts/init_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "sugang.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS department (
    department_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    homepage_url    TEXT
);

CREATE TABLE IF NOT EXISTS professor (
    professor_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    department_id   INTEGER NOT NULL,
    FOREIGN KEY (department_id) REFERENCES department (department_id)
);

CREATE TABLE IF NOT EXISTS course (
    course_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id   INTEGER NOT NULL,
    course_code     TEXT NOT NULL,
    course_name     TEXT NOT NULL,
    credit          INTEGER NOT NULL,
    category        TEXT,               -- 전공필수 / 전공선택 / 교양
    FOREIGN KEY (department_id) REFERENCES department (department_id)
);

CREATE TABLE IF NOT EXISTS course_offering (
    offering_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       INTEGER NOT NULL,
    professor_id    INTEGER,
    semester        TEXT NOT NULL,      -- 예: "2026-2"
    day_time        TEXT,               -- 예: "화3,목3"
    classroom       TEXT,
    FOREIGN KEY (course_id) REFERENCES course (course_id),
    FOREIGN KEY (professor_id) REFERENCES professor (professor_id)
);

CREATE TABLE IF NOT EXISTS review (
    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    offering_id     INTEGER NOT NULL,
    rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment         TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (offering_id) REFERENCES course_offering (offering_id)
);

CREATE TABLE IF NOT EXISTS pdf_source (
    source_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id   INTEGER NOT NULL,
    file_url        TEXT NOT NULL,
    uploaded_date   DATE,
    parsed_at       DATETIME,
    FOREIGN KEY (department_id) REFERENCES department (department_id)
);

CREATE TABLE IF NOT EXISTS cart_item (
    cart_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    offering_id     INTEGER NOT NULL,
    added_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (offering_id) REFERENCES course_offering (offering_id)
);

-- 자주 조회할 컬럼에 인덱스
CREATE INDEX IF NOT EXISTS idx_review_offering ON review (offering_id);
CREATE INDEX IF NOT EXISTS idx_cart_session ON cart_item (session_id);
CREATE INDEX IF NOT EXISTS idx_offering_course ON course_offering (course_id);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()

    print(f"스키마 생성 완료 → {db_path}")


if __name__ == "__main__":
    init_db()
