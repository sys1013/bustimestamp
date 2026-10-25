import sys
from run_session import run_session

def main():
    print("==========================================")
    print("🚌 M6405 & M6450 실시간 버스 수동 수집기")
    print("==========================================")
    print("수집할 운행 방향을 선택하세요:")
    print("  1. 아침 출근 방향 (송도 -> 서울 강남/삼성)")
    print("  2. 저녁 퇴근 방향 (서울 강남/삼성 -> 송도)")
    print("  3. 전체 양방향 (상행 + 하행 모두 기록)")
    print("  0. 종료")
    print("------------------------------------------")

    try:
        choice = input("선택 번호 입력 (기본값: 3): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n취소되었습니다.")
        sys.exit(0)

    if choice == "1":
        direction = "to_seoul"
        dir_label = "출근 (송도 -> 서울)"
    elif choice == "2":
        direction = "to_songdo"
        dir_label = "퇴근 (서울 -> 송도)"
    elif choice == "0":
        print("종료합니다.")
        sys.exit(0)
    else:
        direction = "both"
        dir_label = "전체 양방향"

    print(f"\n[선택됨: {dir_label}]")
    print("데이터 수집을 시작합니다.")
    print("💡 언제든지 [Enter] 키를 누르시면 수집이 종료되고 CSV 저장 및 텔레그램 전송이 수행됩니다.\n")

    # interactive_stop=True 활성화하여 엔터 입력 시 종료되도록 실행
    run_session(session_key="manual", custom_direction=direction, interactive_stop=True)

if __name__ == "__main__":
    main()
