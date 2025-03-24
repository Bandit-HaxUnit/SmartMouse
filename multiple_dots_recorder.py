import tkinter as tk
import random
import math
import json
import os
import time
from pynput.mouse import Controller

# Configure these as needed
MOUSE_DATA_FILE = "mousedata.json"
NUM_DOTS = 20  # Number of dots to place on screen
DOT_RADIUS = 7  # Size of the dots
SAMPLING_INTERVAL = 8  # Mouse position sampling interval (milliseconds)
DISTANCE_THRESHOLDS = [12, 18, 26, 39, 58, 87, 130, 190, 260, 360, 500]

def load_mousedata():
    if os.path.exists(MOUSE_DATA_FILE):
        with open(MOUSE_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_mousedata(data):
    with open(MOUSE_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

def get_threshold_for_distance(distance):
    """Find the appropriate threshold bucket for a given distance."""
    for i, threshold in enumerate(DISTANCE_THRESHOLDS):
        if distance <= threshold:
            return threshold
    return DISTANCE_THRESHOLDS[-1]  # If larger than largest threshold

class DotPathRecorderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Dot Path Recorder")
        self.width = 1500
        self.height = 1000
        # self.master.attributes("-fullscreen", True)
        self.master.geometry(f"{self.width}x{self.height}")

        self.canvas = tk.Canvas(self.master, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Load existing data
        self.mousedata = load_mousedata()
        
        # List to store dot circles and their coordinates
        self.dots = []  # [(circle_id, x, y), ...]
        
        # Path recording variables
        self.positions = []
        self.is_recording = False
        self.last_sample_time = 0
        self.current_start_dot = None
        self.current_start_index = -1
        
        # Stats
        self.paths_recorded = 0
        self.rounds_completed = 0

        # Pynput
        self.mouse_controller = Controller()

        # Bind events
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.master.bind("<Escape>", lambda e: self.quit_app())

        # Schedule regular position sampling
        self.schedule_position_sampling()

        # Start
        self.place_dots(NUM_DOTS)
        self.update_instructions()

        self.master.protocol("WM_DELETE_WINDOW", self.quit_app)

    def place_dots(self, num_dots):
        """Place a specific number of dots randomly on the canvas."""
        colors = ["red", "blue", "green", "purple", "orange", "cyan", "magenta", "brown", "black"]
        
        for i in range(num_dots):
            # Generate random position
            x = random.randint(20, self.width - 20)
            y = random.randint(20, self.height - 20)
            
            # Choose a color (cycle through the colors list)
            color = colors[i % len(colors)]
            
            # Create the dot
            dot = self.canvas.create_oval(
                x - DOT_RADIUS, y - DOT_RADIUS, 
                x + DOT_RADIUS, y + DOT_RADIUS, 
                fill=color, outline="black"
            )
            
            # Store the dot
            self.dots.append((dot, x, y))

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

    def on_mouse_click(self, event):
        """Handle mouse clicks: start/stop recording paths when clicking dots."""
        clicked_dot = None
        clicked_index = -1
        
        # Check if we clicked on any dot
        for i, (dot_id, x, y) in enumerate(self.dots):
            distance = math.hypot(event.x - x, event.y - y)
            if distance <= DOT_RADIUS + 3:  # Small tolerance for clicking
                clicked_dot = (dot_id, x, y)
                clicked_index = i
                break
        
        if clicked_dot:
            if not self.is_recording:
                # Start recording a path from this dot
                self.current_start_dot = clicked_dot
                self.current_start_index = clicked_index
                
                # Move mouse to the clicked dot's position
                self.positions = [(clicked_dot[1], clicked_dot[2])]  # Start with the dot's position
                self.last_sample_time = time.time() * 1000
                
                # Move the physical mouse cursor to the dot position
                global_pos = self.canvas_to_global(clicked_dot[1], clicked_dot[2])
                self.mouse_controller.position = global_pos
                time.sleep(0.05)
                
                self.is_recording = True
                self.update_instructions(f"Recording path from dot {clicked_index+1}...")
            else:
                # End recording at this dot
                self.is_recording = False
                
                # Save the path
                start_dot = self.current_start_dot
                end_dot = clicked_dot
                self.save_path(start_dot, end_dot)
                self.paths_recorded += 1
                
                # Remove both dots - the end dot and the start dot
                # Remove the end dot first 
                self.canvas.delete(end_dot[0])
                
                # Then remove the start dot (make sure indices are correct)
                if clicked_index != self.current_start_index:
                    # Only if they're different dots
                    self.canvas.delete(start_dot[0])
                    # Adjust indices if needed
                    if clicked_index > self.current_start_index:
                        self.dots.pop(clicked_index)
                        self.dots.pop(self.current_start_index)
                    else:
                        self.dots.pop(self.current_start_index)
                        self.dots.pop(clicked_index)
                else:
                    # Same dot clicked twice
                    self.dots.pop(clicked_index)
                
                # Reset
                self.current_start_dot = None
                self.current_start_index = -1
                
                # Check if we've used all dots
                if not self.dots:
                    self.rounds_completed += 1
                    self.update_instructions(f"Round {self.rounds_completed} completed! Respawning new dots...")
                    # Respawn new dots
                    self.place_dots(NUM_DOTS)
                    self.update_instructions(f"New dots placed (Round {self.rounds_completed+1}). Total paths: {self.paths_recorded}")
                else:
                    self.update_instructions(f"Path recorded! {len(self.dots)} dots remaining. Total: {self.paths_recorded}")

    def save_path(self, start_dot, end_dot):
        """Save the recorded path between two dots in the original format."""
        start_x, start_y = start_dot[1], start_dot[2]
        end_x, end_y = end_dot[1], end_dot[2]
        
        # Calculate distance and angle
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.hypot(dx, dy)
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        
        # Convert path to offsets
        offsets = path_to_offsets(self.positions)
        
        # Find the appropriate threshold bucket for this distance
        threshold = get_threshold_for_distance(distance)
        threshold_key = str(threshold)
        
        # Create entry
        entry = {
            "distance": distance,
            "angle_deg": angle_deg,
            "offsets": offsets
        }
        
        # Add to mouse data using the same format as the original script
        if threshold_key not in self.mousedata:
            self.mousedata[threshold_key] = []
        self.mousedata[threshold_key].append(entry)
        
        save_mousedata(self.mousedata)
        
        print(f"[Saved] distance={distance:.1f} => threshold {threshold}, angle={angle_deg:.1f}°")

    def update_instructions(self, message=None):
        """Update the window title with instructions."""
        if message:
            self.master.title(message)
        else:
            self.master.title(f"Dot Path Recorder - Click dots to connect paths ({len(self.dots)} dots)")

    def canvas_to_global(self, cx, cy):
        """Convert canvas coordinates to global screen coordinates."""
        window_left = self.master.winfo_rootx()
        window_top = self.master.winfo_rooty()
        canvas_left = self.canvas.winfo_x()
        canvas_top = self.canvas.winfo_y()
        return (window_left + canvas_left + cx, window_top + canvas_top + cy)

    def quit_app(self):
        """Save data and quit the application."""
        print(f"Exiting. {self.paths_recorded} total paths recorded across {self.rounds_completed} rounds.")
        print(f"{MOUSE_DATA_FILE} saved.")
        save_mousedata(self.mousedata)
        self.master.destroy()

def main():
    root = tk.Tk()
    app = DotPathRecorderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()