import numpy as np
import logging
import json
import time
import os
import asyncio
import requests
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
# Import Mobius client and configuration
from mobius_client import create_content_instance, retrieve_all_content_instances, retrieve_latest_content_instance
from config import AE_NAME

# Import AI model functions
from ai_engine import load_ai_model_v2, preprocess_audio_for_v2, predict_noise_v2

MOBIUS_URL = "https://onem2m.iotcoss.ac.kr/Mobius/ae_Namsan/cnt_noise/la"
HEADERS = {
    "Accept": "application/json",
    "X-M2M-RI": "12345",
    "X-M2M-Origin": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "X-API-KEY": "AWAYXoieop5ncAjTh90YfkHk9eH8Z7Vb",
    "x-auth-custom-lecture": "LCT_20250007",
    "x-auth-custom-creator": "dgunamsan"
}

def get_realtime_noise():
    response = requests.get(MOBIUS_URL, headers=HEADERS)
    if response.status_code == 200:
        res = response.json()
        
        # 'con' 필드가 문자열이 아닌 딕셔너리(JSON) 형태로 들어있을 겁니다.
        # Mobius 서버 설정에 따라 문자열일 수도 있으니 json.loads()가 필요할 수도 있어요.
        content = res['m2m:cin']['con']
        
        # 우리가 대시보드에 뿌려줄 데이터 추출
        result = content['analysis']['result']   # "Footstep"
        db = content['analysis']['db_level']     # 75.2
        severity = content['analysis']['severity'] # "Red"
        
        return {"result": result, "db": db, "severity": severity}
    return None

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- State Management & Constants ---
class HouseState(BaseModel):
    status: str = "quiet"  # quiet, loud
    start_time: datetime | None = None
    last_loud_time: datetime | None = None
    last_packet_severity: str = "Green"
    start_of_quiet: datetime | None = None

house_states: Dict[str, HouseState] = {}
QUIET_PERIOD_SECONDS = 5
VIBRATION_PEAK_THRESHOLD = 0.3 # Example threshold for what constitutes a "peak"

# --- Pydantic Models for Input, Output, and Notifications ---

# --- INPUT (from Arduino via Mobius Notification)
class MetaData(BaseModel):
    sampling_rate: str
    vibration_unit: str
    sound_unit: str

class SensorPayload(BaseModel):
    vibration: Dict[str, List[float]]
    sound_raw: List[int]
    raw_max_amplitude: int

class NewPayload(BaseModel):
    house_id: str
    timestamp: str
    meta: MetaData
    payload: SensorPayload

# --- OUTPUT (to Mobius cnt_noise)
class AnalysisResult(BaseModel):
    result: str
    probability: float
    db_level: float
    severity: str
    duration: float = 0.0
    vibration_peaks: int

class Action(BaseModel):
    mediation_sent: bool
    target: str

class OneM2MPlatformOutput(BaseModel):
    event_id: str
    house_id: str
    timestamp: str
    analysis: AnalysisResult
    action: Action

# --- oneM2M Notification Structure
class Representation(BaseModel):
    con: str # The stringified JSON content from the raw data container

class NotificationEvent(BaseModel):
    rep: Representation

class NotificationPayload(BaseModel):
    nev: NotificationEvent

class MobiusNotification(BaseModel):
    sgn: NotificationPayload

# --- Global App and Model Initialization ---

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the V2 model at startup
if not load_ai_model_v2():
    logger.error("CRITICAL: Failed to load AI model V2 at startup. The application may not function correctly.")

# --- Helper Functions for Analysis ---
def amplitude_to_db(amplitude: int) -> float:
    """Converts raw amplitude to a dB-like scale."""
    if amplitude == 0:
        return 0.0
    # This is a simplified conversion. A calibrated microphone would be needed for true dB.
    # We are creating a logarithmic scale where 0 maps to 0 and 32767 maps to ~96 dB.
    return 20 * np.log10(max(1, amplitude))

def analyze_vibration_peaks(vibration_z_list: np.ndarray, threshold: float = VIBRATION_PEAK_THRESHOLD) -> int:
    """Analyzes vibration data to count peaks above a certain threshold."""
    if vibration_z_list.size == 0:
        return 0
    # A simple peak count - more sophisticated analysis could be done here
    peaks = np.where(vibration_z_list > threshold)[0]
    return len(peaks)

# --- [PDF Generation Imports] ---
from fastapi.responses import Response
import io
from datetime import datetime, time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
# --- [End PDF Generation Imports] ---

active_websocket_connections: List[WebSocket] = []

