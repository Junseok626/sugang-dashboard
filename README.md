# sugang-dashboard

커리큘럼·강의평·시간표 겹침 정보를 한 화면에서 비교하는 수강신청 통합 비교 웹 대시보드입니다.
서버를 켠 컴퓨터에서 브라우저로 `http://localhost:5000`을 열면 됩니다. 별도 웹 서버나 DB 설치는 필요 없습니다.

---

## 0. 준비물

| 프로그램 | 확인 방법 | 비고 |
|---|---|---|
| [Python 3.10 이상](https://www.python.org/downloads/) | 터미널에서 `python --version` (macOS는 `python3 --version`) | Windows는 설치 첫 화면에서 **Add python.exe to PATH**를 꼭 체크 |
| [Git](https://git-scm.com/downloads) (선택) | `git --version` | 없으면 아래 1-1의 ZIP 다운로드를 쓰면 됩니다 |

아래 명령은 **Windows PowerShell**(VS Code 기본 터미널) 기준입니다. macOS·Linux에서 다른 부분은 따로 적었습니다.

---

## 1. 처음 한 번만: 받기와 설치

### 1-1. 저장소 받기

Git이 있으면:

```powershell
git clone https://github.com/Junseok626/sugang-dashboard.git
cd sugang-dashboard
```

Git이 없으면 [저장소 페이지](https://github.com/Junseok626/sugang-dashboard)에서 **Code → Download ZIP**으로 받아 압축을 풀고, 터미널에서 그 폴더(`sugang-dashboard-main`)로 이동합니다.

### 1-2. 가상환경 만들고 패키지 설치

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

macOS·Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

가상환경이 켜지면 터미널 줄 앞에 `(.venv)`가 붙습니다.

### 1-3. DB 만들고 데이터 넣기

DB 파일(`sugang.db`)은 저장소에 올라가 있지 않으므로, 받은 컴퓨터에서 한 번 만들어야 합니다.

```powershell
cd backend
python -m scripts.init_db
python -m scripts.import_csv
```

마지막 줄에 아래처럼 나오면 성공입니다. 중간에 나오는 `[경고]` 줄은 다른 학기 과목이나 시간표 밖 수업을 알려 주는 것이라 무시해도 됩니다.

```
courses.csv 59행, offerings.csv 86행, reviews.csv 36행 반영 (기준일 2026-11-26)
```

---

## 2. 서버 켜기 (매번)

가상환경을 켠 상태로 `backend` 폴더에서 실행합니다.

```powershell
python run.py
```

브라우저에서 **http://localhost:5000** 을 엽니다.

- 서버 끄기: 터미널에서 `Ctrl + C`
- 가상환경 끄기: `deactivate`

터미널을 새로 열었다면 다시 이 순서로 시작합니다.

```powershell
cd sugang-dashboard
.venv\Scripts\Activate.ps1
cd backend
python run.py
```

macOS·Linux에서는 두 번째 줄을 `source .venv/bin/activate`로 바꿉니다.

---

## 3. 다른 PC에서 접속하기 (같은 네트워크)

서버는 같은 와이파이·네트워크의 다른 기기에서도 접속할 수 있게 열립니다.

1. 서버를 켠 PC에서 IP 주소를 확인합니다.
   - Windows: `ipconfig` → "무선 LAN 어댑터 Wi-Fi"의 **IPv4 주소** (예: `172.17.105.23`)
   - macOS: `ipconfig getifaddr en0`
2. 서버를 켭니다 (`python run.py`). 처음 실행할 때 Windows 방화벽 창이 뜨면 Python을 **허용**합니다. 학교 와이파이처럼 "공용 네트워크"로 잡힌 곳이면 공용 네트워크에도 체크해야 합니다.
3. 다른 PC나 휴대폰의 브라우저에서 `http://<1번의 IP 주소>:5000` 을 엽니다.

IP 주소는 와이파이에 다시 접속할 때마다 바뀔 수 있으니 매번 확인하세요. 접속이 안 되면 그 네트워크가 기기끼리의 통신을 막아 둔 경우가 많습니다(학교 와이파이 등). 이때는 휴대폰 핫스팟에 두 기기를 함께 연결하고 1번부터 다시 합니다.

---

## 4. 데이터를 바꿨을 때

`backend/data/raw/`의 CSV(`courses.csv`, `offerings.csv`, `reviews.csv`)를 고쳤다면 `backend` 폴더에서 DB를 새로 만듭니다.

```powershell
python -m scripts.init_db --reset
python -m scripts.import_csv
```

- `--reset`은 DB를 지우고 다시 만듭니다. 화면에서 담은 과목과 직접 쓴 강의평도 함께 지워집니다.
- 엑셀에서 CSV를 저장할 때는 **CSV UTF-8(쉼표로 분리)** 형식을 고릅니다.
- CSV에 틀린 행이 있으면 `courses.csv 17행: …`처럼 파일 이름·행 번호·이유가 나오고, 그 파일은 반영되지 않습니다.

---

## 5. 테스트

`backend` 폴더에서:

```powershell
python -m pytest
```

테스트는 실제 DB를 건드리지 않고 임시 DB에서 돕니다. 기능별 테스트 목록은 [PROMPTS.md](PROMPTS.md)에 있습니다.

---

## 6. 자주 막히는 곳

| 증상 | 해결 |
|---|---|
| `'python'은(는) 내부 또는 외부 명령...이 아닙니다` | Python 설치 때 PATH 체크를 안 한 경우. `python` 대신 `py`를 쓰거나 Python을 다시 설치 |
| PowerShell에서 `Activate.ps1`이 보안 오류로 실행되지 않음 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`를 한 번 실행하거나, cmd에서 `.venv\Scripts\activate.bat` 사용 |
| `No module named 'app'` 또는 `No module named 'scripts'` | `backend` 폴더에서 실행하지 않은 경우. `cd backend` 후 다시 실행 |
| `No module named 'flask'` | 가상환경이 꺼져 있음. 줄 앞에 `(.venv)`가 있는지 확인하고 1-2의 활성화 명령 실행 |
| 화면에 과목이 하나도 없음 | DB가 비어 있음. 1-3의 두 명령을 실행 |
| `Address already in use` / 5000번 포트 사용 중 | 이미 켜 둔 서버가 있으면 끄고 다시 실행. macOS는 AirPlay 수신 모드가 5000번을 쓰므로 `backend/run.py`의 `port=5000`을 `5001`로 바꾸고 `http://localhost:5001`로 접속 |

---

## 7. 더 보기

- [초기설정.md](초기설정.md): 폴더 구조와 개발 환경 자세히
- [로드맵.md](로드맵.md): 주차별 계획과 API 명세
- [스키마 구조.md](스키마%20구조.md): DB 설계
- [PROMPTS.md](PROMPTS.md): 기능 요구사항과 테스트 기록
