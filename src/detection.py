import time
import audio
from datetime import datetime
import head_pose
import eye_gaze
import object_detection
import numpy as np

# place holders 
GLOBAL_CHEAT = 0
PERCENTAGE_CHEAT = 0
CHEAT_THRESH = 0.6

# --- Matplotlib Setup ---
PLOT_LENGTH = 200
XDATA = list(range(PLOT_LENGTH))
YDATA = [0] * PLOT_LENGTH

# State tracking to log events only once
last_log_time = {}
LOG_COOLDOWN = 5 # seconds

def log_event(event_type, message, alert_manager=None, icon="❗"):
    """Logs a cheating event to a file with a timestamp, respecting a cooldown."""
    current_time = time.time()
    if event_type not in last_log_time or current_time - last_log_time[event_type] > LOG_COOLDOWN:
        with open("proctoring_log.txt", "a") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ALERT: {message}\n")
        last_log_time[event_type] = current_time
        if alert_manager:
            alert_manager.add_alert(message, icon)

def avg(current, previous):
    """
    Calculates the Exponential Moving Average (EMA) to smooth the cheat score.
    This provides a more stable and predictable score over time.
    """
    # Alpha is the smoothing factor. A higher alpha makes the average more
    # responsive to recent changes.
    if current > previous: # When cheat score is increasing, be more responsive.
        # When cheat score is increasing, be more responsive.
        alpha = 0.1
    else:
        # When cheat score is decreasing, decay more slowly.
        alpha = 0.01
    return alpha * current + (1 - alpha) * previous

def process(alert_manager, detection_results):
    global GLOBAL_CHEAT, PERCENTAGE_CHEAT, CHEAT_THRESH
    
    # Weights for different cheat detections
    weights = {
        "head_x": 0.2,
        "head_y": 0.3,
        "audio": 0.3,
        "eye_gaze": 0.4,
        "object": 0.5,
        "silent_mouth": 0.45,
        "multiple_faces": 0.9,
        "long_blink": 0.2
    }

    # Initialize cheat score for this frame
    current_cheat_score = 0
    active_detections = []

    # Aggregate scores based on detection results
    if detection_results.get("head_x") or detection_results.get("head_y"):
        log_event("looking_away", "User looked away from the screen.", alert_manager)
        current_cheat_score += max(detection_results.get("head_x", 0) * weights["head_x"], detection_results.get("head_y", 0) * weights["head_y"])
        active_detections.append("head")
    if detection_results.get("audio"):
        log_event("speaking", "Speaking or noise detected.", alert_manager, "🔇")
        current_cheat_score += weights["audio"]
        active_detections.append("audio")
    if detection_results.get("object"):
        log_event("object_detected", "Prohibited object detected.", alert_manager, "📱")
        current_cheat_score += weights["object"]
        active_detections.append("object")
    if detection_results.get("eye_gaze"):
        log_event("gaze_off_center", "Eye gaze is off-center.", alert_manager)
        current_cheat_score += weights["eye_gaze"]
        active_detections.append("eye")
    if detection_results.get("long_blink"):
        log_event("long_blink", "Eyes were closed for an extended period.", alert_manager)
        current_cheat_score += weights["long_blink"]
        active_detections.append("blink")
    if detection_results.get("multiple_faces"):
        log_event("multiple_faces", "Multiple faces detected in the frame.", alert_manager)
        current_cheat_score += weights["multiple_faces"]
        active_detections.append("multi_face")

    PERCENTAGE_CHEAT = avg(current_cheat_score, PERCENTAGE_CHEAT)

    if PERCENTAGE_CHEAT > CHEAT_THRESH:
        GLOBAL_CHEAT = 1
        print("CHEATING")
    else:
        GLOBAL_CHEAT = 0
    
    print(f"Cheat percent: {PERCENTAGE_CHEAT:.2f} | Active: {active_detections if active_detections else 'None'}")
