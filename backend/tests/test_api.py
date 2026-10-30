"""
tests/test_api.py — API 검사  [3주차: 조회 / 4주차: 담기 / 5주차: 강의평]

사용하는 픽스처: client, app (conftest.py — 샘플 CSV를 넣은 임시 DB로 만든 앱)
    res = client.get("/api/courses?q=데이터")
    res.status_code == 200
    data = res.get_json()
응답 모양은 로드맵.md "부록 A. API 명세"와 같아야 한다.

채울 테스트
    [5주차]
    test_review_create         작성 → 201, 상세의 reviews 맨 앞에 보이고 review_count·avg_rating이 바뀌는지
    test_review_shared_by_professor
                               같은 과목·같은 교수의 다른 분반 상세에도 같은 강의평이 보이는지
    test_review_validation     아래는 모두 400
                                   rating 0, 6, 3.5, "5", 빠짐
                                   comment "좋아요"(5자 미만), 501자, 공백만
                                   taken_semester "2026-3", "26-1", 빠짐
    test_review_404            없는 offering_id → 404
"""
"""
tests/test_api.py — API 검사  [3주차: 조회 / 4주차: 담기 / 5주차: 강의평]

사용하는 픽스처: client (conftest.py — 샘플 CSV를 넣은 임시 DB로 만든 앱)
응답 모양은 로드맵.md "부록 A. API 명세"와 같아야 한다.

샘플 데이터의 offering_id (offerings.csv에 적힌 순서대로 1번부터)
    1 기계학습 CSE401-01 (김OO, 화·목 11-12, 평균 4.5)
    2 데이터베이스 CSE402-01 (이OO, 월·수 10-11, 평균 3.5)
    3 데이터베이스 CSE402-02 (이OO, 화·목 15-16, 평균 3.5)
    4 데이터시각화 CSE403-01 (박OO, 화·목 11-12, 평균 4.0)
    5 실용머신러닝 CSE404-01 (김OO, 월·수 12-13, 평균 5.0)
    6 캡스톤디자인 CSE405-01 (미정, 시간 미정, 강의평 없음)
    7 글쓰기와소통 GEN101-01 (최OO, 금 09-11, 2학점, 강의평 없음)
"""
from app.db import connect

COURSE_KEYS = {
    "offering_id", "course_code", "course_name", "professor", "credit", "category",
    "classroom", "day_time", "slots", "avg_rating", "review_count", "in_cart", "conflict",
}


def get_courses(client, query=""):
    """/api/courses 응답에서 과목 목록만 꺼낸다."""
    res = client.get("/api/courses" + query)
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] == len(data["courses"])
    return data["courses"]


def names(courses):
    return sorted(c["course_name"] for c in courses)


# ── 3주차: 조회 ─────────────────────────────────────────
def test_meta(client):
    res = client.get("/api/meta")
    assert res.status_code == 200
    assert res.get_json() == {"semester": "2026-2", "last_updated": "2026-09-20"}


def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "<html" in res.get_data(as_text=True)


def test_search_all(client):
    courses = get_courses(client)
    assert len(courses) == 7
    for course in courses:
        assert set(course) == COURSE_KEYS
    # 3주차에는 아무것도 담지 않았으므로 둘 다 False
    assert not any(c["in_cart"] or c["conflict"] for c in courses)


def test_search_sorted_by_name(client):
    course_names = [c["course_name"] for c in get_courses(client)]
    assert course_names == sorted(course_names)


def test_search_course_shape(client):
    course = next(c for c in get_courses(client) if c["offering_id"] == 1)
    assert course["course_code"] == "CSE401"
    assert course["professor"] == "김OO"
    assert course["day_time"] == "화11:00-12:00,목11:00-12:00"
    assert course["slots"] == [
        {"day": "화", "start": "11:00", "end": "12:00"},
        {"day": "목", "start": "11:00", "end": "12:00"},
    ]
    assert course["avg_rating"] == 4.5
    assert course["review_count"] == 2


def test_search_no_time_and_no_review(client):
    course = next(c for c in get_courses(client) if c["offering_id"] == 6)
    assert course["day_time"] == ""
    assert course["slots"] == []
    assert course["avg_rating"] is None
    assert course["review_count"] == 0


