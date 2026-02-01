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

# Import AI model functions
from ai_engine import load_ai_model_v2, predict_noise_v2, preprocess_audio_for_v2

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

house_states: Dict[str, HouseState] = {}
QUIET_PERIOD_SECONDS = 5
VIBRATION_PEAK_THRESHOLD = 0.3

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
    severity: str
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
    if MOCK_DATA_MODE: asyncio.create_task(mock_data_sender())
    if not load_ai_model_v2(): logger.error("CRITICAL: Failed to load AI model V2.")

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
        sgn = body.get("m2m:sgn") or body.get("sgn")
        content = None
        if sgn and "nev" in sgn and "rep" in sgn["nev"]:
            rep = sgn["nev"]["rep"]
            content = rep.get("m2m:cin", {}).get("con") or rep.get("cin", {}).get("con")
        
        if content == "Apology Sent" or str(content).strip() == "1":
            timestamp = datetime.now(timezone.utc).isoformat()
            data = {"event": "apology", "message": "Apology Sent", "timestamp": timestamp}
            # Save to history
            create_content_instance(data, labels=["apology"], container_name=CNT_APOLOGY)
            # Broadcast
            for c in active_websocket_connections: await c.send_json(data)
    except Exception as e: logger.error(f"Apology Error: {e}")
    return {"status": "ok"}

@app.post("/notification")
async def handle_mobius_notification(request: Request): # [수정] dict 대신 Request 추가
    try:
        # [수정] 여기서부터 body를 가져옵니다.
        body = await request.json()
        print("📢 [RAW DATA RECEIVED]:", body)
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
        if len(audio_np) < 80:
            return {"status": "skipped", "reason": "too short"}
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
    
        # 3. Grading
        raw_amp = payload.get("raw_max_amplitude", 0)
        calc_db = amplitude_to_db(raw_amp)
        num_peaks = analyze_vibration_peaks(vibration_np)
        
        sev = "Green"
        is_foot = "footsteps" in result_label.lower()
        if is_foot and predicted_prob > 0.6: sev = "Yellow"
        elif 65 <= calc_db < 80: sev = "Yellow"
        elif num_peaks > 2: sev = "Yellow"
        
        # 4. State Machine
        current_time = datetime.fromisoformat(timestamp.replace("Z",""))
        state = house_states.get(house_id, HouseState())
        
        final_sev = sev
        if state.start_time:
            dur = (current_time - state.start_time).total_seconds()
            if is_foot and predicted_prob > 0.75 and dur >= 5: final_sev = "Red"
            elif calc_db >= 80 and dur >= 3: final_sev = "Red"
        
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
        # A. Status to CNT_STATUS
        status_data = {"event_id": f"STS_{datetime.now().strftime('%Y%m%d%H%M%S')}", "house_id": house_id, "grade": final_sev, "db": calc_db, "timestamp": timestamp}
        create_content_instance(status_data, labels=["grade"], container_name=CNT_STATUS)
        
        # B. Analysis to CNT_NOISE
        analysis_res = AnalysisResult(
            result=result_label, probability=float(predicted_prob), db_level=float(calc_db), severity=final_sev,
            duration=0.0, vibration_peaks=num_peaks, vibration_max=vibration_max, audio_signature=audio_signature
        )
        output_data = OneM2MPlatformOutput(
            event_id=f"EVT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            house_id=house_id, timestamp=timestamp, analysis=analysis_res,
            action=Action(mediation_sent=(final_sev=="Red"), target=final_sev)
        )
        out_dict = output_data.dict(exclude_none=True)
        # Ensure vibration_max is in analysis for frontend
        create_content_instance(out_dict, labels=["analysis"], container_name=CNT_NOISE)
        
        for c in active_websocket_connections: await c.send_json(out_dict)
        
        return {"status": "success", "result": result_label}
        
    except Exception as e:
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
async def get_logs(limit: int = None):
    logs = retrieve_all_content_instances(limit=limit)
    if logs is not None:
        return {"status": "success", "logs": logs}
    # Only raise 500 if it's truly None (error), but retrieve_all... returns [] on valid empty.
    # So this might catch network errors which return [] too? 
    # mobius_client returns [] on error. Ideally we want to distinguish.
    # But for now, returning success with empty list is safer for the frontend.
    return {"status": "success", "logs": []}

def get_logs_for_report(house_id, start_dt, end_dt):
    all_logs = retrieve_all_content_instances()
    if not all_logs and MOCK_DATA_MODE:
        return []
    filtered = []
    for log in all_logs:
        if log.get("house_id") != house_id: continue
        try:
            ts = datetime.fromisoformat(log.get("timestamp").replace("Z",""))
            if start_dt <= ts <= end_dt: filtered.append(log)
        except: continue
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return filtered

@app.get("/report/csv")
async def get_csv_report(house_id: str, start_date: str, end_date: str):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), dt_time.max)
    except: raise HTTPException(400, "Invalid date")
    logs = get_logs_for_report(house_id, start_dt, end_dt)
    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'event', 'result', 'db', 'prob', 'severity', 'vib_max', 'mediation'])
    for log in logs:
        a = log.get("analysis", {})
        writer.writerow([
            log.get("timestamp"), log.get("event_id"), a.get("result"), a.get("db_level"),
            a.get("probability"), a.get("severity"), a.get("vibration_max", 0), log.get("action", {}).get("mediation_sent")
        ])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=report.csv"})

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
    story.append(Paragraph(f"Noise Report: {house_id}", styles['Title']))
    
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
        
    doc.build(story)
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type='application/pdf', headers={'Content-Disposition': 'attachment; filename=report.pdf'})