import json
import math
import random
import time
import tkinter as tk
from pynput.mouse import Controller

MOUSE_DATA_FILE = "mousedata_parsed_cleaned.json"
DISTANCE_THRESHOLDS = [12, 18, 26, 39, 58, 87, 130, 190, 260, 360, 500]

BASE_SPEEDS = {
    'fast':   (0.005, 0.007),
    'medium': (0.007, 0.010),
    'slow':   (0.010, 0.013)
}

SPEED_VARIANCE = 0.3
NUM_POINTS = 10
DOT_SIZE = 6

# ------------------ EASING FUNCTIONS ------------------
ease_linear        = lambda t: t
ease_out_quart     = lambda t: 1 - (1 - t) ** 4
ease_in_out_quart  = lambda t: 1 - 8 * (1 - t if t >= 0.5 else t) ** 4 if t >= 0.5 else 8 * t**4
ease_out_cubic     = lambda t: 1 - (1 - t) ** 3
ease_in_cubic      = lambda t: t ** 3
ease_in_out_cubic  = lambda t: 1 + (t - 1) ** 3 if t >= 0.5 else 4 * t ** 3

def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1

def ease_out_bounce(t):
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        return n1 * (t - 1.5 / d1) ** 2 + 0.75
    elif t < 2.5 / d1:
        return n1 * (t - 2.25 / d1) ** 2 + 0.9375
    else:
        return n1 * (t - 2.625 / d1) ** 2 + 0.984375

EASING_FUNCTIONS = {
    'short': [
        (ease_out_cubic, 0.4),
        (ease_out_quart, 0.3),
        (ease_in_out_cubic, 0.2),
        (ease_linear, 0.1),
    ],
    'medium': [
        (ease_in_out_cubic, 0.3),
        (ease_in_out_quart, 0.3),
        (ease_out_cubic, 0.2),
        (ease_out_elastic, 0.2),
    ],
    'long': [
        (ease_in_out_quart, 0.4),
        (ease_out_elastic, 0.3),
        (ease_out_bounce, 0.2),
        (ease_in_out_cubic, 0.1),
    ]
}

# ------------------ ORIENTATION LOGIC (8 Directions) ------------------
def angle_to_8_direction(angle_deg):
    """
    Convert angle (degrees in range -180..180 or 0..360) to one of:
    N, NE, E, SE, S, SW, W, NW
    """
    a = angle_deg % 360
    # E = [337.5..360) + [0..22.5)
    # NE = [22.5..67.5)
    # N = [67.5..112.5)
    # NW = [112.5..157.5)
    # W = [157.5..202.5)
    # SW = [202.5..247.5)
    # S = [247.5..292.5)
    # SE = [292.5..337.5)
    if (a >= 337.5 and a < 360) or (a >= 0 and a < 22.5):
        return "E"
    elif a >= 22.5 and a < 67.5:
        return "NE"
    elif a >= 67.5 and a < 112.5:
        return "N"
    elif a >= 112.5 and a < 157.5:
        return "NW"
    elif a >= 157.5 and a < 202.5:
        return "W"
    elif a >= 202.5 and a < 247.5:
        return "SW"
    elif a >= 247.5 and a < 292.5:
        return "S"
    else:
        return "SE"

class VisualizationOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes('-alpha', 0.5, '-topmost', True)
        self.root.overrideredirect(True)

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")

        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg='black')
        self.canvas.pack(fill='both', expand=True)
        self.root.bind('<Escape>', lambda e: self.root.destroy())

    def draw_dot(self, x, y):
        r = DOT_SIZE / 2
        self.canvas.create_oval(x - r - 1, y - r - 1,
                                x + r + 1, y + r + 1,
                                fill='white', outline='')
        self.canvas.create_oval(x - r, y - r,
                                x + r, y + r,
                                fill='red', outline='')
        self.root.update()

def load_mousedata():
    with open(MOUSE_DATA_FILE, "r") as f:
        return json.load(f)

def get_base_speed(distance):
    if distance <= 100:
        return random.uniform(*BASE_SPEEDS['fast'])
    elif distance <= 250:
        return random.uniform(*BASE_SPEEDS['medium'])
    else:
        return random.uniform(*BASE_SPEEDS['slow'])

def add_human_variance(base_speed):
    return base_speed + random.uniform(-base_speed * SPEED_VARIANCE, base_speed * SPEED_VARIANCE)

