# 💡 D-Log

> "소음은 AI가 객관적으로 판단하고, 사과는 IoT로 정중하게 전달한다."
---

## 🎯 시스템 개요

**AI Noise Mediator**는 oneM2M 국제 표준 기반의 층간소음 관제 시스템입니다. AI 분석과 물리 센서 데이터를 결합하여 법적 효력을 갖춘 증거 자료를 실시간으로 생성하고, IoT 기반 사과 메시지 전달 시스템을 통해 이웃 간 갈등을 자동으로 중재합니다.

**주요 특징:**

- 환경분쟁조정위원회 판정 기준 준수 (Leq_1min, Leq_5min, Lmax)
- AI-물리센서 하이브리드 판정 시스템
- oneM2M ACP 기반 세대 간 프라이버시 보호
- 법적 검토 의견이 포함된 전문가급 리포트 자동 생성
- 
---

## 🏗️ 시스템 아키텍처

본 프로젝트는 oneM2M Subscription/Notification 기반 이벤트 드리븐 아키텍처를 사용합니다.

```
[Arduino 센서]
    ↓ POST (원본 데이터)
[Mobius Platform - cnt_raw_data]
    ↓ Notification
[AI Server - 분석 처리]
    ↓ POST (분석 결과)      ↘ WebSocket (실시간 푸시)
[Mobius - cnt_noise]        [Vue Dashboard]
    ↓ Notification
[Arduino - LED 알림]

```

### 데이터 흐름

1. **Arduino → Mobius**: 센서 데이터를 JSON 형식으로 Mobius의 `cnt_raw_data` 컨테이너에 POST
2. **Mobius → AI Server**: 구독(Subscription) 설정에 따라 AI 서버의 `/notification` 엔드포인트로 알림 전송
3. **AI Server**: 데이터 수신 → AI 분석 수행 → 결과 생성
4. **AI Server → Mobius**: 분석 결과를 `cnt_noise` 컨테이너에 POST
5. **AI Server → Dashboard**: WebSocket을 통해 모든 연결된 클라이언트에 실시간 업데이트
6. **Mobius → Arduino**: 분석 결과 컨테이너를 구독한 Arduino가 알림을 받아 LED 제어 등 액션 수행

---

### 소음 등급 및 자동 중재 기준

법적 기준을 바탕으로 3단계 등급 판정 및 자동 중재를 수행합니다.

| 등급 | 기준 | 상태 | 조치 | 중재 메시지 |
| --- | --- | --- | --- | --- |
| 🟢 **GREEN** | 39dB 미만 | 평온 (법적 기준 미달) | 데이터 기록만 수행 | ❌ 발송 안 함 |
| 🟡 **YELLOW** | 39dB ~ 57dB | 주의 (인지 가능한 불편함) | AI 분석 병행 및 대시보드 경고 | ✅ 발송 |
| 🔴 **RED** | 57dB 초과 | 경고 (명백한 고통 유발) | 즉시 경고 및 강력 개입 | ✅ 강력 발송 |

---

## 📦 설치 및 실행

### 1. Backend (FastAPI Server)

1. **의존성 설치:**
    
    ```bash
    pip install -r requirements.txt
    
    ```
    
2. **서버 실행:**
    
    ```bash
    uvicorn main:app --host 0.0.0.0 --reload --port 8080
    
    ```
    서버가 `http://YOUR_IP:8080/notification`에서 Mobius의 알림을 수신합니다.
    

### 2. Frontend (Vue.js Dashboard)

1. **의존성 설치:**
    
    ```bash
    npm install
    
    ```
2. **개발 서버 실행:**
    
    ```bash
    npm run dev
    
    ```
    
    대시보드가 특정 포트(예: `http://localhost:8081`)에서 실행됩니다.
    
3. **네트워크 접근:**
    - 같은 네트워크의 다른 PC나 모바일에서 접근하려면 실제 IPv4 주소를 사용하세요.
    - 예: `http://xxx.xxx.xxx.xxx/dashboard`
    - 자동으로 백엔드 WebSocket에 연결되어 실시간 업데이트를 받습니다.

---

### 최종 결과

- 특정 소음(발망치 등)에 대한 **AI 확신도 대폭 향상** (30% → 75% 이상)
- 물리적 검증 로직 추가로 **판정 정확도 및 시스템 신뢰성 극대화**
- 실제 환경에서 안정적으로 작동하는 실용적인 층간소음 관제 시스템 구축 성공
