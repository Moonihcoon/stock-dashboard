상승 이유 자동 수집기 사용 안내
==============================

이 프로그램은 PC에서 매일 네이버 뉴스 검색 API로 "특징주" 기사를 모아서
대시보드의 "상승 이유" 탭에 쓸 파일(data/reasons.json)과 엑셀 누적 파일을 만듭니다.
(웹페이지 크롤링이 아니라 공식 검색 API를 씁니다.)

[ 1. 한 번만 하는 준비 ]

(1) 네이버 API 키 받기
  - https://developers.naver.com 접속 → 로그인 → Application → 애플리케이션 등록
  - 사용 API: "검색" 선택
  - 비로그인 오픈API 서비스 환경: "WEB 설정"을 고르고 서비스 URL에 http://localhost 입력
  - 등록하면 Client ID 와 Client Secret 이 나옵니다. (화면 문구는 조금 다를 수 있습니다)

(2) Python 확인
  - 시작 메뉴에서 명령 프롬프트(cmd)를 열고  python --version  입력
  - 버전이 나오면 됩니다. (키움 데이터 수집에 이미 쓰셨다면 설치되어 있습니다)
  - 엑셀 누적까지 쓰려면  pip install openpyxl  (없어도 json 저장은 됩니다)

(3) 대시보드 저장소를 PC로 내려받기
  - Git for Windows 설치: https://git-scm.com/download/win (기본값으로 계속 다음)
  - cmd 에서:
      git clone https://github.com/Moonihcoon/stock-dashboard.git C:\stock\stock-dashboard
  - 이 폴더 안에 index.html 과 data 폴더가 있어야 합니다.

(4) 이 수집기 폴더 두기
  - 이 zip 의 파일들을 C:\stock\reasons_tool 에 풉니다. (저장소 폴더 안이 아닌 다른 곳)
  - config.ini.sample 을 복사해서 config.ini 로 이름을 바꾸고 메모장으로 엽니다.
  - client_id, client_secret 에 받은 값을 넣고, repo 에 C:\stock\stock-dashboard 를 적습니다.
  - 자동 업로드까지 쓰려면 push = yes 로 바꿉니다. (아래 3번 참고)

[ 2. 손으로 한 번 돌려 보기 ]

  - 상승이유_수집.bat 을 더블클릭합니다.
  - 끝나면 C:\stock\stock-dashboard\data\reasons.json 이 생기고,
    reasons_tool 폴더에 상승이유_누적.xlsx 와 log.txt 가 생깁니다.
  - log.txt 에 "새로 추가 N건"이 보이면 정상입니다.

[ 3. GitHub 로 올리기 ]

  방법 A (자동): config.ini 에서 push = yes. 처음 한 번은 cmd 에서
      cd C:\stock\stock-dashboard
      git push
    를 실행해 GitHub 로그인 창이 뜨면 로그인해 두세요. 이후에는 수집기가 알아서 올립니다.
  방법 B (수동): GitHub 저장소 화면에서 Add file → Upload files 로
    data/reasons.json 을 올리고 Commit changes 를 누릅니다.

[ 4. 매일 자동 실행 (작업 스케줄러) ]

  cmd(관리자 권한 아님) 에서 한 줄:
    schtasks /Create /SC WEEKLY /D MON,TUE,WED,THU,FRI /TN StockReasons /TR "C:\stock\reasons_tool\상승이유_수집.bat" /ST 16:00
  - 평일 16:00 에 실행됩니다. 시간은 /ST 값을 바꾸면 됩니다.
  - 그 시각에 PC 가 켜져 있고 로그인되어 있어야 합니다.
  - 지우려면: schtasks /Delete /TN StockReasons /F

[ 알아 둘 점 ]

  - 종목명 찾기는 기사 제목에 종목명이 들어 있는지 보는 방식입니다. 이름이 짧거나 흔한 종목은
    잘못 붙을 수 있고, 제목에 종목명이 없는 기사는 놓칩니다.
  - "이유"는 제목에서 종목명과 말머리를 뺀 문장이라 실제 원인과 다를 수 있습니다.
  - 네이버 검색 API는 검색어당 최근 1000건까지만 줍니다. PC 가 며칠 꺼져 있었다면
    그 사이 기사가 일부 빠질 수 있습니다. fetch_days 로 조회 기간을 바꿀 수 있습니다.
  - API 호출 한도와 이용 약관은 네이버 개발자센터 안내를 확인하세요.
  - config.ini 는 비밀값이 들어 있으니 GitHub 에 올리지 마세요.
