"""
app/db.py — SQLite 연결 열고 닫기  [1주차: connect, 3주차: 나머지]

역할
    DB 연결 방법을 한 곳에 모은다. API 요청 하나마다 연결을 하나 열고, 요청이 끝나면 닫는다.
    Flask 공식 튜토리얼의 db.py와 같은 방식이다.
    https://flask.palletsprojects.com/en/stable/tutorial/database/

채울 함수

    [1주차] connect(db_path) -> sqlite3.Connection
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
            → 결과를 row["course_name"]처럼 컬럼 이름으로 꺼낼 수 있다. dict(row)로 바꾸면 JSON으로 보내기 쉽다.
        conn.execute("PRAGMA foreign_keys = ON")
            → SQLite는 이걸 켜야 외래키(FK) 제약을 검사한다. 연결할 때마다 켜야 한다.
        return conn
        scripts/init_db.py, scripts/import_csv.py, tests/conftest.py도 이 함수를 쓴다.

    [3주차] get_db() -> sqlite3.Connection
        flask.g에 연결이 없으면 connect(current_app.config["DB_PATH"])로 만들어 g.db에 넣고,
        이미 있으면 그대로 돌려준다. (한 요청 안에서는 연결 하나를 같이 씀)

    [3주차] close_db(e=None) -> None
        db = g.pop("db", None) 후 db가 있으면 db.close()

    [3주차] init_app(app) -> None
        app.teardown_appcontext(close_db)  → 요청이 끝나면 자동으로 close_db 실행

SQL을 쓸 때 꼭 지킬 것
    값은 항상 ? 자리표시자로 넘긴다. f-string으로 SQL을 만들지 않는다.
        좋음:  db.execute("SELECT * FROM course WHERE course_code = ?", (code,))
        나쁨:  db.execute(f"SELECT * FROM course WHERE course_code = '{code}'")
    나쁜 방식은 과목명에 따옴표가 들어가면 깨지고, SQL 인젝션 공격에도 뚫린다.
"""
import sqlite3

def connect(db_path) -> sqlite3.Connection:
    """DB파일에 연결, 결과를 이름으로 꺼낼 수 있게함. 외래키 검사 ON"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
