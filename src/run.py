import audio
import detection
import alerts
import gui
import tkinter as tk
import threading as th
import os
import sys
import jwt
from urllib.parse import urlparse, parse_qs

# IMPORTANT: This secret key MUST match the one in your Flask app (app.py).
# Load the secret key from an environment variable for better security.
SECRET_KEY = os.environ.get('PROCTORING_SECRET_KEY', 'your-super-secret-and-long-key-fallback')

def validate_token(token):
    """Validates the JWT token."""
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # The token is valid (signature and expiration are checked by jwt.decode)
        print("✅ Token is valid.")
        return decoded_token['user']
    except jwt.ExpiredSignatureError:
        print("❌ Error: Token has expired. Please log in again.")
        return None
    except jwt.InvalidTokenError:
        print("❌ Error: Invalid token. Authentication failed.")
        return None

if __name__ == "__main__":
    user_info = None
    # Check for a "debug" flag to run the app without a token
    is_debug_mode = "--debug" in sys.argv

    # --- Token Validation from Command-Line Argument ---
    if len(sys.argv) > 1:
        # The OS passes the full custom URL as an argument (e.g., "examproctor://start?token=...")
        # Find the argument that looks like our custom URL
        url_arg = next((arg for arg in sys.argv if arg.startswith("examproctor://")), None)

        if url_arg:
            parsed_url = urlparse(url_arg)
            query_params = parse_qs(parsed_url.query)
            token = query_params.get('token', [None])[0]

            if token:
                user_info = validate_token(token)
            else:
                print("❌ Error: No token provided in the launch URL.")

    if is_debug_mode and not user_info:
        print("⚠️ Running in DEBUG mode without a token.")
        user_info = {"fullName": "Debug User", "role": "Student"} # Provide mock user data for debug mode
    elif not user_info:
        print("❌ Error: Application cannot be started directly. Please log in via the web portal.")
        # Exit the script cleanly if not in debug mode and no token is found.
        sys.exit(1)

    # --- Launch Application only if Token is Valid ---
    if user_info:
        print(f"🚀 Starting proctoring session for: {user_info.get('fullName')}")
        
        # --- Create Shared State Objects ---
        alert_manager = alerts.AlertManager()
        # Use a simple dictionary as a mutable object to share state between threads.
        audio_state = {"is_cheating": 0}

        # --- Start Background Threads ---
        # The audio thread will now update the shared audio_state object.
        audio_thread = th.Thread(target=audio.sound, args=(alert_manager, audio_state), daemon=True)
        audio_thread.start()

        # --- Create and Run the Main GUI ---
        root = tk.Tk()
        # Pass all shared objects (detection module, managers, state) to the GUI.
        app = gui.ProctoringApp(root, detection, alert_manager, user_info, audio_state) 
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
