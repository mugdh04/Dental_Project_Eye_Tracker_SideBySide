# Eye Tracker - Advanced Gaze Analysis System

A comprehensive eye tracking application that uses MediaPipe's face landmarker to track user gaze across calibrated screen regions and analyze fixation patterns on Areas of Interest (AOIs).

## Features

✅ **Real-time Gaze Tracking** — Tracks user's gaze point with smooth, calibrated output  
✅ **Side-by-Side Image Comparison** — Pre and post treatment images displayed simultaneously  
✅ **5 Customizable AOIs** — Forehead, Eyes, Nose, Mouth, Chin with per-image configuration  
✅ **Comprehensive Data Logging** — First fixation time, total fixation duration, blink counts per AOI  
✅ **Automatic Calibration** — 12-point calibration for accurate screen-to-gaze mapping  
✅ **Web Interface** — Easy-to-use Flask-based dashboard for session management  
✅ **Flexible Pointer Display** — Toggle gaze pointer visibility to reduce distraction  
✅ **5-Second Buffer** — Black screen between image sets to maintain calibration  
✅ **EXE Executable** — Build standalone Windows executable for non-technical users  

---

## Quick Start

### Option 1: Run with Python (Development/Testing)

#### Prerequisites
- **Python 3.10+** installed on your system
- **Camera** connected and accessible
- **Pre/Post Images** in `images/pre/` and `images/post/` folders

#### Installation Steps

1. **Navigate to the project directory:**
   ```bash
   cd E:\Eye_Tracker_Code - Copy
   ```

2. **Set up virtual environment (if not already done):**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt):**
     ```cmd
     .\venv\Scripts\activate.bat
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Flask web interface:**
   ```bash
   python app.py
   ```
   The Flask server will start at `http://localhost:8001`

6. **Open in your browser:**
   - Navigate to `http://localhost:8001`
   - Follow the pre-flight check
   - Configure session settings and pointer visibility
   - Click **"Start Eye Tracking"** to begin

---

### Option 2: Run EXE (Recommended for End Users)

The EXE file is a standalone executable that does **not require Python** to be installed.

#### Prerequisites
- **Windows 10/11** (64-bit recommended)
- **Camera** connected and accessible
- **Pre/Post Images** in correct folder structure

#### How to Build the EXE

1. **From Python environment, run the build script:**
   ```bash
   python build_exe.py
   ```
   
   Or use the batch file:
   ```bash
   build.bat
   ```

2. **Wait for build completion** (~2-5 minutes)

3. **Find the EXE file:**
   - Location: `dist/eye_tracker.exe`

#### How to Use the EXE

1. **Organize your images:**
   - Create `images/pre/` and `images/post/` folders **in the same directory as `eye_tracker.exe`**
   - Place image pairs with matching IDs (e.g., `1.png`, `2.png`, etc.)

   Directory structure:
   ```
   dist/
   ├── eye_tracker.exe
   ├── aoi_config_per_image.json
   ├── images/
   │   ├── pre/
   │   │   ├── 1.png
   │   │   ├── 2.png
   │   │   └── ...
   │   └── post/
   │       ├── 1.png
   │       ├── 2.png
   │       └── ...
   └── logs/
   ```

2. **Run the EXE:**
   - Double-click `eye_tracker.exe`
   - Flask server starts automatically
   - Browser opens automatically to `http://localhost:8001`

3. **Follow the on-screen workflow:**
   - **Pre-Flight Check** — Verify camera and images are ready
   - **Configure Settings** — Enter group (e.g., "orthodontist", "layperson") and session name
   - **Pointer Visibility Toggle** — Turn on to see gaze pointer, off to hide (default)
   - **Calibration** — Follow the green dots on screen
   - **Tracking** — View pre/post images side-by-side, data automatically logged
   - **Results** — View results in web dashboard, download CSV

---

## Workflow

### 1. Pre-Flight Check
- **Camera Status** — Verifies camera is accessible and shows live preview
- **Image Sets** — Checks that pre and post image directories have matching pairs
- **Model Status** — Face landmarker model will auto-download if needed

