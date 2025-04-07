import tkinter as tk
import random
import math
import json
import os
import time
from pynput.mouse import Controller

MOUSE_DATA_FILE = "mousedata.json"
DOT_RADIUS = 7
SAMPLING_INTERVAL = 8

# Define thresholds in ascending order
DISTANCE_THRESHOLDS = [12, 18, 26, 39, 58, 87, 130, 190, 260, 360, 500]

# We want to cover these 8 directions
ORIENTATIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Number of samples per orientation for each threshold
SAMPLES_PER_ORIENTATION = 1

def load_mousedata():
    if os.path.exists(MOUSE_DATA_FILE):
        with open(MOUSE_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_mousedata(data):
    with open(MOUSE_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def path_to_offsets(positions):
    if len(positions) < 2:
        return [[], []]
    x_offsets, y_offsets = [], []
    for i in range(1, len(positions)):
        px, py = positions[i - 1]
        cx, cy = positions[i]
        dx, dy = cx - px, cy - py
        if dx != 0 or dy != 0:
            x_offsets.append(dx)
            y_offsets.append(dy)
    return [x_offsets, y_offsets]

def distance_range_for_threshold_index(i):
    """
    Given index i in DISTANCE_THRESHOLDS, return (low, high].
    For i=0 => (0, 12]
    For i=1 => (12, 18], etc.
    """
    if i == 0:
        return (DISTANCE_THRESHOLDS[0], DISTANCE_THRESHOLDS[0])
    low = DISTANCE_THRESHOLDS[i - 1]
    high = DISTANCE_THRESHOLDS[i]
    return (low, high)

def get_threshold_for_distance(distance):
    for threshold in DISTANCE_THRESHOLDS:
        if distance <= threshold:
            return threshold
    return DISTANCE_THRESHOLDS[-1]

def generate_point_in_orientation(x1, y1, orientation, low, high, width, height):
    """
    Generate (x2, y2) so that:
      - The distance from (x1, y1) is in (low, high].
      - The angle is ~ the given orientation (with some slack).
      - The final point is within the rectangle [margin, width-margin] x [margin, height-margin].
    """
    # Center angles (in degrees) for each of the 8 directions
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

    angle_slack_deg = 15
    center_angle = center_angles[orientation]
    max_attempts = 2000
    margin = 60

    for _ in range(max_attempts):
        dist = random.uniform(low, high)
        # pick an angle around the center ± slack
        angle_deg = random.uniform(center_angle - angle_slack_deg, center_angle + angle_slack_deg)
        angle_rad = math.radians(angle_deg)

        dx = dist * math.cos(angle_rad)
        # In Tk y grows downward, so we invert sin to keep directions consistent
        dy = -dist * math.sin(angle_rad)

        x2 = x1 + dx
        y2 = y1 + dy

        # Check boundaries
        if margin <= x2 <= width - margin and margin <= y2 <= height - margin:
            return int(x2), int(y2), dist

    # If we couldn't find a suitable point, fallback => None
    return None

class CoverageDotRecorderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Coverage Dot Path Recorder")
        self.width = 700
        self.height = 700
        self.master.geometry(f"{self.width}x{self.height}")
        self.canvas = tk.Canvas(self.master, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.mousedata = load_mousedata()
        self.positions = []
        self.is_recording = False
        self.last_sample_time = 0
        
        # Create a list of all combinations to record
        self.combinations_to_record = self.create_combinations_list()
        random.shuffle(self.combinations_to_record)  # Randomize order
        self.current_combination_index = 0
        self.total_combinations = len(self.combinations_to_record)
        self.total_paths_recorded = 0
        
        # For continuity between dots
        self.last_end_position = None
        
        self.mouse_controller = Controller()

        self.start_dot = None
        self.end_dot = None

        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.master.bind("<Escape>", lambda e: self.quit_app())
        self.master.protocol("WM_DELETE_WINDOW", self.quit_app)

        self.schedule_position_sampling()
        self.spawn_next_dot_pair()

    def create_combinations_list(self):
        """Create a list of all threshold and orientation combinations to record"""
        combinations = []
        for threshold_idx in range(len(DISTANCE_THRESHOLDS)):
            for orient in ORIENTATIONS:
                for sample in range(SAMPLES_PER_ORIENTATION):
                    combinations.append({
                        'threshold_index': threshold_idx,
                        'orientation': orient,
                        'sample': sample
                    })
        return combinations

    def current_orientation(self):
        if self.combinations_to_record:
            return self.combinations_to_record[self.current_combination_index]['orientation']
        return ORIENTATIONS[0]  # Fallback
        
    def spawn_next_dot_pair(self):
        self.canvas.delete("all")
        self.start_dot = None
        self.end_dot = None
        self.is_recording = False
        self.positions = []

        if self.current_combination_index >= len(self.combinations_to_record):
            print("All combinations collected! Exiting.")
            self.quit_app()
            return

        # Get the current combination
        current = self.combinations_to_record[self.current_combination_index]
        threshold_index = current['threshold_index']
        orientation = current['orientation']
        sample_number = current['sample']

        # Get the current distance range
        low, high = distance_range_for_threshold_index(threshold_index)
        
        # Display info text
        progress = f"{self.current_combination_index+1}/{self.total_combinations}"
        self.canvas.create_text(
            self.width // 2, 30, 
            text=f"Progress: {progress}, Distance: {low}-{high}px, Direction: {orientation}, " +
                 f"Sample: {sample_number+1}/{SAMPLES_PER_ORIENTATION}",
            font=("Arial", 12)
        )
        
        margin = 60
        
        # Use the last end position as the new start position if available
        if self.last_end_position:
            base_x, base_y = self.last_end_position
        else:
            # First run, use a random position
            base_x = random.randint(margin, self.width - margin)
            base_y = random.randint(margin, self.height - margin)

        # Generate end point in the correct direction and distance range
        result = generate_point_in_orientation(
            base_x, base_y, orientation, low, high, 
            self.width, self.height
        )
        
        # If generation fails, try with a random start point
        if not result:
            base_x = random.randint(margin, self.width - margin)
            base_y = random.randint(margin, self.height - margin)
            result = generate_point_in_orientation(
                base_x, base_y, orientation, low, high,
                self.width, self.height
            )
            
        # If still fails, try again later
        if not result:
            self.update_instructions("Failed to place dots. Trying again...")
            self.master.after(500, self.spawn_next_dot_pair)
            return
            
        end_x, end_y, actual_distance = result
        
        # Create dots
        start_id = self.create_dot(base_x, base_y, "red")
        end_id = self.create_dot(end_x, end_y, "blue")
        
        # Draw a line between them
        self.canvas.create_line(base_x, base_y, end_x, end_y, fill="lightgray", dash=(4, 4))
        
        # Store dot info
        self.start_dot = (start_id, base_x, base_y)
        self.end_dot = (end_id, end_x, end_y)
        
        # Display distance
        actual_angle = math.degrees(math.atan2(base_y - end_y, end_x - base_x))
        self.update_instructions(
            f"Distance: {actual_distance:.1f}px, Angle: {actual_angle:.1f}°, " +
            f"Threshold: {high}px, Direction: {orientation}"
        )

    def create_dot(self, x, y, color):
        return self.canvas.create_oval(
            x - DOT_RADIUS, y - DOT_RADIUS,
            x + DOT_RADIUS, y + DOT_RADIUS,
            fill=color, outline="black"
        )

    def schedule_position_sampling(self):
        if self.is_recording:
            now = time.time() * 1000
            if now - self.last_sample_time >= SAMPLING_INTERVAL:
                x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
                y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
                self.positions.append((x, y))
                self.last_sample_time = now
        self.master.after(1, self.schedule_position_sampling)

    def canvas_to_global(self, cx, cy):
        window_left = self.master.winfo_rootx()
        window_top = self.master.winfo_rooty()
        canvas_left = self.canvas.winfo_x()
        canvas_top = self.canvas.winfo_y()
        return (window_left + canvas_left + cx, window_top + canvas_top + cy)

    def on_mouse_click(self, event):
        x, y = event.x, event.y

        # Start dot logic
        if not self.is_recording and self.start_dot:
            _, sx, sy = self.start_dot
            if math.hypot(x - sx, y - sy) <= DOT_RADIUS + 3:
                # Teleport mouse to start dot
                global_pos = self.canvas_to_global(sx, sy)
                self.mouse_controller.position = global_pos
                time.sleep(0.05)

                self.is_recording = True
                self.positions = [(sx, sy)]
                self.last_sample_time = time.time() * 1000
                self.canvas.itemconfig(self.start_dot[0], fill="green")
                self.update_instructions("Recording... Click blue dot to finish.")
                return

        # End dot logic
        if self.is_recording and self.end_dot:
            _, ex, ey = self.end_dot
            if math.hypot(x - ex, y - ey) <= DOT_RADIUS + 3:
                self.is_recording = False
                self.save_path(self.start_dot, self.end_dot)
                self.total_paths_recorded += 1
                
                # Store this end position for the next start position
                self.last_end_position = (ex, ey)
                
                # Move to the next combination
                self.next_step()
                return

    def next_step(self):
        # Move to the next combination
        self.current_combination_index += 1
        
        if self.current_combination_index >= len(self.combinations_to_record):
            print("All combinations collected! Exiting.")
            self.quit_app()
            return
            
        self.spawn_next_dot_pair()

    def save_path(self, start_dot, end_dot):
        sx, sy = start_dot[1], start_dot[2]
        ex, ey = end_dot[1], end_dot[2]
        dx, dy = ex - sx, ey - sy
        distance = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx))
        offsets = path_to_offsets(self.positions)
        
        # Get current combination info
        current = self.combinations_to_record[self.current_combination_index]
        threshold_index = current['threshold_index']
        threshold = DISTANCE_THRESHOLDS[threshold_index]
        orientation = current['orientation']
        
        entry = {
            "distance": distance,
            "angle_deg": angle,
            "orientation": orientation,
            "offsets": offsets
        }
        self.mousedata.setdefault(str(threshold), []).append(entry)
        save_mousedata(self.mousedata)
        print(f"[Saved] distance={distance:.1f}px, angle={angle:.1f}° → threshold {threshold}, dir={orientation}")
        print(f"Progress: {self.current_combination_index+1}/{self.total_combinations}")

    def update_instructions(self, message):
        self.master.title(message)

    def quit_app(self):
        print(f"Exiting. {self.total_paths_recorded} paths recorded.")
        save_mousedata(self.mousedata)
        self.master.destroy()

def main():
    root = tk.Tk()
    app = CoverageDotRecorderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()