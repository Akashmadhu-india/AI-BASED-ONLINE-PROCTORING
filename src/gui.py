import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import mediapipe as mp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import head_pose
import object_detection
import eye_gaze
import detection
import audio

class ProctoringApp:
    def __init__(self, root, detection_module, alert_manager, user_info, audio_state):
        self.root = root
        self.detection_module = detection_module
        self.alert_manager = alert_manager
        self.user_info = user_info
        self.audio_state = audio_state # Store the shared audio state

        # --- Set Window Title with User Name ---
        window_title = "Proctoring Application"
        if self.user_info and 'fullName' in self.user_info:
            window_title += f" - {self.user_info['fullName']}"
        self.root.title(window_title)

        self.root.geometry("1200x700")

        # --- Main Frames ---
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        video_frame = ttk.LabelFrame(main_frame, text="Camera Feed")
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        graph_frame = ttk.LabelFrame(right_panel, text="Suspicion Level")
        graph_frame.pack(fill=tk.BOTH, expand=True)

        # --- Video Feed ---
        self.video_label = ttk.Label(video_frame)
        self.video_label.pack(expand=True, fill=tk.BOTH)

        # --- Suspicion Graph ---
        self.fig = plt.Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlim(0, detection.PLOT_LENGTH)
        self.ax.set_ylim(0, 1)
        self.ax.set_title("Suspicion Over Time")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Probability")
        self.line, = self.ax.plot(detection.XDATA, detection.YDATA, 'r-')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- MediaPipe and Camera Setup ---
        self.cap = cv2.VideoCapture(0)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # --- Start the update loop ---
        self.update()

    def update(self):
        """Main loop to update the GUI."""
        # --- Video and Proctoring Logic ---
        success, frame = self.cap.read()
        if success:
            # Process the frame using the logic from eye_gaze.py
            processed_frame = self.process_frame(frame)

            # Convert image for Tkinter
            img = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        # --- Aggregate all detection results ---
        # This is where we now collect the return values from our refactored modules
        all_detection_results = {}
        if hasattr(self, 'head_pose_results'):
            all_detection_results.update(self.head_pose_results)
        if hasattr(self, 'eye_gaze_results'):
            all_detection_results.update(self.eye_gaze_results)
        if hasattr(self, 'object_detection_results'):
            all_detection_results.update(self.object_detection_results)
        # Read the audio cheat status from the shared state object.
        all_detection_results['audio'] = self.audio_state.get("is_cheating", 0)

        # --- Update Suspicion Score and Graph ---
        detection.process(self.alert_manager, all_detection_results)
        detection.YDATA.pop(0)
        detection.YDATA.append(detection.PERCENTAGE_CHEAT)
        self.line.set_ydata(detection.YDATA)
        self.canvas.draw()

        # --- Schedule next update ---
        self.root.after(20, self.update) # ~50 FPS

    def process_frame(self, image):
        """
        Processes a single video frame for all detections.
        This consolidates logic from the original eye_gaze.track_eyes loop.
        """
        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.face_mesh.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # Eye gaze and blink detection
        if results.multi_face_landmarks:
            # Pass the results to head_pose instead of having it re-process
            image, self.head_pose_results = head_pose.pose(image, results, self.alert_manager)
            self.eye_gaze_results = eye_gaze.process_face_landmarks(image, results.multi_face_landmarks[0].landmark)

        # Object detection (can be run periodically if needed)
        image, self.object_detection_results = object_detection.detect_objects(image, self.alert_manager)

        # --- Display Cheat Probability Bar ---
        img_h, img_w, _ = image.shape
        bar_width = int(img_w * 0.8)
        bar_start_x = int((img_w - bar_width) / 2)
        cheat_percent = max(0, min(1, self.detection_module.PERCENTAGE_CHEAT))
        fill_width = int(bar_width * cheat_percent)
        cv2.rectangle(image, (bar_start_x, img_h - 40), (bar_start_x + bar_width, img_h - 20), (255, 255, 255), -1)
        cv2.rectangle(image, (bar_start_x, img_h - 40), (bar_start_x + fill_width, img_h - 20), (0, 0, 255), -1)
        text = f"Suspicion Level: {cheat_percent:.0%}"
        cv2.putText(image, text, (bar_start_x, img_h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # --- Display Real-Time Alerts ---
        active_alerts = self.alert_manager.get_alerts()
        y_pos = 30
        for alert_text in active_alerts:
            (text_width, text_height), _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            overlay = image.copy()
            cv2.rectangle(overlay, (10, y_pos - text_height - 5), (20 + text_width, y_pos + 5), (0, 0, 0), -1)
            alpha = 0.6
            image = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
            cv2.putText(image, alert_text, (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_pos += 30

        return image

    def on_closing(self):
        """Handle window closing."""
        self.cap.release()
        self.root.destroy()