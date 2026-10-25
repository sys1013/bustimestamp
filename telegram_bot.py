import logging
from pathlib import Path
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id and "your_" not in self.token)

    def send_message(self, text: str) -> bool:
        """텔레그램 메시지 전송 (타임아웃 및 재시도 적용)"""
        if not self.is_configured():
            logger.warning("텔레그램 토큰 또는 Chat ID가 설정되지 않아 메시지를 전송하지 않습니다.")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
        }
        for attempt in range(2):
            try:
                resp = requests.post(url, data=payload, timeout=30)
                data = resp.json()
                if data.get("ok"):
                    logger.info("텔레그램 메시지 전송 성공")
                    return True
                else:
                    logger.error(f"텔레그램 메시지 전송 실패: {data.get('description')}")
                    return False
            except Exception as e:
                logger.warning(f"텔레그램 메시지 전송 재시도 ({attempt+1}/2): {e}")
        return False

    def send_document(self, file_path: Path, caption: str = "") -> bool:
        """텔레그램 파일(문서) 전송 (타임아웃 및 재시도 적용)"""
        if not self.is_configured():
            logger.warning("텔레그램 토큰 또는 Chat ID가 설정되지 않아 문서를 전송하지 않습니다.")
            return False

        if not file_path.exists():
            logger.error(f"전송할 파일이 존재하지 않습니다: {file_path}")
            return False

        url = f"{self.base_url}/sendDocument"
        data = {
            "chat_id": self.chat_id,
            "caption": caption
        }
        for attempt in range(2):
            try:
                with open(file_path, "rb") as f:
                    files = {"document": (file_path.name, f)}
                    resp = requests.post(url, data=data, files=files, timeout=40)
                    res_json = resp.json()
                    if res_json.get("ok"):
                        logger.info(f"텔레그램 파일 전송 성공: {file_path.name}")
                        return True
                    else:
                        logger.error(f"텔레그램 파일 전송 실패: {res_json.get('description')}")
                        return False
            except Exception as e:
                logger.warning(f"텔레그램 파일 전송 재시도 ({attempt+1}/2): {e}")
        return False

    def send_report(self, summary_text: str, file_path: Path) -> bool:
        """요약 메시지와 파일을 함께 전송"""
        m_ok = self.send_message(summary_text)
        d_ok = self.send_document(file_path, caption=file_path.name)
        return m_ok and d_ok
