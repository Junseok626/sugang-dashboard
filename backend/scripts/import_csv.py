"""
scripts/import_csv.py — data/raw의 CSV 3개를 DB에 넣기  [2주차에 채움]

실행 (backend 폴더에서, 먼저 python -m scripts.init_db 로 테이블을 만들어 둔 상태)
    python -m scripts.import_csv --captured-at 2026-09-20
    --captured-at : 이 CSV가 언제 기준 자료인지 (YYYY-MM-DD). 화면 헤더의 "최신 반영일"이 된다.
                    생략하면 오늘 날짜.

읽는 파일과 순서 (뒤 파일이 앞 파일의 학수번호를 참조하므로 순서 고정)
    1. data/raw/courses.csv    → department, course
    2. data/raw/offerings.csv  → professor, course_offering, offering_slot
    3. data/raw/reviews.csv    → professor, review        (파일이 없으면 건너뜀)
    각 파일의 컬럼과 규칙은 "스키마 구조.md" §7.

"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from app import config, overlap
from app.db import connect

REQUIRED_COLUMNS = {
    "courses.csv": ["department_name", "course_code", "course_name", "credit", "category"],
    "offerings.csv": ["semester", "course_code", "section", "professor_name", "day_time", "classroom"],
    "reviews.csv": ["course_code", "professor_name", "taken_semester", "rating", "comment"],
}

OPTIONAL_VALUES = {
    "offerings.csv": {"day_time", "classroom"},
}

SEMESTER_RE = re.compile(r"^\d{4}-[12]$")


def warn(message: str) -> None:
    print(f"[경고] {message}", file=sys.stderr)


def _check_required_values(fname: str, row: dict, prefix: str) -> None:
    optional = OPTIONAL_VALUES.get(fname, set())
    for col in REQUIRED_COLUMNS[fname]:
        if col not in optional and row[col] == "":
            raise ValueError(f"{prefix} {col} 칸이 비었습니다")


def read_csv(path) -> list[dict]:
    path = Path(path)
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]

    for col in REQUIRED_COLUMNS.get(path.name, []):
        if col not in df.columns:
            raise ValueError(f"{path.name}: {col} 컬럼이 없습니다")

    records = df.to_dict("records")
    return [{k: str(v).strip() for k, v in row.items()} for row in records]


def _get_or_create(db, table: str, id_col: str, name: str) -> int:
    row = db.execute(f"SELECT {id_col} FROM {table} WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row[0]
    cur = db.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    return cur.lastrowid


def get_or_create_department(db, name: str) -> int:
    return _get_or_create(db, "department", "department_id", name)


def get_or_create_professor(db, name: str) -> int:
    return _get_or_create(db, "professor", "professor_id", name)


def import_courses(db, rows: list[dict]) -> int:
    fname = "courses.csv"
    seen = set()
    count = 0

    for i, row in enumerate(rows):
        line = i + 2 
        prefix = f"{fname} {line}행:"

        _check_required_values(fname, row, prefix)

        code = row["course_code"]
        if code in seen:
            raise ValueError(f"{prefix} course_code {code}가 파일 안에서 중복됩니다")
        seen.add(code)

        try:
            credit = int(row["credit"])
        except ValueError:
            credit = 0
        if credit < 1:
            raise ValueError(f'{prefix} credit "{row["credit"]}"는 1 이상 정수여야 합니다')

        if row["category"] not in config.CATEGORIES:
            raise ValueError(
                f'{prefix} category "{row["category"]}"는 허용되지 않습니다 '
                f"(가능: {', '.join(config.CATEGORIES)})"
            )

        department_id = get_or_create_department(db, row["department_name"])
        db.execute(
            """
            INSERT INTO course (department_id, course_code, course_name, credit, category)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(course_code) DO UPDATE SET
                department_id = excluded.department_id,
                course_name   = excluded.course_name,
                credit        = excluded.credit,
                category      = excluded.category
            """,
            (department_id, code, row["course_name"], credit, row["category"]),
        )
        count += 1

    return count


def _slot_outside_grid(slot: dict) -> bool:
    """시간표 격자(TIMETABLE_DAYS, START~END) 밖인지. "HH:MM"은 문자열 그대로 크기 비교가 된다."""
    if slot["day"] not in config.TIMETABLE_DAYS:
        return True
    return slot["start"] < config.TIMETABLE_START or slot["end"] > config.TIMETABLE_END


def _find_course_id(db, code: str, prefix: str) -> int:
    found = db.execute("SELECT course_id FROM course WHERE course_code = ?", (code,)).fetchone()
    if found is None:
        raise ValueError(f"{prefix} courses.csv에 없는 학수번호 {code}")
    return found[0]


def import_offerings(db, rows: list[dict], current_semester: str) -> int:
    fname = "offerings.csv"
    count = 0

    for i, row in enumerate(rows):
        line = i + 2
        prefix = f"{fname} {line}행:"

        _check_required_values(fname, row, prefix)

        code = row["course_code"]
        course_id = _find_course_id(db, code, prefix)

        try:
            slots = overlap.parse_day_time(row["day_time"])
        except ValueError as e:
            raise ValueError(f"{prefix} day_time {e}") from e

        semester = row["semester"]
        section = row["section"]
        professor_id = get_or_create_professor(db, row["professor_name"])

        db.execute(
            """
            INSERT INTO course_offering (course_id, professor_id, semester, section, classroom)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(semester, course_id, section) DO UPDATE SET
                professor_id = excluded.professor_id,
                classroom    = excluded.classroom
            """,
            (course_id, professor_id, semester, section, row["classroom"]),
        )
        offering_id = db.execute(
            "SELECT offering_id FROM course_offering WHERE semester = ? AND course_id = ? AND section = ?",
            (semester, course_id, section),
        ).fetchone()[0]

    
        db.execute("DELETE FROM offering_slot WHERE offering_id = ?", (offering_id,))
        for slot in slots:
            db.execute(
                "INSERT INTO offering_slot (offering_id, day, start_time, end_time) VALUES (?, ?, ?, ?)",
                (offering_id, slot["day"], slot["start"], slot["end"]),
            )
            if _slot_outside_grid(slot):
                warn(f"{prefix} {code} 수업 시간 {row['day_time']}이(가) 시간표 격자 밖이라 화면에 안 보입니다")

        if semester != current_semester:
            warn(
                f"{prefix} semester {semester}이(가) 현재 학기 "
                f"{current_semester}와 달라 화면에 안 보입니다"
            )
        count += 1

    return count



def import_reviews(db, rows: list[dict]) -> int:
    fname = "reviews.csv"
    count = 0

    for i, row in enumerate(rows):
        line = i + 2
        prefix = f"{fname} {line}행:"

        _check_required_values(fname, row, prefix)

        course_id = _find_course_id(db, row["course_code"], prefix)

        try:
            rating = float(row["rating"])
        except ValueError:
            rating = 0.0
        if not 0.5 <= rating <= 5 or not (rating * 2).is_integer():
            raise ValueError(f'{prefix} rating "{row["rating"]}"는 0.5~5 사이 0.5점 단위여야 합니다')

        comment = row["comment"]
        if not 5 <= len(comment) <= 500:
            raise ValueError(f"{prefix} comment는 5~500자여야 합니다 (현재 {len(comment)}자)")

        taken = row["taken_semester"]
        if not SEMESTER_RE.match(taken):
            raise ValueError(f'{prefix} taken_semester "{taken}" 형식 오류 (예: 2026-1)')

        professor_id = get_or_create_professor(db, row["professor_name"])

        dup = db.execute(
            """
            SELECT 1 FROM review
            WHERE course_id = ? AND professor_id = ? AND taken_semester = ? AND comment = ?
            """,
            (course_id, professor_id, taken, comment),
        ).fetchone()
        if dup is not None:
            continue 

        db.execute(
            """
            INSERT INTO review (course_id, professor_id, rating, comment, taken_semester)
            VALUES (?, ?, ?, ?, ?)
            """,
            (course_id, professor_id, rating, comment, taken),
        )
        count += 1

    return count



def log_source(db, data_type, file_name, row_count, captured_at, semester=None) -> None:
    db.execute(
        """
        INSERT INTO data_source (data_type, file_name, semester, row_count, captured_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (data_type, file_name, semester, row_count, captured_at),
    )


