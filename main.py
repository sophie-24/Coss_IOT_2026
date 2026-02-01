import numpy as np
import logging
import json
import time
import os
import asyncio
import requests
import pandas as pd
import io
import csv
import codecs
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone, time as dt_time
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response, Request
# Import Mobius client and configuration
from mobius_client import create_content_instance, retrieve_all_content_instances, retrieve_latest_content_instance
from config import AE_NAME, MOCK_DATA_MODE, REQUEST_TIMEOUT, CNT_STATUS, CNT_NOISE, CNT_RAW, CNT_APOLOGY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
# Import AI model functions
from ai_engine import load_ai_model_v2, predict_noise_v2, preprocess_audio_for_v2

all_analysis_history = []
MOBIUS_URL = "https://onem2m.iotcoss.ac.kr/Mobius/ae_Namsan/cnt_noise/la"
HEADERS = {
    "Accept": "application/json",
    "X-M2M-RI": "12345",
    "X-M2M-Origin": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "X-API-KEY": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "x-auth-custom-lecture": "LCT_20250007",
    "x-auth-custom-creator": "dgunamsan"
}

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

from collections import deque

# --- State Management & Constants ---
class HouseState(BaseModel):
    status: str = "quiet"  # quiet, loud
    start_time: datetime | None = None
    last_loud_time: datetime | None = None
    last_packet_severity: str = "Green"
    start_of_quiet: datetime | None = None
    mediation_active: bool = False
    mediation_sent_time: str | None = None
    apology_active: bool = False
    apology_sent_time: str | None = None
    lmax_exceed_count: int = 0 # Lmax 초과 횟수 카운트

house_states: Dict[str, HouseState] = {}
QUIET_PERIOD_SECONDS = 5
VIBRATION_PEAK_THRESHOLD = 0.3

# --- Moving Average Buffers ---
noise_buffer: Dict[str, deque] = {} # {house_id: deque([db, db, ...], maxlen=300)}

def update_noise_metrics(house_id: str, current_db: float):
    if house_id not in noise_buffer:
        noise_buffer[house_id] = deque(maxlen=300) # 최대 5분(1초당 1개 기준 300개)
    
    noise_buffer[house_id].append(current_db)
    data = list(noise_buffer[house_id])
    
    # 1분 평균 (최근 60개)
    avg_1min = sum(data[-60:]) / len(data[-60:]) if len(data) >= 60 else sum(data)/len(data)
    # 5분 평균 (전체 300개)
    avg_5min = sum(data) / len(data)
    
    return round(avg_1min, 2), round(avg_5min, 2)

# --- Pydantic Models ---
class MetaData(BaseModel):
    sampling_rate: str
    vibration_unit: str
    sound_unit: str

class SensorPayload(BaseModel):
    vibration: Dict[str, List[float]]
    sound_raw: List[int]
    raw_max_amplitude: int

class NewPayload(BaseModel):
    model_config = ConfigDict(extra='ignore')
    house_id: str
    timestamp: str
    meta: Any
    payload: Any 

class AnalysisResult(BaseModel):
    result: str
    probability: float
    db_level: float
    avg_1min: float = 0.0
    avg_5min: float = 0.0
    severity: str
    is_external: bool = False
    duration: float = 0.0
    vibration_peaks: int = 0
    vibration_max: float = 0.0
    audio_signature: List[float] = []

class Action(BaseModel):
    mediation_sent: bool
    target: str

class ApologyDetail(BaseModel):
    sent: bool
    timestamp: str

class OneM2MPlatformOutput(BaseModel):
    event_id: str
    house_id: str
    timestamp: str
    analysis: AnalysisResult
    action: Action
    apology_detail: Optional[ApologyDetail] = None

class MobiusNotification(BaseModel):
    m2m_sgn: Dict[str, Any] = Field(None, alias="m2m:sgn")
    sgn: Dict[str, Any] = None

