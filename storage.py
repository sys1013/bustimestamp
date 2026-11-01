from datetime import datetime
from pathlib import Path
import pandas as pd
from config import DATA_DIR

# 한글 CSV 컬럼명 매핑 (버스번호별 -> 시간대별 분석하기 가장 편한 순서)
KOREAN_COLUMN_MAP = {
    "date": "날짜",
    "route_name": "노선명",
    "time_slot": "시간대",
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
    def _ensure_time_slot_and_trip(df: pd.DataFrame) -> pd.DataFrame:
        """
        각 버스번호(route_name) 및 차량(plate_no) 운행 회차별로 최초 감지 시각 기준 시간대(예: '05시대')를 부여하고 정렬
        """
        df = df.copy()
        if "trip_id" not in df.columns:
            df["trip_id"] = 1

        # 차량별/회차별 최초 통과시각 계산
        first_times = (
            df.groupby(["route_name", "plate_no", "trip_id"], as_index=False)["time"]
            .min()
            .rename(columns={"time": "_trip_start_time"})
        )
        df = df.merge(first_times, on=["route_name", "plate_no", "trip_id"], how="left")

        if "time_slot" not in df.columns:
            df["time_slot"] = df["_trip_start_time"].str.slice(0, 2) + "시대"
        else:
            missing_mask = df["time_slot"].isna() | (df["time_slot"] == "")
            df.loc[missing_mask, "time_slot"] = df.loc[missing_mask, "_trip_start_time"].str.slice(0, 2) + "시대"

        # 정렬 기준: 노선명(버스번호) -> 시간대 -> 회차 시작시각 -> 차량번호 -> 정류소순번 -> 통과시각
        sort_cols = [
            c for c in ["route_name", "time_slot", "_trip_start_time", "plate_no", "trip_id", "stop_seq", "time"]
            if c in df.columns
        ]
        df = df.sort_values(by=sort_cols).reset_index(drop=True)
        return df

    @staticmethod
    def save_records(records: list[dict], session_key: str, target_date: str = None) -> tuple[Path, str]:
        """
        레코드를 각 버스번호별 -> 시간대별 -> 버스 1대별 연속 타임라인 형태로 정렬하여 한글 CSV로 저장하고 요약 리포트 반환
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

        # 1. 버스번호별 -> 시간대별 -> 출발시각순 -> 정류소순번 정렬
        df = StorageManager._ensure_time_slot_and_trip(df)

        # 2. 요약 리포트 생성 (버스번호별 -> 시간대별 구분)
        summary = StorageManager.generate_summary(df, target_date, session_key)

        # 3. CSV 저장 시 사용자 친화적인 한글 컬럼 및 열 순서 배치
        ordered_keys = [k for k in KOREAN_COLUMN_MAP.keys() if k in df.columns]
        export_df = df[ordered_keys].rename(columns=KOREAN_COLUMN_MAP)
        export_df.to_csv(file_path, index=False, encoding="utf-8-sig")

        return file_path, summary

    @staticmethod
    def generate_summary(df: pd.DataFrame, target_date: str, session_key: str) -> str:
        if "_trip_start_time" not in df.columns or "time_slot" not in df.columns:
            df = StorageManager._ensure_time_slot_and_trip(df)

        if session_key == "morning":
            session_title = "아침 출근 (05:00~10:00)"
        elif session_key == "evening":
            session_title = "저녁 퇴근 (17:00~22:00)"
        else:
            session_title = f"수동 수집 ({session_key})"

        total_records = len(df)
        unique_buses = df["plate_no"].nunique()

        lines = [
            f"🚌 [버스마스터 출퇴근 분석 리포트 - {target_date}]",
            f"📌 세션: {session_title}",
            f"📊 총 기록 건수: {total_records}건 | 감지 차량: {unique_buses}대",
            "================================="
        ]

        # 1단계: 각 버스번호(노선명: M6405, M6450)별 그룹화
        for route_name, r_group in df.groupby("route_name", sort=False):
            route_trips = r_group[["plate_no", "trip_id"]].drop_duplicates()
            lines.append(f"\n🚍 【 {route_name} 】 (총 {len(route_trips)}회 / {r_group['plate_no'].nunique()}대 운행)")

            # 2단계: 각 버스번호 내에서 시간대별(예: 05시대, 06시대...) 그룹화
            for time_slot, t_group in r_group.groupby("time_slot", sort=False):
                hour_str = time_slot[:2]
                slot_range = f"{hour_str}:00~{hour_str}:59" if hour_str.isdigit() else time_slot
                slot_trips = t_group[["plate_no", "trip_id"]].drop_duplicates()
                lines.append(f"  ⏰ [{time_slot} ({slot_range})] — {len(slot_trips)}대")

                # 3단계: 해당 시간대 내 차량(운행 회차)별 시간순 정렬 및 요약
                for (plate_no, trip_id), b_group in t_group.groupby(["plate_no", "trip_id"], sort=False):
                    b_sorted = b_group.sort_values(by=["stop_seq", "time"]).reset_index(drop=True)
                    first_row = b_sorted.iloc[0]
                    last_row = b_sorted.iloc[-1]

                    # 만석(0석) 발생 정류장 확인
                    zero_seat_rows = b_sorted[b_sorted["remain_seats"] == 0]
                    if not zero_seat_rows.empty:
                        zero_sttn = zero_seat_rows.iloc[0]["station_name"]
                        zero_time = str(zero_seat_rows.iloc[0]["time"])[:5]
                        full_info = f"🚨 만석발생: {zero_sttn}({zero_time})"
                    else:
                        valid_s = pd.to_numeric(b_sorted["remain_seats"], errors="coerce").dropna()
                        min_s = int(valid_s.min()) if not valid_s.empty else "미제공"
                        full_info = f"최소잔여: {min_s}석"

                    # 총 이동 시간
                    tot_time = last_row.get("total_duration_str", "-")
                    if tot_time == "-" and len(b_sorted) > 1:
                        t_diff = int((pd.to_datetime(last_row["time"]) - pd.to_datetime(first_row["time"])).total_seconds())
                        tot_time = f"{t_diff // 60}분"

                    lines.append(
                        f"   • [{plate_no}] {first_row['station_name']}({first_row['time'][:5]}) ➔ "
                        f"{last_row['station_name']}({last_row['time'][:5]}) | "
                        f"소요: {tot_time} | {full_info}"
                    )

        lines.append("\n📁 버스번호별·시간대별 상세 정류장 타임라인은 첨부된 엑셀(CSV) 파일을 확인하세요.")
        return "\n".join(lines)
