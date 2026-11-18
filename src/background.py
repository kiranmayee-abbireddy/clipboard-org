# src/background.py
import sys
import os
import winreg
import logging

APP_REG_NAME = "ClipBox"

def set_windows_autostart(enabled: bool = True) -> bool:
    """
    Enable or disable user-level Windows auto-start on logon via HKCU Run registry.
    Requires NO administrator privileges.
    """
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            # If frozen executable, use executable path
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}"'
            else:
                main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
                pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
                cmd = f'"{pythonw_exe}" "{main_py}"'
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            logging.info(f"Enabled autostart: {cmd}")
        else:
            try:
                winreg.DeleteValue(key, APP_REG_NAME)
                logging.info("Disabled autostart")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logging.error(f"Failed to configure autostart: {e}")
        return False

def is_windows_autostart_enabled() -> bool:
    """Check if ClipBox is currently registered to auto-start in HKCU Run"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        _, _ = winreg.QueryValueEx(key, APP_REG_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

# Backward compatibility alias
def create_startup_task():
    return set_windows_autostart(True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--disable":
        set_windows_autostart(False)
        print("Auto-start disabled.")
    else:
        set_windows_autostart(True)
        print("Auto-start enabled (user registry).")
