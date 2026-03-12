import cv2
import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageTk
import time
import json
import threading
import keyboard
import numpy as np
import os
import sys
from gaze_estimator import GazeEstimator
from logger import AOILogger

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_data_path(relative_path):
    """Get path for data files that should be in the executable's directory"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class EyeTrackerApp:
    def __init__(self, output_folder="logs", image_folder="images", show_csv=False):
        self.bg_color = "#000000"

        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.getcwd()

        self.output_folder = os.path.join(self.base_path, output_folder)
        self.image_folder = os.path.join(self.base_path, image_folder)
        self.show_csv = show_csv

        os.makedirs(self.output_folder, exist_ok=True)

        self.root = tk.Tk()
        self.root.title("Eye Tracker")
        self.root.geometry("400x220")
        self.root.configure(bg=self.bg_color)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.update()

        # Read session config
        self.show_pointer = False  # Default: pointer hidden
        config_path = os.path.join(self.base_path, 'session_config.txt')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    lines = f.readlines()
                    self.group = lines[0].strip() if len(lines) > 0 else "unknown"
                    self.session = lines[1].strip() if len(lines) > 1 else "session"
                    self.show_pointer = lines[2].strip() == '1' if len(lines) > 2 else False
                os.remove(config_path)
            except Exception:
                self.group = simpledialog.askstring("Group", "Enter group (eg. orthodontist/dentist/layperson):",
                                                   parent=self.root) or "unknown"
                self.session = simpledialog.askstring("Session Name", "Enter session name:",
                                                    parent=self.root) or "session"
        else:
            self.group = simpledialog.askstring("Group", "Enter group (eg. child/adult/specialist):",
                                               parent=self.root) or "unknown"
            self.session = simpledialog.askstring("Session Name", "Enter session name:",
                                                parent=self.root) or "session"

        self.root.attributes("-topmost", False)
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=self.bg_color)

        self.gaze_model = GazeEstimator()
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.canvas = tk.Canvas(self.root, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.setup_display_regions()

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Could not open camera")
            self.root.destroy()
            return

        self.image_indices = self.get_image_indices()
        if not self.image_indices:
            print("No image pairs found! Exiting...")
            self.root.destroy()
            return

        self.image_index = 0
        self.max_images = len(self.image_indices)
        self.image_change_interval = 30  # seconds per image set
        self.refresh_interval = 5  # 5 second black screen buffer between sets
        self.is_refreshing = False
        self.refresh_start_time = None

        self.pre_image_template = os.path.join(self.image_folder, "pre", "{}.png")
        self.post_image_template = os.path.join(self.image_folder, "post", "{}.png")

        self.calibrate()
        self.load_images()
        self.load_aois()

        # Logger with both pre and post regions for side-by-side display
        self.logger = AOILogger(self.scaled_aois, group=self.group,
                                session_type=self.session, regions=["pre", "post"])
        current_id = self.image_indices[self.image_index]
        self.logger.new_session(
            self.scaled_aois,
            session_name=f"{current_id}.png",
            image_id=current_id
        )

        self.pointer = self.canvas.create_oval(0, 0, 20, 20, fill="LightGrey",
                                                outline="grey", width=2, tags="pointer")
        self.pointer_x = self.screen_width // 2
        self.pointer_y = self.screen_height // 2
        self.update_pointer_position()
        self.canvas.tag_raise("pointer")

        # Hide pointer if user chose to keep it off (default)
        if not self.show_pointer:
            self.canvas.itemconfigure(self.pointer, state='hidden')

        self.last_valid_position = (self.pointer_x, self.pointer_y)
        self.smoothing_factor = 0.25
        self.frame_skip_threshold = 0.03
        self.last_frame_time = time.time()

        # Start timer AFTER calibration + setup so first set gets full viewing time
        self.start_time = time.time()

        threading.Thread(target=self.exit_listener, daemon=True).start()
        self.root.after(1, self.update)
        self.root.mainloop()

    def setup_display_regions(self):
        """Set up two side-by-side display regions for pre (left) and post (right) images"""
        margin_x = 0.04
        margin_top = 0.06
        gap = 0.02
        img_height_ratio = 0.85

        total_img_width = self.screen_width * (1 - 2 * margin_x - gap)
        each_img_width = int(total_img_width / 2)
        img_height = int(self.screen_height * img_height_ratio)

        x_start_left = int(margin_x * self.screen_width)
        y_top = int(margin_top * self.screen_height)

        # Pre image on the left
        self.pre_region = {
            "x_min": x_start_left,
            "x_max": x_start_left + each_img_width,
            "y_min": y_top,
            "y_max": y_top + img_height
        }

        # Post image on the right
        x_start_right = x_start_left + each_img_width + int(gap * self.screen_width)
        self.post_region = {
            "x_min": x_start_right,
            "x_max": x_start_right + each_img_width,
            "y_min": y_top,
            "y_max": y_top + img_height
        }

        # Combined display region for boundary checks
        self.display_region = {
            "x_min": self.pre_region["x_min"],
            "x_max": self.post_region["x_max"],
            "y_min": y_top,
            "y_max": y_top + img_height
        }

        # Calibration points: 4x3 grid across both display regions (12 points)
        x_positions = [
            self.display_region["x_min"],
            self.pre_region["x_max"],
            self.post_region["x_min"],
            self.display_region["x_max"]
        ]
        y_positions = [
            self.display_region["y_min"],
            (self.display_region["y_min"] + self.display_region["y_max"]) // 2,
            self.display_region["y_max"]
        ]

        self.screen_points = []
        for y in y_positions:
            for x in x_positions:
                self.screen_points.append((x, y))

        self.calibration_points = []

    def get_image_indices(self):
        pre_path = os.path.join(self.image_folder, "pre")
        post_path = os.path.join(self.image_folder, "post")
        os.makedirs(pre_path, exist_ok=True)
        os.makedirs(post_path, exist_ok=True)

        pre_images = {f.split('.')[0] for f in os.listdir(pre_path)
                      if f.lower().endswith('.png')}
        post_images = {f.split('.')[0] for f in os.listdir(post_path)
                       if f.lower().endswith('.png')}

        common = sorted(pre_images & post_images, key=lambda x: int(x))
        print(f"Found {len(common)} image sets")
        return common

    def load_images(self):
        """Load both pre and post images side by side"""
        try:
            current_id = self.image_indices[self.image_index]
            pre_path = self.pre_image_template.format(current_id)
            post_path = self.post_image_template.format(current_id)

            # Clear previous images
            if hasattr(self, 'pre_canvas_image'):
                self.canvas.delete(self.pre_canvas_image)
            if hasattr(self, 'post_canvas_image'):
                self.canvas.delete(self.post_canvas_image)

            # Load pre image (left side)
            pre_img = Image.open(pre_path).resize(
                (self.pre_region["x_max"] - self.pre_region["x_min"],
                 self.pre_region["y_max"] - self.pre_region["y_min"]),
                Image.Resampling.LANCZOS
            )
            self.pre_tk_image = ImageTk.PhotoImage(pre_img, master=self.root)
            self.pre_canvas_image = self.canvas.create_image(
                self.pre_region["x_min"], self.pre_region["y_min"],
                anchor=tk.NW, image=self.pre_tk_image
            )

            # Load post image (right side)
            post_img = Image.open(post_path).resize(
                (self.post_region["x_max"] - self.post_region["x_min"],
                 self.post_region["y_max"] - self.post_region["y_min"]),
                Image.Resampling.LANCZOS
            )
            self.post_tk_image = ImageTk.PhotoImage(post_img, master=self.root)
            self.post_canvas_image = self.canvas.create_image(
                self.post_region["x_min"], self.post_region["y_min"],
                anchor=tk.NW, image=self.post_tk_image
            )

            self.canvas.tag_raise("pointer")

        except Exception as e:
            print(f"Error loading images: {e}")

    def load_aois(self):
        """Load AOIs for both pre and post images from per-image config"""
        try:
            aoi_path = resource_path("aoi_config_per_image.json")
            if not os.path.exists(aoi_path):
                aoi_path = get_data_path("aoi_config_per_image.json")

            with open(aoi_path, "r") as f:
                all_aois = json.load(f)

            current_id = self.image_indices[self.image_index]
            img_aois = all_aois.get(str(current_id), {})

            self.scaled_aois = {}

            # Load pre AOIs scaled to the left display region
            pre_dict = img_aois.get("pre", {})
            for name, ((rx1, ry1), (rx2, ry2)) in pre_dict.items():
                x1 = int(self.pre_region["x_min"] + rx1 * (self.pre_region["x_max"] - self.pre_region["x_min"]))
                y1 = int(self.pre_region["y_min"] + ry1 * (self.pre_region["y_max"] - self.pre_region["y_min"]))
                x2 = int(self.pre_region["x_min"] + rx2 * (self.pre_region["x_max"] - self.pre_region["x_min"]))
                y2 = int(self.pre_region["y_min"] + ry2 * (self.pre_region["y_max"] - self.pre_region["y_min"]))
                self.scaled_aois[f"pre_{name}"] = ((x1, y1), (x2, y2))

            # Load post AOIs scaled to the right display region
            post_dict = img_aois.get("post", {})
            for name, ((rx1, ry1), (rx2, ry2)) in post_dict.items():
                x1 = int(self.post_region["x_min"] + rx1 * (self.post_region["x_max"] - self.post_region["x_min"]))
                y1 = int(self.post_region["y_min"] + ry1 * (self.post_region["y_max"] - self.post_region["y_min"]))
                x2 = int(self.post_region["x_min"] + rx2 * (self.post_region["x_max"] - self.post_region["x_min"]))
                y2 = int(self.post_region["y_min"] + ry2 * (self.post_region["y_max"] - self.post_region["y_min"]))
                self.scaled_aois[f"post_{name}"] = ((x1, y1), (x2, y2))

        except Exception as e:
            print(f"Error loading AOIs: {e}")
            self.scaled_aois = {}

    def calibrate(self):
        print("Starting calibration...")
        self.calibration_points = []
        for screen_x, screen_y in self.screen_points:
            target = self.canvas.create_oval(screen_x - 15, screen_y - 15,
                                              screen_x + 15, screen_y + 15, fill="green")
            self.root.update()
            samples = []
            cal_start = time.time()
            while time.time() - cal_start < 2.0:
                success, frame = self.cap.read()
                if success:
                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    import mediapipe as mp_lib
                    mp_image = mp_lib.Image(image_format=mp_lib.ImageFormat.SRGB, data=rgb)
                    result = self.gaze_model.face_landmarker.detect(mp_image)

                    if result.face_landmarks and len(result.face_landmarks) > 0:
                        landmarks = np.array([(lm.x, lm.y) for lm in result.face_landmarks[0]])
                        gaze_point = self.gaze_model.get_gaze_point(landmarks)
                        samples.append(gaze_point)
            if samples:
                median_point = np.median(samples, axis=0)
                self.calibration_points.append(median_point)
            self.canvas.delete(target)
            self.root.update()
        normalized_screen_points = [(x / self.screen_width, y / self.screen_height)
                                     for x, y in self.screen_points]
        self.gaze_model.calibrate(self.calibration_points, normalized_screen_points)
        print("Calibration completed!")

    def is_in_region(self, x, y, region):
        return region["x_min"] <= x <= region["x_max"] and region["y_min"] <= y <= region["y_max"]

    def update_pointer_position(self):
        self.canvas.coords(
            self.pointer,
            self.pointer_x - 10, self.pointer_y - 10,
            self.pointer_x + 10, self.pointer_y + 10
        )

    def show_black_screen(self):
        """Display black screen during buffer period between image sets"""
        if hasattr(self, 'pre_canvas_image'):
            self.canvas.delete(self.pre_canvas_image)
        if hasattr(self, 'post_canvas_image'):
            self.canvas.delete(self.post_canvas_image)
        self.canvas.itemconfigure(self.pointer, state='hidden')

    def show_content(self):
        """Show content after buffer period"""
        if self.show_pointer:
            self.canvas.itemconfigure(self.pointer, state='normal')

    def update(self):
        current_time = time.time()

        # Handle buffer period (black screen between sets)
        if self.is_refreshing:
            # Still read frames to keep gaze model active, but don't log data
            success, frame = self.cap.read()
            if success:
                frame = cv2.flip(frame, 1)
                self.gaze_model.predict_from_frame(frame, 1.0, 1.0)

            if current_time - self.refresh_start_time >= self.refresh_interval:
                self.is_refreshing = False
                self.complete_image_change()
                self.show_content()
            self.root.after(10, self.update)
            return

        if current_time - self.last_frame_time < self.frame_skip_threshold:
            self.root.after(10, self.update)
            return
        self.last_frame_time = current_time

        success, frame = self.cap.read()
        if not success:
            self.root.after(10, self.update)
            return

        frame = cv2.flip(frame, 1)
        norm_x, norm_y = self.gaze_model.predict_from_frame(frame, 1.0, 1.0)
        if norm_x is None or norm_y is None:
            self.root.after(10, self.update)
            return

        screen_x = norm_x * self.screen_width
        screen_y = norm_y * self.screen_height

        in_display = self.is_in_region(screen_x, screen_y, self.display_region)

        if in_display:
            target_x, target_y = screen_x, screen_y
        else:
            target_x, target_y = self.last_valid_position

        self.pointer_x = int((1 - self.smoothing_factor) * self.pointer_x + self.smoothing_factor * target_x)
        self.pointer_y = int((1 - self.smoothing_factor) * self.pointer_y + self.smoothing_factor * target_y)
        self.last_valid_position = (self.pointer_x, self.pointer_y)
        self.pointer_x = max(0, min(self.screen_width, self.pointer_x))
        self.pointer_y = max(0, min(self.screen_height, self.pointer_y))
        self.update_pointer_position()

        blink_ratio = self.gaze_model.get_blink_ratio(frame)
        is_blinking = blink_ratio < 0.18

        self.logger.update((self.pointer_x, self.pointer_y), is_blinking)

        if current_time - self.start_time > self.image_change_interval:
            self.change_images()
        else:
            self.root.after(10, self.update)

    def change_images(self):
        """Move to next image set with black screen buffer"""
        try:
            print(f"Completed image set {self.image_indices[self.image_index]}")
            self.logger.export()

            self.image_index += 1

            # Check if all sets are done
            if self.image_index >= self.max_images:
                print("All image sets completed. Exporting results...")
                summary_filename = f"{self.group}_{self.session}_{self.logger.summary_report_time}.csv"
                summary_path = os.path.join(self.output_folder, summary_filename)
                self.logger.export_all_sessions(filename=summary_path)
                self.cap.release()

                if self.show_csv:
                    try:
                        import webbrowser
                        webbrowser.open(summary_path)
                    except Exception:
                        print(f"Could not open CSV, saved at: {summary_path}")

                self.root.quit()
                return

            # Start 5-second black screen buffer
            self.is_refreshing = True
            self.refresh_start_time = time.time()
            self.show_black_screen()

            self.root.after(10, self.update)
        except Exception as e:
            print(f"Error changing images: {e}")

    def complete_image_change(self):
        """Complete the image change after buffer period"""
        try:
            self.load_images()
            self.load_aois()

            current_id = self.image_indices[self.image_index]
            self.logger.new_session(
                self.scaled_aois,
                session_name=f"{current_id}.png",
                image_id=current_id
            )

            self.start_time = time.time()
        except Exception as e:
            print(f"Error completing image change: {e}")

    def exit_listener(self):
        while True:
            try:
                if keyboard.is_pressed("ctrl+q"):
                    print("Exiting...")
                    self.cap.release()
                    self.logger.export()
                    summary_filename = f"{self.group}_{self.session}_{self.logger.summary_report_time}.csv"
                    summary_path = os.path.join(self.output_folder, summary_filename)
                    self.logger.export_all_sessions(filename=summary_path)
                    self.root.quit()
                    return
            except Exception:
                pass
            time.sleep(0.1)

def run_eye_tracker(output_folder="logs", image_folder="images", show_csv=False):
    os.makedirs(output_folder, exist_ok=True)
    EyeTrackerApp(output_folder=output_folder, image_folder=image_folder, show_csv=show_csv)

if __name__ == "__main__":
    run_eye_tracker()