# --- Helper function for PDF Chart Generation ---
def create_noise_heatmap_image(logs: List[Dict]) -> io.BytesIO:
    """
    Creates a heatmap visualization of noise events by day of the week and hour.
    Returns the image as an in-memory BytesIO buffer.
    """
    if not logs:
        return None

    # Process data into a DataFrame
    event_data = []
    for log in logs:
        severity = log.get("analysis", {}).get("severity")
        if severity in ["Red", "Yellow"]:
            try:
                ts = datetime.fromisoformat(log.get("timestamp"))
                event_data.append({"weekday": ts.weekday(), "hour": ts.hour})
            except (ValueError, TypeError):
                continue
    
    if not event_data:
        return None

    df = pd.DataFrame(event_data)
    
    # Create a 2D pivot table for the heatmap
    heatmap_data = df.pivot_table(index='weekday', columns='hour', aggfunc='size', fill_value=0)
    # Ensure all hours (0-23) and weekdays (0-6) are present
    heatmap_data = heatmap_data.reindex(index=range(7), columns=range(24), fill_value=0)
    
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    # Create plot using matplotlib
    fig, ax = plt.subplots(figsize=(10, 4))
    cax = ax.pcolormesh(heatmap_data.columns, heatmap_data.index, heatmap_data.values, cmap='YlOrRd', shading='auto')
    fig.colorbar(cax, label='Event Count')

    ax.set_title('Weekly Noise Heatmap (Critical Events)', fontsize=14)
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Day of Week')
    
    ax.set_xticks(range(24))
    ax.set_yticks(np.arange(7) + 0.5)
    ax.set_yticklabels(days)
    ax.invert_yaxis()

    # Save plot to a memory buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return buf

# --- API Endpoints ---

@app.post("/notification")
async def handle_mobius_notification(notification: MobiusNotification):
    """
    Handles incoming notifications from Mobius, runs V2 AI model, manages event state,
    calculates duration, and determines final severity based on new logic.
    """
    logger.info("Received notification from Mobius for V2 processing.")
    
    # 1. Parse incoming data
    try:
        raw_data_string = notification.sgn.nev.rep.con
        payload_dict = json.loads(raw_data_string)
        payload = NewPayload(**payload_dict)
        logger.info(f"Successfully parsed raw data for house_id: {payload.house_id}")
    except Exception as e:
        logger.error(f"Error parsing notification payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid notification format or content.")

    # 2. Get AI Analysis & Sensor Data
    sr_int = int(payload.meta.sampling_rate.replace('Hz', ''))
    
    # Convert raw sound to float32 numpy array for processing
    audio_np = np.array(payload.payload.sound_raw, dtype=np.float32)
    # Normalize audio if it's int16
    if np.issubdtype(audio_np.dtype, np.integer):
        audio_np = audio_np / 32768.0

    processed_audio_v2 = preprocess_audio_for_v2(audio_np, sr=sr_int)
    
    if processed_audio_v2 is None:
        logger.error("Failed to preprocess audio for V2 model.")
        raise HTTPException(status_code=500, detail="Audio preprocessing failed.")

    result_label, predicted_prob = predict_noise_v2(processed_audio_v2)
    
    # Get other sensor data for grading logic
    calculated_db = amplitude_to_db(payload.payload.raw_max_amplitude)
    vibration_np = np.array(payload.payload.vibration.get('z', []))
    num_peaks = analyze_vibration_peaks(vibration_np)

    # 3. Determine Preliminary Packet Severity
    packet_severity = "Green"
    is_footsteps = 'footsteps' in result_label.lower()

    if is_footsteps and predicted_prob > 0.60:
        packet_severity = "Yellow"
        logger.info(f"[{payload.house_id}] Preliminary Severity: YELLOW (Footsteps detected with {predicted_prob:.2f} confidence)")
    elif 65 <= calculated_db < 80:
        packet_severity = "Yellow"
        logger.info(f"[{payload.house_id}] Preliminary Severity: YELLOW (dB level is {calculated_db:.2f})")
    elif num_peaks > 2: # Simple vibration check
        packet_severity = "Yellow"
        logger.info(f"[{payload.house_id}] Preliminary Severity: YELLOW (Vibration peaks detected: {num_peaks})")

    # 4. Process State Machine
    house_id = payload.house_id
    current_time = datetime.fromisoformat(payload.timestamp)
    state = house_states.get(house_id, HouseState())
    
    is_loud_packet = packet_severity in ["Yellow", "Red"]
    notification_payload = None

    if is_loud_packet:
        if state.status == "quiet":
            state.status = "loud"
            state.start_time = current_time
            logger.info(f"[{house_id}] Event Start: New loud event started.")
        
        state.last_loud_time = current_time
        state.last_packet_severity = packet_severity
        state.start_of_quiet = None

        event_duration = (current_time - state.start_time).total_seconds()
        
        # Rule Check: Upgrade to RED based on duration and confidence
        final_severity = packet_severity
        if is_footsteps and predicted_prob > 0.75 and event_duration >= 5:
            final_severity = "Red"
            logger.info(f"[{house_id}] Severity UPGRADED to RED (Footsteps {predicted_prob:.2f} confidence & duration >= 5s).")
            # This is a RED event, so we prepare to notify immediately
            notification_payload = (final_severity, event_duration)
        elif calculated_db >= 80 and event_duration >= 3:
            final_severity = "Red"
            logger.info(f"[{house_id}] Severity UPGRADED to RED (dB >= 80 & duration >= 3s).")
            # This is also a RED event, notify immediately
            notification_payload = (final_severity, event_duration)

    else: # Packet is Green
        if state.status == "loud":
            if state.start_of_quiet is None:
                state.start_of_quiet = current_time
            
            # If quiet period has passed since the last loud packet, the event has ended.
            if (current_time - state.last_loud_time).total_seconds() >= QUIET_PERIOD_SECONDS:
                event_duration = (state.last_loud_time - state.start_time).total_seconds()
                final_severity = state.last_packet_severity
                logger.info(f"[{house_id}] Event End: Quiet period detected. Final duration: {event_duration:.1f}s")
                # Prepare to notify about the completed event
                notification_payload = (final_severity, event_duration)
                state = HouseState() # Reset state for the next event
    
    house_states[house_id] = state

    # 5. Send Notification if a final decision was made
    # Only send if there's a payload AND the AI classification for critical sounds is confident enough.
    if notification_payload:
        final_severity, event_duration = notification_payload
        
        # Apply confidence gate: only send alert if AI is sure, or if it's a non-AI based alert (like high dB)
        is_ai_confident = (is_footsteps and predicted_prob >= 0.75)
        is_non_ai_alert = not is_footsteps and final_severity in ["Yellow", "Red"]

        if is_ai_confident or is_non_ai_alert:
            output_data = OneM2MPlatformOutput(
                event_id=f"EVT_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                house_id=payload.house_id, timestamp=payload.timestamp,
                analysis=AnalysisResult(
                    result=result_label, probability=predicted_prob, db_level=calculated_db,
                    severity=final_severity, duration=event_duration,
                    vibration_peaks=num_peaks
                ),
                action=Action(mediation_sent=True, target=final_severity)
            )

            labels = ["analysis_result_v2", output_data.analysis.severity]
            mobius_response = create_content_instance(output_data.dict(), labels=labels)
            
            if mobius_response:
                logger.info(f"Successfully posted final event (V2) to Mobius for {house_id}.")
                for connection in active_websocket_connections:
                    await connection.send_json(output_data.dict())
        else:
            logger.info(f"[{house_id}] Event notification withheld. AI confidence ({predicted_prob:.2f}) for '{result_label}' is below the 0.75 threshold.")

    return {"status": "success", "message": "Notification processed with V2 logic."}


