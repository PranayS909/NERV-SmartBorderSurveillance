#!/usr/bin/env python3
"""Demonstrate motion-gated Face/ANPR inference on a smartphone CCTV stream.

The input may be a phone RTSP/HTTP URL, a webcam index such as ``0``, or a
recorded phone video. Use ``--models none`` for a fast gate-only rehearsal and
``--models both`` for the real Person 3 model demonstration.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.anpr.backend import FastALPRBackend
from ai.common.config import load_config
from ai.face.backend import InsightFaceBackend
from ai.motion_gate import MotionGate


def video_source(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def resize_for_demo(frame, max_width: int):
    if frame.shape[1] <= max_width:
        return frame
    scale = max_width / frame.shape[1]
    return cv2.resize(frame, (max_width, round(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)


def draw_panel(frame, decision, metrics, faces, plates, models_enabled, safety_scan):
    awake_color = (35, 220, 90)
    sleep_color = (255, 170, 45)
    color = awake_color if decision.awake or safety_scan else sleep_color
    status = "SAFETY SCAN" if safety_scan and not decision.awake else ("AI AWAKE" if decision.awake else "AI SLEEPING")
    overlay = frame.copy()
    cv2.rectangle(overlay, (18, 18), (620, 205), (8, 15, 25), -1)
    cv2.addWeighted(overlay, 0.86, frame, 0.14, 0, frame)
    cv2.circle(frame, (48, 52), 11, color, -1)
    cv2.putText(frame, f"SMARTPHONE CCTV  |  {status}", (70, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.82, color, 2)
    cv2.putText(frame, f"Signal: {decision.reason}   Motion: {decision.motion_ratio * 100:.2f}%", (35, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (235, 240, 245), 2)
    cv2.putText(frame, f"Frames: {metrics['frames']}   AI wake ops: {metrics['wake_opportunities']}   Skipped: {metrics['skipped']}", (35, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (235, 240, 245), 2)
    opportunities = max(1, metrics["wake_opportunities"] + metrics["skipped"])
    reduction = 100.0 * metrics["skipped"] / opportunities
    model_text = "Face + ANPR connected" if models_enabled else "Gate rehearsal (models disabled)"
    cv2.putText(frame, f"Inference reduction: {reduction:.1f}%   |   {model_text}", (35, 172), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 205, 225), 2)

    for face in faces:
        x1, y1, x2, y2 = (int(value) for value in face.bbox.as_list())
        cv2.rectangle(frame, (x1, y1), (x2, y2), awake_color, 2)
        cv2.putText(frame, f"FACE {face.detection_score:.2f}", (x1, max(24, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, awake_color, 2)
    for plate in plates:
        x1, y1, x2, y2 = (int(value) for value in plate.bbox.as_list())
        cv2.rectangle(frame, (x1, y1), (x2, y2), (20, 190, 255), 2)
        label = plate.text or "PLATE"
        cv2.putText(frame, f"{label} {plate.detector_confidence:.2f}", (x1, max(24, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 190, 255), 2)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Phone stream URL, webcam index, or recorded video")
    parser.add_argument("--output", default="demo/ai-sleep-mode")
    parser.add_argument("--models", choices=("none", "face", "anpr", "both"), default="none")
    parser.add_argument("--model-every", type=int, default=15, help="Run enabled models every N awake frames")
    parser.add_argument("--motion-ratio", type=float, default=0.03)
    parser.add_argument("--pixel-threshold", type=int, default=25)
    parser.add_argument("--hold-frames", type=int, default=20)
    parser.add_argument("--safety-scan-seconds", type=float, default=5.0, help="Periodic full scan while sleeping; zero disables it")
    parser.add_argument("--max-width", type=int, default=1280)
    parser.add_argument("--max-frames", type=int, default=0, help="Zero means run until the stream ends")
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--config", default="configs/person3.yaml")
    args = parser.parse_args()

    output_directory = Path(args.output)
    output_directory.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    face_backend = None
    plate_backend = None
    if args.models in {"face", "both"}:
        face_backend = InsightFaceBackend(config.face.model_pack, config.face.providers, config.face.detection_size, config.face.model_root)
    if args.models in {"anpr", "both"}:
        plate_backend = FastALPRBackend(config.anpr.detector_model, config.anpr.ocr_model, config.anpr.detector_confidence, config.anpr.providers)

    capture = cv2.VideoCapture(video_source(args.input))
    if not capture.isOpened():
        raise ValueError(f"Unable to open smartphone stream/video: {args.input}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS))
    fps = source_fps if 1 <= source_fps <= 120 else 30.0
    safety_scan_frames = round(fps * args.safety_scan_seconds) if args.safety_scan_seconds > 0 else 0
    gate = MotionGate(args.motion_ratio, args.pixel_threshold, args.hold_frames)
    writer = None
    metrics = {"frames": 0, "awake_frames": 0, "sleeping_frames": 0, "wake_opportunities": 0, "model_inference_calls": 0, "safety_scans": 0, "skipped": 0, "faces": 0, "plates": 0}
    started = time.perf_counter()
    inference_ms: list[float] = []
    last_faces = []
    last_plates = []

    while True:
        ok, source_frame = capture.read()
        if not ok:
            break
        frame = resize_for_demo(source_frame, args.max_width)
        decision = gate.evaluate(frame)
        metrics["frames"] += 1
        if decision.awake:
            metrics["awake_frames"] += 1
        else:
            metrics["sleeping_frames"] += 1

        scheduled = metrics["frames"] % max(1, args.model_every) == 0
        safety_scan = bool(scheduled and safety_scan_frames and metrics["frames"] % safety_scan_frames < max(1, args.model_every))
        should_infer = scheduled and (decision.awake or safety_scan)
        if scheduled:
            if should_infer:
                metrics["wake_opportunities"] += 1
                if safety_scan and not decision.awake:
                    metrics["safety_scans"] += 1
                if args.models != "none":
                    metrics["model_inference_calls"] += 1
                inference_started = time.perf_counter()
                last_faces = face_backend.detect(frame) if face_backend else []
                last_plates = plate_backend.predict(frame) if plate_backend else []
                inference_ms.append((time.perf_counter() - inference_started) * 1000)
                metrics["faces"] += len(last_faces)
                metrics["plates"] += len(last_plates)
            else:
                metrics["skipped"] += 1
                last_faces, last_plates = [], []

        annotated = draw_panel(frame, decision, metrics, last_faces, last_plates, args.models != "none", safety_scan)
        if writer is None:
            height, width = annotated.shape[:2]
            writer = cv2.VideoWriter(str(output_directory / "smartphone-ai-sleep-demo.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        writer.write(annotated)
        if args.display:
            cv2.imshow("PRAMAAN X - Smartphone AI Sleep Mode", annotated)
            if cv2.waitKey(1) & 0xFF in {27, ord("q")}:
                break
        if args.max_frames and metrics["frames"] >= args.max_frames:
            break

    capture.release()
    if writer is not None:
        writer.release()
    if args.display:
        cv2.destroyAllWindows()

    opportunities = metrics["wake_opportunities"] + metrics["skipped"]
    report = {
        "input": args.input,
        "mode": "smartphone_stream_motion_gated_ai",
        "models": args.models,
        "settings": {"motion_ratio": args.motion_ratio, "pixel_threshold": args.pixel_threshold, "hold_frames": args.hold_frames, "model_every": args.model_every, "safety_scan_seconds": args.safety_scan_seconds},
        "metrics": {**metrics, "inference_reduction_percent": round(100 * metrics["skipped"] / opportunities, 2) if opportunities else 0.0, "average_inference_ms": round(sum(inference_ms) / len(inference_ms), 2) if inference_ms else None, "elapsed_seconds": round(time.perf_counter() - started, 2)},
        "claim_note": "Inference reduction is measured. Energy savings were not measured and are not claimed.",
    }
    report_path = output_directory / "ai-sleep-mode-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"video": str(output_directory / "smartphone-ai-sleep-demo.mp4"), "report": str(report_path), **report["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
