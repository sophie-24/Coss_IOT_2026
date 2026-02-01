import requests
import json

# 현재 리더님의 ngrok 주소로 수정하세요!
NGROK_URL = "https://88d0c49bd9cc.ngrok-free.app/notification"
MOBIUS_SUB_URL = "https://onem2m.iotcoss.ac.kr/Mobius/ae_Namsan/cnt_noise"

headers = {
    "Accept": "application/json",
    "X-M2M-RI": "12345",
    "X-M2M-Origin": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb", # 리더님 Origin
    "Content-Type": "application/vnd.onem2m-res+json; ty=23"
}

data = {
    "m2m:sub": {
        "rn": "sub_analysis",
        "nu": [NGROK_URL],
        "nct": 1,
        "enc": {
            "net": [3] # ContentInstance 생성 시 알림
        }
    }
}

# 기존 구독 삭제 후 재등록 (갱신용)
requests.delete(f"{MOBIUS_SUB_URL}/sub_analysis", headers=headers)
response = requests.post(MOBIUS_SUB_URL, headers=headers, json=data)

if response.status_code == 201:
    print("✅ 실시간 구독 성공! 이제 아두이노 데이터가 서버로 들어옵니다.")
else:
    print(f"❌ 구독 실패: {response.text}")