# --- Mock Data Generation ---
async def generate_mock_output_data() -> OneM2MPlatformOutput:
    house_id = "dgu_house_3140"
    current_time = datetime.now()
    results = ["Footstep", "Impact Noise", "Voice", "Silence"]
    severities = ["Green", "Yellow", "Red"]
    result = np.random.choice(results)
    severity = np.random.choice(severities, p=[0.6, 0.3, 0.1])
    db_level = round(np.random.uniform(40, 90), 2)
    if severity == "Green": db_level = round(np.random.uniform(30, 50), 2)
    elif severity == "Red": db_level = round(np.random.uniform(80, 100), 2)
    probability = round(np.random.uniform(0.3, 0.99), 2)
    mediation_sent = severity in ["Yellow", "Red"]
    return OneM2MPlatformOutput(
        event_id=f"MOCK_EVT_{current_time.strftime('%Y%m%d_%H%M%S_%f')}",
        house_id=house_id, timestamp=current_time.isoformat(),
        analysis=AnalysisResult(result=result, probability=probability, db_level=db_level, severity=severity),
        action=Action(mediation_sent=mediation_sent, target=severity)
    )

async def mock_data_sender():
    logger.info("MOCK DATA MODE: Starting sender.")
    while True:
        await asyncio.sleep(2)
        if not active_websocket_connections: continue
        mock_data = await generate_mock_output_data()
        mock_dict = mock_data.dict(exclude_none=True)
        mock_dict["is_mock_data"] = True
        for connection in active_websocket_connections:
            try: await connection.send_json(mock_dict)
            except: pass

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # 1. 모의 데이터 생성 태스크 (오타 수정: asyncio.create_task)
    if MOCK_DATA_MODE:
        asyncio.create_task(mock_data_sender())
        logger.info("📡 모의 데이터 송신 시작...")

    # 2. AI 모델 로드
    if not load_ai_model_v2():
        logger.error("CRITICAL: AI 모델 V2 로드 실패!")

    # 3. Mobius 자동 구독 설정 (실시간 아두이노 연동용)
    # 리더님, ngrok 주소 바뀔 때마다 여기를 업데이트해주시면 됩니다.
    CURRENT_NGROK_URL = "https://88d0c49bd9cc.ngrok-free.app/notification" 
    import random
    sub_name = f"sub_v3_{random.randint(1, 999)}"
    sub_url = f"https://onem2m.iotcoss.ac.kr/Mobius/{AE_NAME}/{CNT_NOISE}"
    sub_body = {
        "m2m:sub": {
            "rn": sub_name,
            "nu": [CURRENT_NGROK_URL],
            "nct": 1,
            "enc": {"net": [3]} # ContentInstance 생성 시 알림 전송
        }
    }

    try:
        requests.delete(f"{sub_url}/sub_analysis_v3", headers=HEADERS, timeout=3)
        # 새 이름으로 구독 신청
        response = requests.post(sub_url, headers=HEADERS, json=sub_body, timeout=3)
        
        if response.status_code == 201:
            logger.info(f"✅ Mobius 구독 성공! 이름: {sub_name}")
        else:
            logger.error(f"❌ 구독 실패(Status {response.status_code}): {response.text}")
    except:
        pass

# --- Helper Functions ---
def amplitude_to_db(amplitude: int) -> float:
    if amplitude == 0: return 0.0
    return 20 * np.log10(max(1, amplitude))

def analyze_vibration_peaks(vibration_z_list: np.ndarray, threshold: float = VIBRATION_PEAK_THRESHOLD) -> int:
    if vibration_z_list.size == 0: return 0
    peaks = np.where(vibration_z_list > threshold)[0]
    return len(peaks)

def create_waveform_image(audio_signature: List[float]) -> io.BytesIO:
    if not audio_signature: return None
    fig, ax = plt.subplots(figsize=(8, 2))
    ax.plot(audio_signature, color='#3182F6', linewidth=1)
    ax.set_title('Event Waveform', fontsize=10)
    ax.axis('off')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf

# --- PDF Imports ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.utils import ImageReader
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

active_websocket_connections: List[WebSocket] = []

