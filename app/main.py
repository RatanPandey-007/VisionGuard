import os
import sys
import time
import base64
import asyncio
import threading
from datetime import datetime
from fastapi import FastAPI, Response, HTTPException, Body
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add app directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera import WebcamCamera, DemoImageCamera, get_available_cameras
from detector import QualityInspector
from database import init_db, log_inspection, get_analytics_summary, get_recent_inspections, populate_mock_history, DB_PATH, IS_VERCEL
from report import generate_pdf_report

# Configure directories dynamically to support read-only cloud filesystems
if IS_VERCEL:
    INSPECTIONS_DIR = "/tmp/inspections"
    REPORTS_DIR = "/tmp/reports"
else:
    INSPECTIONS_DIR = os.path.join("data", "inspections")
    REPORTS_DIR = "reports"

os.makedirs(INSPECTIONS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
init_db()

app = FastAPI(title="VisionGuard Edge Backend")

# System State Configurations
class SystemConfig(BaseModel):
    demo_mode_active: bool = True
    camera_index: int = 0
    decision_threshold: float = 85.0
    inspection_mode: str = "PCB"      # "PCB" or "YOLO"
    demo_override: str = "None"       # "None", "Force PASS", "Force Missing", "Force Misaligned"

class ScanPayload(BaseModel):
    image: str = None  # Optional Base64 data: "data:image/jpeg;base64,..."

class ReportPayload(BaseModel):
    id: int
    timestamp: str
    product_id: str
    result: str
    defect_type: str = None
    confidence: float
    image_path: str = None
    image_b64: str = None

config = SystemConfig()

# Global AI Inspector instance (will gracefully fall back to OpenCV if YOLO is not installed on Vercel)
inspector = QualityInspector()

# Thread-safe Camera Manager to handle webcam sharing
class CameraManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.camera = None
        self.demo_mode_active = True
        self.camera_index = 0
        self.latest_raw_frame = None
        self.latest_annotated_frame = None

    def configure(self, demo_mode: bool, index: int):
        with self.lock:
            if self.demo_mode_active != demo_mode or self.camera_index != index:
                self.demo_mode_active = demo_mode
                self.camera_index = index
                if self.camera is not None:
                    try:
                        self.camera.release()
                    except Exception:
                        pass
                    self.camera = None

    def get_camera(self):
        if self.camera is None:
            if self.demo_mode_active:
                self.camera = DemoImageCamera()
            else:
                self.camera = WebcamCamera(self.camera_index)
        return self.camera

    def capture_frame(self):
        with self.lock:
            try:
                cam = self.get_camera()
                ret, frame = cam.get_frame()
                if ret and frame is not None:
                    self.latest_raw_frame = frame.copy()
                    return True, frame
                return False, None
            except Exception as e:
                print(f"Error capturing frame: {str(e)}")
                self.camera = None
                return False, None

    def release_camera(self):
        with self.lock:
            if self.camera is not None:
                try:
                    self.camera.release()
                except Exception:
                    pass
                self.camera = None

camera_manager = CameraManager()
camera_manager.configure(config.demo_mode_active, config.camera_index)

# Serve generated static resources and frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# Dynamic file routing endpoints to support Vercel serverless /tmp
@app.get("/data/inspections/{filename}")
def get_inspection_image(filename: str):
    path = os.path.join(INSPECTIONS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Inspection image not found.")
    return FileResponse(path)

@app.get("/reports/{filename}")
def get_pdf_report(filename: str):
    path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF report not found.")
    return FileResponse(path, media_type="application/pdf")

# Configuration API Endpoints
@app.get("/api/config")
def get_config():
    return config

@app.post("/api/config")
def update_config(new_config: SystemConfig):
    global config
    config = new_config
    camera_manager.configure(config.demo_mode_active, config.camera_index)
    return {"status": "success", "config": config}

@app.get("/api/cameras")
def get_cameras():
    return get_available_cameras()

# Streaming Video Feed Endpoint (MJPEG)
def gen_frames():
    while True:
        ret, frame = camera_manager.capture_frame()
        if not ret or frame is None:
            import numpy as np
            import cv2
            standby = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(standby, "Camera Standby / Connecting...", (120, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            _, jpeg = cv2.imencode('.jpg', standby)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            time.sleep(0.2)
            continue

        import cv2
        if config.inspection_mode == "PCB":
            res = inspector.inspect_pcb_vision(frame, config.decision_threshold)
            annotated = res["annotated_frame"]
        else:
            annotated, _ = inspector.inspect_yolo_coco(frame)

        camera_manager.latest_annotated_frame = annotated.copy()

        ret, jpeg = cv2.imencode('.jpg', annotated)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
        time.sleep(0.05)

@app.get("/api/video_feed")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# Trigger Single Inspection Scan
@app.post("/api/scan")
def trigger_scan(payload: ScanPayload = None):
    frame = None
    
    # 1. Acquire Image (Either decoded from payload, or snapped from camera)
    if payload and payload.image:
        try:
            # Decode base64 image uploaded from browser camera
            base64_str = payload.image
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            img_data = base64.b64decode(base64_str)
            import numpy as np
            nparr = np.frombuffer(img_data, np.uint8)
            import cv2
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")
            
    if frame is None:
        # Fallback to backend local CameraManager
        ret, frame = camera_manager.capture_frame()
        if not ret or frame is None:
            raise HTTPException(status_code=500, detail="Failed to grab frame from camera source.")

    # Unique product id
    product_id = f"PCB-{int(time.time()) % 10000}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Apply Demo Override if enabled
    import numpy as np
    import cv2
    if config.demo_override == "Force PASS":
        result = "PASS"
        defect_type = None
        confidence = round(np.random.uniform(96.0, 99.5), 1)
        annotated = frame.copy()
        cv2.rectangle(annotated, (120, 90), (520, 390), (0, 255, 0), 3)
        cv2.putText(annotated, "🟢 PASS (DEMO MODE)", (140, 130), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(annotated, f"CONFIDENCE: {confidence}%", (140, 160), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    elif config.demo_override == "Force Defect: Missing Component":
        result = "FAIL"
        defect_type = "Missing Component"
        confidence = round(np.random.uniform(91.0, 94.8), 1)
        annotated = frame.copy()
        cv2.rectangle(annotated, (120, 90), (520, 390), (0, 0, 255), 3)
        cv2.circle(annotated, (250, 200), 30, (0, 0, 255), 2)
        cv2.putText(annotated, "🔴 DEFECT DETECTED: Missing Component", (140, 130), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    elif config.demo_override == "Force Defect: Misalignment":
        result = "FAIL"
        defect_type = "Component Misalignment"
        confidence = round(np.random.uniform(89.0, 93.0), 1)
        annotated = frame.copy()
        cv2.rectangle(annotated, (120, 90), (520, 390), (0, 0, 255), 3)
        cv2.rectangle(annotated, (380, 260), (460, 320), (0, 0, 255), 2)
        cv2.putText(annotated, "🔴 DEFECT DETECTED: Misalignment", (140, 130), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    else:
        # Run actual vision algorithm
        if config.inspection_mode == "PCB":
            res = inspector.inspect_pcb_vision(frame, config.decision_threshold)
            result = res["result"]
            defect_type = res["defect_type"]
            confidence = res["confidence"]
            annotated = res["annotated_frame"]
        else:
            annotated, detections = inspector.inspect_yolo_coco(frame)
            if detections:
                result = "PASS"
                defect_type = None
                confidence = detections[0]["confidence"]
            else:
                result = "FAIL"
                defect_type = "No Object Found"
                confidence = 0.0

    # Save annotated scan image
    img_filename = f"ins_{product_id}.jpg"
    save_path = os.path.join(INSPECTIONS_DIR, img_filename)
    cv2.imwrite(save_path, annotated)

    # Log to SQLite DB
    log_id = log_inspection(product_id, result, defect_type, confidence, save_path)

    # Generate ReportLab PDF report (saved locally in case local mode is running)
    report_filepath = os.path.join(REPORTS_DIR, f"report_{product_id}.pdf")
    rec_dict = {
        "id": log_id,
        "timestamp": timestamp_str,
        "product_id": product_id,
        "result": result,
        "defect_type": defect_type,
        "confidence": confidence,
        "image_path": save_path,
        "model_version": "YOLOv8n-PCB-v1.0"
    }
    try:
        generate_pdf_report(rec_dict, report_filepath)
    except Exception:
        pass

    return {
        "id": log_id,
        "timestamp": timestamp_str,
        "product_id": product_id,
        "result": result,
        "defect_type": defect_type,
        "confidence": confidence,
        "image_path": f"/data/inspections/{img_filename}",
        "report_path": f"/reports/report_{product_id}.pdf"
    }

# Dynamic, stateless report generation endpoint for serverless environments
@app.post("/api/reports/generate")
def generate_report_stream(payload: ReportPayload):
    import tempfile
    
    # 1. Resolve image bytes
    image_bytes = None
    if payload.image_b64:
        try:
            base64_str = payload.image_b64
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            image_bytes = base64.b64decode(base64_str)
        except Exception:
            pass
            
    if image_bytes is None and payload.image_path:
        # Check static mock images
        local_path = payload.image_path.lstrip("/")
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    image_bytes = f.read()
            except Exception:
                pass
                
    if image_bytes is None and payload.image_path:
        # Check active scans folders
        filename = os.path.basename(payload.image_path)
        inspect_path = os.path.join(INSPECTIONS_DIR, filename)
        if os.path.exists(inspect_path):
            try:
                with open(inspect_path, "rb") as f:
                    image_bytes = f.read()
            except Exception:
                pass

    # Save to temp image file (ReportLab takes a filesystem path)
    temp_img_path = None
    if image_bytes:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_img:
                temp_img.write(image_bytes)
                temp_img_path = temp_img.name
        except Exception:
            pass

    # 2. Compile PDF dynamically inside temp folder
    temp_pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf_path = temp_pdf.name
            
        rec_dict = {
            "id": payload.id,
            "timestamp": payload.timestamp,
            "product_id": payload.product_id,
            "result": payload.result,
            "defect_type": payload.defect_type,
            "confidence": payload.confidence,
            "image_path": temp_img_path, # ReportLab reads from temp image
            "model_version": "YOLOv8n-PCB-v1.0"
        }
        
        generate_pdf_report(rec_dict, temp_pdf_path)
        
        # Read compiled PDF bytes
        with open(temp_pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        # Clean up files
        if temp_img_path and os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=VisionGuard_Report_{payload.product_id}.pdf"}
        )
    except Exception as e:
        # Cleanup on failure
        if temp_img_path and os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        raise HTTPException(status_code=500, detail=f"Failed to compile PDF report: {str(e)}")

# Analytics & History Endpoints
@app.get("/api/analytics")
def get_analytics():
    return get_analytics_summary()

@app.get("/api/history")
def get_history():
    history = get_recent_inspections(50)
    for h in history:
        # Standardize web routes for visual image references
        if h.get("image_path"):
            filename = os.path.basename(h["image_path"])
            # If the file path is a static mock image, keep it as is
            if "static/mock_images" in h["image_path"]:
                h["image_path"] = f"/{h['image_path'].replace(os.sep, '/')}"
            else:
                h["image_path"] = f"/data/inspections/{filename}"
        h["report_path"] = f"/reports/report_{h['product_id']}.pdf"
    return history

@app.post("/api/reset_db")
def reset_db():
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        return {"status": "success", "message": "Database successfully reset."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(e)}")

# Shutdown Handler
@app.on_event("shutdown")
def shutdown_event():
    camera_manager.release_camera()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8501, reload=True)