def select_easing_function(distance):
    cat = 'short' if distance <= 100 else 'medium' if distance <= 250 else 'long'
    funcs, weights = zip(*EASING_FUNCTIONS[cat])
    return random.choices(funcs, weights=weights)[0]

def get_sleep_duration(step, total_steps, distance, override_speed=None):
    if total_steps <= 1:
        return 0
    t = step / (total_steps - 1)
    factor = select_easing_function(distance)(t)
    base_speed = add_human_variance(override_speed if override_speed else get_base_speed(distance))
    return base_speed * (0.8 + 0.4 * factor)

def get_distance_category(distance):
    for threshold in DISTANCE_THRESHOLDS:
        if distance <= threshold:
            return str(threshold)
    return str(DISTANCE_THRESHOLDS[-1])

def pick_random_path(mousedata, distance, direction):
    """
    mousedata structure now:
    {
      "12": {
        "N":  [ [ [dx...],[dy...] ], ... ],
        "NE": [ ... ],
        "E":  [ ... ],
        "SE": [ ... ],
        "S":  [ ... ],
        "SW": [ ... ],
        "W":  [ ... ],
        "NW": [ ... ]
      },
      "18": {...},
      ...
    }
    """
    dist_cat = get_distance_category(distance)
    dist_dict = mousedata.get(dist_cat, {})
    paths = dist_dict.get(direction, [])
    if not paths:
        return None
    return random.choice(paths)

def build_exact_path(start_x, start_y, target_x, target_y, x_offsets, y_offsets):
    steps = min(len(x_offsets), len(y_offsets))
    if not steps:
        return [(start_x, start_y), (target_x, target_y)]

    dx = target_x - start_x
    dy = target_y - start_y
    total_offset_x = sum(x_offsets)
    total_offset_y = sum(y_offsets)
    adj_dx, adj_dy = dx - total_offset_x, dy - total_offset_y
    path = []

    for i in range(steps):
        t = (i + 1) / steps
        offset_x = sum(x_offsets[:i + 1])
        offset_y = sum(y_offsets[:i + 1])
        new_x = start_x + adj_dx * t + offset_x
        new_y = start_y + adj_dy * t + offset_y
        path.append((new_x, new_y))
    return path

def generate_random_points(num_points, w, h):
    pad = 600
    return [(random.randint(pad, w - pad), random.randint(pad, h - pad)) for _ in range(num_points)]

def move_to_point(mouse, mousedata, start_x, start_y, target_x, target_y, overlay):
    distance = math.hypot(target_x - start_x, target_y - start_y)
    print(f"Moving to ({target_x}, {target_y}), distance = {distance:.1f}")

    # Compute angle -> 8 direction
    dx = target_x - start_x
    dy = target_y - start_y
    angle_deg = math.degrees(math.atan2(dy, dx))
    direction = angle_to_8_direction(angle_deg)
    print(f"Orientation determined: {direction}")

    offsets_pair = pick_random_path(mousedata, distance, direction)
    if not offsets_pair:
        print(f"No path found for dist={distance:.1f}, direction={direction}. Jumping directly.")
        mouse.position = (target_x, target_y)
        overlay.draw_dot(target_x, target_y)
        return

    x_offsets, y_offsets = offsets_pair
    path = build_exact_path(start_x, start_y, target_x, target_y, x_offsets, y_offsets)

    for i, (px, py) in enumerate(path):
        mouse.position = (px, py)
        time.sleep(get_sleep_duration(i, len(path), distance))

    mouse.position = (target_x, target_y)
    overlay.draw_dot(target_x, target_y)

def main():
    try:
        overlay = VisualizationOverlay()
        mousedata = load_mousedata()
        mouse = Controller()

        # Example points or random generation
        points = [
            (1348, 740),
            (1366, 740),
            (1398, 740),
            (1451, 739),
            (1376, 782),
            (1423, 780),
            (1466, 784),
            (1521, 786),
            (1365, 825),
            (1407, 824),
            (1452, 819),
            (765, 408),
            (973, 479),
            (882, 552),
            (1086, 723),
            (684, 391),
            (636, 619),
            (663, 720),
            (925, 356),
        ]
        # points = generate_random_points(NUM_POINTS, overlay.screen_width, overlay.screen_height)

        current_x, current_y = mouse.position
        for (tx, ty) in points:
            move_to_point(mouse, mousedata, current_x, current_y, tx, ty, overlay)
            current_x, current_y = tx, ty
            time.sleep(random.uniform(0.2, 0.25))

        print("Movement sequence complete. Press ESC to close visualization.")
        overlay.root.mainloop()

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
