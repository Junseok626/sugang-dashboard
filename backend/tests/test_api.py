"""
tests/test_api.py — API 검사  [3주차: 조회 / 4주차: 담기 / 5주차: 강의평]

사용하는 픽스처: client, app (conftest.py — 샘플 CSV를 넣은 임시 DB로 만든 앱)
    res = client.get("/api/courses?q=데이터")
    res.status_code == 200
    data = res.get_json()
응답 모양은 로드맵.md "부록 A. API 명세"와 같아야 한다.

채울 테스트

    [3주차]
    test_meta                  /api/meta → semester "2026-2", last_updated "2026-09-20"
    test_index_page            / → 200, frontend/index.html 내용이 나오는지 (Flask가 화면도 내보내는지)
    test_search_all            /api/courses → count == len(courses), 한 줄에 부록 A의 키가 모두 있는지
    test_search_q              ?q=데이터 → 과목명이나 교수명에 "데이터"가 들어간 것만
    test_search_category       ?category=전공필수&category=교양 → 두 구분만
    test_search_day            ?day=월 → 월요일 수업이 하나라도 있는 과목만 (시간 미정 과목은 빠짐)
    test_search_credit         ?credit=3
    test_search_min_rating     ?min_rating=4 → 평균 4.0 이상만, 강의평 없는 과목은 빠짐
    test_search_bad_param      ?credit=abc → 400 + error
    test_search_no_result      ?q=없는과목 → 200, count 0 (오류가 아님)
    test_detail                /api/courses/<id> → department, semester, reviews(최신순), avg_rating, review_count
    test_detail_404            없는 번호 → 404 + error
    test_unknown_api_404       /api/없는주소 → 404 + JSON error

    [4주차]
    test_cart_empty            처음 /api/cart → items [], total_credit 0
    test_cart_add_and_list     담기 → 201, /api/cart에 보이고 total_credit이 학점 합과 같은지
    test_cart_duplicate        같은 과목 두 번 → 409, reason "already_in_cart"
    test_cart_same_course      같은 과목 다른 분반 → 409, reason "same_course"
    test_cart_time_conflict    시간 겹치는 과목 → 409, reason "time_conflict", conflicts에 담긴 과목 이름
    test_cart_no_time_ok       시간 미정 과목은 겹침 없이 담기는지
    test_cart_not_found        없는 offering_id → 404
    test_cart_bad_body         body 없음 / offering_id가 "abc" → 400
    test_cart_remove           빼기 → 200, 한 번 더 빼면 404
    test_cart_is_per_session   app.test_client()를 두 개 만들어, 한쪽에서 담은 과목이 다른 쪽 /api/cart에 안 보이는지
    test_search_flags          담은 뒤 /api/courses에서 담은 과목 in_cart True, 겹치는 과목 conflict True

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
