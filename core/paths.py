import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Path to a BUNDLED read-only resource embedded inside the app.
    In dev: relative to project root.
    In Nuitka .app/.exe: inside the bundle's internal data dir.
    In PyInstaller: inside _MEIPASS temp dir.
    """
    if getattr(sys, 'frozen', False):
        # Nuitka bundles data files relative to the executable
        base = os.path.dirname(sys.executable)
    elif hasattr(sys, '_MEIPASS'):
        # PyInstaller fallback (Windows only)
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def data_path(relative_path: str) -> str:
    """
    Path to WRITABLE user data (logs, user images, user-edited configs).
    In dev: relative to project root.
    In Nuitka .app (Mac): ~/Library/Application Support/EyeTracker/
    In Nuitka .exe (Win): same directory as the .exe file.
    """
    if getattr(sys, 'frozen', False):
        import platform
        if platform.system() == 'Darwin':
            base = os.path.expanduser('~/Library/Application Support/EyeTracker')
        else:
            base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full = os.path.join(base, relative_path)
    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return full


def ensure_data_dirs():
    """Create all required writable directories if missing."""
    for d in ['images/pre', 'images/post', 'logs', 'models']:
        os.makedirs(data_path(d), exist_ok=True)
