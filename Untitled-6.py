import cv2
import mediapipe as mp
from collections import deque, Counter
from datetime import datetime
import csv
import os
import math


CAM_INDEX = 0                 
FRAME_WIDTH = 960
FRAME_HEIGHT = 540

MIN_DET_CONF = 0.5
MIN_TRK_CONF = 0.5
MAX_HANDS = 1

HOLD_FRAMES = 5               
MARGIN = 0.02                 

DRAW_LANDMARKS = True
SHOW_FPS = True
LOG_TO_CSV = True
CSV_PATH = "gesture_log.csv"


ENABLE_SERIAL = False
SERIAL_PORT = "COM3"          
BAUD = 9600


arduino = None
if ENABLE_SERIAL:
    try:
        import serial
        arduino = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
        print(f"[INFO] Serial connected on {SERIAL_PORT} @ {BAUD}")
    except Exception as e:
        print(f"[WARN] Serial not connected: {e}")
        arduino = None


if LOG_TO_CSV and not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "gesture"])


mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles


THUMB_TIP, THUMB_IP = 4, 3
INDEX_TIP, INDEX_PIP = 8, 6
MIDDLE_TIP, MIDDLE_PIP = 12, 10
RING_TIP, RING_PIP = 16, 14
PINKY_TIP, PINKY_PIP = 20, 18

def norm_dist(a, b):
    """Euclidean distance between two normalized points (x,y)."""
    return math.hypot(a.x - b.x, a.y - b.y)

def finger_states(lm, handed_label):
   
    fingers = [False]*5

    
    thumb_tip = lm[THUMB_TIP]
    thumb_ip  = lm[THUMB_IP]
    if handed_label == "Right":
        fingers[0] = (thumb_tip.x < thumb_ip.x - MARGIN)
    else:  
        fingers[0] = (thumb_tip.x > thumb_ip.x + MARGIN)

    
    pairs = [(INDEX_TIP, INDEX_PIP),
             (MIDDLE_TIP, MIDDLE_PIP),
             (RING_TIP, RING_PIP),
             (PINKY_TIP, PINKY_PIP)]
    for i, (tip_i, pip_i) in enumerate(pairs, start=1):
        fingers[i] = (lm[tip_i].y < lm[pip_i].y - MARGIN)

    return fingers

def is_pinch(lm):
    
    return norm_dist(lm[THUMB_TIP], lm[INDEX_TIP]) < 0.05

def classify_gesture(fingers, lm):
   
    if all(fingers):
        return "CALL_NURSE"       # ✋
    if not any(fingers):
        return "NEED_WATER"       # ✊
    if fingers == [False, True, False, False, False]:
        return "PAIN"             # ☝
    if fingers == [False, True, True, False, False]:
        return "WASHROOM"         # ✌
    if is_pinch(lm):
        return "EMERGENCY"        # 🤏
    return "UNKNOWN"

def stable_label(buf, needed=HOLD_FRAMES):
   
    if len(buf) < needed:
        return None
    last = list(buf)[-needed:]
    if all(l == last[0] for l in last) and last[0] != "UNKNOWN":
        return last[0]
    return None

def color_for(label):
    
    return {
        "CALL_NURSE": (255, 0, 0),     # Blue
        "NEED_WATER": (255, 255, 0),   # Cyan
        "PAIN": (0, 0, 255),           # Red
        "WASHROOM": (0, 200, 0),       # Green
        "EMERGENCY": (0, 0, 255),      # Red
        "UNKNOWN": (200, 200, 200)     # Gray
    }.get(label, (200, 200, 200))

def put_fps(frame, fps):
    cv2.putText(frame, f"FPS: {fps:.1f}", (FRAME_WIDTH - 160, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

def ensure_int(val, default):
    try:
        return int(val)
    except Exception:
        return default


cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

if not cap.isOpened():
    raise RuntimeError("Could not open webcam. Try a different CAM_INDEX (0/1/2) and check camera permissions.")

label_buffer = deque(maxlen=HOLD_FRAMES)
last_logged = None
draw_landmarks = DRAW_LANDMARKS

# FPS calculation
import time
prev_time = time.time()
fps_val = 0.0

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=MAX_HANDS,
    min_detection_confidence=MIN_DET_CONF,
    min_tracking_confidence=MIN_TRK_CONF
) as hands:

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Flip for selfie-view (feels natural)
        frame = cv2.flip(frame, 1)

        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        current_label = "UNKNOWN"

        if results.multi_hand_landmarks and results.multi_handedness:
            
            handLms = results.multi_hand_landmarks[0]
            handedness = results.multi_handedness[0].classification[0].label  

            if draw_landmarks:
                mp_draw.draw_landmarks(
                    frame,
                    handLms,
                    mp_hands.HAND_CONNECTIONS,
                    mp_styles.get_default_hand_landmarks_style(),
                    mp_styles.get_default_hand_connections_style()
                )

            lm = handLms.landmark
            fingers = finger_states(lm, handedness)
            current_label = classify_gesture(fingers, lm)

        label_buffer.append(current_label)
        confirmed = stable_label(label_buffer, HOLD_FRAMES)

        # FPS
        now = time.time()
        dt = now - prev_time
        if dt > 0:
            fps_val = 1.0 / dt
        prev_time = now

        # Draw label
        shown = confirmed if confirmed else current_label
        clr = color_for(shown)
        cv2.rectangle(frame, (8, 8), (350, 80), (0, 0, 0), -1)
        cv2.putText(frame, f"Gesture: {shown}", (16, 54),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, clr, 3, cv2.LINE_AA)

        if SHOW_FPS:
            put_fps(frame, fps_val)

        # Log when a new stable gesture appears (edge-trigger)
        if LOG_TO_CSV and confirmed and confirmed != last_logged:
            with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().isoformat(timespec="seconds"), confirmed])
            last_logged = confirmed

            # Optional: send to Arduino later
            if ENABLE_SERIAL and arduino:
                try:
                    arduino.write((confirmed + "\n").encode("utf-8"))
                except Exception as e:
                    print(f"[WARN] Serial write failed: {e}")

        cv2.imshow("CareGlove - Gesture Detector (press 'q' to quit, 'd' to toggle draw)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('d'):
            draw_landmarks = not draw_landmarks

cap.release()
cv2.destroyAllWindows()
print("[INFO] Closed.")
