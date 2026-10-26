"""
app/routes.py — API 주소(엔드포인트) 목록  [3주차: 조회 / 4주차: 담기 / 5주차: 강의평]

역할
    브라우저의 요청을 받아 models.py 함수를 부르고, 결과를 JSON으로 돌려준다.
    이 파일에는 SQL을 쓰지 않는다.
    요청·응답의 정확한 모양(필드 이름, 상태 코드, 예시 JSON)은 로드맵.md "부록 A. API 명세"를 따른다.
    화면 쪽(frontend/js/api.js)도 같은 명세를 보고 만든다.

만들 것

    bp = Blueprint("api", __name__, url_prefix="/api")      ← app/__init__.py에서 등록

    current_session_id() -> str
        session["sid"]를 돌려준다. (app/__init__.py의 before_request가 미리 만들어 둔 값)

    DB 연결은 db.get_db(), 이번 학기는 current_app.config["CURRENT_SEMESTER"]로 얻는다.

    [3주차]
    GET    /api/meta                         → models.get_meta
    GET    /api/courses                      → models.search_offerings
               쿼리스트링: q, category(여러 개), day(여러 개), credit, min_rating
               여러 개인 값은 request.args.getlist("category")로 읽는다.
               credit은 int, min_rating은 float로 바꾸고, 바꿀 수 없으면 400.
               응답: {"count": 개수, "courses": [...]}
    GET    /api/courses/<int:offering_id>    → models.get_offering_detail, None이면 404

    [4주차]
    GET    /api/cart                         → models.get_cart
               응답: {"semester": ..., "total_credit": 학점 합, "items": [...]}
    POST   /api/cart     body {"offering_id": 3}
                                              → models.add_to_cart
               성공 201 {"ok": true}
               offering_id가 없거나 숫자가 아님 → 400
               LookupError → 404 {"error": "존재하지 않는 과목입니다."}
               CartError   → 409 {"error": e.message, "reason": e.reason, "conflicts": e.conflicts}
    DELETE /api/cart/<int:offering_id>       → models.remove_from_cart, False면 404

    [5주차]
    POST   /api/courses/<int:offering_id>/reviews
               body {"rating": 5, "comment": "...", "taken_semester": "2026-1"}
               먼저 검사하고, 틀리면 400 {"error": "이유"}:
                   rating          1~5 정수 (True/False, 3.5, "5"는 거절)
                   comment         앞뒤 공백을 지운 뒤 5~500자
                   taken_semester  "YYYY-1" 또는 "YYYY-2" (정규식 ^[0-9]{4}-[12]$)
               통과하면 models.add_review → 201 {"review_id": 새 번호}
               LookupError → 404

규칙
    - 오류 응답은 항상 {"error": "한국어 문장"} 모양. 화면이 이 문장을 그대로 사용자에게 보여준다.
    - body는 request.get_json(silent=True) or {} 로 읽는다 (JSON이 아니어도 서버가 죽지 않게).
    - dict를 return하면 Flask가 자동으로 JSON으로 바꿔 준다. 상태 코드는 return 값, 201 처럼 붙인다.
"""
import re
from flask import Blueprint, current_app, request, session

from . import models
from .db import get_db

bp = Blueprint("api", __name__, url_prefix="/api")

NOT_FOUND = "존재하지 않는 과목입니다."
SEMESTER_PATTERN = re.compile(r"^[0-9]{4}-[12]$")  # "YYYY-1" 또는 "YYYY-2"

def current_session_id():
    """이 브라우저의 세션 ID (app/__init__.py의 before_request가 만들어 둠)."""
    return session["sid"]


def current_semester():
    return current_app.config["CURRENT_SEMESTER"]


def error(message, status):
    return {"error": message}, status

@bp.get("/meta")
def meta():
    """A-1. 헤더 정보"""
    return models.get_meta(get_db(), current_semester())


@bp.get("/courses")
def courses():
    """A-2. 과목 검색  예) /api/courses?q=데이터&category=전공필수&day=월&credit=3&min_rating=3.5"""
    args = request.args
    try:
        credit = int(args["credit"]) if args.get("credit") else None
        min_rating = float(args["min_rating"]) if args.get("min_rating") else None
    except ValueError:
        return error("학점과 최소 평점은 숫자로 보내 주세요.", 400)

    items = models.search_offerings(
        get_db(),
        current_semester(),
        session_id=current_session_id(),
        q=args.get("q", ""),
        categories=args.getlist("category"),   # ?category=전공필수&category=교양 → 두 개
        days=args.getlist("day"),
        credit=credit,
        min_rating=min_rating,
    )
    return {"count": len(items), "courses": items}


@bp.get("/courses/<int:offering_id>")
def course_detail(offering_id):
    """A-3. 과목 상세"""
    item = models.get_offering_detail(get_db(), offering_id, current_session_id())
    if item is None:
        return error(NOT_FOUND, 404)
    return item