@app.get("/get_latest_noise_data")
async def get_latest_noise_data():
    logger.info("Proxy endpoint /get_latest_noise_data called by frontend.")
    
    # 1. mobius_client에서 데이터를 가져옴
    content = retrieve_latest_content_instance()
    
    # 2. [핵심] 가져온 데이터가 있는지, 그리고 내용이 있는지 확인
    if content:
        # 터미널에 실제 나가는 데이터 모양을 찍어봅니다 (디버깅용)
        print(f"DEBUG - 프론트엔드로 보낼 데이터: {content}")
        return content
    
    # 3. 데이터가 없을 경우 에러 대신 '준비 중' 상태를 보냅니다.
    logger.warning("가져온 데이터가 비어있습니다.")
    return {
        "analysis": {
            "result": "연결 확인됨",
            "db_level": 0,
            "severity": "Green",
            "note": "데이터 수신 대기 중..."
        }
    }
@app.get("/logs")
async def get_logs(limit: int = None):
    try:
        logs = retrieve_all_content_instances(limit=limit)
        if logs is not None:
            logger.info(f"Successfully retrieved {len(logs)} logs from Mobius (limit={limit}).")
            return {"status": "success", "logs": logs}
        else:
            raise HTTPException(status_code=500, detail="Failed to retrieve logs from Mobius.")
    except Exception as e:
        logger.exception("An error occurred while retrieving logs.")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving logs.")

