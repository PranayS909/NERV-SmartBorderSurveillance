#!/usr/bin/env python3
"""
Setup script for downloading required model files.

This script downloads InsightFace models and ensures all required model files
are present for the application to run correctly.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def download_insightface_models(model_pack: str = "buffalo_l", force: bool = False) -> None:
    """
    Download InsightFace model pack.
    
    Args:
        model_pack: Name of the InsightFace model pack (default: buffalo_l)
        force: Force re-download even if models exist
    """
    print(f"\n📦 Setting up InsightFace model pack: {model_pack}")
    
    models_dir = ROOT / "models" / "insightface"
    model_pack_dir = models_dir / f".insightface/models/{model_pack}"
    
    if model_pack_dir.exists() and not force:
        print(f"✅ InsightFace model pack '{model_pack}' already exists at: {model_pack_dir}")
        return
    
    try:
        from insightface.app import FaceAnalysis
    except ImportError:
        print("❌ InsightFace is not installed!")
        print("   Please install it first:")
        print("   pip install insightface")
        sys.exit(1)
    
    print(f"⬇️  Downloading InsightFace '{model_pack}' models...")
    print("   This may take a few minutes on first run...")
    
    try:
        # Create FaceAnalysis instance - this will auto-download models
        models_dir.mkdir(parents=True, exist_ok=True)
        app = FaceAnalysis(
            name=model_pack,
            root=str(models_dir),
            providers=["CPUExecutionProvider"]
        )
        app.prepare(ctx_id=-1, det_size=(640, 640))
        print(f"✅ Successfully downloaded InsightFace '{model_pack}' model pack")
        print(f"   Location: {models_dir}")
    except Exception as e:
        print(f"❌ Error downloading InsightFace models: {e}")
        sys.exit(1)


def check_existing_models() -> None:
    """Check and report on existing model files."""
    print("\n🔍 Checking existing model files...")
    
    models_dir = ROOT / "models"
    
    # Check for YOLO model
    yolo_model = models_dir / "yolov8n.pt"
    if yolo_model.exists():
        size_mb = yolo_model.stat().st_size / (1024 * 1024)
        print(f"✅ YOLO model found: {yolo_model} ({size_mb:.1f} MB)")
    else:
        print(f"⚠️  YOLO model not found: {yolo_model}")
        print("   You may need to download it manually or run training scripts")
    
    # Check for TransReID model
    transreid_model = models_dir / "transreid_vit_base.onnx"
    if transreid_model.exists():
        size_mb = transreid_model.stat().st_size / (1024 * 1024)
        print(f"✅ TransReID model found: {transreid_model} ({size_mb:.1f} MB)")
    else:
        print(f"⚠️  TransReID model not found: {transreid_model}")
        print("   You may need to train it using scripts/train_transreid.py")
    
    # Check for InsightFace models
    insightface_dir = models_dir / "insightface" / ".insightface" / "models"
    if insightface_dir.exists():
        model_packs = list(insightface_dir.iterdir())
        if model_packs:
            print(f"✅ InsightFace models found:")
            for pack in model_packs:
                if pack.is_dir():
                    onnx_files = list(pack.glob("*.onnx"))
                    print(f"   - {pack.name} ({len(onnx_files)} ONNX files)")
        else:
            print(f"⚠️  InsightFace directory exists but no model packs found")
    else:
        print(f"⚠️  InsightFace models not found at: {insightface_dir}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup required model files for NERV Smart Border Surveillance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download InsightFace models (default buffalo_l pack)
  python setup_models.py --insightface
  
  # Check existing models
  python setup_models.py --check
  
  # Force re-download
  python setup_models.py --insightface --force
  
  # Use a different InsightFace model pack
  python setup_models.py --insightface --model-pack antelopev2
        """
    )
    
    parser.add_argument(
        "--insightface",
        action="store_true",
        help="Download InsightFace face recognition models"
    )
    parser.add_argument(
        "--model-pack",
        type=str,
        default="buffalo_l",
        help="InsightFace model pack to download (default: buffalo_l)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check existing model files"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if models exist"
    )
    
    args = parser.parse_args()
    
    # If no action specified, show check by default
    if not args.insightface and not args.check:
        args.check = True
    
    print("=" * 60)
    print("🚀 NERV Smart Border Surveillance - Model Setup")
    print("=" * 60)
    
    if args.check:
        check_existing_models()
    
    if args.insightface:
        download_insightface_models(model_pack=args.model_pack, force=args.force)
        # Check again to verify
        check_existing_models()
    
    print("\n" + "=" * 60)
    print("✨ Model setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
