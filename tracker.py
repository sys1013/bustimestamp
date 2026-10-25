from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BusTripTracker:
    def __init__(self, route_name: str, route_id: str, stations: list[dict], target_direction: str):
        """
        route_name: 'M6405', 'M6450'
        route_id: API 상의 routeId
        stations: 정류소 목록 [{'seq': 1, 'station_name': '...', 'updowncd': '0'}, ...]
        target_direction: 'to_seoul' (출근) 또는 'to_songdo' (퇴근) 또는 'both'
        """
        self.route_name = route_name
        self.route_id = route_id
        self.stations = {s["seq"]: s["station_name"] for s in stations}
        self.station_updown = {s["seq"]: s.get("updowncd") for s in stations}
        self.target_direction = target_direction
        
        # 회차지 기준 상행/하행 순번 경계 계산
        self.turnaround_seq = self._find_turnaround_seq(stations)
        
        # 차량별 마지막 상태: plate_no -> {"last_seq": int, "last_time": datetime, "last_station": str}
        self.bus_states = {}
        
        # 누적 기록 데이터
        self.records = []

    def _find_turnaround_seq(self, stations: list[dict]) -> int:
        """회차지(강남역, 삼성역 등) 정류소 순번을 찾아 상행/하행 경계 정의"""
        keywords = ["강남역", "삼성역", "한국무역센터", "서초현대타워"]
        for s in stations:
            for kw in keywords:
                if kw in s["station_name"]:
                    logger.info(f"[{self.route_name}] 회차지 감지: {s['station_name']} (순번: {s['seq']})")
                    return s["seq"]
        
        # 특정 키워드가 없는 경우 전체 정류소의 중간 지점으로 추정
        mid = len(stations) // 2 if stations else 1
        logger.warning(f"[{self.route_name}] 회차지 키워드 미발견, 중간 순번({mid})을 회차지로 설정")
        return mid

    def is_in_target_direction(self, seq: int, dircd: str = None) -> bool:
        """해당 차량/정류소가 현재 수집 목표 방향(출근/퇴근)에 해당하는지 판별"""
        # 1. dircd 가 전달된 경우 (0: 상행/출근, 1: 하행/퇴근)
        check_dir = dircd or self.station_updown.get(seq)
        if check_dir is not None and str(check_dir).strip() in ("0", "1"):
            if self.target_direction == "to_seoul":
                return str(check_dir).strip() == "0"
            elif self.target_direction == "to_songdo":
                return str(check_dir).strip() == "1"
            return True

        # 2. 회차지 순번 기준 판별
        if self.target_direction == "to_seoul":
            return seq <= self.turnaround_seq
        elif self.target_direction == "to_songdo":
            return seq >= self.turnaround_seq
        return True

    def process_locations(self, bus_locations: list[dict]):
        """실시간 버스 위치 목록을 받아 새 정류소 진입 시 기록 생성"""
        now = datetime.now()

        for bus in bus_locations:
            plate_no = bus["plate_no"]
            current_seq = bus["latest_stop_seq"]
            remain_seats = bus["remain_seats"]
            dircd = bus.get("dircd")

            # 목표 방향이 아닌 정류소/차량은 스킵
            if not self.is_in_target_direction(current_seq, dircd):
                continue

            station_name = self.stations.get(current_seq, f"정류소({current_seq})")
            last_state = self.bus_states.get(plate_no)

            # 이전 기록이 없거나 정류소 순번이 변경된 경우 (새로운 정류소 통과/도착)
            if not last_state or last_state["last_seq"] != current_seq:
                duration_sec = None
                duration_str = "-"
                seat_change_str = "-"
                total_duration_str = "-"
                total_duration_sec = None

                if last_state:
                    # 직전 정류소 대비 소요시간 계산
                    prev_time = last_state["last_time"]
                    prev_seq = last_state["last_seq"]
                    prev_seat = last_state.get("last_seat")

                    if current_seq > prev_seq:
                        diff_sec = int((now - prev_time).total_seconds())
                        if 10 <= diff_sec <= 7200:
                            duration_sec = diff_sec
                            mins = diff_sec // 60
                            secs = diff_sec % 60
                            duration_str = f"{mins}분 {secs}초" if mins > 0 else f"{secs}초"

                    # 직전 정류소 대비 좌석 변화량 계산
                    if remain_seats >= 0 and prev_seat is not None and prev_seat >= 0:
                        diff_seat = remain_seats - prev_seat
                        if diff_seat < 0:
                            seat_change_str = f"{diff_seat}석 ({abs(diff_seat)}명 탑승)"
                        elif diff_seat > 0:
                            seat_change_str = f"+{diff_seat}석 ({diff_seat}명 하차)"
                        else:
                            seat_change_str = "변화없음(0석)"

                    # 최초 출발 정류소 대비 누적 소요시간 계산
                    first_time = last_state.get("first_time", prev_time)
                    tot_sec = int((now - first_time).total_seconds())
                    if tot_sec > 0:
                        total_duration_sec = tot_sec
                        t_mins = tot_sec // 60
                        t_secs = tot_sec % 60
                        total_duration_str = f"{t_mins}분 {t_secs}초" if t_mins > 0 else f"{t_secs}초"
                    first_recorded_time = first_time
                else:
                    first_recorded_time = now

                if self.target_direction == "to_seoul":
                    direction_text = "출근(송도->서울)"
                elif self.target_direction == "to_songdo":
                    direction_text = "퇴근(서울->송도)"
                else:
                    direction_text = "송도->서울(상행)" if current_seq <= self.turnaround_seq else "서울->송도(하행)"

                record = {
                    "date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S"),
                    "route_name": self.route_name,
                    "direction": direction_text,
                    "plate_no": plate_no,
                    "stop_seq": current_seq,
                    "station_name": station_name,
                    "remain_seats": remain_seats if remain_seats >= 0 else "미제공",
                    "seat_change": seat_change_str,
                    "duration_sec": duration_sec if duration_sec is not None else "",
                    "duration_str": duration_str,
                    "total_duration_sec": total_duration_sec if total_duration_sec is not None else "",
                    "total_duration_str": total_duration_str,
                }
                self.records.append(record)
                logger.info(
                    f"[{self.route_name} - {plate_no}] {station_name}(순번 {current_seq}) | "
                    f"잔여: {record['remain_seats']} | 변화: {seat_change_str} | 소요: {duration_str} | 누적: {total_duration_str}"
                )

                # 상태 갱신
                self.bus_states[plate_no] = {
                    "last_seq": current_seq,
                    "last_time": now,
                    "last_station": station_name,
                    "last_seat": remain_seats,
                    "first_time": first_recorded_time
                }
