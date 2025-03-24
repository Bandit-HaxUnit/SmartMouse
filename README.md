# SmartMouse

This project provides tools for creating realistic mouse movement patterns for use in DreamBot scripts. 

It includes data collection, processing, and example implementation for natural mouse movements.

## Components

### Data Collection Tools

- **`cover_recorder.py`**  
  Records mouse movements for 8 different directions and various distance thresholds using a visual interface with green (start) and red (end) dots.

- **`multiple_dots_recorder.py`**  
  More advanced recorder that supports recording movements between multiple points for creating more complex and chain-like movement patterns.

### Data Processing Tools

- **`parser.py`**  
  Processes raw mouse data into a format usable by DreamBot scripts, organizing movement data by threshold and direction.

- **`remove_outliers.py`**  
  Cleans the dataset by removing outliers and erroneous mouse recordings.

- **`move.py`**  
  Utility for testing the recorded mouse movements visually.

### DreamBot Implementation

- **`SmartMouseMultiDir.java`**  
  A custom mouse movement algorithm implementation for DreamBot that uses the recorded data to create human-like mouse movements.

- **`RandomMouseMover.java`**  
  Example script that demonstrates the use of the custom mouse movement algorithm.

- **`SimulateAFK.java`**  
  Utility class for simulating AFK behavior by moving the mouse off-screen and back with natural movements.

- **`OffScreenPointGenerator.java`**  
  Generates off-screen points for the AFK simulator.

## Usage

The `dreambot_example` folder contains a small pre-made dataset that's ready to use with the algorithm immediately.

If you prefer to create your own custom mouse movement dataset, follow these steps:

### 1. Recording Mouse Movements 

Run the cover recorder to collect movement data: `cover_recorder.py`

> Move your mouse from the green dot and click the red dot for each distance and direction.

For more complex patterns, use the multiple dots recorder: `multiple_dots_recorder.py`

> Start by clicking any random dot and continue clicking other dots.

### 2. Processing Data

- Parse the data into the correct format: `parser.py` generates `mousedata_parsed.json`
- Clean the data by removing outliers: `remove_outliers.py` generates `mousedata_parsed_cleaned.json`

### 3. Implementation in DreamBot

- Rename the generated `mousedata_parsed_cleaned.json` to `mousedata.json` and add it to your DreamBot script resources.
- Implement the `SmartMouseMultiDir` class as your mouse movement algorithm.
- Use the example `RandomMouseMover` script as a template for your own scripts.

## Technical Implementation

### How SmartMouseMultiDir Works

The `SmartMouseMultiDir` class implements DreamBot's `MouseAlgorithm` interface to create realistic mouse movements based on recorded human behavior. Here's how it works:

#### 1. Distance Classification

- Mouse movements are categorized by distance thresholds: `[12, 18, 26, 39, 58, 87, 130, 190, 260, 360, 500]` pixels
- For any movement, the algorithm selects the appropriate threshold bucket for the current distance

#### 2. Direction Selection

- Mouse paths are organized into 8 compass directions `(N, NE, E, SE, S, SW, W, NW)`
- When moving to a target, the algorithm computes the angle and selects the appropriate directional category

#### 3. Path Generation

- For a given distance and direction, the algorithm:
  1. Retrieves a random pre-recorded path from `mousedata.json`
  2. Extracts the offset patterns (dx, dy increments) for each point in the path
  3. Adjusts these offsets to match the exact start and end positions
  4. Generates a complete path with intermediate points

#### 4. Movement Physics

- Each path step uses variable speeds based on distance:
  - Short distances: 0.005-0.007 seconds per step
  - Medium distances: 0.007-0.010 seconds per step
  - Long distances: 0.010-0.013 seconds per step

- The algorithm applies easing functions to simulate human acceleration/deceleration:
  - `ease_out_cubic`: Quick start with gradual slowdown
  - `ease_in_out_cubic`: Gradual start, mid-acceleration, gradual finish
  - `ease_linear`: Constant speed movement

#### 5. Micro-Movement Simulation

- Each point-to-point movement is further subdivided into micro-steps
- Adds subtle human-like variance to speeds (±5%)
- Simulates the natural jitter and imprecision in human movements

### Demo Video

See the algorithm in action here: [Mouse Movement Demo](https://i.imgur.com/SIv4cMb.mp4)

### AFK Simulation

The `SimulateAFK` class allows scripts to move the mouse off-screen to simulate AFK behavior.

```java
// Configure the SimulateAFK settings
SimulateAFK.setFocusManipulation(true);
SimulateAFK.setFocusChances(70, 30);

// Move mouse off-screen occasionally
if (shouldSimulateAFK()) {
    SimulateAFK.moveMouseOut();
}
```


### JSON Data Structure
The mousedata.json file uses a hierarchical structure:

```json
{
  "12": {
    "N":  [ [ [dx offsets], [dy offsets] ], ... ],
    "NE": [ ... ],
    "E":  [ ... ],
    ...
  },
  "18": { ... },
  ...
}
```

- Top level: Distance thresholds
- Second level: 8 directions
- Third level: Lists of recorded path offset pairs


## License

This project is for educational purposes only. Using bots in online games may be against the terms of service.