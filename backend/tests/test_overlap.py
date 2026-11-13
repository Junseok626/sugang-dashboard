"""
tests/test_overlap.py — app/overlap.py 검사  [2주차에 채움, find_conflicts는 4주차]

픽스처 없이 함수만 불러서 검사한다:  from app.overlap import parse_day_time, ...

tests/test_overlap.py — app/overlap.py 검사

픽스처 없이 함수만 불러서 검사한다.
find_conflicts는 4주차에 채우므로, 아직 없으면 그 테스트만 건너뛴다(skip).
"""
import pytest

from app import overlap
from app.overlap import format_day_time, parse_day_time, slots_overlap

# 4주차 전에는 find_conflicts가 없어서 None → 아래 find_conflicts 테스트는 skip
find_conflicts = getattr(overlap, "find_conflicts", None)
needs_find_conflicts = pytest.mark.skipif(
    find_conflicts is None, reason="find_conflicts는 4주차에 채움"
)


def slot(day, start, end):
    """테스트용 수업 시간 한 칸."""
    return {"day": day, "start": start, "end": end}


# ── parse_day_time ───────────────────────────────────────
def test_parse_two_slots():
    assert parse_day_time("화11:00-12:00,목11:00-12:00") == [
        slot("화", "11:00", "12:00"),
        slot("목", "11:00", "12:00"),
    ]


def test_parse_spaces_and_one_digit_hour():
    assert parse_day_time("월 9:00-10:30") == [slot("월", "09:00", "10:30")]


def test_parse_spaces_after_comma():
    assert parse_day_time("화11:00-12:00, 목11:00-12:00") == [
        slot("화", "11:00", "12:00"),
        slot("목", "11:00", "12:00"),
    ]


@pytest.mark.parametrize("text", ["", "   ", None])
def test_parse_empty_means_no_time(text):
    assert parse_day_time(text) == []


@pytest.mark.parametrize("text", [
    "화11:00~12:00",        # 물결표
    "화요일11:00-12:00",    # 요일을 두 글자 이상
    "화25:00-26:00",        # 없는 시각
    "화11:60-12:00",        # 없는 분
    "화12:00-11:00",        # 끝이 시작보다 빠름
    "화11:00-11:00",        # 시작과 끝이 같음
    "화11:00-12:00,",       # 쉼표 뒤가 비어 있음
    "11:00-12:00",          # 요일 없음
])
def test_parse_invalid_raises(text):
    with pytest.raises(ValueError):
        parse_day_time(text)


def test_parse_error_message_has_example():
    with pytest.raises(ValueError, match="화11:00-12:00"):
        parse_day_time("화11:00~12:00")


# ── format_day_time ──────────────────────────────────────
def test_format_round_trip():
    text = "화11:00-12:00,목11:00-12:00"
    assert format_day_time(parse_day_time(text)) == text


def test_format_sorts_by_day_then_start():
    slots = [
        slot("목", "11:00", "12:00"),
        slot("화", "15:00", "16:00"),
        slot("화", "09:00", "10:00"),
    ]
    assert format_day_time(slots) == "화09:00-10:00,화15:00-16:00,목11:00-12:00"


def test_format_empty():
    assert format_day_time([]) == ""


# ── slots_overlap ────────────────────────────────────────
@pytest.mark.parametrize("a, b, expected", [
    (slot("화", "10:00", "11:30"), slot("화", "11:00", "12:00"), True),   # 일부 겹침
    (slot("화", "10:00", "13:00"), slot("화", "11:00", "12:00"), True),   # 한쪽이 다른 쪽 안에 포함
    (slot("화", "11:00", "12:00"), slot("화", "11:00", "12:00"), True),   # 완전히 같음
    (slot("화", "10:00", "11:00"), slot("화", "11:00", "12:00"), False),  # 끝과 시작이 맞닿음
    (slot("월", "11:00", "12:00"), slot("화", "11:00", "12:00"), False),  # 다른 요일
])
def test_slots_overlap(a, b, expected):
    assert slots_overlap(a, b) is expected
    assert slots_overlap(b, a) is expected  # 순서를 바꿔도 결과가 같아야 함


# ── find_conflicts (4주차) ───────────────────────────────
CART = {
    "기계학습": parse_day_time("화11:00-12:00,목11:00-12:00"),
    "데이터베이스": parse_day_time("월10:00-11:00,수10:00-11:00"),
    "실용머신러닝": parse_day_time("월12:00-13:00,수12:00-13:00"),
}


@needs_find_conflicts
def test_find_conflicts_returns_only_overlapping_name():
    target = parse_day_time("목11:30-12:30")
    assert find_conflicts(target, CART) == ["기계학습"]


@needs_find_conflicts
def test_find_conflicts_several():
    target = parse_day_time("월10:30-12:30")  # 데이터베이스, 실용머신러닝 둘 다 겹침
    assert sorted(find_conflicts(target, CART)) == ["데이터베이스", "실용머신러닝"]


@needs_find_conflicts
def test_find_conflicts_none():
    assert find_conflicts(parse_day_time("금09:00-11:00"), CART) == []


@needs_find_conflicts
def test_find_conflicts_no_time_course():
    assert find_conflicts([], CART) == []  # 시간 미정 과목은 겹치지 않음


@needs_find_conflicts
def test_find_conflicts_empty_cart():
    assert find_conflicts(parse_day_time("화11:00-12:00"), {}) == []
