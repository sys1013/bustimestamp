import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# API 및 텔레그램 설정
DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
COLLECT_INTERVAL_SEC = int(os.getenv("COLLECT_INTERVAL_SEC", "40"))

# 데이터 저장 경로
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 대상 버스 노선 정의
TARGET_ROUTES = ["M6405", "M6450"]

# 세션별 시간 및 방향 설정
# direction: 'to_seoul' (아침 출근: 송도 -> 서울), 'to_songdo' (저녁 퇴근: 서울 -> 송도)
SESSION_CONFIG = {
    "morning": {
        "name": "아침 출근 세션",
        "start_time": "05:00",
        "end_time": "10:00",
        "direction": "to_seoul",
    },
    "evening": {
        "name": "저녁 퇴근 세션",
        "start_time": "17:00",
        "end_time": "22:00",
        "direction": "to_songdo",
    }
}

# 국토교통부(TAGO) 표준 버스 API 엔드포인트
TAGO_ROUTE_URL = "https://apis.data.go.kr/1613000/BusRouteInfoInqireService"
TAGO_LOCATION_URL = "https://apis.data.go.kr/1613000/BusLcInfoInqireService"
TAGO_ARRIVAL_URL = "https://apis.data.go.kr/1613000/ArvlInfoInqireService"
TAGO_STATION_URL = "https://apis.data.go.kr/1613000/BusSttnInfoInqireService"

# 인천광역시 BIS 엔드포인트 (보조)
INCHEON_BIS_ROUTE_URL = "https://apis.data.go.kr/6280000/busRouteService"
INCHEON_BIS_LOCATION_URL = "https://apis.data.go.kr/6280000/busLocationService"

# 인천 도시코드 (TAGO 표준)
INCHEON_CITY_CODE = "23"

# 대상 노선 인천 BIS routeId 매핑 (M6405, M6450)
ROUTE_INFO_MAP = {
    "M6405": {
        "route_id": "165000215",
        "name": "M6405",
        "origin": "웰카운티",
        "destination": "강남역서초현대타워앞"
    },
    "M6450": {
        "route_id": "161000004",
        "name": "M6450",
        "origin": "e편한세상정문",
        "destination": "한국무역센터.삼성역"
    }
}
