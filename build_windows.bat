@echo off
setlocal

echo === Eye Tracker - Windows Build ===

call venv\Scripts\activate.bat

SET MODEL_PATH=models\face_landmarker.task
if not exist "%MODEL_PATH%" (
    echo Downloading face landmarker model...
    mkdir models 2>nul
    curl -L -o "%MODEL_PATH%" "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

if exist dist\EyeTracker.exe del /f /q dist\EyeTracker.exe
if exist dist\EyeTracker.dist rmdir /s /q dist\EyeTracker.dist

python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --enable-plugin=pyside6 ^
    --include-qt-plugins=platforms,imageformats,iconengines ^
    --include-package=mediapipe ^
    --include-package=cv2 ^
    --include-package=numpy ^
    --include-package=PIL ^
    --include-data-dir=models=models ^
    --include-data-dir=ui=ui ^
    --include-data-file=aoi_config_per_image.json=aoi_config_per_image.json ^
    --output-dir=dist ^
    --output-filename=EyeTracker ^
    --assume-yes-for-downloads ^
    main.py

echo.
echo === Build Complete ===
echo Executable: dist\EyeTracker.exe
echo.
echo To distribute:
echo   1. Copy dist\EyeTracker.exe to a folder
echo   2. Create images\pre\ and images\post\ beside the .exe
echo   3. Place PNG images in those folders
echo   4. Double-click EyeTracker.exe