def create_noise_heatmap_image(logs: List[Dict]) -> io.BytesIO:
    if not logs: return None
    event_data = []
    for log in logs:
        severity = log.get("analysis", {}).get("severity")
        if severity in ["Red", "Yellow"]:
            try:
                ts = datetime.fromisoformat(log.get("timestamp").replace("Z",""))
                event_data.append({"weekday": ts.weekday(), "hour": ts.hour})
            except: continue
    if not event_data: return None
    df = pd.DataFrame(event_data)
    heatmap_data = df.pivot_table(index='weekday', columns='hour', aggfunc='size', fill_value=0)
    heatmap_data = heatmap_data.reindex(index=range(7), columns=range(24), fill_value=0)
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    fig, ax = plt.subplots(figsize=(8, 3))
    cax = ax.pcolormesh(heatmap_data.columns, heatmap_data.index, heatmap_data.values, cmap='YlOrRd', shading='auto')
    fig.colorbar(cax, label='Event Count')
    ax.set_title('Weekly Heatmap', fontsize=10)
    ax.set_yticks(np.arange(7) + 0.5)
    ax.set_yticklabels(days, fontsize=8)
    ax.invert_yaxis()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf

def create_pie_chart_image(stats: Dict[str, int]) -> io.BytesIO:
    labels = list(stats.keys())
    sizes = list(stats.values())
    if sum(sizes) == 0: return None
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf

# --- Endpoints ---

@app.post("/notification/apology")
async def handle_apology_notification(request: Request):
    try:
        body = await request.json()
        logger.info(f"📩 [APOLOGY RECEIVED]: {body}")
        
        # 1. 컨텐츠 추출 (Mobius vs 직접 전송 대응)
        sgn = body.get("m2m:sgn") or body.get("sgn")
        if sgn:
            rep = sgn.get("nev", {}).get("rep", {})
            content = rep.get("m2m:cin", {}).get("con") or rep.get("cin", {}).get("con")
        else:
            content = body

        # 2. JSON 문자열인 경우 딕셔너리로 변환
        apology_dict = {}
        if isinstance(content, str):
            try: apology_dict = json.loads(content)
            except: apology_dict = {"message": content}
        else:
            apology_dict = content or {}

        # 3. 사과 신호 조건 검사 (규격 통합 체크)
        is_ack = (
            apology_dict.get("apology_ack") == 1 or 
            apology_dict.get("event_type") == "apology_action" or 
            str(content).strip() in ["1", "Apology Sent"]
        )

        if is_ack:
            timestamp = apology_dict.get("timestamp") or datetime.now().isoformat()
            house_id = apology_dict.get("house_id", "Below_301") # 리더님 가구 ID에 맞게 수정
            message = apology_dict.get("message", "위층에서 사과 메시지를 보냈습니다. 소음이 곧 완화될 예정입니다.")
            
            data = {
                "event": "apology", 
                "message": message, 
                "timestamp": timestamp,
                "house_id": house_id,
                "severity": "Green" # 사과 수신 시 화면을 진정시키는 효과용
            }
            
            # 히스토리에 저장 (리포트용)
            all_analysis_history.append(data)
            
            # WebSocket 전파
            if active_websocket_connections:
                await asyncio.gather(*[c.send_json(data) for c in active_websocket_connections], return_exceptions=True)
                logger.info(f"📢 [사과 전파 완료] {house_id} -> 대시보드")

    except Exception as e:
        logger.error(f"❌ Apology Error: {e}")
    
    return {"status": "ok"}

