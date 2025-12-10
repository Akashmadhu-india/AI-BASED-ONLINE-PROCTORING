from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import jwt
import datetime
import os

# --- App Initialization ---
app = Flask(__name__, static_folder=None)
# Enable CORS to allow requests from the frontend (running on a different port)
CORS(app)

# --- JWT Configuration ---
# IMPORTANT: In a production environment, use a strong, secret key and load it securely.
# Load the secret key from an environment variable for better security.
app.config['SECRET_KEY'] = os.environ.get('PROCTORING_SECRET_KEY', 'your-super-secret-and-long-key-fallback')

# --- In-Memory Mock User Database ---
# In a real application, this would be a database (e.g., PostgreSQL, MySQL).
# Passwords are pre-hashed for security. Never store plain-text passwords.
MOCK_USERS = [
    {
        "id": 1,
        "fullName": "John Doe",
        "usn": "1AB23CS001",
        "username": "john.doe@example.com",
        "password_hash": generate_password_hash("studentpass123"),
        "role": "Student"
    },
    {
        "id": 2,
        "fullName": "Jane Smith",
        "usn": "ADMIN01",
        "username": "admin@proctor.com",
        "password_hash": generate_password_hash("adminpass123"),
        "role": "Admin"
    }
]


@app.route('/')
def serve_index():
    """Serves the main index.html file."""
    # The '.' indicates the current directory where app.py is running.
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serves other static files like style.css and script.js."""
    return send_from_directory('.', filename)


# --- API Routes ---

@app.route('/api/login', methods=['POST'])
def login():
    """
    Handles user login requests.
    Validates username, password, and role against the mock user list.
    """
    data = request.get_json()
    if not data:
        return jsonify({"ok": False, "error": "Invalid request format."}), 400

    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    # --- Find User and Validate Credentials ---
    user = next((u for u in MOCK_USERS if u['username'] == username), None)

    if not user:
        return jsonify({"ok": False, "error": "Invalid username or password."}), 401

    if not check_password_hash(user['password_hash'], password):
        return jsonify({"ok": False, "error": "Invalid username or password."}), 401

    if user['role'] != role:
        return jsonify({"ok": False, "error": f"User is not registered as a {role}."}), 401

    # --- Generate JWT Token ---
    # On successful login, create a token that includes user data and an expiration time.
    user_data = {key: val for key, val in user.items() if key != 'password_hash'}
    token = jwt.encode({
        'user': user_data,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5) # Token expires in 5 minutes
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({
        "ok": True, 
        "token": token,
        "user": user_data # Also return user data for immediate use in frontend if needed
    }), 200

if __name__ == '__main__':
    # Run the app in debug mode for development
    app.run(debug=True, port=5001)