@app.get("/report/pdf")
async def get_pdf_report(house_id: str, start_date: str, end_date: str):
    """
    Generates a PDF report for a given house_id and date range.
    Date format for query parameters: YYYY-MM-DD
    """
    try:
        # 1. Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        # Include the entire end day
        end_dt = datetime.combine(datetime.strptime(end_date, "%Y-%m-%d"), time.max)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # 2. Fetch all logs
    all_logs = retrieve_all_content_instances()
    if not all_logs:
        raise HTTPException(status_code=404, detail="No logs found on Mobius platform.")

    # 3. Filter logs by house_id and date range
    filtered_logs = []
    severity_counts = {"Red": 0, "Yellow": 0, "Green": 0}

    for log in all_logs:
        if log.get("house_id") == house_id:
            try:
                log_dt = datetime.fromisoformat(log.get("timestamp"))
                if start_dt <= log_dt <= end_dt:
                    filtered_logs.append(log)
                    severity = log.get("analysis", {}).get("severity")
                    if severity in severity_counts:
                        severity_counts[severity] += 1
            except (ValueError, TypeError):
                # Ignore logs with invalid timestamp format
                continue
    
    # Sort logs by timestamp
    filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 4. Generate PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    story = []
    styles = getSampleStyleSheet()

    # Title
    story.append(Paragraph(f"층간소음 분석 리포트", styles['h1']))
    story.append(Paragraph(f"({house_id})", styles['h2']))
    story.append(Paragraph(f"리포트 기간: {start_date} ~ {end_date}", styles['Normal']))
    story.append(Paragraph("<br/><br/>", styles['Normal']))

    # Summary Section
    story.append(Paragraph("소음 발생 요약", styles['h3']))
    summary_text = f"""
    - <font color='red'>Red (경고)</font>: {severity_counts['Red']} 회
    - <font color='orange'>Yellow (주의)</font>: {severity_counts['Yellow']} 회
    - <font color='green'>Green (안정)</font>: {severity_counts['Green']} 회
    """
    story.append(Paragraph(summary_text, styles['BodyText']))
    story.append(Paragraph("<br/><br/>", styles['Normal']))

    # --- NEW: Add Heatmap to PDF ---
    story.append(Paragraph("주간/시간대별 소음 발생 빈도", styles['h3']))
    heatmap_buffer = create_noise_heatmap_image(filtered_logs)
    if heatmap_buffer:
        story.append(Image(ImageReader(heatmap_buffer), width=6*inch, height=2.5*inch))
    else:
        story.append(Paragraph("시각화할 데이터가 부족합니다.", styles['Normal']))
    story.append(Paragraph("<br/><br/>", styles['Normal']))
    # --- END NEW SECTION ---

    # Detailed Log Section
    story.append(Paragraph("상세 발생 이력", styles['h3']))
    
    if not filtered_logs:
        story.append(Paragraph("해당 기간에 기록된 소음 데이터가 없습니다.", styles['Normal']))
    else:
        table_data = [["타임스탬프", "소음 종류", "심각도", "지속 시간(초)", "최대 데시벨", "주요 진동 주파수"]]
        for log in filtered_logs:
            analysis = log.get("analysis", {})
            
            severity = analysis.get("severity", "N/A")
            if severity == "Red":
                severity_p = Paragraph(f"<font color='red'>{severity}</font>", styles['Normal'])
            elif severity == "Yellow":
                severity_p = Paragraph(f"<font color='orange'>{severity}</font>", styles['Normal'])
            else:
                severity_p = Paragraph(f"<font color='green'>{severity}</font>", styles['Normal'])

            dom_freq_text = f"{analysis.get('dominant_frequency', 0.0):.1f} Hz"
            duration_text = f"{analysis.get('duration', 0.0):.1f}s"

            table_data.append([
                log.get("timestamp", "N/A"),
                analysis.get("result", "N/A"),
                severity_p,
                duration_text,
                f"{analysis.get('db_level', 0):.2f} dB",
                dom_freq_text
            ])

        # Create Table
        t = Table(table_data, colWidths=[1.5*inch, 1.1*inch, 0.7*inch, 0.8*inch, 1*inch, 1.2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(t)

    doc.build(story)

    # 5. Return PDF as a response
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="report_{house_id}_{start_date}_to_{end_date}.pdf"'}
    )

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websocket_connections.append(websocket)
    logger.info(f"WebSocket client connected: {websocket.client}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websocket_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected: {websocket.client}")
    except Exception as e:
        if websocket in active_websocket_connections:
            active_websocket_connections.remove(websocket)
        logger.exception(f"Unhandled error in WebSocket connection for client {websocket.client}.")

@app.websocket("/ws/noise")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 1. 학교 서버에서 최신 데이터 가져오기
            response = requests.get(MOBIUS_URL, headers=HEADERS)
            if response.status_code == 200:
                content = response.json()['m2m:cin']['con']
                
                # 2. 대시보드로 실시간 전송
                await websocket.send_json({
                    "type": content['analysis']['result'],    # Footstep
                    "db": content['analysis']['db_level'],     # 75.2
                    "severity": content['analysis']['severity'] # Red
                })
            
            await asyncio.sleep(2)  # 2초마다 업데이트
    except Exception as e:
        print(f"연결 종료: {e}")