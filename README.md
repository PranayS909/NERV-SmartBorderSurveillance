# NERV-SmartBorderSurveillance

Smart Border Surveillance System using AI for face recognition, person tracking, ANPR (Automatic Number Plate Recognition), and threat detection.

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/PranayS909/NERV-SmartBorderSurveillance.git
cd NERV-SmartBorderSurveillance/ibvap
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Setup AI models** (Required for face recognition)
```bash
python scripts/setup_models.py --insightface
```

This will download the InsightFace models (~300 MB) required for face recognition.

4. **Verify installation**
```bash
python scripts/setup_models.py --check
```

You should see:
- ✅ YOLO model found
- ✅ TransReID model found
- ✅ InsightFace models found

### Running the Application

```bash
# Start the backend server
cd ibvap
python backend/main.py

# In another terminal, start the frontend
cd ibvap/frontend
npm install
npm run dev
```

## 📦 Models

The system uses three types of AI models:

### Included in Repository
- **YOLOv8n** (6.2 MB) - Object detection
- **TransReID ViT-Base** (2.3 MB) - Person re-identification

### Auto-Downloaded
- **InsightFace buffalo_l** (~300 MB) - Face detection & recognition
  - Downloaded automatically by setup script
  - Stored in `models/insightface/` (git-ignored)

See [ibvap/models/README.md](ibvap/models/README.md) for detailed model information.

## 🔧 Troubleshooting

### "model.onnx not found" or InsightFace errors

Run the model setup script:
```bash
cd ibvap
python scripts/setup_models.py --insightface
```

### Force re-download models

```bash
python scripts/setup_models.py --insightface --force
```

## 🏗️ Project Structure

```
ibvap/
├── ai/                 # AI modules
│   ├── face/          # Face recognition (InsightFace)
│   ├── detection/     # Object detection (YOLO)
│   ├── tracking/      # Person re-identification (TransReID)
│   ├── anpr/          # License plate recognition
│   └── threat/        # Threat detection
├── backend/           # FastAPI backend
├── frontend/          # React frontend
├── models/            # AI model files
├── scripts/           # Utility scripts
│   └── setup_models.py  # Model download script
└── requirements.txt   # Python dependencies
```

## 📝 Features

- 🎯 Real-time face detection and recognition
- 🚶 Cross-camera person tracking
- 🚗 Automatic number plate recognition (ANPR)
- ⚠️ Threat and weapon detection
- 📊 Dashboard for monitoring and alerts
- 🎥 Multi-camera support

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [InsightFace](https://github.com/deepinsight/insightface) - Face recognition models
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - Object detection
- [TransReID](https://github.com/damo-cv/TransReID) - Person re-identification
