import cv2
import numpy as np
import math

# Constants for eye tracking
EAR_THRESHOLD = 0.2  # Eye Aspect Ratio threshold for blink detection
CONSECUTIVE_FRAMES_THRESHOLD = 5  # Number of consecutive frames for a blink to be registered
GAZE_THRESHOLD = 0.3  # Reduced threshold for detecting horizontal (left/right) gaze to decrease sensitivity
VERTICAL_GAZE_THRESHOLD = 0.2 # Reduced threshold for detecting vertical (up/down) gaze to decrease sensitivity. Looking up is > 1-thresh, down is < thresh.

# Landmark indices from MediaPipe
LEFT_EYE_LANDMARKS = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE_LANDMARKS = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
LEFT_IRIS_LANDMARKS = [474, 475, 476, 477]
RIGHT_IRIS_LANDMARKS = [469, 470, 471, 472]

def euclidean_distance(p1, p2):
    """Calculate Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def get_ear(landmarks, eye_indices):
    """Calculate the Eye Aspect Ratio (EAR) for a single eye."""
    try:
        # Vertical landmarks (use landmark objects directly)
        p2 = landmarks[eye_indices[11]]
        p6 = landmarks[eye_indices[3]]
        p3 = landmarks[eye_indices[12]]
        p5 = landmarks[eye_indices[4]]

        # Horizontal landmarks (use landmark objects directly)
        p1 = landmarks[eye_indices[0]]
        p4 = landmarks[eye_indices[8]]

        ver_dist1 = euclidean_distance((p2.x, p2.y), (p6.x, p6.y))
        ver_dist2 = euclidean_distance((p3.x, p3.y), (p5.x, p5.y))
        hor_dist = euclidean_distance((p1.x, p1.y), (p4.x, p4.y))

        return (ver_dist1 + ver_dist2) / (2.0 * hor_dist)
    except:
        return 0.0

def get_gaze_ratio(landmarks, eye_indices, iris_indices, img_w, img_h):
    """Calculate the gaze ratio to determine horizontal eye movement."""
    try:
        eye_region = np.array([(landmarks[i].x * img_w, landmarks[i].y * img_h) for i in eye_indices])
        
        # Get corners of the eye
        eye_left_corner = (landmarks[eye_indices[0]].x * img_w, landmarks[eye_indices[0]].y * img_h)
        eye_right_corner = (landmarks[eye_indices[8]].x * img_w, landmarks[eye_indices[8]].y * img_h)
        eye_width = euclidean_distance(eye_left_corner, eye_right_corner)

        # Get center of the iris
        iris_center_x = sum([landmarks[i].x for i in iris_indices]) / len(iris_indices) * img_w
        
        # Calculate gaze ratio
        gaze_ratio = (iris_center_x - eye_left_corner[0]) / eye_width
        return gaze_ratio
    except:
        return 0.5 # Return center if something fails

def get_vertical_gaze_ratio(landmarks, eye_indices, iris_indices, img_w, img_h):
    """Calculate the vertical gaze ratio to determine up/down eye movement."""
    try:
        # Get top and bottom of the eye
        eye_top = (landmarks[eye_indices[11]].x * img_w, landmarks[eye_indices[11]].y * img_h)
        eye_bottom = (landmarks[eye_indices[3]].x * img_w, landmarks[eye_indices[3]].y * img_h)
        eye_height = euclidean_distance(eye_top, eye_bottom)

        if eye_height == 0: return 0.5

        # Get center of the iris
        iris_center_y = sum([landmarks[i].y for i in iris_indices]) / len(iris_indices) * img_h

        # Calculate gaze ratio
        vertical_gaze_ratio = (iris_center_y - eye_top[1]) / eye_height
        return vertical_gaze_ratio
    except:
        return 0.5 # Return center if something fails

def process_face_landmarks(image, landmarks):
    """
    Processes face landmarks to detect blinks and gaze direction for a single frame.
    Updates global cheat flags.
    """
    persistent_blink_counter = getattr(process_face_landmarks, "persistent_blink_counter", 0)
    detection_results = {
        "eye_gaze": 0,
        "long_blink": 0
    }

    img_h, img_w, _ = image.shape

    # --- Blink Detection ---
    left_ear = get_ear(landmarks, LEFT_EYE_LANDMARKS)
    right_ear = get_ear(landmarks, RIGHT_EYE_LANDMARKS)
    avg_ear = (left_ear + right_ear) / 2.0

    if avg_ear < EAR_THRESHOLD:
        persistent_blink_counter += 1
    else:
        if persistent_blink_counter >= CONSECUTIVE_FRAMES_THRESHOLD:
            detection_results["long_blink"] = 1 # Set cheat flag for long blink
        # No need for an else, the flag is 0 by default
        persistent_blink_counter = 0
    
    process_face_landmarks.persistent_blink_counter = persistent_blink_counter

    # --- Gaze Detection ---
    left_gaze_ratio = get_gaze_ratio(landmarks, LEFT_EYE_LANDMARKS, LEFT_IRIS_LANDMARKS, img_w, img_h)
    right_gaze_ratio = get_gaze_ratio(landmarks, RIGHT_EYE_LANDMARKS, RIGHT_IRIS_LANDMARKS, img_w, img_h)
    avg_gaze_ratio = (left_gaze_ratio + right_gaze_ratio) / 2.0

    left_vertical_gaze = get_vertical_gaze_ratio(landmarks, LEFT_EYE_LANDMARKS, LEFT_IRIS_LANDMARKS, img_w, img_h)
    right_vertical_gaze = get_vertical_gaze_ratio(landmarks, RIGHT_EYE_LANDMARKS, RIGHT_IRIS_LANDMARKS, img_w, img_h)
    avg_vertical_gaze = (left_vertical_gaze + right_vertical_gaze) / 2.0

    # Check for horizontal and vertical gaze deviation independently
    horizontal_gaze_off_center = avg_gaze_ratio > 1 - GAZE_THRESHOLD or avg_gaze_ratio < GAZE_THRESHOLD
    vertical_gaze_off_center = avg_vertical_gaze > 1 - VERTICAL_GAZE_THRESHOLD or avg_vertical_gaze < VERTICAL_GAZE_THRESHOLD

    if horizontal_gaze_off_center or vertical_gaze_off_center:
        detection_results["eye_gaze"] = 1 # Looking away from center

    return detection_results

if __name__ == '__main__':
    pass # This module is not meant to be run directly