@app.post("/notification")
async def handle_mobius_notification(request: Request): 
    try:
        # [수정] 여기서부터 body를 가져옵니다.
        body = await request.json()
        if not body:
            return {"status": "ignored", "reason": "empty body"}

        
        sgn = body.get("m2m:sgn") or body.get("sgn")
        if not sgn: return {"status": "ignored"}
        
        rep = sgn["nev"]["rep"]
        raw_con = rep.get("m2m:cin", {}).get("con") or rep.get("cin", {}).get("con")
        
        # JSON 문자열인 경우 안전하게 파싱
        if isinstance(raw_con, str):
            try:
                payload_dict = json.loads(raw_con)
            except json.JSONDecodeError:
                logger.error("❌ JSON 파싱 실패: 데이터 형식이 올바르지 않습니다.")
                return {"status": "error", "message": "Invalid JSON in con"}
        else:
            payload_dict = raw_con

        # New Payload Parse
        house_id = payload_dict.get("house_id", "unknown")
        timestamp = payload_dict.get("timestamp", datetime.now().isoformat())
        meta = payload_dict.get("meta", {})
        payload = payload_dict.get("payload", {})
        # 1. Data Prep & Validation (리더 규리님 수정 버전)
        # payload_dict에서 실제 데이터가 들어있는 payload 부분을 먼저 가져옵니다.
        sensor_data = payload_dict.get("payload", {}) 
        sound_raw = sensor_data.get("sound_raw", []) # payload 안에서 sound_raw 추출
        vibration_z = payload.get("vibration", {}).get("z", [])
        raw_max_amplitude = payload.get("raw_max_amplitude", 0)

        audio_np = np.array(sound_raw, dtype=np.float32)
        print(f"🔍 [DEBUG] 수신된 오디오 샘플 개수: {len(audio_np)}개")
        # 3. 데이터 보정 (Zero-Padding)
        # [Validation] Data Length Check
        MIN_REQUIRED_SAMPLES = 10 # Lowered for testing connectivity
        if len(audio_np) < MIN_REQUIRED_SAMPLES:
            logger.warning(f"Skipping analysis: Data too short ({len(audio_np)})")
            return {"status": "skipped", "message": "Insufficient data length"}
        if len(audio_np) < 1000:
            audio_np = np.concatenate([audio_np, np.zeros(1000 - len(audio_np))])

        vibration_z = payload_dict.get("payload", {}).get("vibration", {}).get('z', [])
        vibration_np = np.array(vibration_z)
        # Calculate pure shock by removing 1.0g gravity component
        vibration_max = float(np.max(np.abs(vibration_np - 1.0))) if vibration_np.size > 0 else 0.0
        
        # Signature
        target_sig_len = 300
        audio_signature = audio_np.tolist()
        if len(audio_np) > target_sig_len:
            indices = np.linspace(0, len(audio_np)-1, target_sig_len).astype(int)
            audio_signature = audio_np[indices].tolist()

        # 2. AI Inference
        sr_val = meta.get("sampling_rate", "16000Hz")
        sr_int = int(str(sr_val).lower().replace("hz",""))
        audio_input = audio_np.flatten()
        processed = preprocess_audio_for_v2(audio_np, sr=sr_int)
        if hasattr(processed, 'numpy'): # 텐서 형태일 경우
            processed_input = processed.numpy().flatten()
        else: # 넘파이 형태일 경우
            processed_input = np.array(processed).flatten()
        result_label, predicted_prob = predict_noise_v2(processed, sr=sr_int, vibration_z = vibration_z)
        
        logger.info(f"✅ 분석 성공! 결과: {result_label} ({predicted_prob:.2f})")
    
        # 3. Grading (법적 기준 + 진동 하이브리드 로직)
        raw_amp = payload.get("raw_max_amplitude", 0)
        calc_db = amplitude_to_db(raw_amp)
        num_peaks = analyze_vibration_peaks(vibration_np)
        
        # [신규] 1분/5분 평균 계산 (Leq_1min, Leq_5min)
        current_time = datetime.fromisoformat(timestamp.replace("Z",""))
        avg_1min, avg_5min = update_noise_metrics(house_id, calc_db)
        
        # 시간대 파악 (주간: 06~22시, 야간: 22~06시)
        current_hour = current_time.hour
        is_night = current_hour >= 22 or current_hour < 6
        
        # [Step 1] 법적 기준치 설정
        min_threshold = 34.0 if is_night else 39.0
        max_db_limit = 52.0 if is_night else 57.0 # Lmax 기준
        suin_limit = 35.0 if is_night else 40.0 # 수인한도
        airborne_limit = 40.0 if is_night else 45.0 # 공기전달 소음 기준 (5분 평균)

        state = house_states.get(house_id, HouseState())

        # Lmax 초과 횟수 카운트
        if calc_db >= max_db_limit:
            state.lmax_exceed_count += 1
            logger.info(f"⚠️ [Lmax 초과] {calc_db:.1f}dB 감지 (누적: {state.lmax_exceed_count}회)")

        # [신규] 법적 검토 메시지 생성
        legal_review = []
        if avg_1min > suin_limit: legal_review.append("환경분쟁조정위 수인한도 초과")
        elif avg_1min > min_threshold: legal_review.append("직접충격 소음 주의 단계")
        
        if avg_5min > airborne_limit: legal_review.append("공기전달 소음 기준 위반")
        
        if calc_db > max_db_limit: legal_review.append(f"최고소음도(Lmax) 기준 초과 감지")
        if state.lmax_exceed_count >= 3: legal_review.append("최고소음도 반복 발생 (분쟁 시 매우 불리)")

        review_msg = " | ".join(legal_review) if legal_review else "법적 기준 이내 (정상)"
        
        # [신규] 외부 소음(thunderstorm, car_horn, siren) 예외 처리
        external_noises = ["thunderstorm", "car_horn", "siren"]
        is_external = any(ext in result_label.lower() for ext in external_noises)

        if is_external:
            sev = "Green"
            logger.info(f"🍃 [{house_id}] 외부 소음 감지({result_label}): 무조건 Green 판정")
        elif calc_db < min_threshold and avg_1min < min_threshold:
            # 법적 기준 미달이면 AI가 뭐라고 하든 무조건 Green (기록만 함, 중재 안 함)
            sev = "Green"
            logger.info(f"[{house_id}] {calc_db:.1f}dB < {min_threshold}dB: 법적 기준치 미달 (Green)")
        else:
            # 기본적으로 기준을 넘었으므로 Yellow로 시작
            sev = "Yellow"
            
            # [Step 2] 진동 하이브리드 격상 로직 (vibration_max 0.2 이상 또는 AI 발망치 고확신 시 Red)
            is_foot = "footsteps" in result_label.lower()
            if vibration_max >= 0.2 or (is_foot and predicted_prob > 0.7) or avg_1min > suin_limit:
                sev = "Red"
                logger.info(f"🚩 [{house_id}] 격상: 진동, 발망치 또는 수인한도 초과로 Red 판정")
            
            # [Step 3] 진동은 없어도 소음 자체가 한계치를 넘은 경우 Red
            if calc_db >= max_db_limit:
                sev = "Red"
                logger.info(f"🚩 [{house_id}] 격상: 최고소음도({calc_db:.1f}dB) 초과로 Red 판정")
        
        # 4. State Machine (지속 시간 체크 및 상태 유지)
        current_time = datetime.fromisoformat(timestamp.replace("Z",""))
        
        final_sev = sev
        
        # 상태 업데이트 (Loud/Quiet 상태 전환)
        if final_sev in ["Yellow", "Red"]:
            if state.status == "quiet":
                state.status = "loud"
                state.start_time = current_time
            state.last_loud_time = current_time
        else:
            if state.status == "loud" and (current_time - state.last_loud_time).total_seconds() >= 5:
                state.status = "quiet"
                state.start_time = None
        house_states[house_id] = state
        
        # 5. Post & Broadcast
        # [핵심 로직] 확실한 중재 제어: Yellow 또는 Red일 때만 True, Green일 때는 무조건 False
        is_mediation_active = final_sev in ["Yellow", "Red"]

        # A. Status to CNT_STATUS (LED 제어용 단순 등급)
        status_data = {
            "event_id": f"STS_{datetime.now().strftime('%Y%m%d%H%M%S')}", 
            "house_id": house_id, 
            "grade": final_sev, 
            "db": calc_db, 
            "timestamp": timestamp
        }
        create_content_instance(status_data, labels=["grade"], container_name=CNT_STATUS)
        
        # B. Analysis 결과 구성 (상세 데이터)
        analysis_res = AnalysisResult(
            result=result_label, 
            probability=float(predicted_prob), 
            db_level=float(calc_db), 
            avg_1min=avg_1min,
            avg_5min=avg_5min,
            severity=final_sev,
            is_external=is_external,
            duration=0.0, 
            vibration_peaks=num_peaks, 
            vibration_max=vibration_max, 
            audio_signature=audio_signature
        )
        
        # C. 최종 출력 데이터 (중재 상태 확정 및 법적 검토 메시지 포함)
        output_data = OneM2MPlatformOutput(
            event_id=f"EVT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            house_id=house_id, 
            timestamp=timestamp, 
            analysis=analysis_res,
            action=Action(
                mediation_sent=is_mediation_active, # 등급 판정에 따른 정확한 중재 제어
                target=final_sev
            )
        )
        
        out_dict = output_data.dict(exclude_none=True)
        # 법적 검토 메시지 추가
        out_dict["legal_review"] = review_msg
        out_dict["lmax_count"] = state.lmax_exceed_count
        
        all_analysis_history.append(out_dict)
        # 세션 내 히스토리가 충분히 유지되도록 제한 상향 (메모리 허용 범위 내)
        if len(all_analysis_history) > 5000:
            all_analysis_history.pop(0)

        
        # D. oneM2M 저장: 분석 결과만 기록 (중재 발송 상태를 따로 보낼 필요 없음)
        create_content_instance(out_dict, labels=["analysis"], container_name=CNT_NOISE)
        
        # E. 대시보드 전파: 실시간으로 중재 발송됨 상태를 화면에 띄움
        for c in active_websocket_connections: 
            await c.send_json(out_dict)
        
        logger.info(f"🚀 중재 상태: {'발송' if is_mediation_active else '대기'} | 등급: {final_sev}")
        return {"status": "success", "result": result_label, "mediation": is_mediation_active}

    except Exception as e: # 여기서 try 블록을 안전하게 닫아줍니다.
        logger.error(f"Error: {e}")
        return {"status": "error"}
    
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websocket_connections.append(websocket)
    try:
        while True: await websocket.receive_text()
    except: active_websocket_connections.remove(websocket)