def test_search_q_course_name(client):
    assert names(get_courses(client, "?q=데이터")) == ["데이터베이스", "데이터베이스", "데이터시각화"]


def test_search_q_professor(client):
    assert names(get_courses(client, "?q=김")) == ["기계학습", "실용머신러닝"]


def test_search_category(client):
    courses = get_courses(client, "?category=전공필수&category=교양")
    assert {c["category"] for c in courses} == {"전공필수", "교양"}
    assert len(courses) == 4


def test_search_day(client):
    # 월요일 수업이 하나라도 있는 과목만. 시간 미정 과목은 빠진다.
    assert names(get_courses(client, "?day=월")) == ["데이터베이스", "실용머신러닝"]


def test_search_credit(client):
    assert names(get_courses(client, "?credit=2")) == ["글쓰기와소통"]


def test_search_min_rating(client):
    courses = get_courses(client, "?min_rating=4")
    assert names(courses) == ["기계학습", "데이터시각화", "실용머신러닝"]
    assert all(c["avg_rating"] >= 4 for c in courses)


def test_search_filters_combined(client):
    assert names(get_courses(client, "?q=데이터&day=화&min_rating=3.5")) == ["데이터베이스", "데이터시각화"]


def test_search_bad_param(client):
    for query in ["?credit=abc", "?min_rating=높음"]:
        res = client.get("/api/courses" + query)
        assert res.status_code == 400
        assert "error" in res.get_json()


def test_search_no_result(client):
    res = client.get("/api/courses?q=없는과목")
    assert res.status_code == 200
    assert res.get_json() == {"count": 0, "courses": []}


def test_detail(client):
    res = client.get("/api/courses/1")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data) == COURSE_KEYS | {"department", "semester", "section", "reviews"}
    assert data["department"] == "컴퓨터공학과"
    assert data["semester"] == "2026-2"
    assert data["section"] == "01"
    assert len(data["reviews"]) == data["review_count"] == 2
    for review in data["reviews"]:
        assert set(review) == {"review_id", "rating", "comment", "taken_semester", "created_at"}


def test_detail_reviews_shared_by_sections(client):
    # 같은 과목·같은 교수의 두 분반은 같은 강의평을 보여준다
    first = client.get("/api/courses/2").get_json()
    second = client.get("/api/courses/3").get_json()
    assert first["reviews"] == second["reviews"]
    assert first["avg_rating"] == second["avg_rating"] == 3.5


def test_detail_404(client):
    res = client.get("/api/courses/999")
    assert res.status_code == 404
    assert res.get_json() == {"error": "존재하지 않는 과목입니다."}


def test_unknown_api_404(client):
    res = client.get("/api/없는주소")
    assert res.status_code == 404
    assert "error" in res.get_json()

# ── 4주차: 담기 (내 시간표) ─────────────────────────────
def add(client, offering_id):
    """담기 요청을 보내고 응답을 돌려준다."""
    return client.post("/api/cart", json={"offering_id": offering_id})


def cart(client):
    res = client.get("/api/cart")
    assert res.status_code == 200
    return res.get_json()


def test_cart_empty(client):
    assert cart(client) == {"semester": "2026-2", "total_credit": 0, "items": []}


def test_cart_add_and_list(client):
    for offering_id in (2, 1, 7):  # 데이터베이스(3), 기계학습(3), 글쓰기와소통(2)
        res = add(client, offering_id)
        assert res.status_code == 201
        assert res.get_json() == {"ok": True}

    data = cart(client)
    assert [item["offering_id"] for item in data["items"]] == [2, 1, 7]  # 담은 순서
    assert data["total_credit"] == 8
    assert set(data["items"][0]) == {
        "offering_id", "course_code", "course_name", "professor", "credit",
        "category", "classroom", "day_time", "slots",
    }


def test_cart_duplicate(client):
    add(client, 1)
    res = add(client, 1)
    assert res.status_code == 409
    assert res.get_json() == {
        "error": "이미 담은 과목입니다.", "reason": "already_in_cart", "conflicts": [],
    }


