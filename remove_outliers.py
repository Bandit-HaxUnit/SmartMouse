import json
import numpy as np


def calculate_path_length(dx_offsets, dy_offsets):
    # Calculate the distance from the starting position to the ending position
    start_x, start_y = 0, 0  # Assuming the path starts at (0, 0)
    end_x = start_x + np.sum(dx_offsets)
    end_y = start_y + np.sum(dy_offsets)
    return np.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)


def distance_range_for_threshold_index(thresholds, index):
    """
    Given index i in DISTANCE_THRESHOLDS, return (low, high].
    """
    if index == 0:
        return (0, thresholds[0])
    return (thresholds[index - 1], thresholds[index])


def detect_invalid_samples(mouse_data, distance_thresholds):
    cleaned_data = {}

    for threshold, directions in mouse_data.items():
        threshold_index = distance_thresholds.index(int(threshold))
        min_dist, max_dist = distance_range_for_threshold_index(distance_thresholds, threshold_index)

        cleaned_data[threshold] = {}

        for direction, samples in directions.items():
            valid_samples = []

            for sample in samples:
                dx_offsets, dy_offsets = sample[0], sample[1]
                distance = calculate_path_length(dx_offsets, dy_offsets)

                # Check if distance is within the valid range
                if min_dist < distance <= max_dist:
                    valid_samples.append(sample)

            print(
                f"{len(samples) - len(valid_samples)} invalid samples removed for threshold {threshold}, direction {direction}.")
            cleaned_data[threshold][direction] = valid_samples

    return cleaned_data


# Load JSON data
with open('mousedata_parsed.json', 'r') as f:
    mouse_data = json.load(f)

# Thresholds from recorder.py
DISTANCE_THRESHOLDS = [12, 18, 26, 39, 58, 87, 130, 190, 260, 360, 500]

# Detect and clean invalid samples
cleaned_mouse_data = detect_invalid_samples(mouse_data, DISTANCE_THRESHOLDS)

# Save the cleaned data
with open('mousedata_parsed_cleaned.json', 'w') as f:
    json.dump(cleaned_mouse_data, f, indent=4)