import org.dreambot.api.Client;
import org.dreambot.api.input.Mouse;
import org.dreambot.api.input.mouse.algorithm.MouseAlgorithm;
import org.dreambot.api.input.mouse.destination.AbstractMouseDestination;
import org.dreambot.api.input.event.impl.mouse.MouseButton;
import org.dreambot.api.script.ScriptManager;
import org.dreambot.api.utilities.Logger;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.awt.Point;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.awt.Canvas;

public class SmartMouseMultiDir implements MouseAlgorithm {
	Canvas canvas = Client.getCanvas();
	int screenWidth = canvas.getWidth();
	int screenHeight = canvas.getHeight();
	
    private static final int[] DISTANCE_THRESHOLDS = {12, 18, 26, 39, 58, 87, 130, 190, 260, 360, 500};

    private static final double[][] BASE_SPEED_RANGES = {
        // short range
        {0.005, 0.007},
        // medium range
        {0.007, 0.010},
        // long range
        {0.010, 0.013}
    };

    private static final double SPEED_VARIANCE = 0.05;

    private static final List<WeightedEasing> SHORT_EASINGS = Arrays.asList(
        new WeightedEasing(EasingFunction.EASE_OUT_CUBIC, 0.4),
        // new WeightedEasing(EasingFunction.EASE_OUT_QUART, 0.3),
        new WeightedEasing(EasingFunction.EASE_IN_OUT_CUBIC, 0.2),
        new WeightedEasing(EasingFunction.EASE_LINEAR, 0.1)
    );

    private static final List<WeightedEasing> MEDIUM_EASINGS = Arrays.asList(
		// new WeightedEasing(EasingFunction.EASE_IN_OUT_QUART, 0.3),
		new WeightedEasing(EasingFunction.EASE_OUT_CUBIC, 0.3),
        new WeightedEasing(EasingFunction.EASE_IN_OUT_CUBIC, 0.2),
		new WeightedEasing(EasingFunction.EASE_LINEAR, 0.1)
    );

    private static final List<WeightedEasing> LONG_EASINGS = Arrays.asList(
        // new WeightedEasing(EasingFunction.EASE_IN_OUT_QUART, 0.3),
        new WeightedEasing(EasingFunction.EASE_IN_OUT_CUBIC, 0.2),
		new WeightedEasing(EasingFunction.EASE_LINEAR, 0.1)
    );

    /**
     * Expected structure in mousedata.json:
     *
     * {
     *   "12": {
     *     "N":  [ [ [dxOffsets...],[dyOffsets...] ], ... ],
     *     "NE": [ ... ],
     *     "E":  [ ... ],
     *     "SE": [ ... ],
     *     "S":  [ ... ],
     *     "SW": [ ... ],
     *     "W":  [ ... ],
     *     "NW": [ ... ]
     *   },
     *   "18": { ... },
     *   ...
     * }
     */
    private Map<String, Object> mouseData;

    private final Random random = new Random();
    private boolean lastActionWasRightClick = false;

    public SmartMouseMultiDir() {
        loadMouseData();
    }

    @Override
    public boolean handleClick(MouseButton mouseButton) {
        boolean result = Mouse.getDefaultMouseAlgorithm().handleClick(mouseButton);

        if (mouseButton == MouseButton.RIGHT_CLICK) {
            lastActionWasRightClick = true;
            sleep(randomDouble(111, 222));
        } else {
            lastActionWasRightClick = false;
        }

        return result;
    }

