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
