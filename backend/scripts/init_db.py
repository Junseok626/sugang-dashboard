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
