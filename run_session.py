import argparse
from datetime import datetime, time as dtime
import logging
import signal
import sys
import threading
import time
from api_client import BusApiClient
from config import (
    TARGET_ROUTES,
    SESSION_CONFIG,
    COLLECT_INTERVAL_SEC,
)
from storage import StorageManager
from telegram_bot import TelegramNotifier
from tracker import BusTripTracker

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 수집 중단 플래그
stop_requested = False

def sig_handler(signum, frame):
    global stop_requested
    logger.info(f"종료 시그널({signum}) 수신. 수집을 안전하게 마무리하고 텔레그램으로 전송합니다...")
    stop_requested = True

def run_session(session_key: str, max_duration_sec: int = None, custom_direction: str = None, interactive_stop: bool = False):
    """
    session_key: 'morning', 'evening', 또는 'manual'
    max_duration_sec: 최대 실행 시간 (초)
    custom_direction: 'to_seoul', 'to_songdo', 'both'
    interactive_stop: True면 엔터(Enter) 입력 시 수집 종료
    """
    global stop_requested
    stop_requested = False

    # 시그널 핸들러 등록 (SIGINT, SIGTERM)
    try:
        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)
    except ValueError:
        pass  # 서브스레드일 경우 생략

    conf = SESSION_CONFIG.get(session_key, {
        "name": "수동 테스트 세션",
        "start_time": datetime.now().strftime("%H:%M"),
        "end_time": "23:59",
        "direction": custom_direction or "both",
    })

    session_name = conf["name"]
    direction = custom_direction or conf.get("direction", "both")
    end_time_str = conf.get("end_time", "23:59")
    end_h, end_m = map(int, end_time_str.split(":"))
    end_dtime = dtime(end_h, end_m)

    logger.info(f"=== {session_name} 수집 시작 ===")
    logger.info(f"방향: {direction} | 종료 기준: {end_time_str} | 수집 주기: {COLLECT_INTERVAL_SEC}초")

    api_client = BusApiClient()
    trackers: list[BusTripTracker] = []

    # 1. 노선 정보 및 정류소 목록 초기화
    for route_name in TARGET_ROUTES:
        logger.info(f"[{route_name}] 노선 ID 검색 중...")
        route_id = api_client.search_route_id(route_name)
        if not route_id:
            logger.error(f"[{route_name}] 노선 ID를 찾을 수 없습니다. (API 키 확인 필요)")
            continue

        logger.info(f"[{route_name}] 정류소 목록 조회 중 (routeId: {route_id})...")
        stations = api_client.get_route_stations(route_id)
        if not stations:
            logger.warning(f"[{route_name}] 정류소 목록이 비어 있습니다.")

        tracker = BusTripTracker(route_name, route_id, stations, target_direction=direction)
        trackers.append(tracker)

    if not trackers:
        logger.error("수집 가능한 노선이 없습니다. API 설정을 확인하세요.")
        return

    # 대화형 엔터 키 감지 백그라운드 스레드
    if interactive_stop:
        def wait_for_enter():
            global stop_requested
            try:
                input("\n👉 [종료 안내] 수집을 중단하고 텔레그램으로 결과를 받으려면 언제든 [Enter] 키를 누르세요.\n\n")
                stop_requested = True
            except (EOFError, KeyboardInterrupt):
                stop_requested = True

        stop_thread = threading.Thread(target=wait_for_enter, daemon=True)
        stop_thread.start()

    start_timestamp = time.time()

    # 2. 실시간 루프 수집
    while not stop_requested:
        now = datetime.now()

        # 시간 종료 조건 검사
        if max_duration_sec:
            if (time.time() - start_timestamp) >= max_duration_sec:
                logger.info(f"지정된 실행 시간({max_duration_sec}초)이 경과하여 수집을 종료합니다.")
                break
        elif session_key in SESSION_CONFIG:
            if now.time() >= end_dtime:
                logger.info(f"세션 정규 종료 시각({end_time_str})에 도달하여 수집을 종료합니다.")
                break

        # 각 노선별 실시간 위치 조회 및 추적
        for tracker in trackers:
            try:
                locations = api_client.get_bus_locations(tracker.route_id)
                tracker.process_locations(locations)
            except Exception as e:
                logger.error(f"[{tracker.route_name}] 위치 수집 중 에러: {e}")

        # 수집 주기 동안 분할 수면 (중단 요청 즉각 반응)
        for _ in range(COLLECT_INTERVAL_SEC):
            if stop_requested:
                break
            time.sleep(1)

    # 3. 데이터 취합 및 CSV 저장
    all_records = []
    for tracker in trackers:
        all_records.extend(tracker.records)

    timestamp_suffix = datetime.now().strftime("%H%M%S") if session_key == "manual" else session_key
    file_tag = f"{session_key}_{timestamp_suffix}" if session_key == "manual" else session_key
    today_str = datetime.now().strftime("%Y-%m-%d")

    csv_path, summary_text = StorageManager.save_records(all_records, file_tag, today_str)
    logger.info(f"데이터가 저장되었습니다: {csv_path}")
    print("\n" + summary_text + "\n")

    # 4. 텔레그램 알림 발송
    notifier = TelegramNotifier()
    if notifier.is_configured():
        logger.info("텔레그램으로 요약 리포트 및 CSV 파일을 전송합니다...")
        notifier.send_report(summary_text, csv_path)
    else:
        logger.warning(".env 파일에 텔레그램 봇 토큰 및 Chat ID가 없어 알림을 건너뜁니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M6405/M6450 버스 실시간 데이터 수집기")
    parser.add_argument("--session", choices=["morning", "evening", "manual"], default="morning",
                        help="수집 세션 선택")
    parser.add_argument("--direction", choices=["to_seoul", "to_songdo", "both"], default=None,
                        help="수집 방향 강제 지정")
    parser.add_argument("--duration", type=int, default=None,
                        help="실행 시간 지정 (초 단위)")
    parser.add_argument("--interactive", action="store_true",
                        help="엔터 키 입력으로 수동 종료 활성화")
    args = parser.parse_args()

    run_session(args.session, args.duration, args.direction, args.interactive)
