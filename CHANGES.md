# ONNX Model Handling - Changes Summary

## Issue
The repository had InsightFace models not committed, causing "model.onnx not found" errors after cloning.

## Root Cause Analysis

1. **InsightFace models were never committed** - The `models/insightface/` directory was in `.gitignore`
2. **Two ONNX/PT models were in git history** but lost in main branch:
   - `transreid_vit_base.onnx` (2.3 MB) - TransReID person re-identification
   - `yolov8n.pt` (6.2 MB) - YOLOv8 object detection
3. **No setup instructions** for downloading InsightFace models after cloning

## Changes Made

### 1. Restored Missing Model Files ✅
- **Restored from commit `c0701bd`**:
  - `ibvap/models/transreid_vit_base.onnx` (2.3 MB)
  - `ibvap/models/yolov8n.pt` (6.2 MB)
- These files are now **included in the repository** (staged for commit)

### 2. Created `.gitignore` Configuration ✅
- **File**: `ibvap/.gitignore`
- **Purpose**: Properly ignore large model files while allowing specific committed models
- **Key patterns**:
  ```
  models/*.onnx              # Ignore all ONNX files
  !models/transreid_vit_base.onnx  # EXCEPT this one (committed)
  models/*.pt                # Ignore all PyTorch files
  !models/yolov8n.pt         # EXCEPT this one (committed)
  models/insightface/        # Always ignore InsightFace downloads
  ```

### 3. Created Model Download Script ✅
- **File**: `ibvap/scripts/setup_models.py`
- **Features**:
  - Downloads InsightFace models automatically
  - Checks existing model files
  - Supports force re-download
  - Clear status messages with emojis
  - Handles errors gracefully
- **Usage**:
  ```bash
  python scripts/setup_models.py --insightface    # Download InsightFace
  python scripts/setup_models.py --check          # Check all models
  python scripts/setup_models.py --insightface --force  # Force re-download
  ```

### 4. Created Documentation ✅

#### `ibvap/models/README.md`
- Explains all three model types
- Shows which are committed vs. downloaded
- Provides troubleshooting steps
- Documents storage structure

#### `README.md` (updated)
- Added Quick Start section
- Added model setup instructions
- Added troubleshooting section
- Improved project structure documentation

#### `SETUP.md` (new)
- Complete step-by-step setup guide
- Prerequisites checklist
- Troubleshooting for common issues
- Expected outputs for each step
- Quick command reference

### 5. Updated Dependencies ✅
- **File**: `ibvap/requirements.txt`
- **Added**: All required dependencies including:
  - `insightface>=1.0,<2`
  - `onnxruntime>=1.18,<2`
  - `opencv-python-headless>=4.9,<5`
  - FastAPI, SQLAlchemy, and other backend dependencies

## File Changes Summary

| File | Status | Size | Purpose |
|------|--------|------|---------|
| `README.md` | Modified | +127 lines | Added setup instructions |
| `SETUP.md` | New | 300+ lines | Complete setup guide |
| `CHANGES.md` | New | This file | Documents changes |
| `ibvap/.gitignore` | New | 51 lines | Git ignore patterns |
| `ibvap/models/README.md` | New | 127 lines | Model documentation |
| `ibvap/models/transreid_vit_base.onnx` | Restored | 2.3 MB | Person re-ID model |
| `ibvap/models/yolov8n.pt` | Restored | 6.2 MB | Object detection model |
| `ibvap/requirements.txt` | Created | 26 lines | Python dependencies |
| `ibvap/scripts/setup_models.py` | New | 170 lines | Model download script |

## Model Handling Strategy

### Committed to Git (In Repository)
✅ **TransReID ONNX** (2.3 MB) - Small enough for Git  
✅ **YOLOv8n PT** (6.2 MB) - Small enough for Git

### Downloaded Automatically (Ignored by Git)
📥 **InsightFace buffalo_l** (~300 MB) - Too large for Git
- Downloaded by `setup_models.py --insightface`
- Stored in `models/insightface/` (git-ignored)
- Uses official InsightFace distribution

## Testing Results

### Model Check Status
```bash
$ python scripts/setup_models.py --check
============================================================
🚀 NERV Smart Border Surveillance - Model Setup
============================================================
🔍 Checking existing model files...
✅ YOLO model found: models/yolov8n.pt (6.2 MB)
✅ TransReID model found: models/transreid_vit_base.onnx (2.3 MB)
⚠️  InsightFace models not found (expected - needs download)
============================================================
```

### Git Ignore Verification
- ✅ `transreid_vit_base.onnx` - Will be tracked (exception)
- ✅ `yolov8n.pt` - Will be tracked (exception)
- ✅ `models/insightface/` - Will be ignored
- ✅ `models/other.onnx` - Would be ignored (pattern match)

## What a Fresh Clone Will Experience

1. **Clone repository**
   ```bash
   git clone https://github.com/PranayS909/NERV-SmartBorderSurveillance.git
   cd NERV-SmartBorderSurveillance/ibvap
   ```

2. **Already have these models** (no download needed):
   - ✅ `models/transreid_vit_base.onnx` (2.3 MB)
   - ✅ `models/yolov8n.pt` (6.2 MB)

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download InsightFace models** (one-time, ~300 MB):
   ```bash
   python scripts/setup_models.py --insightface
   ```

5. **Ready to run!** No more "model.onnx not found" errors

## Next Steps (For You)

### Ready to Commit
All changes are staged and ready:
```bash
git status
# Shows 8 files ready to commit
```

### Recommended Commit Message
```bash
git commit -m "fix: Add ONNX model handling and setup scripts

- Restore transreid_vit_base.onnx and yolov8n.pt to repository
- Add .gitignore to properly handle model files
- Create setup_models.py script for InsightFace download
- Add comprehensive documentation (SETUP.md, model README)
- Update requirements.txt with all dependencies

Fixes the 'model.onnx not found' error for fresh clones.
After cloning, users just need to run:
pip install -r requirements.txt
python scripts/setup_models.py --insightface"
```

### To Push Changes
```bash
git push origin main
```

## Storage Impact

### Repository Size
- **Before**: ~42 MB
- **After**: ~51 MB (+9 MB)
- **Reason**: Added two model files (2.3 MB + 6.2 MB)

### Post-Clone Download
- **InsightFace models**: ~300 MB (one-time, auto-download)
- **Python dependencies**: ~500 MB
- **Total first-time setup**: ~800 MB

## Verification Commands

```bash
# Check what's staged
git status

# Verify models exist
ls -lh ibvap/models/

# Test setup script
cd ibvap && python scripts/setup_models.py --check

# Verify gitignore works
git check-ignore -v ibvap/models/transreid_vit_base.onnx  # Should NOT match
git check-ignore -v ibvap/models/insightface/test.onnx   # Should match
```

## Benefits

1. ✅ **No more "model.onnx not found" errors** after cloning
2. ✅ **Clear setup instructions** for new contributors
3. ✅ **Automated model download** with helpful script
4. ✅ **Proper git ignore patterns** prevent bloat
5. ✅ **Small committed models** work immediately
6. ✅ **Large models** downloaded only when needed
7. ✅ **Comprehensive documentation** for troubleshooting

## Important Notes

- **DO NOT commit the changes yet** - As per your instructions
- **InsightFace models are NOT in the commit** - They're git-ignored
- **Only 9 MB added to repo** - The two small ONNX/PT files
- **All other models download automatically** - Using the setup script
