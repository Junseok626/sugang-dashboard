"""
app/overlap.py — 수업 시간 문자열 처리와 시간 겹침 판단
    [2주차: parse_day_time, format_day_time, slots_overlap / 4주차: find_conflicts]

역할
    Flask나 DB와 상관없는 "순수 함수"만 둔다. 입력을 넣으면 결과만 돌려주므로
    서버를 켜지 않고도 tests/test_overlap.py로 바로 검사할 수 있다.
    import_csv.py(CSV → offering_slot)와 models.py(겹침 검사, day_time 문자열 만들기)가 함께 쓴다.

수업 시간 표기 규칙 (CSV의 day_time 칸, API 응답의 day_time 필드 공통)
    "화11:00-12:00,목11:00-12:00"
    - 요일 한 글자 + 시작 HH:MM + "-" + 끝 HH:MM, 여러 개는 쉼표로 이어 적는다.
    - 빈 문자열은 "시간 미정"(온라인 등) → 수업 시간 0개
    - frontend/js/dashboard.js의 parseSlots()가 읽는 형식과 같다.
    - 저장할 때는 시각을 항상 두 자리로 맞춘다 (9:00 → 09:00).
      그래야 문자열 비교("09:00" < "10:30")가 시간 비교와 똑같이 동작한다.

수업 시간 한 칸(slot)의 모양 — 이 파일 전체에서 같은 dict를 쓴다
    {"day": "화", "start": "11:00", "end": "12:00"}

채울 함수

    [2주차] parse_day_time(text: str) -> list[dict]
        "화11:00-12:00,목11:00-12:00"
            → [{"day": "화", "start": "11:00", "end": "12:00"},
               {"day": "목", "start": "11:00", "end": "12:00"}]
        - 쉼표로 나누고, 각 조각의 공백을 모두 지운 뒤 정규식으로 읽는다.
              ^([월화수목금토일])([0-9]{1,2}:[0-9]{2})-([0-9]{1,2}:[0-9]{2})$
        - "9:00"은 "09:00"으로 바꿔 저장한다.
        - 아래 경우는 ValueError("무엇이 틀렸는지 + 올바른 예") 를 발생시킨다.
          import_csv.py가 이 문장을 "몇 번째 줄 오류"와 함께 보여준다.
            · 형식이 다름 (예: "화11:00~12:00", "화요일 11시")
            · 시는 0~23, 분은 0~59가 아님
            · 시작이 끝보다 늦거나 같음 (예: "화12:00-11:00")
        - text가 빈 문자열이면 [] 를 돌려준다.

    [2주차] format_day_time(slots: list[dict]) -> str
        parse_day_time의 반대. 요일 순서(월→일), 같은 요일이면 시작 시각 순으로 정렬해서 이어 붙인다.
        [] 이면 "" 를 돌려준다.

    [2주차] slots_overlap(a: dict, b: dict) -> bool
        같은 요일이고  a["start"] < b["end"]  그리고  b["start"] < a["end"]  이면 True.
        끝과 시작이 딱 맞닿는 경우(10:00-11:00 과 11:00-12:00)는 겹침이 아니다.

    [4주차] find_conflicts(target: list[dict], others: dict[str, list[dict]]) -> list[str]
        target = 담으려는 과목의 수업 시간들
        others = {"기계학습": [slot, ...], "데이터베이스": [slot, ...]}  (이미 담긴 과목 이름 → 수업 시간들)
        target의 칸 하나라도 겹치는 과목의 이름을 목록으로 돌려준다. 없으면 [].
        models.add_to_cart()가 담기 전에, models.search_offerings()가 "시간 겹침" 표시를 정할 때 쓴다.
"""

import re # 정규식 모듈

DAY_ORDER = "월화수목금토일"
# 요일 한 글자 + 시:분 - 시:분  (시는 1~2자리, 분은 2자리)
_SLOT_PATTERN = re.compile(r"^([월화수목금토일])([0-9]{1,2}):([0-9]{2})-([0-9]{1,2}):([0-9]{2})$")
EXAMPLE = "예: 화11:00-12:00"


def _to_clock(hour, minute, piece):
    """("9", "00") → "09:00". 없는 시각이면 ValueError."""
    hour, minute = int(hour), int(minute)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f'"{piece}"에 없는 시각이 있습니다 ({EXAMPLE})')
    return f"{hour:02d}:{minute:02d}"


def parse_day_time(text):
    """"화11:00-12:00,목11:00-12:00" → 수업 시간 칸 목록. 형식이 틀리면 ValueError."""
    text = (text or "").strip()
    if not text:
        return []  # 시간 미정

    slots = []
    for piece in text.split(","):
        piece = "".join(piece.split())  # 공백 모두 제거: "월 9:00-10:30" → "월9:00-10:30"
        if not piece:
            raise ValueError(f'쉼표 사이에 빈 칸이 있습니다 ({EXAMPLE})')

        match = _SLOT_PATTERN.match(piece)
        if not match:
            raise ValueError(f'"{piece}" 형식 오류 ({EXAMPLE})')

        day, start_h, start_m, end_h, end_m = match.groups()
        start = _to_clock(start_h, start_m, piece)
        end = _to_clock(end_h, end_m, piece)
        if start >= end:
            raise ValueError(f'"{piece}" 시작 시각이 끝 시각보다 같거나 늦습니다 ({EXAMPLE})')

        slots.append({"day": day, "start": start, "end": end})
    return slots


def format_day_time(slots):
    """parse_day_time의 반대. 요일 순(월→일), 같은 요일이면 시작 시각 순으로 이어 붙인다."""
    ordered = sorted(slots, key=lambda s: (DAY_ORDER.index(s["day"]), s["start"]))
    return ",".join(f'{s["day"]}{s["start"]}-{s["end"]}' for s in ordered)


def slots_overlap(a, b):
    """같은 요일이고 시간이 조금이라도 겹치면 True. 끝과 시작이 맞닿기만 하면 False."""
    return a["day"] == b["day"] and a["start"] < b["end"] and b["start"] < a["end"]


def find_conflicts(target, others):
    """target(담으려는 과목의 칸들)과 겹치는 과목 이름 목록.

    others = {"기계학습": [칸, ...], "데이터베이스": [칸, ...]}  (이미 담긴 과목 이름 → 칸들)
    """
    return [
        name for name, slots in others.items()
        if any(slots_overlap(t, s) for t in target for s in slots)
    ]