    @Override
    public boolean handleMovement(AbstractMouseDestination destination) {
        if (!ScriptManager.getScriptManager().isRunning()) {
            // Logger.log("Script stopped; not moving mouse.");
            return false;
        }

        Point target = destination.getSuitablePoint();
        Point current = Mouse.getPosition();

        if (current.equals(target)) {
            // Logger.log("Current mouse position is already at target. No movement needed.");
            return true;
        }
		
		if (!isWithinCanvas(current) && !isWithinCanvas(target)) {
			Logger.log("Mouse position and target is outside the client canvas. Skipping path-based movement and hopping.");
			Point outside_exit = Mouse.getPointOutsideScreen();
			Mouse.hop(outside_exit);
            Mouse.setPosition(target.x, target.y);
			return true;
		}

        double distance = distance(current, target);
        Logger.log("handleMovement => Current: " + current + ", Target: " + target + ", Distance: " + distance);

        // Compute angle in degrees from current -> target
        double dx = target.getX() - current.getX();
        double dy = target.getY() - current.getY();
        double angleDeg = Math.toDegrees(Math.atan2(dy, dx)); // range: -180..180
        String orientation = angleTo8Direction(angleDeg);
        // Logger.log("Orientation determined: " + orientation);

        // Generate path from JSON offsets + final point
        List<Point> path = generatePath(current, target, distance, orientation);
        // Logger.log("Generated path with " + path.size() + " points.");

        // Select a single EasingFunction for the entire movement
        EasingFunction easingFunc = selectEasingFunction(distance);
        // Logger.log("Chosen easing function: " + easingFunc.name() + " for distance: " + distance);

        // Walk through the path
        for (int i = 0; i < path.size(); i++) {
            Point stepPoint = path.get(i);

            // Time in SECONDS for the entire step from i -> i+1
            double stepDurationSeconds = calculateSleepDuration(i, path.size(), distance, easingFunc);

            // Move smoothly from the current position to stepPoint
            moveSmoothly(Mouse.getPosition(), stepPoint, stepDurationSeconds, easingFunc);
        }

        double finalDistance = distance(Mouse.getPosition(), target);
        // Logger.log("Final distance to target after movement: " + finalDistance);

        if (lastActionWasRightClick) {
            sleep(randomDouble(111, 222));
        }

        return finalDistance < 2;
    }
	
	private boolean isWithinCanvas(Point point) {
		return point.getX() >= 0 && point.getY() >= 0 &&
			   point.getX() < screenWidth && point.getY() < screenHeight;
	}


    /**
     * Convert angle (in degrees) to one of the 8 compass directions: N, NE, E, SE, S, SW, W, NW.
     */
    private String angleTo8Direction(double angleDeg) {
        // Normalize to [0..360)
        double a = (angleDeg + 360) % 360;

        // E = [337.5..360) + [0..22.5)
        // NE = [22.5..67.5)
        // N = [67.5..112.5)
        // NW = [112.5..157.5)
        // W = [157.5..202.5)
        // SW = [202.5..247.5)
        // S = [247.5..292.5)
        // SE = [292.5..337.5)
        if ( (a >= 337.5 && a < 360) || (a >= 0 && a < 22.5) ) {
            return "E";
        } else if (a >= 22.5 && a < 67.5) {
            return "NE";
        } else if (a >= 67.5 && a < 112.5) {
            return "N";
        } else if (a >= 112.5 && a < 157.5) {
            return "NW";
        } else if (a >= 157.5 && a < 202.5) {
            return "W";
        } else if (a >= 202.5 && a < 247.5) {
            return "SW";
        } else if (a >= 247.5 && a < 292.5) {
            return "S";
        } else {
            return "SE";
        }
    }

    /**
     * Move from 'start' to 'end' in multiple micro-steps, each with a short sleep.
     */
    private void moveSmoothly(Point start, Point end, double totalMovementSeconds, EasingFunction easingFunc) {
        // Distance between start and end
        double dist = start.distance(end);
        
        // Decide how many micro-steps (subdivisions) to use.
        int subdivisions = Math.max(5, (int) (dist / 2.5));
        
        // For time-based pacing, compute how long each micro-step should take.
        double microSleepMs = (totalMovementSeconds * 1000.0) / subdivisions;
    
        // Decompose start/end into x/y
        double sx = start.getX();
        double sy = start.getY();
        double ex = end.getX();
        double ey = end.getY();
    
        // Delta
        double dx = ex - sx;
        double dy = ey - sy;
    
        // Perform the micro-steps
        for (int i = 1; i <= subdivisions; i++) {
            // Linear fraction from 0.0 to 1.0
            double t = (double) i / subdivisions;
            
            // Apply the easing function to get a non-linear fraction
            double easedFrac = easingFunc.apply(t);
    
            // Interpolate position with easedFrac
            double ix = sx + dx * easedFrac;
            double iy = sy + dy * easedFrac;
    
            // "Hop" or move the mouse to the eased position
            Mouse.hop(new Point((int) ix, (int) iy));
    
            // Brief sleep so it's not instantaneous
            sleep(microSleepMs);
        }
    }
    

