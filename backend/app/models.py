"""
app/models.py — DB에서 꺼내고 넣는 함수 모음  [3주차: 조회 / 4주차: 담기 / 5주차: 강의평]

역할
    SQL은 전부 이 파일에 모은다. routes.py는 "요청 읽기 → 이 파일의 함수 호출 → JSON 응답"만 한다.
    - 모든 함수는 첫 번째 인자로 DB 연결(db)을 받는다. 테스트에서 임시 DB를 넣기 쉽다.
    - 돌려주는 값은 dict나 list로 바꿔서(dict(row)) 돌려준다. 그래야 routes.py에서 바로 JSON이 된다.
    - 테이블과 컬럼 이름은 "스키마 구조.md"를 따른다. 검색 SQL의 뼈대는 스키마 구조.md §6에 있다.
    - 응답 필드 이름은 로드맵.md "부록 A. API 명세"와 똑같이 맞춘다.

"""

"""
app/models.py — DB에서 꺼내고 넣는 함수 모음  [3주차: 조회 / 4주차: 담기 / 5주차: 강의평]

SQL은 전부 이 파일에 모은다. routes.py는 "요청 읽기 → 이 파일의 함수 호출 → JSON 응답"만 한다.
- 모든 함수는 첫 번째 인자로 DB 연결(db)을 받는다.
- 돌려주는 값은 dict / list (JSON으로 바로 바꿀 수 있는 모양).
- 응답 필드 이름은 로드맵.md "부록 A. API 명세"와 같다.
"""
import sqlite3

from . import overlap

# 개설 과목 한 줄을 만드는 공통 SELECT (스키마 구조.md §6)
# 뒤에 WHERE / ORDER BY를 붙여서 검색·상세·내 시간표가 함께 쓴다.
_OFFERING_SELECT = """
SELECT o.offering_id, o.course_id, o.professor_id, o.semester, o.section, o.classroom,
       c.course_code, c.course_name, c.credit, c.category,
       d.name AS department,
       p.name AS professor,
       ROUND(r.avg_rating, 1)      AS avg_rating,      -- 강의평 없으면 NULL
       COALESCE(r.review_count, 0) AS review_count
FROM course_offering o
JOIN course c     ON c.course_id = o.course_id
JOIN department d ON d.department_id = c.department_id
JOIN professor p  ON p.professor_id = o.professor_id
LEFT JOIN (                                            -- LEFT: 강의평 0개 과목도 나와야 함
    SELECT course_id, professor_id,
           AVG(rating) AS avg_rating, COUNT(*) AS review_count
    FROM review
    GROUP BY course_id, professor_id
) r ON r.course_id = o.course_id AND r.professor_id = o.professor_id
"""

# 과목 객체에 공통으로 들어가는 키 (부록 A)
_BASE_KEYS = ("offering_id", "course_code", "course_name", "professor",
              "credit", "category", "classroom")


# ── 공통 도우미 ─────────────────────────────────────────
def _placeholders(values):
    """[a, b, c] → "?, ?, ?"   (IN (...) 안에 넣을 자리표시자. 값은 따로 params로 넘긴다)"""
    return ", ".join("?" for _ in values)


def _load_slots(db, offering_ids):
    """{offering_id: [수업 시간 칸, ...]}  — 요일 순(월→일), 시작 시각 순으로 정렬."""
    slots = {oid: [] for oid in offering_ids}
    if not offering_ids:
        return slots
    rows = db.execute(
        "SELECT offering_id, day, start_time, end_time FROM offering_slot"
        f" WHERE offering_id IN ({_placeholders(offering_ids)})",
        list(offering_ids),
    )
    for row in rows:
        slots[row["offering_id"]].append(
            {"day": row["day"], "start": row["start_time"], "end": row["end_time"]}
        )
    for items in slots.values():
        items.sort(key=lambda s: (overlap.DAY_ORDER.index(s["day"]), s["start"]))
    return slots


def _base_item(row, slots):
    """DB 한 줄 + 수업 시간 → 과목 객체의 기본 키들."""
    item = {key: row[key] for key in _BASE_KEYS}
    item["day_time"] = overlap.format_day_time(slots)
    item["slots"] = slots
    return item


