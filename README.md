# sugang-dashboard

커리큘럼·강의평·시간표 겹침 정보를 한 화면에서 비교하는 수강신청 통합 비교 웹 대시보드.

- `backend/`: Python (Flask) + SQLite + pandas, JSON API 제공
- `frontend/`: HTML/CSS/JS, 백엔드 API를 호출해 화면 구성

VS CODE에서 웹 확인하기
터미널에서 이 명령어 실행
```
python -m http.server 5510 --directory C:/Users/user/Documents/sugang-dashboard/frontend
```
Serving HTTP on :: port 5510 나오면
http://localhost:5510 접속

엑셀 파일 저장할 때 CSV-UTF8 파일로 저장.
