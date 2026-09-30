"""
run.py — 서버를 켜는 파일  [3주차에 채움]

역할
    `python run.py` 한 줄로 Flask 개발 서버를 띄운다.
    - http://localhost:5000          → frontend/ 화면 (index.html)
    - http://localhost:5000/api/...  → API (JSON)
    화면과 API가 같은 주소(localhost:5000)에서 나오므로 CORS 설정이 필요 없다.

무엇을 채우나
    1. app 패키지의 create_app()을 불러와 앱을 만든다.
           from app import create_app
           app = create_app()
    2. 이 파일을 직접 실행했을 때만 서버를 켠다.
           if __name__ == "__main__":
               app.run(debug=True, port=5000)
       debug=True면 코드를 저장할 때마다 서버가 자동으로 다시 켜지고, 오류 화면이 자세히 나온다.

어떻게 실행하나
    backend 폴더에서, 가상환경을 켠 상태로:  python run.py
    (다른 폴더에서 실행하면 `import app`을 찾지 못한다.)

완료 확인
    서버를 켠 뒤 브라우저에서 http://localhost:5000/api/meta 를 열었을 때 JSON이 보이면 성공.
    macOS에서 5000번 포트가 이미 쓰이고 있다는 오류가 나면 port=5001로 바꾼다.
"""