def import_all(db, raw_dir, captured_at, current_semester) -> dict:
    raw_dir = Path(raw_dir)
    result = {}

    steps = [
        ("courses", "courses.csv", lambda rows: import_courses(db, rows)),
        ("offerings", "offerings.csv", lambda rows: import_offerings(db, rows, current_semester)),
        ("reviews", "reviews.csv", lambda rows: import_reviews(db, rows)),
    ]

    for data_type, file_name, importer in steps:
        path = raw_dir / file_name
        if not path.exists():
            if data_type == "reviews":
                continue
            raise ValueError(f"{file_name}: 파일을 찾을 수 없습니다 ({path})")

        try:
            rows = read_csv(path)
            n = importer(rows)
            semester = None
            if data_type == "offerings":
                semester = ", ".join(sorted({r["semester"] for r in rows})) or None
            log_source(db, data_type, file_name, n, captured_at, semester)
            db.commit()
        except Exception:
            db.rollback()
            raise

        result[data_type] = n

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="data/raw의 CSV를 DB에 넣는다")
    parser.add_argument(
        "--captured-at",
        default=date.today().isoformat(),
        help="CSV 기준일 YYYY-MM-DD (생략하면 오늘)",
    )
    args = parser.parse_args()

    try:
        date.fromisoformat(args.captured_at)
    except ValueError:
        print(f'--captured-at "{args.captured_at}" 형식 오류 (예: 2026-09-20)')
        sys.exit(1)

    conn = connect(config.DB_PATH)
    try:
        result = import_all(conn, config.RAW_DIR, args.captured_at, config.CURRENT_SEMESTER)
    except ValueError as e:
        print(e)
        sys.exit(1)
    finally:
        conn.close()

    summary = ", ".join(f"{name}.csv {n}행" for name, n in result.items())
    print(f"{summary} 반영 (기준일 {args.captured_at})")


if __name__ == "__main__":
    main()