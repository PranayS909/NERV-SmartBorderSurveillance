# IBVAP — Intelligent Border Video Analytics Platform

> **An Indigenous, Software-Defined AI/CV Surveillance Platform Transforming Conventional Border Security Infrastructure into Autonomous Intelligence Networks.**

---

## 📌 Background

Border security forces deploy CCTV cameras across Border Out Posts (BOPs), check posts, border roads, and strategic locations for surveillance. However, conventional CCTV systems primarily provide passive video recording and live monitoring, requiring continuous human observation—a process highly susceptible to fatigue, oversight, and delayed response times. 

Advanced surveillance capabilities like Facial Recognition Systems (FRS), Automatic Number Plate Recognition (ANPR), intrusion detection, and object tracking typically mandate specialized, proprietary hardware. This vendor dependency makes large-scale deployments prohibitively expensive, complex to scale, and difficult to maintain across remote, harsh border terrains.

---

## 💡 Proposed Solution

To eliminate hardware lock-in and high capital expenditure, the **Intelligent Border Video Analytics Platform (IBVAP)** introduces an indigenous, software-defined AI surveillance platform. 

IBVAP transforms existing IP-based CCTV infrastructure into an automated, intelligent surveillance network without requiring dedicated FRS, ANPR, or smart-camera hardware. By ingesting live video streams directly from standard legacy cameras, the platform leverages state-of-the-art Artificial Intelligence, Machine Learning, and Computer Vision techniques to perform real-time video analytics and extract actionable operational intelligence.

---

## ⚡ Key Capabilities

| Capability | Module / Tech | Operational Description |
| :--- | :--- | :--- |
| **Human Detection & Tracking** | YOLOv8 + ByteTrack / Deep-OC-SORT | Real-time person detection, multi-target tracking, and trajectory estimation across continuous frame streams. |
| **Vehicle Detection & Classification** | YOLOv8 Multi-Class Detection | Classification of civilian, transport, and tactical vehicles (cars, trucks, buses, motorcycles) at checkpoints and transit gates. |
| **Facial Recognition & Watchlist Matching (FRS)** | InsightFace (`buffalo_l`) + 512-D Cosine Embeddings | Non-destructive facial quality gating, pose filtering, and sub-second matching against local privacy-compliant tactical watchlists. |
| **Automatic Number Plate Recognition (ANPR)** | Fast-ALPR + Multi-Frame Consensus | License plate localization and OCR with Indian and BH-series syntax validation and cross-camera character provenance. |
| **Virtual Fence & Restricted-Zone Intrusion** | Ray-Casting Polygon Geofencing | Zero-latency detection of unauthorized perimeter breaches across user-defined polygon zones with configurable severity thresholds. |
| **Suspicious Object & Armed Threat Detection** | Spatial Overlap Bounding Box Analysis | Identifies unauthorized weapons, carried firearms, and unattended objects overlapping with tracked entities. |
| **Night Movement & Low-Light Anomaly Detection** | IR / Thermal Heuristics & Luminance Analysis | Detects suspicious movements and thermal heat signatures during night cycles and compromised visibility conditions. |
| **Cross-Camera Person & Vehicle Association** | Re-ID Embedding Fusion & Proximity Correlation | Correlates individuals entering or exiting vehicles across disparate camera nodes for comprehensive situational awareness. |

---

## 🎯 Impact of the Solution

- **Zero Hardware Lock-In:** Operates over standard RTSP/HTTP legacy IP cameras, commodity servers, and even edge devices without requiring proprietary smart sensor units.
- **Over 90% Capital Expenditure Reduction:** Eliminates the need to replace existing cameras with expensive specialized FRS/ANPR hardware.
- **Autonomous 24/7 Tactical Vigilance:** Eliminates operator fatigue with sub-second alert generation, reducing operational response times from minutes to milliseconds.
- **Extreme Terrain & Edge Resilience:** Fully functional in zero-connectivity environments with local edge inference, file replay (`SAMPLE FOOTAGE` mode), and field smartphone streams (`LIVE SMARTPHONE` mode).
- **Tamper-Evident Evidence Integrity:** Comprehensive audit trails, forensic snapshots, and tamper-evident Evidence Passports supporting chain-of-custody requirements.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph INGESTION ["1. Pluggable Video Ingestion Layer"]
        VSM[VideoSourceManager]
        VSM -->|Mode: SAMPLE| FVS[FileVideoSource / SyntheticVideoSource]
        VSM -->|Mode: LIVE_PHONE| PSS[PhoneStreamSource / RTSPVideoSource]
    end

    subgraph AI_PIPELINE ["2. Central AI Integration Engine (ai/engine.py)"]
        NF[NormalizedFrame: camera_id, frame_id, timestamp, ndarray]
        NF --> CAD[Inference Decimation & Cadence Scheduler]
        CAD --> DET[YOLOv8 Object & Threat Detector]
        CAD --> TRK[ByteTrack / Deep-OC-SORT Motion Tracker]
        TRK --> ZON[Virtual Fence & Zone Intrusion Engine]
        TRK --> FRS[InsightFace Watchlist Matching]
        TRK --> ANPR[Fast-ALPR Plate OCR & Grammar Validator]
        TRK --> WPN[Weapon & Suspicious Object Overlap Analyzer]
        TRK --> NGT[Night Luminance & IR Signature Analyzer]
        TRK --> ASSOC[Cross-Camera Person-Vehicle Associator]
    end

    subgraph BACKEND ["3. FastAPI Backend & Persistence Layer"]
        EVT_GEN[Event Builder & Async ThreadPool Dispatcher]
        EVT_GEN -->|POST /api/v1/events| API[FastAPI Event Service]
        API -->|Transactional Commit & Flush| DB[(PostgreSQL 10-Table Database)]
        API -->|Auto-Generated Alerts| ALT[(Alerts Table)]
        API -->|Real-Time Push| WS[Single Canonical /ws/events WebSocket]
        BUF[Pre-Encoded JPEG Buffer] --> MJPEG[/api/v1/cameras/:id/stream]
        BUF --> SNAP[/api/v1/cameras/:id/snapshot]
    end

    subgraph FRONTEND ["4. React Tactical Command Dashboard"]
        WS -.->|Live Event Stream| DASH[Command Center Dashboard]
        MJPEG -.->|Low-Latency MJPEG Feed| MAIN_VIEW[Active CCTV Speaker View]
        SNAP -.->|Lightweight Polling 0.5Hz| TILES[Multi-Sensor Camera Tiles]
        DASH -->|Mode Toggle: SAMPLE / LIVE_PHONE| MODE_API[/api/v1/mode]
        DASH --> MAP[Tactical Zone Map & Geospatial HUD]
    end

    VSM --> NF
    ZON --> EVT_GEN
    FRS --> EVT_GEN
    ANPR --> EVT_GEN
    WPN --> EVT_GEN
    NGT --> EVT_GEN
    ASSOC --> EVT_GEN
