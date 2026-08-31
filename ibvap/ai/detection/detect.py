import cv2
import json
import uuid
from datetime import datetime, timezone
from ultralytics import YOLO

# ----------------------------------------------------------------------
# CONFIG & MODEL LOADING
# ----------------------------------------------------------------------
CAMERA_ID = "BOP-01"

# Replace with the exact IP and Port shown in your IP Webcam app
# Standard IP Webcam stream endpoint is "/video"
IP_WEBCAM_URL = "http://192.168.1.3:4747/video"
VIDEO_SOURCE = IP_WEBCAM_URL

# Paths
ENTITY_MODEL_PATH = r"D:\Engineering_Projects\NERV-SmartBorderSurveillance\ibvap\models\detection\entity.pt"
WEAPON_MODEL_PATH = r"D:\Engineering_Projects\NERV-SmartBorderSurveillance\ibvap\models\detection\weapons.pt"

# Load models
entity_model = YOLO(ENTITY_MODEL_PATH)
weapon_model = YOLO(WEAPON_MODEL_PATH)

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}
SAVE_EVENTS_LOG = True
EVENTS_LOG_PATH = "detections_log.jsonl"

event_counter = 1


def check_overlap(boxA, boxB):
    """Checks if weapon bounding box overlaps with person bounding box."""
    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    return ix1 < ix2 and iy1 < iy2


def build_event_json(event_num, event_type, entity_type, entity_id, cls_name, conf, bbox, track_id, severity, metadata=None):
    """Constructs the exact JSON schema required by spec."""
    return {
        "event_id": f"EVT-{event_num:06d}",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "camera_id": CAMERA_ID,
        "entity": {
            "entity_id": entity_id,
            "entity_type": entity_type
        },
        "detection": {
            "class": cls_name,
            "confidence": round(conf, 2),
            "bbox": bbox,
            "track_id": track_id
        },
        "severity": severity,
        "metadata": metadata if metadata is not None else {}
    }


# ----------------------------------------------------------------------
# MAIN INFERENCE LOOP
# ----------------------------------------------------------------------
cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    print(f"Error: Could not open IP Webcam stream at '{VIDEO_SOURCE}'.")
    print("Check that your phone and PC are on the same Wi-Fi network and the URL is correct.")
    exit(1)

log_file = open(EVENTS_LOG_PATH, "a") if SAVE_EVENTS_LOG else None

print(f"Starting Inference Engine connected to IP Webcam ({VIDEO_SOURCE})... Press 'q' to exit.")

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame from stream. Reconnecting or ending stream...")
            break

        # 1. Run inference passes
        entity_results = entity_model(frame, conf=0.40, verbose=False)[0]
        weapon_results = weapon_model(frame, conf=0.75, verbose=False)[0]

        persons = []
        weapons = []
        vehicles = []

        # Parse entity model (persons + vehicles)
        for idx, box in enumerate(entity_results.boxes):
            cls_id = int(box.cls[0])
            cls_name = entity_results.names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])

            if cls_name == "person":
                persons.append({
                    "bbox": [x1, y1, x2, y2],
                    "conf": conf,
                    "track_id": idx + 1
                })
            elif cls_name in VEHICLE_CLASSES:
                vehicles.append({
                    "class": cls_name,
                    "bbox": [x1, y1, x2, y2],
                    "conf": conf,
                    "track_id": idx + 1
                })

        # Parse weapon model
        for idx, box in enumerate(weapon_results.boxes):
            cls_id = int(box.cls[0])
            w_label = weapon_results.names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            weapons.append({
                "class": w_label,
                "bbox": [x1, y1, x2, y2],
                "conf": conf,
                "track_id": idx + 100
            })

        frame_events = []
        threat_flag = False

        # 2. Process Person Detections & Check Armed Threat
        for person in persons:
            px1, py1, px2, py2 = person["bbox"]
            is_armed = False
            detected_weapon_label = None

            for weapon in weapons:
                if check_overlap((px1, py1, px2, py2), weapon["bbox"]):
                    is_armed = True
                    threat_flag = True
                    detected_weapon_label = weapon["class"]
                    break

            # Set schema fields based on armed status
            if is_armed:
                event_type = "hostile_activity"
                severity = "HIGH"
                meta = {"threat": "armed_individual", "weapon_detected": detected_weapon_label}
            else:
                event_type = "person_detected"
                severity = "LOW"
                meta = {}

            entity_id = f"G-{person['track_id']:03d}"
            evt = build_event_json(
                event_num=event_counter,
                event_type=event_type,
                entity_type="person",
                entity_id=entity_id,
                cls_name="person",
                conf=person["conf"],
                bbox=person["bbox"],
                track_id=person["track_id"],
                severity=severity,
                metadata=meta
            )
            event_counter += 1
            frame_events.append(evt)

            # Draw Person Box
            color = (0, 0, 255) if is_armed else (0, 255, 0)
            label = "ARMED THREAT!" if is_armed else f"Person {person['conf']:.2f}"
            cv2.rectangle(frame, (px1, py1), (px2, py2), color, 3 if is_armed else 2)
            cv2.putText(frame, label, (px1, max(py1 - 10, 25)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 3. Process Vehicle Detections
        for vehicle in vehicles:
            vx1, vy1, vx2, vy2 = vehicle["bbox"]
            entity_id = f"V-{vehicle['track_id']:03d}"
            
            evt = build_event_json(
                event_num=event_counter,
                event_type="vehicle_detected",
                entity_type="vehicle",
                entity_id=entity_id,
                cls_name=vehicle["class"],
                conf=vehicle["conf"],
                bbox=vehicle["bbox"],
                track_id=vehicle["track_id"],
                severity="LOW"
            )
            event_counter += 1
            frame_events.append(evt)

            # Draw Vehicle Box
            cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (255, 165, 0), 2)
            cv2.putText(frame, f"{vehicle['class'].upper()} {vehicle['conf']:.2f}", 
                        (vx1, max(vy1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)

        # 4. Draw Weapon Bboxes
        for weapon in weapons:
            wx1, wy1, wx2, wy2 = weapon["bbox"]
            cv2.rectangle(frame, (wx1, wy1), (wx2, wy2), (0, 0, 255), 2)
            cv2.putText(frame, f"{weapon['class'].upper()} {weapon['conf']:.2f}", 
                        (wx1, max(wy1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # 5. Output JSON payload to terminal & append to file
        for evt in frame_events:
            json_output = json.dumps(evt, indent=2)
            print(json_output)
            if log_file:
                log_file.write(json.dumps(evt) + "\n")
                log_file.flush()

        if threat_flag:
            cv2.putText(frame, "ALERT: ARMED INDIVIDUAL DETECTED", (30, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)

        cv2.imshow("Triple Model Inference Engine", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    if log_file:
        log_file.close()