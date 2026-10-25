import sys
from pathlib import Path
from api_client import BusApiClient
from config import (
    DATA_GO_KR_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    BASE_DIR
)
from storage import StorageManager
from telegram_bot import TelegramNotifier

def test_system():
    print("==========================================")
    print("🚌 버스 데이터 수집 시스템 설정 점검 도구")
    print("==========================================")

    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        print("❌ [.env 파일 누락] 프로젝트 루트에 .env 파일이 없습니다.")
        print("   .env.example 파일을 복사하여 .env 를 만들고 키 값을 입력해주세요.")
        return

    print("✅ .env 파일 확인 완료")

    # 1. 텔레그램 연동 점검
    print("\n[1] 텔레그램 봇 연동 테스트 중...")
    notifier = TelegramNotifier()
    if not notifier.is_configured():
        print("⚠️ 텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.")
        print(f"   현재 TOKEN: {'설정됨' if TELEGRAM_BOT_TOKEN else '미입력'}")
        print(f"   현재 CHAT_ID: {'설정됨' if TELEGRAM_CHAT_ID else '미입력'}")
    else:
        success = notifier.send_message("🔔 [BusTracker 테스트] 텔레그램 연동이 성공적으로 확인되었습니다!")
        if success:
            print("✅ 텔레그램 테스트 메시지 전송 성공! (휴대폰 텔레그램 확인)")
        else:
            print("❌ 텔레그램 메시지 전송 실패. 토큰과 chat_id를 확인해주세요.")

    # 2. 공공데이터포털 API 연동 점검
    print("\n[2] 공공데이터포털 국토교통부(TAGO) API 연동 테스트 중...")
    if not DATA_GO_KR_API_KEY or "your_" in DATA_GO_KR_API_KEY:
        print("❌ 공공데이터포털 API 키가 설정되지 않았습니다.")
        print("   .env 파일에 DATA_GO_KR_API_KEY 값을 채워주세요.")
        return

    client = BusApiClient()
    for route_name in ["M6405", "M6450"]:
        print(f"\n   [{route_name}] 노선 정보 조회 시도...")
        route_id = client.search_route_id(route_name)
        if route_id:
            print(f"✅ {route_name} 노선 ID 조회 성공: {route_id}")
            stations = client.get_route_stations(route_id)
            print(f"✅ 경유 정류소 {len(stations)}개 조회 성공!")
            if stations:
                print(f"   - 기점: {stations[0]['station_name']}")
                print(f"   - 종점/회차지: {stations[-1]['station_name']}")

            locations = client.get_bus_locations(route_id)
            print(f"✅ 현재 실시간 운행 중인 차량 {len(locations)}대 발견")
            for b in locations[:4]:
                seat_str = f"잔여좌석: {b['remain_seats']}석" if b['remain_seats'] >= 0 else "잔여좌석: 미제공"
                print(f"   • 차량: {b['plate_no']} | 정류소: {b.get('latest_stop_name', '정류소')} (순번: {b['latest_stop_seq']}) | {seat_str}")
        else:
            print(f"❌ {route_name} 노선 조회 실패")

    print("\n==========================================")
    print("점검 완료!")
    print("==========================================")

if __name__ == "__main__":
    test_system()