    /**
     * Build a path of points from 'start' to 'target' using offsets from mousedata (if any),
     * for the chosen 8-direction category.
     */
    private List<Point> generatePath(Point start, Point target, double distance, String orientation) {
        List<Point> path = new ArrayList<>();
        List<List<Double>> offsets = getPathOffsets(distance, orientation);

        if (offsets == null) {
            // No offsets found => direct single hop
            // Logger.log("No path offsets found for distance/orientation. Moving directly.");
            path.add(target);
            return path;
        }

        // Logger.log("Using offsets -> xSize=" + offsets.get(0).size() + ", ySize=" + offsets.get(1).size());

        List<Double> xOffsets = offsets.get(0);
        List<Double> yOffsets = offsets.get(1);

        double dx = target.getX() - start.getX();
        double dy = target.getY() - start.getY();

        double totalOffsetX = xOffsets.stream().mapToDouble(Double::doubleValue).sum();
        double totalOffsetY = yOffsets.stream().mapToDouble(Double::doubleValue).sum();
        // Logger.log("Total offset from mouse => X: " + totalOffsetX + ", Y: " + totalOffsetY);

        double adjustedDx = dx - totalOffsetX;
        double adjustedDy = dy - totalOffsetY;

        double sx = start.getX();
        double sy = start.getY();

        for (int i = 0; i < xOffsets.size(); i++) {
            double t = (i + 1.0) / xOffsets.size();

            double offsetX = 0.0;
            double offsetY = 0.0;
            for (int j = 0; j <= i; j++) {
                offsetX += xOffsets.get(j);
                offsetY += yOffsets.get(j);
            }

            double newX = sx + adjustedDx * t + offsetX;
            double newY = sy + adjustedDy * t + offsetY;
            path.add(new Point((int) newX, (int) newY));
        }

        // Ensure final target is included
        path.add(target);
        return path;
    }

    /**
     * For a given distance and direction, pick a random offsets-pair from the JSON.
     */
    @SuppressWarnings("unchecked")
    private List<List<Double>> getPathOffsets(double distance, String direction) {
        String category = getDistanceCategory(distance);
        // Logger.log("getPathOffsets => distance=" + distance + ", category=" + category + ", direction=" + direction);

        Map<String, Object> subMap = (Map<String, Object>) mouseData.get(category);
        if (subMap == null) {
            // Logger.log("No data for distance category: " + category);
            return null;
        }

        // subMap has keys: "N","NE","E","SE","S","SW","W","NW"
        List<List<List<Double>>> directionPaths = (List<List<List<Double>>>) subMap.get(direction);
        if (directionPaths == null || directionPaths.isEmpty()) {
            // Logger.log("No paths found in JSON for category=" + category + " / direction=" + direction);
            return null;
        }

        // Randomly select one path
        int index = random.nextInt(directionPaths.size());
        List<List<Double>> selectedPath = directionPaths.get(index);

        // Logger.log("Selected path index " + index + " with xOffsets=" + selectedPath.get(0).size() + ", yOffsets=" + selectedPath.get(1).size()); 
        return selectedPath;
    }

    /**
     * Each step's duration is determined by a base speed with variance,
     * multiplied by an easing function factor.
     */
    private double calculateSleepDuration(int step, int totalSteps, double distance, EasingFunction easingFunc) {
		if (totalSteps <= 1) {
			// Logger.log("Total steps <= 1, returning 0.0");
			return 0.0;
		}
		
		double t = (double) step / (totalSteps - 1);
		// // Logger.log("Step: " + step + ", Total Steps: " + totalSteps + ", t: " + t);

		double baseSpeed = getBaseSpeed(distance);
		// // Logger.log("Distance: " + distance + ", Base Speed: " + baseSpeed);

		double variedSpeed = addHumanVariance(baseSpeed);
		// // Logger.log("Varied Speed with Human Variance: " + variedSpeed);

		double factor = easingFunc.apply(t);
		// // Logger.log("Easing Function Factor (t=" + t + "): " + factor);

		// double sleepDuration = variedSpeed * (0.8 + 0.4 * factor);
		double sleepDuration = variedSpeed * (0.8 + 0.1 * factor);
		// // Logger.log("Calculated Sleep Duration (seconds): " + sleepDuration);
		
		return sleepDuration;
	}