### 2. Calibration
- **12-Point Grid** — Green calibration dots appear across the screen
- **Duration** — ~2 seconds per point, ~24 seconds total
- **What to do** — Look directly at each dot; the system records your gaze

### 3. Tracking Session
- **Side-by-Side Display** — Pre image on left, post image on right
- **Gaze Pointer** — Optional gray circle shows where you're looking (if enabled)
- **Duration** — 30 seconds per image set, 5-second black screen buffer between sets
- **Data Logged** — First fixation time, total fixation time, blink count per AOI

### 4. Results
- **Per-Image Summary** — Pre and post results shown side-by-side in web dashboard
- **CSV Export** — Download full dataset for external analysis
- **Metrics** — Total blinks, blink rate (blinks/minute)

---

## AOI Configuration

AOIs (Areas of Interest) are defined per image in `aoi_config_per_image.json`:

```json
{
  "1": {
    "pre": {
      "forehead": [[0.10, 0.00], [0.90, 0.22]],
      "eyes":     [[0.06, 0.22], [0.94, 0.40]],
      "nose":     [[0.30, 0.40], [0.70, 0.52]],
      "mouth":    [[0.15, 0.52], [0.85, 0.73]],
      "chin":     [[0.20, 0.73], [0.80, 0.98]]
    },
    "post": { ... }
  }
}
```

**Coordinates:** Normalized 0–1 range where:
- `[x_min, y_min]` — Top-left corner
- `[x_max, y_max]` — Bottom-right corner
- (0, 0) is top-left of image, (1, 1) is bottom-right

**To customize:**
1. Open `aoi_config_per_image.json`
2. Adjust coordinates for each AOI and image number
3. Restart the application

---

## Session Settings

### Group
- Standard values: `orthodontist`, `dentist`, `layperson`, `specialist`
- Custom values accepted (used for result file naming)
- Example: `orthodontist_group_1`

### Session Name
- Descriptive label for the tracking session
- Example: `smile_treatment_precheck`
- Used in result filenames and data organization

### Pointer Visibility
- **OFF (Default)** — Gaze pointer is invisible but tracking continues
- **ON** — Gaze pointer visible on screen (may distract some users)
- Useful for validation and debugging when ON

---

## Output Files

### Results CSV
**Location:** `logs/{group}_{session}_{timestamp}.csv`

**Format (Side-by-Side):**
```
Session - 1.png:
Pre Treatment Image Report:,,,,,Post Treatment Image Report:
AOI,First Fixation (s),Total Fixation (s),Blinks,,AOI,First Fixation (s),Total Fixation (s),Blinks
chin,0.0,0.3,0,,chin,0.5,1.2,0
eyes,2.1,5.4,2,,eyes,0.0,0.0,0
forehead,0.0,0.0,0,,forehead,0.0,0.0,0
mouth,1.8,8.2,1,,mouth,3.2,12.1,2
nose,2.5,6.1,0,,nose,0.0,0.0,0

First Focused AOI,chin,,,,First Focused AOI,mouth
Most Focused AOI,mouth,,,,Most Focused AOI,mouth
```

**Columns:**
- **First Fixation (s)** — Time until user first looked at AOI
- **Total Fixation (s)** — Total time spent looking at AOI
- **Blinks** — Number of blinks detected while in AOI

**Summary Section:**
- **Total Blinks** — Across all AOIs and images
- **Blink Rate** — Blinks per minute

---

## System Requirements

### Minimum
- **OS:** Windows 10/11 (64-bit)
- **RAM:** 4 GB
- **CPU:** Dual-core 2.0 GHz
- **Camera:** 720p minimum, USB 2.0+
- **Display:** 1280x720 minimum

### Recommended
- **OS:** Windows 10/11 (64-bit)
- **RAM:** 8 GB
- **CPU:** Quad-core 2.5 GHz
- **Camera:** 1080p, USB 3.0+
- **Display:** 1920x1080 or higher

### Network (for Python version)
- Must be on same machine or accessible via network (for Flask)

