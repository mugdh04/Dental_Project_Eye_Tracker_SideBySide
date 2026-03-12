"""
Build script for Eye Tracker executable.
Downloads required models and creates a standalone EXE using PyInstaller.
"""
import os
import sys
import subprocess
import shutil
import urllib.request

def download_model():
    """Download the face landmarker model if not present"""
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    model_path = os.path.join(model_dir, 'face_landmarker.task')

    if os.path.exists(model_path):
        print(f"Model already exists at {model_path}")
        return model_path

    os.makedirs(model_dir, exist_ok=True)
    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

    print(f"Downloading face landmarker model...")
    urllib.request.urlretrieve(url, model_path)
    print(f"Model downloaded to {model_path}")
    return model_path

def clean_build():
    """Clean previous build artifacts"""
    for folder in ['build', 'dist']:
        path = os.path.join(os.path.dirname(__file__), folder)
        if os.path.exists(path):
            print(f"Cleaning {path}...")
            shutil.rmtree(path)

def build():
    """Build the executable"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Install dependencies
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

    # Download model
    print("\nDownloading model...")
    download_model()

    # Clean previous builds
    print("\nCleaning previous builds...")
    clean_build()

    # Build with PyInstaller
    print("\nBuilding executable...")
    spec_path = os.path.join(script_dir, 'eye_tracker.spec')

    if os.path.exists(spec_path):
        subprocess.check_call([sys.executable, '-m', 'PyInstaller', spec_path, '--noconfirm'])
    else:
        print("Error: eye_tracker.spec not found!")
        sys.exit(1)

    # Copy additional files to dist
    dist_dir = os.path.join(script_dir, 'dist')
    if os.path.exists(dist_dir):
        # Copy models directory
        models_src = os.path.join(script_dir, 'models')
        models_dst = os.path.join(dist_dir, 'models')
        if os.path.exists(models_src) and not os.path.exists(models_dst):
            shutil.copytree(models_src, models_dst)
            print(f"Copied models to {models_dst}")

        # Copy images directory
        images_src = os.path.join(script_dir, 'images')
        images_dst = os.path.join(dist_dir, 'images')
        if os.path.exists(images_src) and not os.path.exists(images_dst):
            shutil.copytree(images_src, images_dst)
            print(f"Copied images to {images_dst}")

        # Copy AOI configs
        for config in ['aoi_config_per_image.json', 'aoi_config.json']:
            src = os.path.join(script_dir, config)
            dst = os.path.join(dist_dir, config)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"Copied {config} to dist")

    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print(f"Executable: {os.path.join(dist_dir, 'EyeTracker.exe')}")
    print("=" * 60)

if __name__ == '__main__':
    build()
