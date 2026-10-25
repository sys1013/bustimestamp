from typing import Optional
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / ".bus_tracker.pid"
LOG_FILE = BASE_DIR / "manual_run.log"

def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def get_running_pid() -> Optional[int]:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if is_running(pid):
                return pid
        except ValueError:
            pass
    return None

def start_collection(session: str, direction: str):
    pid = get_running_pid()
    if pid:
        print(f"⚠️ 이미 수집 프로세스가 실행 중입니다! (PID: {pid})")
        print("중단하려면 'python bus_ctl.py stop' 명령을 사용하세요.")
        return

    cmd = [
        sys.executable,
        str(BASE_DIR / "run_session.py"),
        "--session", session,
    ]
    if direction:
        cmd.extend(["--direction", direction])

    with open(LOG_FILE, "a") as f:
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STREDERR if hasattr(subprocess, "STREDERR") else f, cwd=str(BASE_DIR))

    PID_FILE.write_text(str(proc.pid))
    print(f"🚀 [수집 시작] 백그라운드 프로세스가 시작되었습니다. (PID: {proc.pid})")
    print(f"   로그 확인: tail -f {LOG_FILE.name}")
    print("   종료 및 텔레그램 발송: python bus_ctl.py stop")

def stop_collection():
    pid = get_running_pid()
    if not pid:
        print("ℹ️ 현재 실행 중인 수집 프로세스가 없습니다.")
        if PID_FILE.exists():
            PID_FILE.unlink()
        return

    print(f"🛑 [수집 종료 요청] PID {pid}에 안전 종료 신호(SIGTERM)를 전달합니다...")
    try:
        os.kill(pid, signal.SIGTERM)
        # 프로세스가 데이터를 저장하고 텔레그램을 보낼 때까지 최대 15초 대기
        for _ in range(15):
            if not is_running(pid):
                break
            time.sleep(1)

        if not is_running(pid):
            print("✅ 프로세스가 정상적으로 데이터를 저장하고 텔레그램 발송을 마친 후 종료되었습니다.")
        else:
            print("⚠️ 프로세스가 아직 마무리 중입니다. 잠시 후 완전히 종료됩니다.")
    except Exception as e:
        print(f"종료 처리 중 오류: {e}")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()

def status_collection():
    pid = get_running_pid()
    if pid:
        print(f"🟢 [실행 중] 수집 프로세스가 정상 작동 중입니다. (PID: {pid})")
        if LOG_FILE.exists():
            print("\n[최근 로그 5줄]")
            lines = LOG_FILE.read_text().strip().splitlines()
            for line in lines[-5:]:
                print(f"  {line}")
    else:
        print("⚪ [정지 상태] 실행 중인 수집 프로세스가 없습니다.")

def main():
    parser = argparse.ArgumentParser(description="버스 데이터 수집 제어 도구 (시작 / 중지 / 상태)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # start 명령어
    start_parser = subparsers.add_parser("start", help="백그라운드 수집 시작")
    start_parser.add_argument("--session", choices=["morning", "evening", "manual"], default="manual")
    start_parser.add_argument("--direction", choices=["to_seoul", "to_songdo", "both"], default="both")

    # stop 명령어
    subparsers.add_parser("stop", help="수집 중단 및 텔레그램 전송")

    # status 명령어
    subparsers.add_parser("status", help="현재 수집 상태 확인")

    args = parser.parse_args()

    if args.command == "start":
        start_collection(args.session, args.direction)
    elif args.command == "stop":
        stop_collection()
    elif args.command == "status":
        status_collection()

if __name__ == "__main__":
    main()
