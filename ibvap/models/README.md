# Model Weights Directory

This directory stores trained deep learning weights for Person Re-ID and detection models:

- `transreid_vit_base.onnx` / `transreid_vit_base.pth`: Vision Transformer TransReID weights (768-d embeddings).
- `yolov8n.pt` / custom trained YOLO weights.

To download pre-trained TransReID weights from cloud storage, run:
```bash
python scripts/download_weights.py
```
# Model Files

This directory contains the machine learning models required by the NERV Smart Border Surveillance system.

## Required Models

### 1. Face Recognition - InsightFace Models
**Location**: `models/insightface/`  
**Status**: ⚠️ NOT included in repository (auto-downloaded)  
**Size**: ~100-300 MB depending on model pack

The application uses InsightFace for face detection and recognition. These models are downloaded automatically when you run the setup script.

**Setup**:
```bash
cd ibvap
python scripts/setup_models.py --insightface
```

**Default Model Pack**: `buffalo_l`  
Alternative packs: `antelopev2`, `buffalo_s`, `buffalo_sc`

### 2. Person Re-identification - TransReID
**Location**: `models/transreid_vit_base.onnx`  
**Status**: ✅ Included in repository  
**Size**: 2.3 MB

Vision Transformer model for person re-identification across multiple cameras.

### 3. Object Detection - YOLOv8
**Location**: `models/yolov8n.pt`  
**Status**: ✅ Included in repository  
**Size**: 6.2 MB

YOLOv8 nano model for real-time object detection (persons, vehicles, threats).

## Quick Setup

After cloning the repository, run:

```bash
cd ibvap

# Install dependencies
pip install -r requirements.txt

# Download InsightFace models
python scripts/setup_models.py --insightface

# Verify all models are present
python scripts/setup_models.py --check
```

## Model Details

| Model | Purpose | Committed | Download Size | Runtime |
|-------|---------|-----------|---------------|---------|
| InsightFace buffalo_l | Face detection & recognition | ❌ No | ~300 MB | Auto-download |
| TransReID ViT-Base | Person re-identification | ✅ Yes | 2.3 MB | Included |
| YOLOv8n | Object detection | ✅ Yes | 6.2 MB | Included |

## Why aren't InsightFace models committed?

InsightFace models are:
- **Large** (~100-300 MB per model pack)
- **Pre-trained** and publicly available
- **Easily downloadable** via the InsightFace library
- Better managed through their official distribution system

The setup script handles downloading them automatically on first run.

## Troubleshooting

### "InsightFace models not found" error

Run the setup script:
```bash
python scripts/setup_models.py --insightface
```

### Force re-download models

```bash
python scripts/setup_models.py --insightface --force
```

### Use a different InsightFace model pack

```bash
python scripts/setup_models.py --insightface --model-pack antelopev2
```

### Check model status

```bash
python scripts/setup_models.py --check
```

## Storage Structure

```
models/
├── README.md                    (this file)
├── transreid_vit_base.onnx     (2.3 MB, in repo)
├── yolov8n.pt                  (6.2 MB, in repo)
└── insightface/                (ignored, auto-downloaded)
    └── .insightface/
        └── models/
            └── buffalo_l/      (~300 MB)
                ├── det_10g.onnx
                ├── genderage.onnx
                └── w600k_r50.onnx
```

## Manual Download

If automated download fails, you can download InsightFace models manually:

1. Install InsightFace: `pip install insightface`
2. Run in Python:
```python
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l', root='./models/insightface')
app.prepare(ctx_id=-1, det_size=(640, 640))
```

This will download models to `models/insightface/.insightface/models/buffalo_l/`