@app.get("/get_latest_noise_data")
async def get_latest_noise_data():
    content = retrieve_latest_content_instance()
    if content: return content
    return {"analysis": {"result": "대기 중", "db_level": 0, "severity": "Green"}}

@app.get("/logs")
async def get_logs(limit: int = 100): # 기본값을 100으로 상향하여 초기 로드시 더 많은 히스토리를 가져옴
    logs = retrieve_all_content_instances(limit=limit)
    if logs is not None:
        return {"status": "success", "logs": logs}
    # Only raise 500 if it's truly None (error), but retrieve_all... returns [] on valid empty.
    # So this might catch network errors which return [] too? 
    # mobius_client returns [] on error. Ideally we want to distinguish.
    # But for now, returning success with empty list is safer for the frontend.
    return {"status": "success", "logs": []}

def get_logs_for_report(house_id, start_dt, end_dt):
    local_logs = all_analysis_history
    platform_logs=retrieve_all_content_instances() or []
    combined_logs = local_logs + platform_logs
    if not combined_logs: return []
    
    filtered = []
    seen_events = set()
    for log in combined_logs:
        eid = log.get("event_id")
        if eid in seen_events: continue
        
        if log.get("house_id") != house_id: continue
        
        try:
            ts_str = log.get("timestamp").replace("Z", "")
            # UTC/KST 보정이 필요하다면 여기서 timedelta(hours=9)를 더하세요
            ts = datetime.fromisoformat(ts_str) 
            if start_dt <= ts <= end_dt: 
                filtered.append(log)
                seen_events.add(eid)
        except: continue

    return sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)

