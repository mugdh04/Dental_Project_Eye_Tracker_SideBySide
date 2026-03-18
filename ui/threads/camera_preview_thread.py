from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import cv2


class CameraPreviewThread(QThread):
    """Captures webcam frames and emits them as QImage for UI display."""
    frame_ready = Signal(QImage)
    camera_ok = Signal(bool)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self._running = False
        self.camera_index = camera_index

    def run(self):
        self._running = True
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.camera_ok.emit(False)
            return
        self.camera_ok.emit(True)
        try:
            while self._running:
                ok, frame = cap.read()
                if ok:
                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb.shape
                    img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                    self.frame_ready.emit(img.copy())
                self.msleep(33)  # ~30 fps
        finally:
            cap.release()

    def stop(self):
        self._running = False
        self.wait()
