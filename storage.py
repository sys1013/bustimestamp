from datetime import datetime
from pathlib import Path
import pandas as pd
from config import DATA_DIR

# 한글 CSV 컬럼명 매핑 (분석하기 가장 편한 순서)
KOREAN_COLUMN_MAP = {
    "date": "날짜",
    "route_name": "노선명",
    "plate_no": "차량번호",
    "direction": "운행방향",
    "stop_seq": "정류소순번",
    "station_name": "정류소명",
    "time": "통과시각",
    "remain_seats": "잔여좌석수",
    "seat_change": "좌석변동",
    "duration_str": "구간소요시간",
    "total_duration_str": "누적소요시간",
    "duration_sec": "소요시간(초)",
    "total_duration_sec": "누적시간(초)",
}

class StorageManager:
    @staticmethod
    def save_records(records: list[dict], session_key: str, target_date: str = None) -> tuple[Path, str]:
        """
        레코드를 버스 1대별 연속 타임라인 형태로 정렬하여 한글 CSV로 저장하고 요약 리포트 반환
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

        # 1. 버스 1대(차량번호) 단위로 이동 경로가 차례대로 이어지도록 정렬
        sort_cols = [c for c in ["route_name", "plate_no", "stop_seq", "time"] if c in df.columns]
        df = df.sort_values(by=sort_cols).reset_index(drop=True)

        # 2. 요약 리포트 생성
        summary = StorageManager.generate_summary(df, target_date, session_key)

        # 3. CSV 저장 시 사용자 친화적인 한글 컬럼 및 열 순서 배치
        ordered_keys = [k for k in KOREAN_COLUMN_MAP.keys() if k in df.columns]
        export_df = df[ordered_keys].rename(columns=KOREAN_COLUMN_MAP)
        export_df.to_csv(file_path, index=False, encoding="utf-8-sig")

        return file_path, summary

    @staticmethod
    def generate_summary(df: pd.DataFrame, target_date: str, session_key: str) -> str:
        session_title = "아침 출근 (05:00~10:00)" if session_key == "morning" else "저녁 퇴근 (17:00~22:00)"
        total_records = len(df)
        unique_buses = df["plate_no"].nunique()

        lines = [
            f"🚌 [버스 출퇴근 분석 리포트 - {target_date}]",
            f"📌 세션: {session_title}",
            f"📊 총 기록 건수: {total_records}건 | 감지 차량: {unique_buses}대",
            "================================="
        ]

        # 노선별, 차량별 상세 분석
        for route_name, r_group in df.groupby("route_name"):
            lines.append(f"\n🔹 【 {route_name} 】 (총 {r_group['plate_no'].nunique()}대 운행)")

            for plate_no, b_group in r_group.groupby("plate_no"):
                b_sorted = b_group.sort_values(by=["stop_seq", "time"]).reset_index(drop=True)
                first_row = b_sorted.iloc[0]
                last_row = b_sorted.iloc[-1]

                # 만석(0석) 발생 정류장 확인
                zero_seat_rows = b_sorted[b_sorted["remain_seats"] == 0]
                if not zero_seat_rows.empty:
                    zero_sttn = zero_seat_rows.iloc[0]["station_name"]
                    full_info = f"🚨 만석발생: {zero_sttn}"
                else:
                    # 최소 잔여좌석
                    valid_s = pd.to_numeric(b_sorted["remain_seats"], errors="coerce").dropna()
                    min_s = int(valid_s.min()) if not valid_s.empty else "미제공"
                    full_info = f"최소잔여: {min_s}석"

                # 총 이동 시간
                tot_time = last_row.get("total_duration_str", "-")
                if tot_time == "-" and len(b_sorted) > 1:
                    t_diff = int((pd.to_datetime(last_row["time"]) - pd.to_datetime(first_row["time"])).total_seconds())
                    tot_time = f"{t_diff // 60}분"

                lines.append(
                    f" • [{plate_no}] {first_row['station_name']}({first_row['time'][:5]}) ➔ "
                    f"{last_row['station_name']}({last_row['time'][:5]}) | "
                    f"소요: {tot_time} | {full_info}"
                )

        lines.append("\n📁 버스 1대별 상세 정류장 타임라인은 첨부된 엑셀(CSV) 파일을 확인하세요.")
        return "\n".join(lines)