@app.get("/report/csv")
def get_noise_degree(avg_1min, avg_5min, timestamp_str):
    """
    1분/5분 평균 소음과 시간대를 바탕으로 법적 소음 정도를 판정하는 함수
    """
    try:
        # 시간대 파악 (KST 기준 보정 필요시 확인)
        ts = datetime.fromisoformat(timestamp_str.replace("Z", ""))
        is_night = ts.hour >= 22 or ts.hour < 6
    except:
        is_night = False

    # 1. 직접충격 소음 기준 (1분 평균)
    threshold_1min = 34 if is_night else 39
    limit_1min = 35 if is_night else 40  # 수인한도 (참아야 할 한계)

    # 2. 공기전달 소음 기준 (5분 평균)
    threshold_5min = 40 if is_night else 45

    status = []

    # 판정 로직
    if avg_1min > limit_1min:
        status.append(f"수인한도 초과(기준:{limit_1min}dB)")
    elif avg_1min > threshold_1min:
        status.append(f"법적 주의(기준:{threshold_1min}dB)")

    if avg_5min > threshold_5min:
        status.append(f"공기전달 소음 위반(기준:{threshold_5min}dB)")

    if not status:
        return "정상(생활소음 범위)"
    
    return " | ".join(status)


async def get_csv_report(house_id: str, start_date: str, end_date: str):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), dt_time.max)
    except: raise HTTPException(400, "Invalid date")
    logs = get_logs_for_report(house_id, start_dt, end_dt)
    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'event', 'result', 'db', '1min_avg', '5min_avg', 'noise_degree', 'legal_review', 'lmax_count', 'prob', 'severity', 'vib_max', 'mediation'])
    for log in logs:
        a = log.get("analysis", {})
        ts = log.get("timestamp")
        degree = get_noise_degree(a.get("avg_1min", 0), a.get("avg_5min", 0), ts)
        writer.writerow([
            ts, log.get("event_id"), a.get("result"), a.get("db_level"),
            a.get("avg_1min", 0), a.get("avg_5min", 0), degree,
            log.get("legal_review", ""), log.get("lmax_count", 0),
            a.get("probability"), a.get("severity"), a.get("vibration_max", 0), log.get("action", {}).get("mediation_sent")
        ])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=report.csv"})