def _search_items(db, rows, session_id, semester):
    """검색·상세용 과목 객체 목록 (평점, 담김 여부, 시간 겹침까지)."""
    slots_by_id = _load_slots(db, [row["offering_id"] for row in rows])
    cart = get_cart(db, session_id, semester) if session_id else []
    cart_ids = {item["offering_id"] for item in cart}
    taken = {item["course_name"]: item["slots"] for item in cart}

    items = []
    for row in rows:
        item = _base_item(row, slots_by_id[row["offering_id"]])
        item["avg_rating"] = row["avg_rating"]
        item["review_count"] = row["review_count"]
        item["in_cart"] = row["offering_id"] in cart_ids
        item["conflict"] = (
            bool(taken)
            and not item["in_cart"]
            and bool(overlap.find_conflicts(item["slots"], taken))
        )
        items.append(item)
    return items


def _has_final_consonant(word):
    """한글 마지막 글자에 받침이 있으면 True (조사 은/는, 과/와 고르기용)."""
    last = word[-1] if word else ""
    return "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0


# ── 3주차: 조회 ─────────────────────────────────────────
def get_meta(db, semester):
    """헤더 정보: 이번 학기와 최신 반영일(offerings CSV의 가장 최근 기준일)."""
    row = db.execute(
        "SELECT MAX(captured_at) AS last_updated FROM data_source WHERE data_type = 'offerings'"
    ).fetchone()
    return {"semester": semester, "last_updated": row["last_updated"]}


def search_offerings(db, semester, session_id=None, q="", categories=(), days=(),
                     credit=None, min_rating=None):
    """과목 찾기 표의 목록. 비어 있는 조건은 빼고 검색한다."""
    where = ["o.semester = ?"]
    params = [semester]

    q = (q or "").strip()
    if q:  # 과목명 또는 교수명에 부분 일치
        where.append("(c.course_name LIKE '%' || ? || '%' OR p.name LIKE '%' || ? || '%')")
        params += [q, q]
    if categories:  # 이수구분 중 하나라도
        where.append(f"c.category IN ({_placeholders(categories)})")
        params += list(categories)
    if days:  # 수업 요일 중 하나라도 포함
        where.append(
            "EXISTS (SELECT 1 FROM offering_slot s WHERE s.offering_id = o.offering_id"
            f" AND s.day IN ({_placeholders(days)}))"
        )
        params += list(days)
    if credit is not None:
        where.append("c.credit = ?")
        params.append(credit)
    if min_rating is not None:  # 화면에 보이는 값(소수 1자리) 기준. NULL(평점 없음)은 자동으로 빠짐
        where.append("ROUND(r.avg_rating, 1) >= ?")
        params.append(min_rating)

    sql = _OFFERING_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY c.course_name, o.section"
    rows = db.execute(sql, params).fetchall()
    return _search_items(db, rows, session_id, semester)


def get_offering_detail(db, offering_id, session_id=None):
    """과목 상세 (검색 한 줄 + 학과·학기·분반·강의평). 없으면 None."""
    row = db.execute(_OFFERING_SELECT + " WHERE o.offering_id = ?", (offering_id,)).fetchone()
    if row is None:
        return None

    item = _search_items(db, [row], session_id, row["semester"])[0]
    item["department"] = row["department"]
    item["semester"] = row["semester"]
    item["section"] = row["section"]
    item["reviews"] = [
        dict(r) for r in db.execute(
            "SELECT review_id, rating, comment, taken_semester, created_at FROM review"
            " WHERE course_id = ? AND professor_id = ?"
            " ORDER BY created_at DESC, review_id DESC",
            (row["course_id"], row["professor_id"]),
        )
    ]
    return item

def get_cart(db, session_id, semester):
    # 이 브라우저가 담은 이번 학기 과목, 담은 순서대로.
    rows = db.execute(
        _OFFERING_SELECT
        + " JOIN cart_item ci ON ci.offering_id = o.offering_id"
          " WHERE ci.session_id = ? AND o.semester = ?"
          " ORDER BY ci.added_at, ci.cart_id",
        (session_id, semester),
    ).fetchall()
    slots_by_id = _load_slots(db, [row["offering_id"] for row in rows])
    return [_base_item(row, slots_by_id[row["offering_id"]]) for row in rows]

