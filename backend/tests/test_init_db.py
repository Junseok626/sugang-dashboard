"""
tests/test_init_db.py — 스키마 검사  [1주차에 채움]

사용하는 픽스처: db (conftest.py — 빈 테이블만 있는 임시 DB 연결)
함수 이름은 test_로 시작해야 pytest가 찾는다. 오류가 나야 맞는 경우는 with pytest.raises(sqlite3.IntegrityError): 로 감싼다.

채울 테스트

    test_all_tables_created(db)
        sqlite_master에서 테이블 이름을 읽어 8개가 모두 있는지
        {"department", "course", "professor", "course_offering",
         "offering_slot", "review", "cart_item", "data_source"}

    test_foreign_keys_on(db)
        db.execute("PRAGMA foreign_keys").fetchone()[0] == 1   (app.db.connect가 켰는지)

    test_course_code_unique(db)
        같은 course_code로 course를 두 번 INSERT하면 IntegrityError

    test_category_check(db)
        category에 "전공필수/전공선택/교양" 말고 다른 값(예: "전공핵심")을 넣으면 IntegrityError

    test_rating_check(db)
        review.rating에 0이나 6을 넣으면 IntegrityError

    test_slot_time_check(db)
        offering_slot에 start_time "12:00", end_time "11:00"을 넣으면 IntegrityError

    test_offering_unique(db)
        같은 (semester, course_id, section)을 두 번 넣으면 IntegrityError

    test_foreign_key_enforced(db)
        없는 department_id(예: 999)로 course를 넣으면 IntegrityError

    test_create_tables_twice(db)
        scripts.init_db.create_tables(db)를 한 번 더 불러도 오류가 없는지 (IF NOT EXISTS)
"""

"""
tests/test_init_db.py — 스키마 검사

사용하는 픽스처: db (conftest.py — 빈 테이블만 있는 임시 DB 연결)
오류가 나야 맞는 경우는 with pytest.raises(sqlite3.IntegrityError): 로 감싼다.
"""
import sqlite3

import pytest

from scripts.init_db import create_tables

EXPECTED_TABLES = {
    "department", "course", "professor", "course_offering",
    "offering_slot", "review", "cart_item", "data_source",
}


# ── 테스트용 행을 넣는 도우미 함수 ─────────────────────────
def add_department(db, name="컴퓨터공학과"):
    return db.execute("INSERT INTO department (name) VALUES (?)", (name,)).lastrowid


def add_course(db, department_id, code="CSE401", name="기계학습", credit=3, category="전공선택"):
    return db.execute(
        "INSERT INTO course (department_id, course_code, course_name, credit, category)"
        " VALUES (?, ?, ?, ?, ?)",
        (department_id, code, name, credit, category),
    ).lastrowid


def add_professor(db, name="김OO"):
    return db.execute("INSERT INTO professor (name) VALUES (?)", (name,)).lastrowid


def add_offering(db, course_id, professor_id, semester="2026-2", section="01"):
    return db.execute(
        "INSERT INTO course_offering (course_id, professor_id, semester, section)"
        " VALUES (?, ?, ?, ?)",
        (course_id, professor_id, semester, section),
    ).lastrowid


def add_review(db, course_id, professor_id, rating):
    return db.execute(
        "INSERT INTO review (course_id, professor_id, rating, comment, taken_semester)"
        " VALUES (?, ?, ?, ?, ?)",
        (course_id, professor_id, rating, "테스트 강의평입니다.", "2026-1"),
    ).lastrowid


# ── 테스트 ───────────────────────────────────────────────
def test_all_tables_created(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    assert {row["name"] for row in rows} == EXPECTED_TABLES


def test_foreign_keys_on(db):
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_course_code_unique(db):
    dept = add_department(db)
    add_course(db, dept, code="CSE401")
    with pytest.raises(sqlite3.IntegrityError):
        add_course(db, dept, code="CSE401", name="다른 과목")


def test_category_check(db):
    dept = add_department(db)
    with pytest.raises(sqlite3.IntegrityError):
        add_course(db, dept, category="전공핵심")


def test_category_allowed_values(db):
    dept = add_department(db)
    for i, category in enumerate(["전공필수", "전공선택", "교양"]):
        add_course(db, dept, code=f"C{i}", category=category)
    assert db.execute("SELECT COUNT(*) FROM course").fetchone()[0] == 3


@pytest.mark.parametrize("rating", [0, 6])
def test_rating_check(db, rating):
    course = add_course(db, add_department(db))
    prof = add_professor(db)
    with pytest.raises(sqlite3.IntegrityError):
        add_review(db, course, prof, rating)


def test_rating_allowed_range(db):
    course = add_course(db, add_department(db))
    prof = add_professor(db)
    for rating in range(1, 6):
        add_review(db, course, prof, rating)
    assert db.execute("SELECT COUNT(*) FROM review").fetchone()[0] == 5


def test_slot_time_check(db):
    offering = add_offering(db, add_course(db, add_department(db)), add_professor(db))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO offering_slot (offering_id, day, start_time, end_time)"
            " VALUES (?, '화', '12:00', '11:00')",
            (offering,),
        )


def test_offering_unique(db):
    course = add_course(db, add_department(db))
    prof = add_professor(db)
    add_offering(db, course, prof, semester="2026-2", section="01")
    with pytest.raises(sqlite3.IntegrityError):
        add_offering(db, course, prof, semester="2026-2", section="01")


def test_foreign_key_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        add_course(db, department_id=999)


def test_create_tables_twice(db):
    create_tables(db)  # IF NOT EXISTS라서 두 번째도 오류 없음
    test_all_tables_created(db)