try:
    pdfmetrics.registerFont(TTFont('Pretendard', 'Pretendard.ttf'))
    FONT_NAME = 'Pretendard'
except:
    # 폰트 파일이 없을 경우를 대비한 기본값
    FONT_NAME = 'Helvetica'
    logger.error("❌ 한글 폰트 로드 실패! 'Pretendard.ttf' 파일 확인 필요.")

@app.get("/report/pdf")
async def get_pdf_report(house_id: str, start_date: str, end_date: str):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), dt_time.max)
    except: raise HTTPException(400, "Invalid date")

    logs = get_logs_for_report(house_id, start_dt, end_dt)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    korean_style = ParagraphStyle(
        name='KoreanStyle',
        fontName=FONT_NAME, # 등록한 폰트 적용
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # 제목에 적용
    story.append(Paragraph(f"층간소음 분석 리포트: {house_id}", korean_style))
    
    # 본문용 스타일도 필요하다면 추가
    body_style = ParagraphStyle(
        name='BodyStyle',
        fontName=FONT_NAME,
        fontSize=10,
        leading=15
    )
    story.append(Paragraph(f"측정 기간: {start_date} ~ {end_date}", body_style))

    
    # [추가] 층간소음 기준 안내 텍스트
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>[층간소음 및 수인한도 기준 안내]</b>", styles['Normal']))
    story.append(Paragraph("• 주간(06~22시): 1분 평균 39dB 초과 시 문제 소음 / 수인한도 40dB / 5분 평균 45dB 초과 시 층간소음", styles['Normal']))
    story.append(Paragraph("• 야간(22~06시): 1분 평균 34dB 초과 시 문제 소음 / 수인한도 35dB / 5분 평균 40dB 초과 시 층간소음", styles['Normal']))
    story.append(Paragraph("• 소음 예시: 30dB(조용한 주택가), 40dB(낮은 TV), 50dB(보통 대화), 60dB(식당 대화)", styles['Normal']))
    story.append(Spacer(1, 10))

    # Add Heatmap
    hm = create_noise_heatmap_image(logs)
    if hm: story.append(Image(hm, width=6*inch, height=2.5*inch))
    
    # Add Waveform of Critical Event
    max_ev = None
    for log in logs:
        sev = log.get("analysis", {}).get("severity")
        if sev == "Red":
            max_ev = log
            break
    if max_ev:
        sig = max_ev.get("analysis", {}).get("audio_signature")
        wf = create_waveform_image(sig)
        if wf: story.append(Image(wf, width=6*inch, height=1.5*inch))
        
    # Add Table of Events
    if logs:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Detailed Event Log", styles['Heading2']))
        table_data = [['Time', 'Type', 'Max', '1m Avg', '5m Avg', 'Degree', 'Sev']]
        for log in logs[:20]: # Show last 20 events in PDF for space
            a = log.get("analysis", {})
            ts_full = log.get("timestamp")
            ts = ts_full[11:19]
            degree = get_noise_degree(a.get("avg_1min", 0), a.get("avg_5min", 0), ts_full)
            legal = log.get("legal_review", "N/A")
            table_data.append([
                ts, a.get("result"), f"{a.get('db_level',0):.1f}", 
                f"{a.get('avg_1min',0):.1f}", f"{a.get('avg_5min',0):.1f}",
                degree, a.get("severity")
            ])
        t = Table(table_data, colWidths=[0.8*inch, 1.3*inch, 0.5*inch, 0.6*inch, 0.6*inch, 1.3*inch, 0.6*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
        
    doc.build(story)
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type='application/pdf', headers={'Content-Disposition': 'attachment; filename=report.pdf'})

