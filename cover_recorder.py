import tkinter as tk
import random
import math
import json
import os
import time

from pynput.mouse import Controller

MOUSE_DATA_FILE = "mousedata.json"

# Define thresholds in ascending order
DISTANCE_THRESHOLDS = [12, 18, 26, 39, 58, 87, 130, 190, 260, 360, 500]

# Number of samples *per orientation* for each threshold
SAMPLES_PER_ORIENTATION = 5

# We want to cover these 8 directions
ORIENTATIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Mouse position sampling interval (milliseconds)
SAMPLING_INTERVAL = 8

###############################################################################
# Utility: Load/Save the JSON
###############################################################################
def load_mousedata():
    if os.path.exists(MOUSE_DATA_FILE):
        with open(MOUSE_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_mousedata(data):
    with open(MOUSE_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

###############################################################################
# Utility: Convert a path of positions → offset pairs
###############################################################################
def path_to_offsets(positions):
    """
    Convert a list of absolute positions [(x0,y0), (x1,y1), ...]
    into [ [dx1, dx2, ...], [dy1, dy2, ...] ], excluding any zero-value offsets.
    """
    if len(positions) < 2:
        return [[], []]
    x_offsets = []
    y_offsets = []
    for i in range(1, len(positions)):
        px, py = positions[i - 1]
        cx, cy = positions[i]
        dx = cx - px
        dy = cy - py
        if dx != 0 or dy != 0:
            x_offsets.append(dx)
            y_offsets.append(dy)
    return [x_offsets, y_offsets]

###############################################################################
# Distance Bucket Utility
###############################################################################
def distance_range_for_threshold_index(i):
    """
    Given index i in DISTANCE_THRESHOLDS, return (low, high].
    For i=0 => (0, 12]
    For i=1 => (12, 18], etc.
    """
    if i == 0:
        return (0, DISTANCE_THRESHOLDS[0])
    low = DISTANCE_THRESHOLDS[i - 1]
    high = DISTANCE_THRESHOLDS[i]
    return (low, high)

###############################################################################
# Generate a second point in a given orientation & distance range
###############################################################################
def generate_point_in_orientation(x1, y1, orientation, low, high, width, height):
    """
    Generate (x2, y2) so that:
      - The distance from (x1, y1) is in (low, high].
      - The angle is ~ the given orientation (with some slack).
      - The final point is within the rectangle [20, width-20] x [20, height-20].

    We'll allow ±30° slack around each cardinal direction or diagonal.
    """
    # Center angles (in degrees) for each of the 8 directions
    # We'll define them in a dictionary for clarity:
    center_angles = {
        "N": 90,
        "NE": 45,
        "E": 0,
        "SE": 315,  # or -45
        "S": 270,
        "SW": 225,
        "W": 180,
        "NW": 135
    }

    angle_slack_deg = 30
    center_angle = center_angles[orientation]
    max_attempts = 2000

    for _ in range(max_attempts):
        dist = random.uniform(low, high)
        # pick an angle around the center ± slack
        angle_deg = random.uniform(center_angle - angle_slack_deg, center_angle + angle_slack_deg)
        angle_rad = math.radians(angle_deg)

        dx = dist * math.cos(angle_rad)
        # negative of sin(...) if we treat Y-down, but let's keep normal geometry:
        # Actually, Tk y grows downward, so let's invert sin to keep the direction consistent.
        dy = -dist * math.sin(angle_rad)

        x2 = x1 + dx
        y2 = y1 + dy

        # Check boundaries
        if 20 <= x2 <= width - 20 and 20 <= y2 <= height - 20:
            return int(x2), int(y2), dist

    # If we couldn't find a suitable point, fallback => None
    return None

###############################################################################
# The Tkinter App
###############################################################################
class DistanceRecorderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Distance Recorder (8 Directions)")
        self.width = 765
        self.height = 503
        self.master.geometry(f"{self.width}x{self.height}")

        self.canvas = tk.Canvas(self.master, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Load existing data
        self.mousedata = load_mousedata()

        # We'll keep track of threshold index and orientation index
        self.thresholds = DISTANCE_THRESHOLDS
        self.current_threshold_index = 0
        self.orientation_index = 0  # 0..7 for N,NE,E,SE,S,SW,W,NW
        self.samples_this_orientation = 0

        self.positions = []
        self.is_recording = False
        self.last_sample_time = 0

        self.green_circle = None
        self.red_circle = None

        self.current_pair = None  # (x1, y1, x2, y2, dist)

        # We'll define how many total samples we want per orientation
        self.samples_per_orientation = SAMPLES_PER_ORIENTATION

        # Pynput
        self.mouse_controller = Controller()

        # Bind events
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.master.bind("<Escape>", lambda e: self.quit_app())

        # Schedule regular position sampling
        self.schedule_position_sampling()

        # Start
        self.display_instructions()
        self.place_new_pair()

        self.master.protocol("WM_DELETE_WINDOW", self.quit_app)

    def schedule_position_sampling(self):
        """Sample the mouse position if recording."""
        if self.is_recording:
            now_ms = time.time() * 1000
            if now_ms - self.last_sample_time >= SAMPLING_INTERVAL:
                x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
                y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
                self.positions.append((x, y))
                self.last_sample_time = now_ms
        self.master.after(1, self.schedule_position_sampling)

    def on_mouse_move(self, event):
        pass

    def on_mouse_click(self, event):
        # Check if we clicked near the red circle
        if not self.red_circle:
            return
        (rx1, ry1, rx2, ry2) = self.canvas.coords(self.red_circle)
        cx = (rx1 + rx2) / 2.0
        cy = (ry1 + ry2) / 2.0
        dist_click = math.hypot(event.x - cx, event.y - cy)
        if dist_click <= 15:
            # success
            self.is_recording = False
            self.save_current_path()
            self.next_step()

    def current_orientation(self):
        return ORIENTATIONS[self.orientation_index]

    def place_new_pair(self):
        """
        For the current threshold & orientation,
        place a random green circle, then generate the red circle accordingly.
        """
        i = self.current_threshold_index
        (low, high) = distance_range_for_threshold_index(i)
        orientation = self.current_orientation()

        # random green location
        x1 = random.randint(20, self.width - 20)
        y1 = random.randint(20, self.height - 20)

        # attempt to generate red in the correct direction & distance
        result = generate_point_in_orientation(x1, y1, orientation, low, high, self.width, self.height)
        if not result:
            # fallback: if we fail to find a valid point, just random
            x2 = random.randint(20, self.width - 20)
            y2 = random.randint(20, self.height - 20)
            dist = math.hypot(x2 - x1, y2 - y1)
        else:
            (x2, y2, dist) = result

        self.current_pair = (x1, y1, x2, y2, dist)

        # Remove old circles
        if self.green_circle:
            self.canvas.delete(self.green_circle)
        if self.red_circle:
            self.canvas.delete(self.red_circle)

        # Draw them
        r = 5
        self.green_circle = self.canvas.create_oval(
            x1 - r, y1 - r, x1 + r, y1 + r, fill="green"
        )
        self.red_circle = self.canvas.create_oval(
            x2 - r, y2 - r, x2 + r, y2 + r, fill="red"
        )

        # Teleport mouse to green
        self.master.update_idletasks()
        global_green = self.canvas_to_global(x1, y1)
        self.mouse_controller.position = global_green
        time.sleep(0.05)

        self.positions = [(x1, y1)]
        self.last_sample_time = time.time() * 1000
        self.is_recording = True

    def canvas_to_global(self, cx, cy):
        # Convert a canvas coordinate to global
        window_left = self.master.winfo_rootx()
        window_top = self.master.winfo_rooty()
        canvas_left = self.canvas.winfo_x()
        canvas_top = self.canvas.winfo_y()
        return (window_left + canvas_left + cx, window_top + canvas_top + cy)

    def save_current_path(self):
        if not self.current_pair:
            return
        (x1, y1, x2, y2, dist) = self.current_pair

        # final angle in degrees
        dx = x2 - x1
        dy = y2 - y1
        angle_rad = math.atan2(dy, dx)  # range [-pi, pi]
        angle_deg = math.degrees(angle_rad)  # range [-180, 180]

        offsets = path_to_offsets(self.positions)

        threshold = self.thresholds[self.current_threshold_index]
        threshold_key = str(threshold)

        entry = {
            "distance": dist,
            "angle_deg": angle_deg,
            "offsets": offsets
        }

        if threshold_key not in self.mousedata:
            self.mousedata[threshold_key] = []
        self.mousedata[threshold_key].append(entry)
        save_mousedata(self.mousedata)

        print(
            f"[Saved] distance ~ {dist:.1f} => threshold {threshold}, "
            f"dir={self.current_orientation()}, angle={angle_deg:.1f}°"
        )

    def next_step(self):
        # move to the next sample for this orientation
        self.samples_this_orientation += 1
        if self.samples_this_orientation >= self.samples_per_orientation:
            # move to the next orientation
            self.orientation_index += 1
            self.samples_this_orientation = 0

            if self.orientation_index >= len(ORIENTATIONS):
                # move to next threshold
                self.orientation_index = 0
                self.current_threshold_index += 1

                if self.current_threshold_index >= len(self.thresholds):
                    print("All thresholds (and directions) collected! Exiting.")
                    self.quit_app()
                    return

        self.display_instructions()
        self.place_new_pair()

    def display_instructions(self):
        t = self.thresholds[self.current_threshold_index]
        orientation = self.current_orientation()
        s = self.samples_this_orientation + 1
        self.master.title(
            f"Distance ≤ {t}, Orientation={orientation}, Sample {s}/{self.samples_per_orientation}"
        )

    def quit_app(self):
        print("Exiting. mousedata.json saved.")
        save_mousedata(self.mousedata)
        self.master.destroy()

def main():
    root = tk.Tk()
    app = DistanceRecorderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
