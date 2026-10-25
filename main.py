import argparse
from datetime import datetime, time as dtime
import logging
import time
import schedule
from run_session import run_session

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def check_and_run_current_window():
    """현재 시각이 수집 시간대(05:00~10:00, 17:00~22:00) 안이면 즉시 세션 시작"""
    now_time = datetime.now().time()
    morning_start = dtime(5, 0)
    morning_end = dtime(10, 0)
    evening_start = dtime(17, 0)
    evening_end = dtime(22, 0)

    if morning_start <= now_time < morning_end:
        logger.info("현재 시각이 아침 출근 수집 시간대(05:00~10:00)입니다. 즉시 수집을 시작합니다.")
        run_session("morning")
    elif evening_start <= now_time < evening_end:
        logger.info("현재 시각이 저녁 퇴근 수집 시간대(17:00~22:00)입니다. 즉시 수집을 시작합니다.")
        run_session("evening")
    else:
        logger.info("현재는 수집 시간대가 아닙니다. 다음 스케줄(05:00 또는 17:00)을 대기합니다.")

def main():
    parser = argparse.ArgumentParser(description="M6405 / M6450 버스 자동 스케줄러 데몬")
    parser.add_argument("--run-now", action="store_true",
                        help="시작 시 현재 시각이 05~10시 또는 17~22시 사이라면 즉시 수집 세션을 가동")
    args = parser.parse_args()

    logger.info("==========================================")
    logger.info("M6405 & M6450 버스 시간/좌석 자동 수집 스케줄러 시작")
    logger.info("• 아침 세션: 매일 05:00 ~ 10:00 (송도 -> 서울 출근)")
    logger.info("• 저녁 세션: 매일 17:00 ~ 22:00 (서울 -> 송도 퇴근)")
    logger.info("==========================================")

    # 스케줄 등록
    schedule.every().day.at("05:00").do(lambda: run_session("morning"))
    schedule.every().day.at("17:00").do(lambda: run_session("evening"))

    if args.run_now:
        check_and_run_current_window()

    logger.info("스케줄러가 활성화되었습니다. 대기 중... (중단: Ctrl+C)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("스케줄러가 종료되었습니다.")

if __name__ == "__main__":
    main()
