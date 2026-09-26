// 임시 샘플 데이터 (Figma 디자인 기준).
// 백엔드 API가 준비되면 dashboard.js의 loadCourses()에서 fetch로 교체.
// 필드명은 초기설정.md의 course / course_offering 스키마를 따름.
// day_time: "요일HH:MM-HH:MM"을 쉼표로 구분 (30분 단위, 09:00~19:00)
const SAMPLE_COURSES = [
  { offering_id: 1, course_name: "기계학습", professor: "김OO", day_time: "화11:00-12:00,목11:00-12:00", credit: 3, category: "전공선택", rating: 4.2 },
  { offering_id: 2, course_name: "데이터베이스", professor: "이OO", day_time: "월10:00-11:00,수10:00-11:00", credit: 3, category: "전공필수", rating: 3.8 },
  { offering_id: 3, course_name: "데이터시각화", professor: "박OO", day_time: "화11:00-12:00,목11:00-12:00", credit: 3, category: "전공선택", rating: 4.0 },
  { offering_id: 4, course_name: "실용머신러닝", professor: "김OO", day_time: "월12:00-13:00,수12:00-13:00", credit: 3, category: "전공선택", rating: 4.5 },
];

// 처음 화면에 담겨 있는 과목 (offering_id)
const SAMPLE_CART = [1, 2];
