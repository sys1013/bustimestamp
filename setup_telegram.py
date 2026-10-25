import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

def auto_detect_chat_id():
    print("==========================================")
    print("🤖 텔레그램 Chat ID 자동 연결 도구")
    print("==========================================")
    print("텔레그램에서 아래 봇을 열고 [/시작] 또는 아무 메시지나 보내주세요:")
    print("👉 https://t.me/YoyOs_bus_master_bot (@YoyOs_bus_master_bot)")
    print("------------------------------------------")
    print("메시지 수신 대기 중 (최대 60초)...")

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    for i in range(12):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                results = data.get("result", [])
                if results:
                    last_msg = results[-1]
                    chat = last_msg.get("message", {}).get("chat", {})
                    chat_id = chat.get("id")
                    user = chat.get("username") or chat.get("first_name", "사용자")
                    if chat_id:
                        print(f"\n🎉 연결 성공! 사용자: {user} (Chat ID: {chat_id})")
                        
                        # .env 파일에 업데이트
                        lines = ENV_PATH.read_text().splitlines()
                        new_lines = []
                        for line in lines:
                            if line.startswith("TELEGRAM_CHAT_ID="):
                                new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}")
                            else:
                                new_lines.append(line)
                        ENV_PATH.write_text("\n".join(new_lines) + "\n")
                        print("✅ .env 파일에 TELEGRAM_CHAT_ID 가 자동 저장되었습니다.")

                        # 환영 테스트 메시지 발송
                        send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                        send_data = urllib.parse.urlencode({
                            "chat_id": chat_id,
                            "text": "🚌 [BusMaster] 텔레그램 연동이 완료되었습니다!\n이제 정해진 시간 또는 수동 수집 종료 시 버스 운행 리포트와 CSV 파일이 이곳으로 자동 발송됩니다."
                        }).encode("utf-8")
                        send_req = urllib.request.Request(send_url, data=send_data, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(send_req) as s_resp:
                            print("✅ 텔레그램으로 환영 확인 메시지를 보냈습니다.")
                        return chat_id
        except Exception as e:
            pass
        time.sleep(5)
        print(".", end="", flush=True)

    print("\n⚠️ 아직 메시지가 감지되지 않았습니다. 봇에게 메시지를 보낸 후 다시 실행해주세요.")
    return None

if __name__ == "__main__":
    auto_detect_chat_id()
