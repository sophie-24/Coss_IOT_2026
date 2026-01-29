# 💡 AI Noise Mediator
> **"소음은 AI가 객관적으로 판단하고, 사과는 IoT로 정중하게 전달한다."**

## 🏗️ System Architecture (v2.0 - Notification Based)
This project uses an event-driven architecture based on oneM2M Subscription/Notification.

1.  **Arduino → Mobius:** An Arduino device with sensors posts the raw sensor data (in the specified JSON format) to a dedicated container on the Mobius platform (e.g., `cnt_raw_data`).
2.  **Mobius → AI Server (Notification):** The AI Server subscribes to this raw data container. When new data is posted, Mobius sends a notification to the AI Server's `/notification` endpoint.
3.  **AI Server (Analysis):** The AI Server receives the notification, extracts the raw data, performs AI analysis, and generates a result.
4.  **AI Server → Mobius (Result):** The AI Server posts the analysis result to a different container (e.g., `cnt_noise`).
5.  **AI Server → Dashboard (WebSocket):** Simultaneously, the server pushes the analysis result to all connected dashboard clients via WebSocket for a real-time UI update.
6.  **Mobius → Arduino (Result):** The Arduino device subscribes to the analysis result container (`cnt_noise`) to receive the final result and trigger actions like turning on an LED.

---

## 🚀 How to Run

### 1. One-Time Setup: Mobius Subscription
Before running the server for the first time, you need to set up the subscription.
1.  **Edit `config.py`:**
    -   Fill in the correct `RAW_DATA_CONTAINER_NAME` (the container where Arduino posts raw data).
    -   Update `AI_SERVER_URL` with the public/local IP address of the machine where the AI server will run (e.g., `http://10.74.26.152:8080`).
2.  **Run the script:** Execute the setup script once.
    ```bash
    python setup_mobius_subscription.py
    ```
    This will create a subscription on Mobius that links the raw data container to your AI server's `/notification` endpoint.

### 2. Backend (FastAPI Server)
Install all required Python packages.
```bash
pip install -r requirements.txt
```
Run the FastAPI development server, allowing external access.
```bash
uvicorn main:app --host 0.0.0.0 --reload --port 8080
```
The server is now running and listening for notifications from Mobius at `http://YOUR_IP:8080/notification`.

### 3. Frontend (Vue.js Dashboard)
Install all required Node.js packages.
```bash
npm install
```
Run the Vue development server. This will now be accessible on your local network.
```bash
npm run dev
```
The dashboard will be running on a specific port (e.g., `http://localhost:8081`).
**Important for Network Access:** To view the dashboard from other PCs or mobile devices on the same network, use your PC's actual IPv4 address, for example: `http://192.168.0.115:8081/dashboard`.
It will automatically connect to the backend's WebSocket for real-time updates.

## ✅ How to Test
Since the server now reacts to Mobius notifications instead of direct requests, testing is done by simulating the Arduino's action.

1.  **Prepare your test data:** Create a JSON file (e.g., `test_data.json`) with the raw data payload you want to send. The *content* of this file should be the stringified JSON that will go into the `con` field. For example:
    ```json
    {
      "m2m:cin": {
        "con": "{\"house_id\":\"Below_301\",\"timestamp\":\"...\",\"meta\":{...},\"payload\":{...}}",
        "lbl": ["raw_data", "test"]
      }
    }
    ```
2.  **POST to Mobius:** Use a tool like `Postman` or `curl` to send a `POST` request to the raw data container on Mobius (`/Mobius/ae_Namsan/cnt_raw_data`).
    -   **URL:** `https://onem2m.iotcoss.ac.kr/Mobius/ae_Namsan/YOUR_RAW_DATA_CONTAINER_NAME`
    -   **Headers:** Use the same headers as specified in `mobius_client.py` (`X-M2M-Origin`, `X-API-KEY`, etc.), but with `Content-Type: application/json;ty=4`.
    -   **Body:** The content of your `test_data.json`.
3.  **Observe:**
    -   The AI server's terminal should log that it received a notification and processed it.
    -   The Vue.js dashboard in your browser should instantly update with the new analysis result.

---

## 🏛️ Core Design Principles

