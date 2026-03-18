import time
import csv
import os

class AOILogger:
    def __init__(self, aois, group, session_type="pre", regions=None, session_name=None):
        self.aois = aois
        self.group = group.lower()
        self.session = session_type.lower()
        self.regions = regions if regions else ["pre", "post"]
        self.session_name = session_name or "session"
        self.session_summaries = []
        self.session_names = []
        self.total_blinks = 0
        self.total_duration = 0
        self.total_sessions = 0
        self.summary_report_time = int(time.time())
        self.current_image_id = "1"  # Changed from index to ID
        self._was_blinking = False  # Track blink state transitions
        self._last_update_time = None  # For real elapsed time
        self.reset_session_data()

    def reset_session_data(self):
        self.start_time = time.time()
        self.end_time = None
        self.blink_count = 0
        self.total_blink_time = 0
        self.aoi_data = {
            name: {
                "entered": False,
                "first_fixation_time": None,
                "total_time": 0,
                "entry_time": None,
                "blink_count": 0
            } for name in self.aois
        }
        self.first_focused_aoi = {region: None for region in self.regions}
        self.most_focused_aoi = {region: None for region in self.regions}

    def update(self, pointer_pos, is_blinking):
        current_time = float(time.time())
        is_blinking = bool(is_blinking)

        # Calculate real elapsed time since last update
        if self._last_update_time is None:
            dt = 0.0
        else:
            dt = float(current_time - self._last_update_time)
        self._last_update_time = current_time

        # Detect blink transitions (not every frame)
        blink_event = is_blinking and not self._was_blinking
        self._was_blinking = is_blinking

        for name, ((x1, y1), (x2, y2)) in self.aois.items():
            inside = x1 <= pointer_pos[0] <= x2 and y1 <= pointer_pos[1] <= y2
            aoi = self.aoi_data[name]

            if inside:
                if not aoi["entered"]:
                    aoi["entered"] = True
                    aoi["first_fixation_time"] = current_time - self.start_time
                    aoi["entry_time"] = current_time
                    for region in self.first_focused_aoi:
                        if name.startswith(region + "_") and self.first_focused_aoi[region] is None:
                            self.first_focused_aoi[region] = name.split("_", 1)[1]
                if blink_event:
                    aoi["blink_count"] += 1
                if not is_blinking:
                    aoi["total_time"] += dt
            else:
                aoi["entry_time"] = None

        if blink_event:
            self.blink_count += 1

    def export(self, filename=None):
        self.end_time = time.time()
        duration_sec = self.end_time - self.start_time
        self.total_blinks += self.blink_count
        self.total_duration += duration_sec
        self.total_sessions += 1

        region_aois = {region: [] for region in self.regions}
        for name in self.aoi_data:
            for region in self.regions:
                if name.startswith(region + "_"):
                    region_aois[region].append(name)

        aoi_order = sorted([name.split("_", 1)[1] for name in self.aois if name.startswith(self.regions[0] + "_")])

        for region in self.regions:
            max_time = -1
            max_aoi = None
            for name in region_aois[region]:
                total_time = self.aoi_data[name]["total_time"]
                if total_time > max_time:
                    max_time = total_time
                    max_aoi = name.split("_", 1)[1]
            self.most_focused_aoi[region] = max_aoi if max_time > 0 else None

        session_file = f"{self.current_image_id}.png"
        self.session_names.append(session_file)

        # Build side-by-side report: Pre on left columns, Post on right columns
        session_lines = [[f"Session - {session_file}:"]]

        # Header row: Pre columns on left, gap, Post columns on right
        session_lines.append([
            "Pre Treatment Image Report:", "", "", "",
            "",
            "Post Treatment Image Report:"
        ])
        session_lines.append([
            "AOI", "First Fixation Time (s)", "Total Fixation Time (s)", "Blink Count in AOI",
            "",
            "AOI", "First Fixation Time (s)", "Total Fixation Time (s)", "Blink Count in AOI"
        ])

        # Data rows side by side
        for aoi in aoi_order:
            pre_name = f"pre_{aoi}"
            post_name = f"post_{aoi}"
            pre_data = self.aoi_data.get(pre_name, {"first_fixation_time": 0, "total_time": 0, "blink_count": 0})
            post_data = self.aoi_data.get(post_name, {"first_fixation_time": 0, "total_time": 0, "blink_count": 0})
            session_lines.append([
                aoi,
                round(pre_data["first_fixation_time"] or 0, 2),
                round(pre_data["total_time"], 2),
                pre_data["blink_count"],
                "",
                aoi,
                round(post_data["first_fixation_time"] or 0, 2),
                round(post_data["total_time"], 2),
                post_data["blink_count"]
            ])

        session_lines.append([])
        # First Focused and Most Focused side by side
        session_lines.append([
            "First Focused AOI", self.first_focused_aoi.get("pre", "None") or "None",
            "", "", "",
            "First Focused AOI", self.first_focused_aoi.get("post", "None") or "None"
        ])
        session_lines.append([
            "Most Focused AOI", self.most_focused_aoi.get("pre", "None") or "None",
            "", "", "",
            "Most Focused AOI", self.most_focused_aoi.get("post", "None") or "None"
        ])

        self.session_summaries.append(session_lines)

    def export_all_sessions(self, filename=None):
        if filename is None:
            from core.paths import data_path
            safe_group = self.group.replace(" ", "_")
            safe_session = self.session.replace(" ", "_")
            filename = data_path(f"logs/{safe_group}_{safe_session}_{self.summary_report_time}.csv")
        output_dir = os.path.dirname(filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(filename, "w", newline='') as f:
            writer = csv.writer(f)
            for idx, session_lines in enumerate(self.session_summaries):
                for line in session_lines:
                    writer.writerow(line)
                if idx < len(self.session_summaries) - 1:
                    writer.writerow([])
                    writer.writerow([])
            for _ in range(5):
                writer.writerow([])

            blink_rate = self.total_blinks / (self.total_duration / 60.0) if self.total_duration > 0 else 0
            writer.writerow(["Total Blinks", self.total_blinks])
            writer.writerow(["Blink Rate (blinks/min)", round(blink_rate, 2)])

    def new_session(self, aois, session_name, image_id):  # Changed parameter name
        self.aois = aois
        self.session_name = session_name
        self.current_image_id = image_id  # Store actual image ID
        self._was_blinking = False
        self._last_update_time = None
        self.reset_session_data()