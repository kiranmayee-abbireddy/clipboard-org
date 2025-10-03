import subprocess
import sys
import os

def create_startup_task():
    task_name = "ClipboardMonitorBackground"
    python_exe = sys.executable
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "clipboard_monitor.py"))
    cmd = f'"{python_exe}" "{script_path}"'
    print(cmd)

    # Create or update the scheduled task to run at user logon
    try:
        subprocess.run([
            "schtasks",
            "/Create",
            "/TN", task_name,
            "/TR", cmd,
            "/SC", "ONLOGON",
            "/RL", "HIGHEST",  # Run with highest privileges
            "/F"  # Force create if exists
        ], check=True)
        print(f"Scheduled task '{task_name}' created or updated.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create scheduled task: {e}")

if __name__ == "__main__":
    create_startup_task()
