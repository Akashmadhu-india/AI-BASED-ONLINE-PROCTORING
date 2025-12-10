import cv2
import numpy as np
import os

# --- Constants and Model Loading ---
PROHIBITED_OBJECTS = ["cell phone", "book", "laptop", "remote", "keyboard"] # Add headphones if your model supports it
CONF_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4

# Construct absolute paths to model files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")
COCO_NAMES_PATH = os.path.join(MODELS_DIR, "coco.names")
YOLO_WEIGHTS_PATH = os.path.join(MODELS_DIR, "yolov3.weights")
YOLO_CFG_PATH = os.path.join(MODELS_DIR, "yolov3.cfg")

# Load class names
try:
    with open(COCO_NAMES_PATH, "r") as f:
        CLASSES = [line.strip() for line in f.readlines()]
except FileNotFoundError:
    print(f"Error: {COCO_NAMES_PATH} not found. Make sure the model files are in the 'src/models/' directory.")
    CLASSES = []

# Load YOLO model
try:
    net = cv2.dnn.readNet(YOLO_WEIGHTS_PATH, YOLO_CFG_PATH)
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    LAYER_NAMES = net.getLayerNames()
    OUTPUT_LAYERS = [LAYER_NAMES[i - 1] for i in net.getUnconnectedOutLayers()]
except cv2.error:
    print(f"Error: YOLO model files not found. Make sure '{os.path.basename(YOLO_WEIGHTS_PATH)}' and '{os.path.basename(YOLO_CFG_PATH)}' are in the 'src/models/' directory.")
    net = None

def detect_objects(image, alert_manager=None):
    """
    Detects prohibited objects in the given image frame.
    Updates the global OBJECT_CHEAT flag.
    """
    object_cheat = 0

    if net is None or not CLASSES:
        # Return the original image if the model isn't loaded
        return image, {"object": object_cheat}


    height, width, _ = image.shape
    blob = cv2.dnn.blobFromImage(image, 1/255.0, (320, 320), swapRB=True, crop=False)
    net.setInput(blob)
    layer_outputs = net.forward(OUTPUT_LAYERS)

    boxes, confidences, class_ids = [], [], []

    for output in layer_outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > CONF_THRESHOLD:
                center_x, center_y, w, h = (detection[0:4] * np.array([width, height, width, height])).astype('int')
                x, y = int(center_x - w / 2), int(center_y - h / 2)
                boxes.append([x, y, int(w), int(h)])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Apply Non-Max Suppression
    indices = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESHOLD, NMS_THRESHOLD)

    if len(indices) > 0:
        for i in indices.flatten():
            box = boxes[i]
            x, y, w, h = box[0], box[1], box[2], box[3]
            class_name = CLASSES[class_ids[i]]

            if class_name in PROHIBITED_OBJECTS:
                # A prohibited object is detected
                object_cheat = 1
                
                # Draw bounding box and label
                color = (0, 0, 255) # Red for prohibited objects
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
                text = f"{class_name}: {confidences[i]:.2f}"
                cv2.putText(image, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                break # Stop after finding one prohibited object

    return image, {"object": object_cheat}