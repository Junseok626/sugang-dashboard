"""
tests/test_import_csv.py — scripts/import_csv.py 검사  [2주차에 채움]

사용하는 픽스처: db, sample_raw_dir (conftest.py)
    from scripts.import_csv import import_all
    result = import_all(db, sample_raw_dir, "2026-09-20", "2026-2")

채울 테스트

    test_import_counts(db, sample_raw_dir)
        import_all이 돌려준 개수와 course, course_offering, review 테이블의 행 수가 CSV 행 수와 같은지

    test_import_twice_no_duplicates(db, sample_raw_dir)
        import_all을 두 번 불러도 course, course_offering, offering_slot, review 행 수가 그대로인지

    test_names_become_ids(db, sample_raw_dir)
        CSV에 여러 번 나온 학과명·교수명이 department, professor 테이블에 한 번씩만 들어갔는지

    test_slots_created(db, sample_raw_dir)
        "화11:00-12:00,목11:00-12:00"인 과목의 offering_slot이 2행이고 값이 맞는지
        day_time이 빈칸인 과목은 offering_slot이 0행인지

    test_changed_time_replaces_slots(db, sample_raw_dir)
        offerings.csv의 시간을 바꿔 다시 넣으면 옛 시간 칸이 남지 않고 새 시간으로 바뀌는지

    test_bad_credit_rolls_back(db, tmp_path)
        credit 칸이 "삼"인 courses.csv → 오류가 나고, 오류 문장에 행 번호가 들어 있고, course 테이블은 비어 있는지

    test_unknown_course_code(db, tmp_path)
        offerings.csv에 courses.csv에 없는 학수번호 → 오류 문장에 그 학수번호와 행 번호가 들어 있는지

    test_bad_day_time(db, tmp_path)
        day_time이 "화11:00~12:00" → 오류, course_offering은 하나도 들어가지 않았는지

    test_missing_column(db, tmp_path)
        헤더에서 category를 뺀 courses.csv → 어떤 컬럼이 없는지 알려 주는 오류

    test_reviews_optional(db, tmp_path)
        reviews.csv가 없어도 courses, offerings는 정상 반영되는지

    test_data_source_logged(db, sample_raw_dir)
        data_source에 파일마다 한 줄씩, captured_at "2026-09-20", offerings 행의 semester "2026-2"

    오류 테스트용 CSV는 tmp_path 아래에 직접 써서 만든다. 오류를 어떤 예외로 알릴지는
    import_csv.py를 만들 때 정한 것(예: ValueError)에 맞춰 pytest.raises(...)에 적는다.
"""
