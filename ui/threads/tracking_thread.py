import cv2
from PySide6.QtCore import QThread, Signal


class TrackingThread(QThread):
    """Core gaze tracking loop — emits gaze coordinates and blink state."""
    gaze_updated = Signal(float, float, bool)   # norm_x, norm_y, is_blinking
    no_face = Signal()

    def __init__(self, gaze_model):
        super().__init__()
        self._running = False
        self.gaze_model = gaze_model

    def run(self):
        self._running = True
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return
        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    self.msleep(10)
                    continue
                frame = cv2.flip(frame, 1)
                norm_x, norm_y = self.gaze_model.predict_from_frame(frame, 1.0, 1.0)
                if norm_x is None:
                    self.no_face.emit()
                    self.msleep(10)
                    continue
                blink_ratio = self.gaze_model.get_blink_ratio(frame)
                is_blinking = blink_ratio < 0.18
                self.gaze_updated.emit(float(norm_x), float(norm_y), is_blinking)
                self.msleep(10)
        finally:
            cap.release()

    def stop(self):
        self._running = False
        self.wait()
