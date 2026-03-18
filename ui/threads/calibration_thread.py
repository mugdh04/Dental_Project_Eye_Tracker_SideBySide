import time
import cv2
import numpy as np
import mediapipe as mp_lib
from PySide6.QtCore import QThread, Signal


class CalibrationThread(QThread):
    """Samples gaze landmarks at each calibration point and emits the median."""
    sample_collected = Signal(object)   # emits np.array median gaze point
    frame_ready = Signal(object)        # emits raw BGR frame (optional debug)

    def __init__(self, gaze_model, sample_duration: float = 2.0):
        super().__init__()
        self._running = False
        self._collect = False
        self.gaze_model = gaze_model
        self.sample_duration = sample_duration
        self.cap = None
        self._samples = []
        self._collect_start = None

    def open_camera(self):
        self.cap = cv2.VideoCapture(0)

    def start_collecting(self):
        """Call from main thread when a new calibration dot is shown."""
        self._collect = True
        self._samples = []
        self._collect_start = None

    def run(self):
        self._running = True
        if self.cap is None:
            self.open_camera()
        
        try:
            while self._running:
                if self.cap and self.cap.isOpened():
                    ok, frame = self.cap.read()
                    if ok:
                        frame = cv2.flip(frame, 1)
                        if self._collect:
                            if self._collect_start is None:
                                self._collect_start = time.time()
                            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            mp_image = mp_lib.Image(
                                image_format=mp_lib.ImageFormat.SRGB, data=rgb
                            )
                            result = self.gaze_model.face_landmarker.detect(mp_image)
                            if result.face_landmarks:
                                landmarks = np.array(
                                    [(lm.x, lm.y) for lm in result.face_landmarks[0]]
                                )
                                gaze_pt = self.gaze_model.get_gaze_point(landmarks)
                                self._samples.append(gaze_pt)
                            if time.time() - self._collect_start >= self.sample_duration:
                                self._collect = False
                                if self._samples:
                                    median_pt = np.median(self._samples, axis=0)
                                    self.sample_collected.emit(median_pt)
                                else:
                                    # No samples — emit None so calibration can handle it
                                    self.sample_collected.emit(None)
                self.msleep(16)  # ~60 fps capture
        finally:
            if self.cap:
                self.cap.release()
                self.cap = None

    def stop(self):
        self._running = False
        self.wait()
