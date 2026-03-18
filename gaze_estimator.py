import os
import sys
import cv2
import numpy as np
from collections import deque
import urllib.request

from core.paths import resource_path, data_path as get_data_path

def download_model_if_needed():
    """Download the face landmarker model if not present"""
    bundled_model = resource_path(os.path.join("models", "face_landmarker.task"))
    data_model_dir = get_data_path("models")
    data_model = os.path.join(data_model_dir, "face_landmarker.task")

    if os.path.exists(bundled_model):
        return bundled_model
    if os.path.exists(data_model):
        return data_model

    os.makedirs(data_model_dir, exist_ok=True)
    print("Downloading face landmarker model...")
    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    try:
        urllib.request.urlretrieve(url, data_model)
        print("Model downloaded successfully!")
        return data_model
    except Exception as e:
        print(f"Failed to download model: {e}")
        return None

# Try to import mediapipe
MEDIAPIPE_AVAILABLE = False
mp = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe import tasks
    MEDIAPIPE_AVAILABLE = True
    USE_TASKS_API = True
    print(f"MediaPipe {mp.__version__} loaded successfully (Tasks API)")
except ImportError as e:
    print(f"Warning: MediaPipe import failed: {e}")
    print("Please install mediapipe: pip install mediapipe>=0.10.14")

