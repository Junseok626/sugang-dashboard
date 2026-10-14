"""
app/models.py — DB에서 꺼내고 넣는 함수 모음  [3주차: 조회 / 4주차: 담기 / 5주차: 강의평]

역할
    SQL은 전부 이 파일에 모은다. routes.py는 "요청 읽기 → 이 파일의 함수 호출 → JSON 응답"만 한다.
    - 모든 함수는 첫 번째 인자로 DB 연결(db)을 받는다. 테스트에서 임시 DB를 넣기 쉽다.
    - 돌려주는 값은 dict나 list로 바꿔서(dict(row)) 돌려준다. 그래야 routes.py에서 바로 JSON이 된다.
    - 테이블과 컬럼 이름은 "스키마 구조.md"를 따른다. 검색 SQL의 뼈대는 스키마 구조.md §6에 있다.
    - 응답 필드 이름은 로드맵.md "부록 A. API 명세"와 똑같이 맞춘다.

── 3주차: 조회 ──────────────────────────────────────────────────────

    get_meta(db, semester) -> dict
        {"semester": "2026-2", "last_updated": "2026-09-20"}
        last_updated = data_source에서 data_type = 'offerings'인 행의 MAX(captured_at). 기록이 없으면 None.

    search_offerings(db, semester, session_id=None, q="", categories=(), days=(),
                     credit=None, min_rating=None) -> list[dict]
        이번 학기 개설 과목 목록 = 과목 찾기 표의 한 줄씩.
        한 줄에 들어갈 키:
            offering_id, course_code, course_name, professor, credit, category, classroom,
            day_time(문자열), slots(목록), avg_rating(소수 1자리, 강의평 없으면 None),
            review_count, in_cart, conflict
        조건 붙이는 법 (값이 비어 있으면 그 조건은 빼고 SQL을 만든다):
            q           과목명 또는 교수명에 부분 일치   c.course_name LIKE '%' || ? || '%' OR p.name LIKE ...
            categories  하나라도 맞으면                 c.category IN (?, ?, ...)
            days        수업 요일 중 하나라도 포함        EXISTS (SELECT 1 FROM offering_slot s
                                                          WHERE s.offering_id = o.offering_id AND s.day IN (?, ...))
            credit      같은 학점                       c.credit = ?
            min_rating  평균 평점 이상 (평점 없는 과목 제외)  avg_rating >= ?
        slots, day_time:
            해당 offering들의 offering_slot을 한 번에 읽어 offering_id별로 묶고,
            overlap.format_day_time(slots)로 day_time 문자열을 만든다.
        in_cart, conflict [4주차에 추가]:
            session_id가 담은 과목 목록을 get_cart()로 읽어 비교한다.
            in_cart  = 이미 담은 과목인지
            conflict = 담지 않은 과목이면서 overlap.find_conflicts() 결과가 있는지 (담은 과목은 항상 False)
            3주차에는 둘 다 False로 채워 둔다.
        정렬: 과목명 가나다순, 같으면 분반순

    get_offering_detail(db, offering_id, session_id=None) -> dict | None
        search_offerings 한 줄과 같은 키 + department(학과명), semester, section, reviews
        reviews = 같은 (course_id, professor_id)의 강의평 목록, 최신순(created_at DESC, review_id DESC)
            한 개: {"review_id", "rating", "comment", "taken_semester", "created_at"}
        offering_id가 없으면 None → routes.py가 404로 바꾼다.

── 4주차: 담기 (내 시간표) ─────────────────────────────────────────

    class CartError(Exception)
        담기를 거절할 때 쓰는 예외. 속성 3개를 가진다.
            reason     "already_in_cart" | "same_course" | "time_conflict"
            message    화면에 그대로 띄울 한국어 문장
            conflicts  겹치는 과목 이름 목록 (time_conflict일 때만, 나머지는 [])

    get_cart(db, session_id, semester) -> list[dict]
        이 브라우저가 담은 이번 학기 과목, 담은 순서(added_at, cart_id)대로.
        한 개: offering_id, course_code, course_name, professor, credit, category, classroom, day_time, slots

    add_to_cart(db, session_id, offering_id, semester) -> None
        아래 순서로 검사하고, 통과하면 cart_item에 INSERT 후 db.commit().
          1) offering이 없거나 다른 학기          → LookupError 발생 (routes에서 404)
          2) 이미 담은 offering                  → CartError("already_in_cart", "이미 담은 과목입니다.")
          3) 같은 과목(course_id)의 다른 분반을 담음 → CartError("same_course", "같은 과목의 다른 분반이 이미 담겨 있습니다.")
          4) 담은 과목과 시간이 겹침               → CartError("time_conflict",
                 '"데이터시각화"는 담긴 과목 "기계학습"과 시간이 겹쳐 담을 수 없습니다.', ["기계학습"])
        겹침 검사: get_cart()로 담은 과목들의 slots를 {과목명: slots}로 만들어 overlap.find_conflicts()에 넣는다.

    remove_from_cart(db, session_id, offering_id) -> bool
        DELETE 후 지운 행이 있으면 True, 원래 없었으면 False (cursor.rowcount 사용). db.commit() 잊지 말 것.

── 5주차: 강의평 ─────────────────────────────────────────────────────

    add_review(db, offering_id, rating, comment, taken_semester) -> int
        offering_id로 course_id, professor_id를 찾아 review에 INSERT하고 새 review_id(cursor.lastrowid)를 돌려준다.
        offering이 없으면 LookupError.
        입력값 검사(별점 범위, 글자 수, 학기 형식)는 routes.py에서 먼저 하고, 여기서는 저장만 한다.
"""
import sqlite3
from . import overlap

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
_BASE_KEYS = ("offering_id", "course_code", "course_name", "professor", "credit", "category",
              "classroom")

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
