import math
import json

INPUT_MOUSE_DATA_FILE = "mousedata.json"
OUTPUT_FILE = "mousedata_parsed.json"

# Toggle this to True if you want 8 directions (N, NE, E, SE, S, SW, W, NW).
# Otherwise False => 4 directions (N, E, S, W).
USE_8_DIRECTIONS = True

def load_mousedata(filename):
    with open(filename, "r") as f:
        return json.load(f)

def save_mousedata(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# ------------------------------------------------------------------------
# Angle Binning Helpers
# ------------------------------------------------------------------------
def angle_to_4_dir(angle_deg):
    """
    Bin angle into one of: N, E, S, W
    We define boundaries at 45°, 135°, 225°, 315° (in degrees).
    """
    a = angle_deg % 360
    # Ranges (assuming 0°=E, 90°=N, 180°=W, 270°=S):
    #   E = [0..45) U [315..360)
    #   N = [45..135)
    #   W = [135..225)
    #   S = [225..315)
    if 45 <= a < 135:
        return "N"
    elif 135 <= a < 225:
        return "W"
    elif 225 <= a < 315:
        return "S"
    else:
        return "E"

def angle_to_8_dir(angle_deg):
    """
    Bin angle into 8 directions: N, NE, E, SE, S, SW, W, NW
    Each direction is a 45° slice, centered on multiples of 45.
    We'll define boundaries at every 45° offset by ±22.5.
    """
    a = angle_deg % 360
    # Ranges (in 45° increments):
    # E = [337.5..360) + [0..22.5)
    # NE = [22.5..67.5)
    # N = [67.5..112.5)
    # NW = [112.5..157.5)
    # W = [157.5..202.5)
    # SW = [202.5..247.5)
    # S = [247.5..292.5)
    # SE = [292.5..337.5)
    if (337.5 <= a < 360) or (0 <= a < 22.5):
        return "E"
    elif 22.5 <= a < 67.5:
        return "NE"
    elif 67.5 <= a < 112.5:
        return "N"
    elif 112.5 <= a < 157.5:
        return "NW"
    elif 157.5 <= a < 202.5:
        return "W"
    elif 202.5 <= a < 247.5:
        return "SW"
    elif 247.5 <= a < 292.5:
        return "S"
    else:  # 292.5 <= a < 337.5
        return "SE"

# ------------------------------------------------------------------------
# Main Binning Logic
# ------------------------------------------------------------------------
def main():
    data_in = load_mousedata(INPUT_MOUSE_DATA_FILE)

    # We'll build a new dictionary with the structure:
    #
    #   {
    #     "<threshold>": {
    #       "<dir>": [ [ [dx1, dx2...], [dy1, dy2...] ], ... ],
    #       ...
    #     },
    #     ...
    #   }
    #
    # Directions are either 4 or 8, depending on USE_8_DIRECTIONS.
    #
    # We do NOT store distance/angle/offsets keys, we only store the
    # 2D offset array.
    #

    # Decide which direction function to use
    if USE_8_DIRECTIONS:
        direction_labels = ["N","NE","E","SE","S","SW","W","NW"]
        get_dir = angle_to_8_dir
    else:
        direction_labels = ["N","E","S","W"]
        get_dir = angle_to_4_dir

    data_out = {}

    for threshold_str, entries_list in data_in.items():
        # Initialize sub-dict with empty lists for each direction label
        data_out[threshold_str] = {d: [] for d in direction_labels}

        # Each "entry" in entries_list is something like:
        # { "distance": ..., "angle_deg": ..., "offsets": [ [dx...],[dy...] ] }
        for entry in entries_list:
            angle_deg = entry["angle_deg"]
            offsets_2d = entry["offsets"]  # This is the [[dx...], [dy...]]

            dir_label = get_dir(angle_deg)
            # Append only the offset array
            data_out[threshold_str][dir_label].append(offsets_2d)

    # Save the simplified data
    save_mousedata(data_out, OUTPUT_FILE)
    print(f"Created '{OUTPUT_FILE}' with {'8' if USE_8_DIRECTIONS else '4'} directions, no extra fields.")

if __name__ == "__main__":
    main()