    private double getBaseSpeed(double distance) {
        if (distance <= 100) {
            return randomDouble(BASE_SPEED_RANGES[0][0], BASE_SPEED_RANGES[0][1]);
        } else if (distance <= 250) {
            return randomDouble(BASE_SPEED_RANGES[1][0], BASE_SPEED_RANGES[1][1]);
        } else {
            return randomDouble(BASE_SPEED_RANGES[2][0], BASE_SPEED_RANGES[2][1]);
        }
    }

    private double addHumanVariance(double baseSpeed) {
        double maxDelta = baseSpeed * SPEED_VARIANCE;
        double offset = randomDouble(-maxDelta, maxDelta);
        return baseSpeed + offset;
    }

    private EasingFunction selectEasingFunction(double distance) {
        List<WeightedEasing> candidates;
        if (distance <= 100) {
            candidates = SHORT_EASINGS;
        } else if (distance <= 250) {
            candidates = MEDIUM_EASINGS;
        } else {
            candidates = LONG_EASINGS;
        }

        double totalWeight = 0;
        for (WeightedEasing we : candidates) {
            totalWeight += we.weight;
        }

        double r = random.nextDouble() * totalWeight;
        for (WeightedEasing we : candidates) {
            r -= we.weight;
            if (r <= 0) {
                return we.function;
            }
        }
        // Fallback
        return candidates.get(candidates.size() - 1).function;
    }

    private String getDistanceCategory(double distance) {
        for (int threshold : DISTANCE_THRESHOLDS) {
            if (distance <= threshold) {
                return String.valueOf(threshold);
            }
        }
        // If it's bigger than the largest threshold
        return String.valueOf(DISTANCE_THRESHOLDS[DISTANCE_THRESHOLDS.length - 1]);
    }

    private void sleep(double millis) {
        try {
            long ms = Math.round(millis);
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private double randomDouble(double min, double max) {
        return min + (max - min) * random.nextDouble();
    }

    /**
     * Load mouse data from resource: mousedata.json
     * We assume it has the structure:
     * {
     *   "12": {
     *     "N":  [ [ [dx...],[dy...] ], ... ],
     *     "NE": [ ... ],
     *     ...
     *   },
     *   "18": { ... },
     *   ...
     * }
     */
    private void loadMouseData() {
        Gson gson = new Gson();
        try (InputStream is = getClass().getResourceAsStream("/mousedata.json")) {
            if (is == null) {
                // Logger.log("Error: mousedata.json not found in resources.");
            } else {
                Reader reader = new InputStreamReader(is);
                mouseData = gson.fromJson(reader, new TypeToken<Map<String, Object>>() {}.getType());
                // Logger.log("Mouse data loaded successfully with keys: " + mouseData.keySet());
            }
        } catch (Exception e) {
            // Logger.log("Error loading mouse data: " + e.getMessage());
        }
    }

    private double distance(Point p1, Point p2) {
        return p1.distance(p2);
    }

    /**
     * WeightedEasing is a small helper for random selection of EasingFunction by weight.
     */
    private static class WeightedEasing {
        public EasingFunction function;
        public double weight;
        public WeightedEasing(EasingFunction function, double weight) {
            this.function = function;
            this.weight = weight;
        }
    }

    /**
     * Easing functions used to shape timing distribution over sub-steps.
     */
    /**
     * Easing functions used to shape timing distribution over sub-steps.
     */
    private enum EasingFunction {
        EASE_LINEAR {
            @Override
            public double apply(double t) {
                return t;
            }
        },
        // EASE_OUT_QUART {
            // @Override
            // public double apply(double t) {
                // return 1 - Math.pow(1 - t, 4);
            // }
        // },
        // EASE_IN_OUT_QUART {
            // @Override
            // public double apply(double t) {
                // if (t < 0.5) {
                    // return 8 * Math.pow(t, 4);
                // } else {
                    // return 1 - Math.pow(-2 * t + 2, 4) / 2;
                // }
            // }
        // },
        EASE_OUT_CUBIC {
            @Override
            public double apply(double t) {
                return 1 - Math.pow(1 - t, 3);
            }
        },
        EASE_IN_OUT_CUBIC {
            @Override
            public double apply(double t) {
                return (t < 0.5)
                    ? 4 * t * t * t
                    : 1 - Math.pow(-2 * t + 2, 3) / 2;
            }
        };
        public abstract double apply(double t);
    }
}