def test_cart_same_course(client):
    add(client, 2)                 # 데이터베이스 01반
    res = add(client, 3)           # 데이터베이스 02반 (시간은 안 겹침)
    assert res.status_code == 409
    assert res.get_json() == {
        "error": "같은 과목의 다른 분반이 이미 담겨 있습니다.", "reason": "same_course", "conflicts": [],
    }


def test_cart_time_conflict(client):
    add(client, 1)                 # 기계학습 화·목 11-12
    res = add(client, 4)           # 데이터시각화 화·목 11-12
    assert res.status_code == 409
    assert res.get_json() == {
        "error": '"데이터시각화"는 담긴 과목 "기계학습"과 시간이 겹쳐 담을 수 없습니다.',
        "reason": "time_conflict",
        "conflicts": ["기계학습"],
    }
    assert [item["offering_id"] for item in cart(client)["items"]] == [1]  # 거절된 과목은 안 담김


def test_cart_no_time_ok(client):
    add(client, 1)
    assert add(client, 6).status_code == 201  # 캡스톤디자인 (시간 미정) → 겹침 없음


def test_cart_not_found(client):
    res = add(client, 999)
    assert res.status_code == 404
    assert res.get_json() == {"error": "존재하지 않는 과목입니다."}


def test_cart_other_semester(app, client):
    # 이번 학기(2026-2)가 아닌 개설 과목은 없는 과목으로 취급한다
    conn = connect(app.config["DB_PATH"])
    other_id = conn.execute(
        "INSERT INTO course_offering (course_id, professor_id, semester, section)"
        " VALUES (1, 1, '2026-1', '01')"
    ).lastrowid
    conn.commit()
    conn.close()

    res = add(client, other_id)
    assert res.status_code == 404
    assert res.get_json() == {"error": "존재하지 않는 과목입니다."}


def test_cart_bad_body(client):
    bad_requests = [
        client.post("/api/cart", json={}),                     # offering_id 없음
        client.post("/api/cart", json={"offering_id": "abc"}),  # 글자
        client.post("/api/cart", json={"offering_id": "1"}),    # 숫자처럼 보이는 글자
        client.post("/api/cart", json={"offering_id": True}),   # True는 1로 통과하면 안 됨
        client.post("/api/cart", data="1"),                     # JSON이 아님
    ]
    for res in bad_requests:
        assert res.status_code == 400
        assert res.get_json() == {"error": "offering_id를 숫자로 보내 주세요."}
    assert cart(client)["items"] == []


def test_cart_remove(client):
    add(client, 1)
    res = client.delete("/api/cart/1")
    assert res.status_code == 200
    assert res.get_json() == {"ok": True}
    assert cart(client)["items"] == []

    res = client.delete("/api/cart/1")  # 이미 뺀 과목
    assert res.status_code == 404
    assert res.get_json() == {"error": "담겨 있지 않은 과목입니다."}


def test_cart_remove_then_add_again(client):
    add(client, 1)
    client.delete("/api/cart/1")
    assert add(client, 4).status_code == 201  # 기계학습을 뺐으니 데이터시각화가 담김


def test_cart_is_per_session(app, client):
    other = app.test_client()  # 다른 브라우저
    add(client, 1)
    assert cart(other)["items"] == []
    assert add(other, 4).status_code == 201   # 다른 브라우저에서는 겹침 아님
    assert [i["offering_id"] for i in cart(client)["items"]] == [1]


def test_search_flags(client):
    add(client, 1)  # 기계학습
    flags = {c["offering_id"]: (c["in_cart"], c["conflict"]) for c in get_courses(client)}
    assert flags[1] == (True, False)    # 담은 과목
    assert flags[4] == (False, True)    # 데이터시각화: 시간 겹침
    assert flags[6] == (False, False)   # 시간 미정: 겹침 없음
    assert sum(in_cart for in_cart, _ in flags.values()) == 1
    assert sum(conflict for _, conflict in flags.values()) == 1


def test_detail_flags(client):
    add(client, 1)
    assert client.get("/api/courses/1").get_json()["in_cart"] is True
    assert client.get("/api/courses/4").get_json()["conflict"] is True