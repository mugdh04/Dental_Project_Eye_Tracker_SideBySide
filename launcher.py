"""
Eye Tracker Launcher
This script launches the Flask app and opens the browser automatically.
"""
import os
import sys
import time
import threading
import webbrowser
import socket

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_base_path():
    """Get the base path for data files (logs, images, etc.)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port=8001, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    return start_port

def open_browser(port):
    """Open browser after a short delay to allow server to start"""
    time.sleep(2)
    url = f'http://localhost:{port}'
    print(f"Opening browser at {url}")
    webbrowser.open(url)

def setup_environment():
    """Setup necessary directories and environment"""
    base_path = get_base_path()

    dirs_to_create = [
        os.path.join(base_path, 'images', 'pre'),
        os.path.join(base_path, 'images', 'post'),
        os.path.join(base_path, 'logs'),
        os.path.join(base_path, 'models')
    ]

    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)

    # Copy bundled images if they don't exist in the target location
    bundled_images_pre = resource_path(os.path.join('images', 'pre'))
    bundled_images_post = resource_path(os.path.join('images', 'post'))
    target_images_pre = os.path.join(base_path, 'images', 'pre')
    target_images_post = os.path.join(base_path, 'images', 'post')

    if os.path.exists(bundled_images_pre) and bundled_images_pre != target_images_pre:
        import shutil
        for f in os.listdir(bundled_images_pre):
            src = os.path.join(bundled_images_pre, f)
            dst = os.path.join(target_images_pre, f)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)

    if os.path.exists(bundled_images_post) and bundled_images_post != target_images_post:
        import shutil
        for f in os.listdir(bundled_images_post):
            src = os.path.join(bundled_images_post, f)
            dst = os.path.join(target_images_post, f)
            if not os.path.exists(dst):
                shutil.copy2(src, dst)

    # Copy models if needed
    bundled_model = resource_path(os.path.join('models', 'face_landmarker.task'))
    target_model = os.path.join(base_path, 'models', 'face_landmarker.task')
    if os.path.exists(bundled_model) and not os.path.exists(target_model):
        import shutil
        shutil.copy2(bundled_model, target_model)

    return base_path

def main():
    """Main entry point"""
    print("=" * 60)
    print("       Eye Tracker - Advanced Gaze Analysis System")
    print("=" * 60)
    print()

    # Setup environment
    print("Setting up environment...")
    base_path = setup_environment()
    print(f"Base path: {base_path}")

    # Change to base path for relative imports
    os.chdir(base_path)

    # Find available port
    port = find_available_port(8001)
    print(f"Using port: {port}")

    # Start browser opener in background thread
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()

    # Import and run Flask app
    print("Starting Flask server...")
    print()
    print("=" * 60)
    print(f"  Server running at: http://localhost:{port}")
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    from app import app

    app.run(
        debug=False,
        host='0.0.0.0',
        port=port,
        use_reloader=False,
        threaded=True
    )

if __name__ == '__main__':
    main()