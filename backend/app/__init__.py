"""
app/__init__.py — Flask 앱 조립  [3주차에 채움, 4주차에 세션 부분 추가]

역할
    흩어져 있는 부품(config.py, db.py, routes.py)을 모아 Flask 앱 하나를 만드는
    create_app() 함수를 둔다. 이 파일이 있어서 app/ 폴더가 파이썬 "패키지"가 된다.

채울 함수
    create_app(test_config: dict | None = None) -> Flask

    1. 앱 만들기 — frontend/ 폴더를 정적 파일 폴더로 지정
           app = Flask(__name__, static_folder=str(config.FRONTEND_DIR), static_url_path="")
       static_url_path=""이면 frontend/css/dashboard.css가 /css/dashboard.css 주소로 나간다.
       index.html 안의 상대 경로(css/..., js/...)가 그대로 동작한다.

    2. 설정 읽기
           app.config.from_object(config)          # config.py의 대문자 변수들
           if test_config: app.config.update(test_config)
       테스트는 create_app({"TESTING": True, "DB_PATH": 임시_DB_경로})처럼 불러
       실제 sugang.db 대신 임시 DB를 쓰게 한다.

    3. db.init_app(app) — 요청이 끝날 때 DB 연결을 닫도록 등록

    4. from .routes import bp → app.register_blueprint(bp)

    5. "/" 주소 → frontend/index.html 돌려주기
           @app.get("/")
           def index(): return app.send_static_file("index.html")

    6. [4주차] 브라우저 구분용 세션 ID 만들기
           @app.before_request
           def ensure_session_id():
               if "sid" not in session:
                   session["sid"] = uuid.uuid4().hex
                   session.permanent = True     # PERMANENT_SESSION_LIFETIME(180일) 동안 유지
       이 sid가 cart_item.session_id에 저장된다. 로그인 없이 "내 시간표"를 구분하는 방법이다.
       session은 SECRET_KEY로 서명된 쿠키라서 사용자가 값을 몰래 바꿀 수 없다.

    7. /api 로 시작하는 주소의 404·405·500 오류를 JSON으로 바꾸기
           @app.errorhandler(404) 등에서 request.path가 "/api"로 시작하면
           return {"error": "요청한 주소를 찾을 수 없습니다."}, 404
       화면 코드가 오류도 항상 {"error": "..."} 모양으로 받을 수 있게 한다.

    8. return app

완료 확인
    tests/conftest.py의 app 픽스처가 create_app(...)으로 앱을 만들고,
    tests/test_api.py가 통과하면 된다.
"""
