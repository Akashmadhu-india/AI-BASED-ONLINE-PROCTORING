import sys
import winreg as reg
import os

def register_protocol():
    """
    Registers a custom URL protocol 'examproctor://' on Windows.
    This allows web links to launch the proctoring application.
    
    IMPORTANT: This script must be run with Administrator privileges.
    """
    try:
        # Get the absolute path to the Python executable and the run.py script
        python_exe = sys.executable
        script_path = os.path.abspath("run.py")

        # The command that will be executed when the protocol is invoked
        command = f'"{python_exe}" "{script_path}" "%1"'

        # Create the main protocol key
        key = reg.CreateKey(reg.HKEY_CLASSES_ROOT, "examproctor")
        reg.SetValue(key, None, reg.REG_SZ, "URL:Exam Proctoring Protocol")
        reg.SetValueEx(key, "URL Protocol", 0, reg.REG_SZ, "")

        # Create the shell command key
        shell_key = reg.CreateKey(key, r"shell\open\command")
        reg.SetValue(shell_key, None, reg.REG_SZ, command)

        print("✅ Protocol 'examproctor://' registered successfully!")
        print(f"It is now linked to execute: {command}")
    except Exception as e:
        print(f"❌ Error: Failed to register protocol. Please ensure you are running this script as an Administrator.")
        print(f"   Details: {e}")

if __name__ == "__main__":
    register_protocol()