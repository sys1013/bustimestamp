from typing import Optional, List, Dict
import logging
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import (
    DATA_GO_KR_API_KEY,
    INCHEON_BIS_ROUTE_URL,
    INCHEON_BIS_LOCATION_URL,
    ROUTE_INFO_MAP,
)

logger = logging.getLogger(__name__)

class BusApiClient:
    def __init__(self, api_key: str = None):
        raw_key = api_key or DATA_GO_KR_API_KEY
        if "%" in raw_key:
            self.api_key = urllib.parse.unquote(raw_key)
        else:
            self.api_key = raw_key

        self.session = requests.Session()
        # 인천 BIS 서버는 브라우저 표준 헤더가 있어야 정상 응답함
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

    def search_route_id(self, route_no: str) -> Optional[str]:
        """노선명으로 인천 BIS routeId 조회"""
        clean_no = route_no.upper().strip()
        if clean_no in ROUTE_INFO_MAP:
            return ROUTE_INFO_MAP[clean_no]["route_id"]

        url = f"{INCHEON_BIS_ROUTE_URL}/getBusRouteNo"
        params = {
            "serviceKey": self.api_key,
            "routeNo": clean_no,
            "numOfRows": 20,
            "pageNo": 1,
        }
        try:
            resp = self.session.get(url, params=params, timeout=10)
            root = ET.fromstring(resp.text)
            for it in root.iter("itemList"):
                r_no = it.findtext("ROUTENO")
                r_id = it.findtext("ROUTEID")
                if r_no and clean_no in r_no.upper():
                    return str(r_id).strip()
        except Exception as e:
            logger.error(f"노선 ID 조회 중 에러 ({route_no}): {e}")

        return None

    def get_route_stations(self, route_id: str) -> List[Dict]:
        """인천 BIS getBusRouteSectionList 로 전체 경유 정류소 목록 조회"""
        url = f"{INCHEON_BIS_ROUTE_URL}/getBusRouteSectionList"
        params = {
            "serviceKey": self.api_key,
            "routeId": route_id,
            "numOfRows": 150,
            "pageNo": 1,
        }
        stations = []
        try:
            resp = self.session.get(url, params=params, timeout=10)
            root = ET.fromstring(resp.content)
            for it in root.iter("itemList"):
                seq = it.findtext("BSTOPSEQ")
                name = it.findtext("BSTOPNM")
                node_id = it.findtext("BSTOPID")
                dircd = it.findtext("DIRCD")  # 0: 상행(출근: 송도->서울), 1: 하행(퇴근: 서울->송도)
                if seq is not None and name:
                    stations.append({
                        "seq": int(seq),
                        "station_id": node_id,
                        "station_name": name,
                        "updowncd": str(dircd) if dircd is not None else None,
                    })
            stations.sort(key=lambda x: x["seq"])
        except Exception as e:
            logger.error(f"정류소 목록 조회 중 에러 ({route_id}): {e}")
        return stations

    def get_bus_locations(self, route_id: str) -> List[Dict]:
        """인천 BIS getBusRouteLocation 로 실시간 운행 버스 위치 및 '잔여 좌석 수' 조회"""
        url = f"{INCHEON_BIS_LOCATION_URL}/getBusRouteLocation"
        params = {
            "serviceKey": self.api_key,
            "routeId": route_id,
            "numOfRows": 50,
            "pageNo": 1,
        }
        bus_list = []
        try:
            resp = self.session.get(url, params=params, timeout=10)
            root = ET.fromstring(resp.content)
            for it in root.iter("itemList"):
                plate_no = it.findtext("BUS_NUM_PLATE")
                seq = it.findtext("LATEST_STOPSEQ")
                sttn_name = it.findtext("LATEST_STOP_NAME")
                node_id = it.findtext("LATEST_STOP_ID")
                remain_seat = it.findtext("REMAIND_SEAT")
                dircd = it.findtext("DIRCD")  # 0: 출근(송도->서울), 1: 퇴근(서울->송도)

                remain_val = -1
                if remain_seat and str(remain_seat).isdigit():
                    s_int = int(remain_seat)
                    if s_int != 255:  # 255는 미제공
                        remain_val = s_int

                if plate_no and seq:
                    bus_list.append({
                        "plate_no": str(plate_no).strip(),
                        "latest_stop_seq": int(seq),
                        "latest_stop_name": sttn_name,
                        "latest_stop_id": node_id,
                        "remain_seats": remain_val,
                        "dircd": str(dircd) if dircd is not None else None,
                    })
        except Exception as e:
            logger.error(f"실시간 버스 위치/좌석 조회 중 에러 ({route_id}): {e}")
        return bus_list