### 1. 신뢰도 기반 알림 임계값 (Confidence-based Alert Threshold)
본 시스템은 AI 모델의 예측 결과에 대한 확신도(Probability)를 기반으로 알림의 중요도를 판단합니다. 특히 층간소음의 주범인 '발망치(footsteps)'와 같은 **핵심 소음에 대해서는 AI 확신도가 75% 이상일 때** 유의미한 알림으로 간주하여 등급 판정 로직에 반영합니다. 이는 AI가 애매하게 판단한 결과를 필터링하여 시스템의 오작동을 방지하고, 알림의 전체적인 신뢰도를 높입니다. 다만, AI 분석 결과와 별개로 **극심한 소음 데시벨(dB)과 같은 명확한 물리적 지표가 감지될 경우에는 확신도와 상관없이 알림이 발생**할 수 있습니다.

### 2. 세대 간 개인정보 보호 설계 (Privacy by Design via oneM2M ACP)
본 시스템은 국제 IoT 표준 oneM2M의 핵심 보안 기능인 **ACP(Access Control Policy, 접근 제어 정책)**를 활용하여 세대 간 프라이버시를 원천적으로 보호하도록 설계되었습니다. ACP는 "누가, 어떤 데이터에, 무슨 작업을 할 수 있는지"를 정의하는 강력한 규칙입니다.

- **소음 원본 데이터 (`cnt_raw_data`)의 ACP 규칙:**
  - **쓰기 권한:** 오직 해당 세대의 아두이노에게만 부여됩니다.
  - **읽기 권한:** 오직 AI 서버에게만 부여됩니다.
  - **결과:** 이 규칙에 따라, 이웃 세대나 관리자 등 그 누구도 소음의 원본 데이터에 접근할 수 없어 완벽한 프라이버시가 보장됩니다.

- **분석 결과 데이터 (`cnt_noise`)의 ACP 규칙:**
  - **쓰기 권한:** 오직 AI 서버에게만 부여됩니다.
  - **읽기 권한:** 알림을 받아야 할 윗집의 IoT 기기와 관리자 대시보드에게만 부여됩니다.
  - **결과:** 소음을 발생시킨 아랫집은 윗집의 데이터에 접근할 수 없는 등, 각 주체는 꼭 필요한 최소한의 데이터만 읽고 쓸 수 있습니다.

이러한 ACP 설계를 통해, 각 세대의 데이터는 상호 격리되며 허가된 주체만이 최소한의 정보에 접근할 수 있어 신뢰도 높은 중재 시스템을 구축할 수 있습니다.

### 3. 소음 등급 분류 기준 (Noise Level Classification Criteria)
AI 서버는 아래 규칙을 순서대로 검사하여 가장 먼저 해당하는 규칙에 따라 최종 등급을 결정합니다.

- **🔴 RED (경고): "명백하고 지속적인 고통"**
  > 아래 조건 중 하나라도 만족하면 **RED**로 최종 판정
  1.  **지속적인 발망치/충격음:** AI가 소음을 **`footsteps`(발망치)으로 분석**했고 (**확신도 75% 이상**), 해당 소음의 **`지속 시간`이 5초 이상**일 경우
  2.  **과도하게 시끄러운 소음의 지속:** 소음 종류와 상관없이, **`소음 크기`가 매우 높은 수준(예: 80dB 이상)으로 측정**되었고, 그 상태가 **3초 이상 지속**될 경우

- **🟡 YELLOW (주의): "인지 가능한 불편함"**
  > 위의 RED 조건에 해당하지 않으면서, 아래 조건 중 하나라도 만족하면 **YELLOW**로 판정
  1.  **순간적인 발망치/충격음:** AI가 소음을 **`footsteps`으로 분석**했고 (**확신도 60% 이상**), 혹은 소음 분석과 별개로 **`진동 Peak`가 기준치(2개 이상) 이상으로 감지**되었을 경우 (지속 시간이 짧음)
  2.  **상당한 수준의 생활 소음:** 소음 종류와 상관없이, **`소음 크기`가 일반적인 수준을 넘어선 상태(예: 65dB ~ 80dB)**일 경우

- **🟢 GREEN (안정): "일상적인 생활 소음"**
  > 위의 RED, YELLOW 조건에 어느 것도 해당되지 않는 모든 경우