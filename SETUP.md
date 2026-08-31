# Setup Guide for NERV Smart Border Surveillance

This guide will help you set up the project correctly after cloning.

## Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Git**
- At least **2GB free disk space** (for AI models)

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/PranayS909/NERV-SmartBorderSurveillance.git
cd NERV-SmartBorderSurveillance
```

### 2. Navigate to Project Directory

```bash
cd ibvap
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (backend framework)
- InsightFace (face recognition)
- ONNX Runtime (model inference)
- OpenCV (computer vision)
- And other required libraries

### 4. Download AI Models (IMPORTANT!)

```bash
python scripts/setup_models.py --insightface
```

This script will:
- ✅ Verify YOLO and TransReID models are present (included in repo)
- ⬇️ Download InsightFace models (~300 MB, takes 2-5 minutes)
- 📁 Store them in `models/insightface/` directory

**Expected Output:**
```
============================================================
🚀 NERV Smart Border Surveillance - Model Setup
============================================================
⬇️  Downloading InsightFace 'buffalo_l' models...
   This may take a few minutes on first run...
✅ Successfully downloaded InsightFace 'buffalo_l' model pack
✅ YOLO model found: models/yolov8n.pt (6.2 MB)
✅ TransReID model found: models/transreid_vit_base.onnx (2.3 MB)
✅ InsightFace models found:
   - buffalo_l (3 ONNX files)
============================================================
✨ Model setup complete!
============================================================
```

### 5. Verify Installation

```bash
python scripts/setup_models.py --check
```

All three checkmarks (✅) should appear:
- ✅ YOLO model found
- ✅ TransReID model found  
- ✅ InsightFace models found

### 6. Set Up Environment Variables (Optional)

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 7. Run the Backend

```bash
# From ibvap directory
python backend/main.py
```

Backend should start on `http://localhost:8000`

### 8. Run the Frontend (In a New Terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend should start on `http://localhost:5173`

## Troubleshooting

### Issue: "InsightFace models not found"

**Solution:**
```bash
python scripts/setup_models.py --insightface
```

### Issue: "model.onnx not found" error when running

**Cause:** InsightFace models weren't downloaded

**Solution:**
```bash
cd ibvap
python scripts/setup_models.py --insightface --force
```

### Issue: Import errors for InsightFace

**Solution:**
```bash
pip install insightface onnxruntime
```

### Issue: Slow model download

**Cause:** InsightFace downloads from GitHub releases

**Solution:** Be patient, it's a one-time download (~300 MB)

### Issue: Want to use a different InsightFace model

```bash
# Available: buffalo_l (default), buffalo_s, buffalo_sc, antelopev2
python scripts/setup_models.py --insightface --model-pack antelopev2
```

## What Gets Downloaded?

| Component | Size | When | Where |
|-----------|------|------|-------|
| Python dependencies | ~500 MB | `pip install -r requirements.txt` | Python site-packages |
| InsightFace models | ~300 MB | `setup_models.py --insightface` | `models/insightface/` |
| Node modules | ~200 MB | `npm install` | `frontend/node_modules/` |

**Total:** ~1 GB

## Files Already in Repository

These models are already included (no download needed):
- ✅ `models/yolov8n.pt` (6.2 MB) - Object detection
- ✅ `models/transreid_vit_base.onnx` (2.3 MB) - Person tracking

## Directory Structure After Setup

```
ibvap/
├── models/
│   ├── transreid_vit_base.onnx     ✅ In repo
│   ├── yolov8n.pt                  ✅ In repo  
│   ├── insightface/                📥 Downloaded
│   │   └── .insightface/
│   │       └── models/
│   │           └── buffalo_l/
│   │               ├── det_10g.onnx
│   │               ├── genderage.onnx
│   │               └── w600k_r50.onnx
│   └── README.md
├── backend/
├── frontend/
├── scripts/
│   └── setup_models.py
└── requirements.txt
```

## Quick Command Reference

```bash
# Check model status
python scripts/setup_models.py --check

# Download InsightFace models
python scripts/setup_models.py --insightface

# Force re-download
python scripts/setup_models.py --insightface --force

# Use different model pack
python scripts/setup_models.py --insightface --model-pack buffalo_s

# Run backend
python backend/main.py

# Run frontend (separate terminal)
cd frontend && npm run dev
```

## Next Steps

After setup is complete:
1. Read the [README.md](README.md) for feature overview
2. Check [models/README.md](ibvap/models/README.md) for model details
3. Run the demo scripts in `ibvap/scripts/`

## Support

If you encounter issues:
1. Verify Python version: `python --version` (should be 3.8+)
2. Check disk space: `df -h .` (need at least 2GB free)
3. Run model verification: `python scripts/setup_models.py --check`
4. Check InsightFace installation: `pip show insightface`

For more help, open an issue on GitHub.