# ── 4주차: 담기 (내 시간표) ─────────────────────────────
"""
class CartError(Exception):
    # 담기를 거절할 때 쓰는 예외. routes.py가 409로 바꾼다.

    def __init__(self, reason, message, conflicts=None):
        super().__init__(message)
        self.reason = reason              # "already_in_cart" | "same_course" | "time_conflict"
        self.message = message            # 화면에 그대로 띄울 문장
        self.conflicts = conflicts or []  # 겹치는 과목 이름들 (time_conflict일 때만)


def get_cart(db, session_id, semester):
    # 이 브라우저가 담은 이번 학기 과목, 담은 순서대로.
    rows = db.execute(
        _OFFERING_SELECT
        + " JOIN cart_item ci ON ci.offering_id = o.offering_id"
          " WHERE ci.session_id = ? AND o.semester = ?"
          " ORDER BY ci.added_at, ci.cart_id",
        (session_id, semester),
    ).fetchall()
    slots_by_id = _load_slots(db, [row["offering_id"] for row in rows])
    return [_base_item(row, slots_by_id[row["offering_id"]]) for row in rows]


def add_to_cart(db, session_id, offering_id, semester):
    # 검사를 통과하면 담는다. 실패하면 LookupError(없는 과목) 또는 CartError.
    row = db.execute(
        "SELECT o.offering_id, o.semester, c.course_code, c.course_name"
        " FROM course_offering o JOIN course c ON c.course_id = o.course_id"
        " WHERE o.offering_id = ?",
        (offering_id,),
    ).fetchone()
    # 1) 없는 과목이거나 다른 학기
    if row is None or row["semester"] != semester:
        raise LookupError("존재하지 않는 과목입니다.")

    cart = get_cart(db, session_id, semester)
    # 2) 이미 담은 과목
    if any(item["offering_id"] == offering_id for item in cart):
        raise CartError("already_in_cart", "이미 담은 과목입니다.")
    # 3) 같은 과목의 다른 분반 (학수번호가 같으면 같은 과목)
    if any(item["course_code"] == row["course_code"] for item in cart):
        raise CartError("same_course", "같은 과목의 다른 분반이 이미 담겨 있습니다.")
    # 4) 시간 겹침
    target = _load_slots(db, [offering_id])[offering_id]
    taken = {item["course_name"]: item["slots"] for item in cart}
    names = overlap.find_conflicts(target, taken)
    if names:
        name = row["course_name"]
        topic = "은" if _has_final_consonant(name) else "는"
        with_ = "과" if _has_final_consonant(names[-1]) else "와"
        quoted = ", ".join(f'"{n}"' for n in names)
        raise CartError(
            "time_conflict",
            f'"{name}"{topic} 담긴 과목 {quoted}{with_} 시간이 겹쳐 담을 수 없습니다.',
            names,
        )

    try:
        db.execute(
            "INSERT INTO cart_item (session_id, offering_id) VALUES (?, ?)",
            (session_id, offering_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # 버튼을 빠르게 두 번 눌러 거의 동시에 들어온 경우 → UNIQUE 제약이 막아 줌
        db.rollback()
        raise CartError("already_in_cart", "이미 담은 과목입니다.")


def remove_from_cart(db, session_id, offering_id):
    # 빼기. 지웠으면 True, 원래 담겨 있지 않았으면 False.
    cursor = db.execute(
        "DELETE FROM cart_item WHERE session_id = ? AND offering_id = ?",
        (session_id, offering_id),
    )
    db.commit()
    return cursor.rowcount > 0


# ── 5주차: 강의평 ───────────────────────────────────────
def add_review(db, offering_id, rating, comment, taken_semester):
    # 강의평 저장 (과목 + 교수 단위). 새 review_id를 돌려준다. 입력값 검사는 routes.py에서.
    row = db.execute(
        "SELECT course_id, professor_id FROM course_offering WHERE offering_id = ?",
        (offering_id,),
    ).fetchone()
    if row is None:
        raise LookupError("존재하지 않는 과목입니다.")

    cursor = db.execute(
        "INSERT INTO review (course_id, professor_id, rating, comment, taken_semester)"
        " VALUES (?, ?, ?, ?, ?)",
        (row["course_id"], row["professor_id"], rating, comment, taken_semester),
    )
    db.commit()
    return cursor.lastrowid
"""