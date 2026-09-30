"""
tests/test_init_db.py — 스키마 검사  [1주차에 채움]

사용하는 픽스처: db (conftest.py — 빈 테이블만 있는 임시 DB 연결)
함수 이름은 test_로 시작해야 pytest가 찾는다. 오류가 나야 맞는 경우는 with pytest.raises(sqlite3.IntegrityError): 로 감싼다.

채울 테스트

    test_all_tables_created(db)
        sqlite_master에서 테이블 이름을 읽어 8개가 모두 있는지
        {"department", "course", "professor", "course_offering",
         "offering_slot", "review", "cart_item", "data_source"}

    test_foreign_keys_on(db)
        db.execute("PRAGMA foreign_keys").fetchone()[0] == 1   (app.db.connect가 켰는지)

    test_course_code_unique(db)
        같은 course_code로 course를 두 번 INSERT하면 IntegrityError

    test_category_check(db)
        category에 "전공필수/전공선택/교양" 말고 다른 값(예: "전공핵심")을 넣으면 IntegrityError

    test_rating_check(db)
        review.rating에 0이나 6을 넣으면 IntegrityError

    test_slot_time_check(db)
        offering_slot에 start_time "12:00", end_time "11:00"을 넣으면 IntegrityError

    test_offering_unique(db)
        같은 (semester, course_id, section)을 두 번 넣으면 IntegrityError

    test_foreign_key_enforced(db)
        없는 department_id(예: 999)로 course를 넣으면 IntegrityError

    test_create_tables_twice(db)
        scripts.init_db.create_tables(db)를 한 번 더 불러도 오류가 없는지 (IF NOT EXISTS)
"""
