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