---

## Troubleshooting

### Issue: Camera Not Detected
**Solution:**
1. Check device manager — camera should appear under "Cameras"
2. Ensure no other application is using the camera
3. Try different USB port
4. Restart the application

### Issue: No Image Sets Found
**Solution:**
1. Verify image folder structure:
   ```
   images/
   ├── pre/
   │   ├── 1.png
   │   ├── 2.png
   │   └── ...
   └── post/
       ├── 1.png
       ├── 2.png
       └── ...
   ```
2. Ensure pre and post folders have matching image IDs
3. Image format must be PNG

### Issue: Model Download Fails
**Solution:**
1. Check internet connection
2. Model will auto-download on first run (requires ~200 MB)
3. If using EXE, model should be bundled; if not, manually download from:
   ```
   https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
   ```
   Place in `models/` folder

### Issue: Calibration Failing
**Solution:**
1. Ensure good lighting on your face
2. Keep head still during calibration
3. Avoid glasses glare or reflections
4. Sit at normal distance (50-70 cm from screen)

### Issue: Gaze Pointer Not Visible
**Solution:**
1. Check if "Show Pointer" toggle is ON in pre-flight check
2. If OFF by design, pointer still works in background; results are unaffected

### Issue: Flask Server Won't Start
**Solution:**
1. Check if port 8001 is already in use:
   ```bash
   netstat -ano | findstr :8001
   ```
2. Kill the process using that port:
   ```bash
   taskkill /PID [PID_NUMBER] /F
   ```
3. Try a different port by editing `app.py` line 284: `app.run(..., port=8002)`

---

## Development

### Project Structure
```
Eye_Tracker_Code - Copy/
├── app.py                      # Flask web application
├── main.py                     # Core eye tracker logic
├── gaze_estimator.py          # MediaPipe face detection & gaze calculation
├── logger.py                  # Data logging and CSV export
├── launcher.py                # Startup script
├── requirements.txt           # Python dependencies
├── build_exe.py               # EXE build script
├── aoi_config_per_image.json  # AOI definitions
├── templates/                 # HTML templates
│   ├── index.html
│   ├── pre_flight_check.html
│   ├── results.html
│   └── view_images.html
├── static/
│   └── css/
│       └── style.css          # Styling
├── models/                    # MediaPipe models
│   └── face_landmarker.task
└── images/
    ├── pre/                   # Pre-treatment images
    └── post/                  # Post-treatment images
```

### Key Dependencies
- **Flask** — Web framework
- **MediaPipe** — Face detection and gaze estimation
- **OpenCV** — Camera and image processing
- **NumPy** — Numerical computations
- **Pillow** — Image handling

---

## Keyboard Shortcuts

During tracking:
- **Ctrl+Q** — Exit current session early

---

## Data Privacy

- All data is stored **locally** on your computer
- No data is transmitted to external servers
- CSV files can be deleted after analysis
- Camera feed is processed in real-time but not recorded

---

## Support & Issues

For bugs or feature requests:
1. Check troubleshooting section above
2. Verify all prerequisites are met
3. Check system requirements

---

## License

Advanced Gaze Analysis System © 2025

---

## About

Eye Tracker is built using:
- **MediaPipe** — Google's cross-platform framework for ML models for perception
- **Flask** — Python web framework
- **OpenCV** — Computer vision library

---

## Quick Reference

### Run with Python
```bash
# Activate environment
.\venv\Scripts\activate.bat

# Install dependencies (first time only)
pip install -r requirements.txt

# Run Flask server
python app.py

# Visit http://localhost:8001
```

### Build and Run EXE
```bash
# Build EXE (first time only)
python build_exe.py

# Double-click dist/eye_tracker.exe
# Browser opens automatically to http://localhost:8001
```

### Next Steps
1. Prepare your images in `images/pre/` and `images/post/`
2. Customize AOIs in `aoi_config_per_image.json` if needed
3. Run the application
4. Follow the pre-flight check
5. Start tracking
6. Download results when complete
