import time
import cv2
import numpy as np
import mediapipe as mp
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from gaze_estimator import GazeEstimator


class EngineThread(QThread):
    """
    Unified background thread for Camera and MediaPipe operations.
    Prevents thread deadlocks common to creating OpenCV and FaceLandmarker
    across multiple threads.
    """
    MODE_IDLE = 0
    MODE_PREVIEW = 1
    MODE_CALIBRATE = 2
    MODE_TRACK = 3

    # Signals
    camera_ok = Signal(bool)
    frame_ready = Signal(QImage)
    calibration_sample = Signal(object) # median tuple or None
    gaze_point = Signal(float, float, bool) # norm_x, norm_y, is_blinking
    no_face = Signal()
    engine_ready = Signal()

    def __init__(self):
        super().__init__()
        self.mode = self.MODE_IDLE
        self._running = False
        self.gaze_model = None
        self.cap = None

        # Calibration state
        self._collecting = False
        self._collect_start = 0
        self._samples = []
        self._sample_duration = 2.0
        
        # Screen size for normalization
        self.screen_w = 1920
        self.screen_h = 1080

    def start_preview(self):
        self.mode = self.MODE_PREVIEW

    def start_calibration(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.mode = self.MODE_CALIBRATE

    def start_collecting_sample(self, duration=2.0):
        self._collecting = True
        self._samples = []
        self._sample_duration = duration
        self._collect_start = time.time()

    def set_calibrated_points(self, calib_points, screen_points):
        if self.gaze_model:
            self.gaze_model.calibrate(calib_points, screen_points)

    def start_tracking(self):
        self.mode = self.MODE_TRACK

    def go_idle(self):
        """Switch to idle mode (stops processing but keeps thread alive)."""
        self.mode = self.MODE_IDLE

    def release_camera(self):
        """Release the camera hardware while keeping the thread alive."""
        self.mode = self.MODE_IDLE
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def stop(self):
        self._running = False
        self.wait(3000)

    def run(self):
        self._running = True
        
        # 1. Initialize Thread-Safe Resources
        self.gaze_model = GazeEstimator()
        self.engine_ready.emit()

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.camera_ok.emit(False)
            return
            
        self.camera_ok.emit(True)

        try:
            while self._running:
                if self.mode == self.MODE_IDLE:
                    self.msleep(50)
                    continue

                # If camera was released, skip
                if self.cap is None or not self.cap.isOpened():
                    self.msleep(50)
                    continue

                ok, frame = self.cap.read()
                if not ok:
                    self.msleep(16)
                    continue

                frame = cv2.flip(frame, 1)

                if self.mode == self.MODE_PREVIEW:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb.shape
                    img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                    self.frame_ready.emit(img.copy())
                    self.msleep(33)

                elif self.mode == self.MODE_CALIBRATE:
                    if self._collecting:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                        result = self.gaze_model.face_landmarker.detect(mp_image)
                        if result.face_landmarks:
                            landmarks = np.array([(lm.x, lm.y) for lm in result.face_landmarks[0]])
                            gaze_pt = self.gaze_model.get_gaze_point(landmarks)
                            self._samples.append(gaze_pt)
                        
                        if time.time() - self._collect_start >= self._sample_duration:
                            self._collecting = False
                            if self._samples:
                                median_pt = np.median(self._samples, axis=0)
                                self.calibration_sample.emit(median_pt)
                            else:
                                self.calibration_sample.emit(None)
                    else:
                        pass # waiting for signal to collect
                    self.msleep(16)

                elif self.mode == self.MODE_TRACK:
                    # Single MediaPipe pass for both gaze + blink
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    result = self.gaze_model.face_landmarker.detect(mp_image)

                    if not result.face_landmarks:
                        self.no_face.emit()
                    else:
                        landmarks = np.array([(lm.x, lm.y) for lm in result.face_landmarks[0]])
                        is_blinking = bool(self.gaze_model.detect_blink(landmarks))

                        if is_blinking and self.gaze_model.last_valid_gaze is not None:
                            # During blink, hold last known position
                            norm_x = float(self.gaze_model.last_valid_gaze[0])
                            norm_y = float(self.gaze_model.last_valid_gaze[1])
                        elif not is_blinking and self.gaze_model.is_calibrated:
                            gaze_point = self.gaze_model.get_gaze_point(landmarks)
                            try:
                                cam_pt = np.array([[[gaze_point[0], gaze_point[1]]]], dtype=np.float32)
                                transformed = cv2.perspectiveTransform(cam_pt, self.gaze_model.transform)
                                raw_x, raw_y = transformed[0, 0]

                                current_pos = np.array([raw_x, raw_y])
                                sf = self.gaze_model._apply_velocity_smoothing(current_pos)
                                self.gaze_model.last_raw_position = current_pos.copy()

                                self.gaze_model.gaze_history.append((raw_x, raw_y))
                                if len(self.gaze_model.gaze_history) >= 3:
                                    weights = np.exp(np.linspace(-1.0, 0, len(self.gaze_model.gaze_history)))
                                    weights /= weights.sum()
                                    point = np.average(self.gaze_model.gaze_history, weights=weights, axis=0)
                                else:
                                    point = np.array([raw_x, raw_y])

                                if self.gaze_model.last_position is not None:
                                    diff = point - self.gaze_model.last_position
                                    mag = np.linalg.norm(diff)
                                    if mag < self.gaze_model.movement_threshold:
                                        point = self.gaze_model.last_position + diff * 0.1
                                    elif mag < self.gaze_model.movement_threshold * 3:
                                        point = self.gaze_model.last_position + diff * self.gaze_model.dampening
                                    else:
                                        point = self.gaze_model.last_position + diff * (self.gaze_model.dampening + 0.2)

                                self.gaze_model.last_position = point.copy()
                                self.gaze_model.last_valid_gaze = point.copy()
                                norm_x = float(point[0])
                                norm_y = float(point[1])
                            except Exception:
                                self.no_face.emit()
                                self.msleep(10)
                                continue
                        else:
                            self.no_face.emit()
                            self.msleep(10)
                            continue

                        self.gaze_point.emit(float(norm_x), float(norm_y), bool(is_blinking))
                    self.msleep(10)
        finally:
            if self.cap:
                self.cap.release()
            # Clean up mediapipe resources inside this thread
            if self.gaze_model and hasattr(self.gaze_model, 'face_landmarker'):
                self.gaze_model.face_landmarker.close()
