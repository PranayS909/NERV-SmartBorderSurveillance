#!/usr/bin/env python3
"""
scripts/test_face.py — Test InsightFace (buffalo_l) 512-D Face Recognition & Watchlist Matching.

Usage:
    # 1. Test detection & embedding on an image
    python scripts/test_face.py --image kushal.jpeg

    # 2. Enroll a person into the watchlist
    python scripts/test_face.py --image kushal.jpeg --enroll --name "Kushal" --person-id "PERS-001"

    # 3. Match against the enrolled watchlist
    python scripts/test_face.py --image kushal.jpeg
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
from ai.face.backend import InsightFaceBackend
from ai.face.watchlist import WatchlistStore


def main():
    parser = argparse.ArgumentParser(description="Test InsightFace buffalo_l & Watchlist")
    parser.add_argument("--image", default="kushal.jpeg", help="Path to input image (default: kushal.jpeg)")
    parser.add_argument("--watchlist", default="demo/watchlist/watchlist.json", help="Path to watchlist JSON")
    parser.add_argument("--enroll", action="store_true", help="Enroll detected face into the watchlist")
    parser.add_argument("--name", default="Kushal", help="Name to enroll (if --enroll)")
    parser.add_argument("--person-id", default="PERS-001", help="Person ID to enroll (if --enroll)")
    parser.add_argument("--consent", default="DEMO-AUTH-2026", help="Consent reference code")
    parser.add_argument("--save-annotated", default="detected_face.jpg", help="Output annotated image")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"❌ Error: Image '{img_path}' not found.")
        sys.exit(1)

    img = cv2.imread(str(img_path))
    if img is None:
        print(f"[ERROR] Could not decode image '{img_path}'.")
        sys.exit(1)

    print(f"\n========================================================")
    print(f"[TEST] Testing InsightFace (buffalo_l) on: {img_path.name}")
    print(f"       Image Resolution: {img.shape[1]}x{img.shape[0]}")
    print(f"========================================================\n")

    # 1. Initialize InsightFace Backend
    print("[*] Loading InsightFace buffalo_l models (RetinaFace det_10g + ArcFace w600k_r50)...")
    backend = InsightFaceBackend(
        model_pack="buffalo_l",
        model_root="models/insightface/.insightface"
    )
    print(f"[OK] Model loaded: {backend.model_name}\n")

    # 2. Detect Faces & Extract 512-D Embeddings
    print("[*] Running face detection and embedding extraction...")
    faces = backend.detect(img)
    print(f"    Found {len(faces)} face(s)\n")

    if not faces:
        print("[WARN] No faces detected in the image.")
        return

    # 3. Load Watchlist Store
    watchlist_path = Path(args.watchlist)
    store = WatchlistStore(watchlist_path, backend.model_name)

    # 4. Handle Enrollment if requested
    if args.enroll:
        first_face = faces[0]
        store.enroll(
            person_id=args.person_id,
            display_name=args.name,
            embeddings=[first_face.embedding],
            consent_reference=args.consent,
        )
        print(f"[ENROLLED] {args.name} (ID: {args.person_id}) into {watchlist_path}")
        print(f"           Total watchlist entries: {len(store.entries)}\n")

    # 5. Process each detected face & perform watchlist matching
    annotated = img.copy()

    for idx, face in enumerate(faces, 1):
        x1, y1, x2, y2 = int(face.bbox.x1), int(face.bbox.y1), int(face.bbox.x2), int(face.bbox.y2)
        emb = face.embedding
        score = face.detection_score

        print(f"--- Face #{idx} ---")
        print(f"  * Detection Score: {score:.4f}")
        print(f"  * Bounding Box:    [{x1}, {y1}, {x2}, {y2}] (Size: {x2-x1}x{y2-y1}px)")
        print(f"  * Embedding Dim:   {len(emb)} dimensions")
        print(f"  * Vector Sample:   [{emb[0]:.4f}, {emb[1]:.4f}, {emb[2]:.4f}, ... , {emb[-1]:.4f}]")

        # Watchlist Match
        match = store.match(
            embedding=emb,
            possible_threshold=0.40,
            match_threshold=0.50,
            ambiguity_margin=0.04,
        )

        label = "UNKNOWN"
        color = (0, 165, 255)  # Orange for unknown/unresolved

        if match.status.value == "MATCH_CANDIDATE":
            label = f"MATCH: {match.display_name} ({match.similarity*100:.1f}%)"
            color = (52, 217, 180)  # Signal teal
            print(f"  [MATCH] Status: {match.status.value}")
            print(f"          Person: {match.display_name} (ID: {match.person_id})")
            print(f"          Cosine Similarity: {match.similarity:.4f} (Threshold: >= 0.50)")
        elif match.status.value == "POSSIBLE_MATCH":
            label = f"POSSIBLE: {match.display_name} ({match.similarity*100:.1f}%)"
            color = (0, 220, 255)  # Yellow
            print(f"  [POSSIBLE] Person: {match.display_name} (Score: {match.similarity:.4f})")
        else:
            reason = match.reasons[0] if match.reasons else "no_match"
            print(f"  [NO MATCH] (Reason: {reason})")

        print()

        # Draw on annotated image
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            annotated,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    # Save output annotated image
    out_file = Path(args.save_annotated)
    cv2.imwrite(str(out_file), annotated)
    print(f"[OUTPUT] Saved annotated detection output to: {out_file.resolve()}\n")



if __name__ == "__main__":
    main()
