import math
import cv2
import mediapipe as mp
import numpy as np

# --- Constants for Mouth Movement Detection ---
MOUTH_AR_THRESH = 0.3  # Threshold for detecting an open mouth
MOUTH_AR_CONSECUTIVE_FRAMES = 5
mouth_ar_counter = 0

# Landmark indices from MediaPipe for inner mouth
MOUTH_INNER_LANDMARKS = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

def euclidean_distance(p1, p2):
    """Helper function to calculate Euclidean distance."""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def get_mouth_aspect_ratio(landmarks):
    """Calculates the Mouth Aspect Ratio (MAR)."""
    # Vertical distances
    p2, p10 = landmarks[12], landmarks[4] # Example vertical points
    p4, p8 = landmarks[14], landmarks[2]
    # Horizontal distance
    p1, p7 = landmarks[0], landmarks[6]
    return (euclidean_distance(p2, p10) + euclidean_distance(p4, p8)) / (2.0 * euclidean_distance(p1, p7))

def pose(image, results, alert_manager=None):
    # Use function-level state for counters instead of global
    mouth_ar_counter = getattr(pose, "mouth_ar_counter", 0)

    detection_results = {
        "head_x": 0, "head_y": 0, "mouth": 0, "multiple_faces": 0
    }

    if results.multi_face_landmarks:
        # --- Multiple Face Detection ---
        if len(results.multi_face_landmarks) > 1:
            detection_results["multiple_faces"] = 1

        img_h, img_w, img_c = image.shape
        face_ids = [33, 263, 1, 61, 291, 199]

        for face_landmarks in results.multi_face_landmarks: # This loop will process all faces
            face_2d = []
            face_3d = []

            mp_drawing.draw_landmarks(
                image=image,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None
            )

            # --- Mouth Movement Detection ---
            inner_lip_landmarks = [face_landmarks.landmark[i] for i in MOUTH_INNER_LANDMARKS]
            mar = get_mouth_aspect_ratio(inner_lip_landmarks)

            if mar > MOUTH_AR_THRESH:
                mouth_ar_counter += 1
            else:
                mouth_ar_counter = 0
            
            if mouth_ar_counter >= MOUTH_AR_CONSECUTIVE_FRAMES:
                detection_results["mouth"] = 1

            # Head pose is typically only calculated for the primary face
            for idx, lm in enumerate(face_landmarks.landmark):
                # print(lm)
                if idx in face_ids:
                    if idx == 1:
                        nose_2d = (lm.x * img_w, lm.y * img_h)
                        nose_3d = (lm.x * img_w, lm.y * img_h, lm.z * 8000)

                    x, y = int(lm.x * img_w), int(lm.y * img_h)

                    # Get the 2D Coordinates
                    face_2d.append([x, y])

                    # Get the 3D Coordinates
                    face_3d.append([x, y, lm.z])       
            
            # Convert it to the NumPy array
            face_2d = np.array(face_2d, dtype=np.float64)

            # Convert it to the NumPy array
            face_3d = np.array(face_3d, dtype=np.float64)

            # The camera matrix
            focal_length = 1 * img_w

            cam_matrix = np.array([ [focal_length, 0, img_h / 2],
                                    [0, focal_length, img_w / 2],
                                    [0, 0, 1]])

            # The Distance Matrix
            dist_matrix = np.zeros((4, 1), dtype=np.float64)

            # Solve PnP
            success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)

            # Get rotational matrix
            rmat, jac = cv2.Rodrigues(rot_vec)

            # Get angles
            angles, mtxR, mtxQ, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)

            # Get the y rotation degree
            x = angles[0] * 360
            y = angles[1] * 360

            # Y is left / right
            # X is up / down
            if y < -20 or y > 20:
                detection_results["head_x"] = 1

            if x < -20 or x > 20: # Detect both up and down movement, increased threshold
                detection_results["head_y"] = 1
            
            # Break after processing the first face for head pose to avoid conflicting data
            break 

    pose.mouth_ar_counter = mouth_ar_counter
    return image, detection_results