from datetime import datetime
from pathlib import Path
import pandas as pd
from config import DATA_DIR

# 한글 CSV 컬럼명 매핑
KOREAN_COLUMN_MAP = {
    "date": "날짜",
    "time": "통과시각",
    "route_name": "노선명",
    "direction": "운행방향",
    "plate_no": "차량번호",
    "stop_seq": "정류소순번",
    "station_name": "정류소명",
    "remain_seats": "잔여좌석수",
    "duration_sec": "소요시간(초)",
    "duration_str": "소요시간",
}

class StorageManager:
    @staticmethod
    def save_records(records: list[dict], session_key: str, target_date: str = None) -> tuple[Path, str]:
        """
        레코드를 한글 컬럼 CSV 파일로 저장하고, 요약 텍스트를 반환
        반환값: (저장된_파일_경로, 텔레그램_요약_메시지)
        """
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        filename = f"{target_date}_{session_key}.csv"
        file_path = DATA_DIR / filename

        df = pd.DataFrame(records)
        if df.empty:
            empty_df = pd.DataFrame(columns=list(KOREAN_COLUMN_MAP.values()))
            empty_df.to_csv(file_path, index=False, encoding="utf-8-sig")
            summary = f"[{target_date} {session_key}] 수집된 버스 운행 데이터가 없습니다."
            return file_path, summary

        # 1. 요약 리포트 생성 (내부 계산)
        summary = StorageManager.generate_summary(df, target_date, session_key)

        # 2. CSV 저장 시 사용자용 100% 한글 컬럼으로 변경
        export_df = df.rename(columns=KOREAN_COLUMN_MAP)
        export_df.to_csv(file_path, index=False, encoding="utf-8-sig")

        return file_path, summary

    @staticmethod
    def generate_summary(df: pd.DataFrame, target_date: str, session_key: str) -> str:
        session_title = "아침 출근 (05:00~10:00)" if session_key == "morning" else "저녁 퇴근 (17:00~22:00)"
        total_records = len(df)
        unique_buses = df["plate_no"].nunique()

        lines = [
            f"🚌 [버스 운행 기록 요약 - {target_date}]",
            f"📌 세션: {session_title}",
            f"📊 총 기록 건수: {total_records}건",
            f"🚍 운행 감지 차량 수: {unique_buses}대",
            "--------------------------------"
        ]

        # 노선별 요약
        for route_name, group in df.groupby("route_name"):
            route_buses = group["plate_no"].nunique()
            lines.append(f"\n🔹 {route_name} (총 {route_buses}대 운행)")

            # 숫자형 좌석 데이터만 필터링
            valid_seats = group[pd.to_numeric(group["remain_seats"], errors="coerce").notnull()].copy()
            valid_seats["remain_seats"] = valid_seats["remain_seats"].astype(int)

            if not valid_seats.empty:
                # 정류장별 평균 잔여 좌석 (주요 정류소 상위 5개)
                seat_by_station = valid_seats.groupby(["stop_seq", "station_name"])["remain_seats"].mean().reset_index()
                lines.append(" [정류소별 평균 잔여좌석]")
                for _, row in seat_by_station.head(6).iterrows():
                    lines.append(f"  • {row['station_name']}: 평균 {row['remain_seats']:.1f}석")

            # 소요 시간 계산
            valid_durations = group[pd.to_numeric(group["duration_sec"], errors="coerce").notnull()].copy()
            valid_durations["duration_sec"] = valid_durations["duration_sec"].astype(float)
            if not valid_durations.empty:
                avg_dur_min = (valid_durations["duration_sec"].mean()) / 60
                lines.append(f"  • 정류소 간 평균 이동소요시간: {avg_dur_min:.1f}분")

        lines.append("\n📁 상세 데이터는 첨부된 CSV 파일을 확인해주세요.")
        return "\n".join(lines)
