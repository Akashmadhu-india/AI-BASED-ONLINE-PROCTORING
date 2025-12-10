document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const loginForm = document.getElementById('login-form');
    const errorMessageDiv = document.getElementById('error-message');
    const cameraPlaceholder = document.getElementById('camera-placeholder');
    const loginButton = document.querySelector('.login-button');
    const cameraFeed = document.getElementById('camera-feed');

    // --- Event Listener for Form Submission ---
    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        // Hide previous error messages
        errorMessageDiv.style.display = 'none';
        errorMessageDiv.textContent = '';

        // Disable the button to prevent multiple submissions
        const originalButtonText = loginButton.textContent;
        loginButton.disabled = true;
        loginButton.textContent = 'Logging in...';

        // --- 1. Client-Side Validation ---
        const formData = new FormData(loginForm);
        const formProps = Object.fromEntries(formData);

        if (!formProps.fullName || !formProps.usn || !formProps.username || !formProps.password) {
            showError('All fields are required. Please fill out the form completely.');
            loginButton.disabled = false; // Re-enable button
            loginButton.textContent = originalButtonText;
            return;
        }

        // --- 2. Request Camera Access ---
        try {
            await startCamera();
        } catch (error) {
            console.error('Camera access error:', error);
            showError('Camera access is required for the exam. Please allow camera permissions and try again.');
            loginButton.disabled = false; // Re-enable button
            loginButton.textContent = originalButtonText;
            return;
        }

        // --- 3. Send Login Data to Backend ---
        try {
            const response = await fetch('http://127.0.0.1:5001/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: formProps.username,
                    password: formProps.password,
                    role: formProps.role,
                }),
            });

            const result = await response.json();

            if (result.ok) {
                // On success, first stop the camera feed in the browser to release the device.
                stopCamera();

                // Then, redirect to the custom protocol to launch the desktop app.
                // The user will be prompted by the browser to open the application.
                window.location.href = `examproctor://start?token=${result.token}`;
            } else {
                // Show error from the backend
                showError(result.error || 'An unknown error occurred.');
                loginButton.disabled = false; // Re-enable button
                loginButton.textContent = originalButtonText;
                stopCamera(); // Stop camera on login failure
            }
        } catch (networkError) {
            console.error('Network or server error:', networkError);
            showError('Could not connect to the server. Please check your connection and try again.');
            loginButton.disabled = false; // Re-enable button
            loginButton.textContent = originalButtonText;
            stopCamera(); // Stop camera on network failure
        }
    });

    // --- Helper Functions ---

    /**
     * Displays an error message in the UI.
     * @param {string} message The error message to display.
     */
    function showError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
    }

    /**
     * Requests camera access and displays the feed.
     */
    async function startCamera() {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        cameraFeed.srcObject = stream;
        cameraPlaceholder.style.display = 'none';
        cameraFeed.style.display = 'block';
    }

    /**
     * Stops the camera feed and resets the UI.
     */
    function stopCamera() {
        const stream = cameraFeed.srcObject;
        stream?.getTracks().forEach(track => track.stop());
        cameraFeed.srcObject = null;
        cameraPlaceholder.style.display = 'block';
        cameraFeed.style.display = 'none';
    }
});