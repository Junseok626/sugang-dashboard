# sugang-dashboard

커리큘럼·강의평·시간표 겹침 정보를 한 화면에서 비교하는 수강신청 통합 비교 웹 대시보드.

- `backend/`: Python (Flask) + SQLite + pandas, JSON API 제공
- `frontend/`: HTML/CSS/JS, 백엔드 API를 호출해 화면 구성

VS CODE에서 웹 확인하기
터미널에서 이 명령어 실행
```
python -m http.server 5510 --directory C:/Users/user/Documents/sugang-dashboard/frontend
```
'backend' 폴더에서 python run.py를 터미널에 입력.
http://localhost:5000 접속.

엑셀 파일 저장할 때 CSV-UTF8 파일로 저장.
```
# 1. main 브랜치로 이동 후 최신 상태로 업데이트
git switch main
git pull origin main

# 2. 새 브랜치 생성 및 전환
git switch -c feature/login

# 3. 코드 작성 (에디터에서 작업)

# 4. 변경사항 스테이징 및 커밋
git add .
git commit -m "로그인 기능 구현"

# 5. 원격 저장소로 push (최초 push 시 -u로 upstream 설정)
git push -u origin feature/login

# 6. Pull Request 생성
gh pr create --base main --title "로그인 기능 구현" --body "로그인 기능 구현했습니다"

# 7. merge후 브랜치 삭제까지
merge 한 이후 vscode에서 git pull origin main (최신 상태로 업데이트)
git branch -d feature/login
```
