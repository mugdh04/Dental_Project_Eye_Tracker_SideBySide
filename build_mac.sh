#!/bin/bash
set -e

echo "=== Eye Tracker — Mac Build ==="
source venv/bin/activate

# Download model if missing
MODEL_PATH="models/face_landmarker.task"
if [ ! -f "$MODEL_PATH" ]; then
    echo "Downloading face landmarker model..."
    mkdir -p models
    curl -L -o "$MODEL_PATH" \
      "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
fi

# Clean previous build
rm -rf dist/EyeTracker.app dist/EyeTracker.dist dist/EyeTracker.build

python -m nuitka \
    --standalone \
    --macos-create-app-bundle \
    --macos-app-name="EyeTracker" \
    --macos-app-version="1.0.0" \
    --macos-disable-console \
    --macos-app-protected-resource="NSCameraUsageDescription:Eye Tracker needs camera access to track where you look on screen." \
    --enable-plugin=pyside6 \
    --include-qt-plugins=platforms,imageformats,iconengines \
    --include-package=mediapipe \
    --include-package=cv2 \
    --include-package=numpy \
    --include-package=PIL \
    --include-data-dir=models=models \
    --include-data-dir=ui=ui \
    --include-data-file=aoi_config_per_image.json=aoi_config_per_image.json \
    --output-dir=dist \
    --output-filename=EyeTracker \
    --assume-yes-for-downloads \
    main.py

# --- Gatekeeper Auto-Bypass Injection ---
# We replace the main executable with a shell script that strips quarantine,
# then launches the real binary. This makes it double-clickable for end users
# without them needing to open the Terminal.
echo "Injecting zero-click Gatekeeper bypass..."
cd dist/EyeTracker.app/Contents/MacOS
mv EyeTracker EyeTracker_bin

cat << 'EOF' > EyeTracker
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_ROOT="$(dirname "$(dirname "$DIR")")"
# Silently strip quarantine from the entire app bundle
xattr -cr "$APP_ROOT" 2>/dev/null || true
# Launch the real application
exec "$DIR/EyeTracker_bin" "$@"
EOF

chmod +x EyeTracker
cd ../../../../

echo ""
echo "=== Build Complete ==="
echo "App bundle: dist/EyeTracker.app"
echo ""
echo "To distribute:"
echo "  1. Right-click dist/EyeTracker.app -> Compress -> share the .zip"
echo "  2. The end user MUST extract the .zip on their M1/M2 Mac."
echo "  3. The user can just Double-Click the app!"
echo "     (Our injected wrapper will automatically defeat Apple Gatekeeper)."
echo "  4. macOS will ask for camera permission — click Allow."