class GazeEstimator:
    def __init__(self):
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError(
                "MediaPipe is not available. Please install it with:\n"
                "  pip install mediapipe>=0.10.14"
            )

        model_path = download_model_if_needed()
        if model_path is None:
            raise RuntimeError("Could not download face landmarker model")

        # Initialize Face Landmarker with Tasks API
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.face_landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        # Landmark indices for iris tracking
        self.left_iris_idx = [468, 469, 470, 471, 472]
        self.right_iris_idx = [473, 474, 475, 476, 477]

        # Eye corner landmarks
        self.left_eye_inner = 133
        self.left_eye_outer = 33
        self.right_eye_inner = 362
        self.right_eye_outer = 263

        # Eye landmarks for blink detection
        self.left_eye_top = 159
        self.left_eye_bottom = 145
        self.right_eye_top = 386
        self.right_eye_bottom = 374

        # Gaze tracking variables
        self.gaze_history = deque(maxlen=15)
        self.SMOOTH_FACTOR = 0.15
        self.movement_threshold = 0.003
        self.dampening = 0.6
        self.blink_threshold = 0.18
        self.last_position = None
        self.last_valid_gaze = None
        self.transform = None
        self.is_calibrated = False

        # Velocity-based smoothing
        self.velocity_history = deque(maxlen=5)
        self.last_raw_position = None
        self.head_pose_history = deque(maxlen=10)

    def calibrate(self, calibration_points, screen_points):
        if len(calibration_points) >= 4 and len(screen_points) >= 4:
            src = np.array(calibration_points, dtype=np.float32)
            dst = np.array(screen_points, dtype=np.float32)
            if len(calibration_points) >= 8:
                self.transform, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
            else:
                self.transform, mask = cv2.findHomography(src, dst, 0)
            self.is_calibrated = True
            print(f"Calibration completed with {len(calibration_points)} points")
        else:
            raise ValueError("Calibration requires at least 4 points.")

    def get_gaze_point(self, landmarks):
        """Calculate gaze point using iris positions with improved accuracy"""
        left_iris = np.mean([landmarks[i] for i in self.left_iris_idx], axis=0)
        right_iris = np.mean([landmarks[i] for i in self.right_iris_idx], axis=0)

        left_inner = landmarks[self.left_eye_inner]
        left_outer = landmarks[self.left_eye_outer]
        right_inner = landmarks[self.right_eye_inner]
        right_outer = landmarks[self.right_eye_outer]

        left_eye_width = np.linalg.norm(left_inner - left_outer)
        right_eye_width = np.linalg.norm(right_inner - right_outer)

        if left_eye_width > 0 and right_eye_width > 0:
            gaze_x = (left_iris[0] + right_iris[0]) / 2
            gaze_y = (left_iris[1] + right_iris[1]) / 2
        else:
            gaze_x = (left_iris[0] + right_iris[0]) / 2
            gaze_y = (left_iris[1] + right_iris[1]) / 2

        return np.array([gaze_x, gaze_y])

    def detect_blink(self, landmarks):
        """Improved blink detection using eye aspect ratio"""
        left_top = landmarks[self.left_eye_top]
        left_bottom = landmarks[self.left_eye_bottom]
        left_inner = landmarks[self.left_eye_inner]
        left_outer = landmarks[self.left_eye_outer]

        left_height = np.linalg.norm(left_top - left_bottom)
        left_width = np.linalg.norm(left_inner - left_outer)
        left_ratio = left_height / (left_width + 1e-6)

        right_top = landmarks[self.right_eye_top]
        right_bottom = landmarks[self.right_eye_bottom]
        right_inner = landmarks[self.right_eye_inner]
        right_outer = landmarks[self.right_eye_outer]

        right_height = np.linalg.norm(right_top - right_bottom)
        right_width = np.linalg.norm(right_inner - right_outer)
        right_ratio = right_height / (right_width + 1e-6)

        avg_ratio = (left_ratio + right_ratio) / 2
        return bool(avg_ratio < self.blink_threshold)

    def _apply_velocity_smoothing(self, current_pos):
        """Apply velocity-based smoothing for more natural movement"""
        if self.last_raw_position is not None:
            velocity = current_pos - self.last_raw_position
            self.velocity_history.append(velocity)

            if len(self.velocity_history) >= 3:
                avg_velocity = np.mean(self.velocity_history, axis=0)
                velocity_magnitude = np.linalg.norm(avg_velocity)

                if velocity_magnitude < 0.002:
                    smooth_factor = 0.1
                elif velocity_magnitude > 0.02:
                    smooth_factor = 0.4
                else:
                    smooth_factor = 0.2

                return smooth_factor

        return self.SMOOTH_FACTOR

    def predict_from_frame(self, frame, screen_w, screen_h):
        """Process frame and predict gaze position"""
        if not self.is_calibrated:
            return None, None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self.face_landmarker.detect(mp_image)

        if not result.face_landmarks or len(result.face_landmarks) == 0:
            return None, None

        face_landmarks = result.face_landmarks[0]
        landmarks = np.array([(lm.x, lm.y) for lm in face_landmarks])

        if self.detect_blink(landmarks):
            if self.last_valid_gaze is not None:
                return self.last_valid_gaze[0], self.last_valid_gaze[1]
            return None, None

        gaze_point = self.get_gaze_point(landmarks)

        try:
            cam_point = np.array([[[gaze_point[0], gaze_point[1]]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(cam_point, self.transform)
            x, y = transformed[0, 0]

            current_pos = np.array([x, y])
            smooth_factor = self._apply_velocity_smoothing(current_pos)
            self.last_raw_position = current_pos.copy()

            self.gaze_history.append((x, y))
            if len(self.gaze_history) >= 3:
                weights = np.exp(np.linspace(-1.0, 0, len(self.gaze_history)))
                weights /= weights.sum()
                point = np.average(self.gaze_history, weights=weights, axis=0)
            else:
                point = np.array([x, y])

            if self.last_position is not None:
                diff = point - self.last_position
                diff_magnitude = np.linalg.norm(diff)

                if diff_magnitude < self.movement_threshold:
                    point = self.last_position + diff * 0.1
                elif diff_magnitude < self.movement_threshold * 3:
                    point = self.last_position + diff * self.dampening
                else:
                    point = self.last_position + diff * (self.dampening + 0.2)

            self.last_position = point.copy()
            self.last_valid_gaze = point.copy()

            return float(point[0]), float(point[1])

        except Exception as e:
            print(f"Transform error: {e}")
            return None, None

    def get_blink_ratio(self, frame):
        """Get current blink ratio for external use"""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self.face_landmarker.detect(mp_image)

        if not result.face_landmarks or len(result.face_landmarks) == 0:
            return 1.0

        face_landmarks = result.face_landmarks[0]
        landmarks = np.array([(lm.x, lm.y) for lm in face_landmarks])

        left_top = landmarks[self.left_eye_top]
        left_bottom = landmarks[self.left_eye_bottom]
        left_inner = landmarks[self.left_eye_inner]
        left_outer = landmarks[self.left_eye_outer]

        left_height = np.linalg.norm(left_top - left_bottom)
        left_width = np.linalg.norm(left_inner - left_outer)

        right_top = landmarks[self.right_eye_top]
        right_bottom = landmarks[self.right_eye_bottom]
        right_inner = landmarks[self.right_eye_inner]
        right_outer = landmarks[self.right_eye_outer]

        right_height = np.linalg.norm(right_top - right_bottom)
        right_width = np.linalg.norm(right_inner - right_outer)

        left_ratio = left_height / (left_width + 1e-6)
        right_ratio = right_height / (right_width + 1e-6)

        return (left_ratio + right_ratio) / 2

    def close(self):
        """Clean up resources"""
        if hasattr(self, 'face_landmarker'):
            self.face_landmarker.close()