```

---

## 🔄 End-to-End Operational Workflow

1. **Stream Ingestion & Normalization:**
   - `VideoSourceManager` connects to RTSP streams, recorded video files, or mobile IP camera feeds, outputting uniform `NormalizedFrame` structures.
   - Decoupled architecture: the AI analytics pipeline is completely agnostic of the physical video source.

2. **Decimated Real-Time AI Processing:**
   - Frames are processed through a multi-threaded worker engine.
   - **Inference Decimation**: Heavy neural network models (YOLO, InsightFace, Fast-ALPR) run on a tuned cadence (every 3rd frame), persisting detections across intermediate frames to maintain silky-smooth 22+ FPS video playback on standard CPU hardware.

3. **Event Generation & Database Persistence:**
   - When a security threshold is crossed (e.g. zone intrusion or weapon detection), events are asynchronously dispatched to `POST /api/v1/events`.
   - The transaction flushes records to PostgreSQL (`events` and `alerts` tables) and broadcasts the payload instantly to all connected operators over the `/ws/events` WebSocket.

4. **Tactical Command Center Visualization:**
   - The React frontend receives live telemetry and renders an active-speaker CCTV viewport, multi-tile sensor monitors, an interactive geospatial radar map, and an active alerts triage panel.
   - Operators can toggle live surveillance sources between pre-recorded border scenarios and live smartphone cameras with a single click.

---

## 🛠️ Technology Stack

```
IBVAP
├── AI & Computer Vision
│   ├── Ultralytics YOLOv8        # Real-time entity & weapon detection
│   ├── ByteTrack & Deep-OC-SORT   # Multi-target spatial-temporal tracking
│   ├── InsightFace (buffalo_l)   # 512-D face embedding & watchlist identification
│   ├── Fast-ALPR & Plate OCR     # High-speed license plate detection & recognition
│   ├── TransReID                 # Transformer-based cross-camera re-identification
│   └── OpenCV (cv2)              # Frame normalization, rendering, & MJPEG encoding
│
├── Backend & Streaming Services
│   ├── FastAPI                   # High-performance async REST API framework
│   ├── Starlette WebSocket       # Canonical real-time event distribution (/ws/events)
│   ├── SQLAlchemy 2.0            # Relational ORM with connection pooling
│   ├── Pydantic v2               # Data contract validation & schema enforcement
│   └── Uvicorn                   # Lightning-fast ASGI web server
│
├── Database & Storage
│   └── PostgreSQL 16             # ACID-compliant storage with JSONB metadata & foreign keys
│
└── Frontend & Operator Dashboard
    ├── React 19                  # Modern reactive component architecture
    ├── Vite                      # Next-generation frontend build tooling
    ├── Leaflet & React-Leaflet   # Geospatial tactical zone mapping
    ├── Lucide React              # Operational HUD icon system
    └── WebSocket API             # Resilient, auto-reconnecting browser telemetry
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.13 recommended)
- Node.js 18+ & npm
- PostgreSQL 14+ running locally on port 5432 (database: `ibvap`)

### 2. Backend Setup
```powershell
# Navigate to the ibvap directory
cd NERV-SmartBorderSurveillance/ibvap

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start FastAPI backend service (includes AI engine & video sources)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`
- **WebSocket Endpoint:** `ws://localhost:8000/ws/events`

### 3. Frontend Dashboard Setup
```powershell
# Open a new terminal and navigate to frontend
cd NERV-SmartBorderSurveillance/ibvap/frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
- **Operator Dashboard:** Open `http://localhost:5173` in your browser.

---

## 🧪 Testing & Verification

Run the comprehensive test suite verifying video sources, AI modules, API endpoints, and tracking:

```powershell
# Run all unit and integration tests
python -m pytest tests/test_ai_engine.py tests/test_api_endpoints.py tests/test_video_sources.py -v
```

---

## 📄 License

Internal Defense and Engineering Evaluation Prototype — Developed for Border Security Automation.
