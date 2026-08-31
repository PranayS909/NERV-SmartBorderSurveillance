#!/usr/bin/env python3
"""
scripts/extract_face_from_video.py — Extract faces from video footage & match against watchlist.

Capabilities:
  1. Scans video footage frame-by-frame (or with configurable sampling interval).
  2. Detects faces and extracts 512-D embeddings using InsightFace (buffalo_l).
  3. Crops and saves high-quality face images to disk with timestamps and metadata.
  4. Matches extracted embeddings against the active watchlist (demo/watchlist/watchlist.json).
  5. Optionally renders and saves an annotated video with bounding boxes, names, and similarity.

Usage:
    # Basic extraction and watchlist matching
    python scripts/extract_face_from_video.py --video path/to/footage.mp4

    # Save annotated output video
    python scripts/extract_face_from_video.py --video path/to/footage.mp4 --output-video results.mp4

    # Enroll a face detected in the video directly into the watchlist
    python scripts/extract_face_from_video.py --video path/to/footage.mp4 --enroll --name "Target Name" --person-id "PERS-002"
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from ai.face.backend import InsightFaceBackend
from ai.face.watchlist import WatchlistStore


def main():
    parser = argparse.ArgumentParser(description="Extract faces from video and match to watchlist")
    parser.add_argument("--video", required=True, help="Path to input video file")
    parser.add_argument("--watchlist", default="demo/watchlist/watchlist.json", help="Path to watchlist JSON")
    parser.add_argument("--output-dir", default="extracted_faces", help="Directory to save extracted face crops")
    parser.add_argument("--output-video", default=None, help="Optional path to save annotated output video")
    parser.add_argument("--sample-rate", type=int, default=5, help="Process every Nth frame (default: 5)")
    parser.add_argument("--min-score", type=float, default=0.60, help="Minimum face detection confidence (default: 0.60)")
    parser.add_argument("--enroll", action="store_true", help="Enroll best detected face into watchlist")
    parser.add_argument("--name", default="Target Subject", help="Name for enrollment")
    parser.add_argument("--person-id", default="PERS-TARGET", help="ID for enrollment")
    parser.add_argument("--consent", default="OPERATIONAL-AUTH-2026", help="Consent reference code")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[ERROR] Video file '{video_path}' not found.")
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERROR] Could not open video file '{video_path}'.")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / fps if fps > 0 else 0.0

    print(f"\n========================================================")
    print(f"[INPUT] Video: {video_path.name}")
    print(f"        Resolution: {width}x{height} | FPS: {fps:.1f} | Frames: {total_frames}")
    print(f"        Duration: {duration_sec:.1f}s | Sample Cadence: every {args.sample_rate} frames")
    print(f"========================================================\n")

    # Initialize InsightFace buffalo_l backend
    print("[*] Loading InsightFace buffalo_l models...")
    backend = InsightFaceBackend(
        model_pack="buffalo_l",
        model_root="models/insightface/.insightface"
    )
    print(f"[OK] Loaded backend: {backend.model_name}\n")

    # Load Watchlist
    watchlist_path = Path(args.watchlist)
    store = WatchlistStore(watchlist_path, backend.model_name)
    print(f"[*] Loaded Watchlist: {watchlist_path} ({len(store.entries)} enrolled subjects)")
    for entry in store.entries:
        print(f"    - {entry.get('display_name')} (ID: {entry.get('person_id')})")
    print()

    # Prepare output directory for face crops
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Optional video writer
    writer = None
    if args.output_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.output_video, fourcc, fps, (width, height))
        print(f"[*] Recording annotated output to: {args.output_video}\n")

    frame_idx = 0
    faces_detected_count = 0
    matches_found: list[dict] = []
    best_face_for_enroll = None
    best_score_for_enroll = 0.0

    start_time = time.time()
    last_detections_for_video = []

    print("[*] Processing video frames...")

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        frame_idx += 1
        timestamp_sec = frame_idx / fps

        # Decide whether to run detection on this frame
        if frame_idx % args.sample_rate == 0 or frame_idx == 1:
            faces = backend.detect(frame)
            current_detections = []

            for f_idx, face in enumerate(faces):
                if face.detection_score < args.min_score:
                    continue

                faces_detected_count += 1
                x1, y1, x2, y2 = [int(v) for v in (face.bbox.x1, face.bbox.y1, face.bbox.x2, face.bbox.y2)]
                
                # Clamp bbox to image boundaries
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(width, x2), min(height, y2)

                if x2 - x1 < 20 or y2 - y1 < 20:
                    continue

                # Crop face thumbnail
                face_crop = frame[y1:y2, x1:x2].copy()
                crop_filename = out_dir / f"face_f{frame_idx:05d}_{f_idx}.jpg"
                cv2.imwrite(str(crop_filename), face_crop)

                # Track best face for enrollment
                if face.detection_score > best_score_for_enroll:
                    best_score_for_enroll = face.detection_score
                    best_face_for_enroll = face

                # Watchlist match
                match = store.match(
                    embedding=face.embedding,
                    possible_threshold=0.40,
                    match_threshold=0.50,
                    ambiguity_margin=0.04,
                )

                label = "UNKNOWN"
                color = (0, 165, 255)  # Orange

                if match.status.value == "MATCH_CANDIDATE":
                    label = f"MATCH: {match.display_name} ({match.similarity*100:.1f}%)"
                    color = (52, 217, 180)  # Signal teal
                    matches_found.append({
                        "frame": frame_idx,
                        "time_sec": timestamp_sec,
                        "person_id": match.person_id,
                        "name": match.display_name,
                        "similarity": match.similarity,
                        "crop_file": str(crop_filename),
                    })
                    print(f"  ⚡ [MATCH FOUND] Frame {frame_idx:05d} ({timestamp_sec:.2f}s): "
                          f"{match.display_name} ({match.person_id}) - {match.similarity*100:.1f}% "
                          f"-> Saved: {crop_filename.name}")

                elif match.status.value == "POSSIBLE_MATCH":
                    label = f"POSSIBLE: {match.display_name} ({match.similarity*100:.1f}%)"
                    color = (0, 220, 255)  # Yellow
                    print(f"  ? [POSSIBLE MATCH] Frame {frame_idx:05d} ({timestamp_sec:.2f}s): "
                          f"{match.display_name} ({match.similarity*100:.1f}%)")

                current_detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "label": label,
                    "color": color,
                    "score": face.detection_score,
                })

            last_detections_for_video = current_detections

        # If saving annotated video, draw bounding boxes & banners
        if writer is not None:
            annotated_frame = frame.copy()
            for det in last_detections_for_video:
                bx1, by1, bx2, by2 = det["bbox"]
                cv2.rectangle(annotated_frame, (bx1, by1), (bx2, by2), det["color"], 2)
                cv2.putText(
                    annotated_frame,
                    det["label"],
                    (bx1, max(by1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    det["color"],
                    2,
                    cv2.LINE_AA,
                )
            # HUD Watermark
            cv2.putText(
                annotated_frame,
                f"IBVAP FRS | FRM {frame_idx:05d} | {timestamp_sec:.2f}s",
                (15, height - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (180, 190, 200),
                1,
            )
            writer.write(annotated_frame)

        # Print progress every 100 frames
        if frame_idx % 100 == 0:
            pct = (frame_idx / total_frames) * 100 if total_frames > 0 else 0
            print(f"  ... processed {frame_idx}/{total_frames} frames ({pct:.1f}%)")

    cap.release()
    if writer is not None:
        writer.release()

    elapsed = time.time() - start_time
    print(f"\n========================================================")
    print(f"[SUMMARY] Video Analysis Complete in {elapsed:.2f}s")
    print(f"          Frames Processed: {frame_idx}")
    print(f"          Faces Extracted & Saved: {faces_detected_count}")
    print(f"          Watchlist Matches Detected: {len(matches_found)}")
    print(f"          Crops Directory: {out_dir.resolve()}")
    if args.output_video:
        print(f"          Annotated Video: {Path(args.output_video).resolve()}")
    print(f"========================================================")

    # Optional Enrollment from Video
    if args.enroll:
        if best_face_for_enroll is not None:
            store.enroll(
                person_id=args.person_id,
                display_name=args.name,
                embeddings=[best_face_for_enroll.embedding],
                consent_reference=args.consent,
            )
            print(f"\n[ENROLLED] Enrolled {args.name} (ID: {args.person_id}) with best detection "
                  f"(score: {best_score_for_enroll:.3f}) into {watchlist_path}")
        else:
            print("\n[WARN] Could not enroll: no faces met the confidence threshold.")

    # Match details table
    if matches_found:
        print("\n--- Detailed Matches ---")
        for m in matches_found[:10]:
            print(f"  * At {m['time_sec']:.2f}s (Frame #{m['frame']}): {m['name']} "
                  f"[{m['person_id']}] Similarity: {m['similarity']*100:.1f}% | Crop: {m['crop_file']}")
        if len(matches_found) > 10:
            print(f"  ... and {len(matches_found) - 10} more occurrences.")
    else:
        print("\n[INFO] No watchlist matches found in this video footage.")


if __name__ == "__main__":
    main()

