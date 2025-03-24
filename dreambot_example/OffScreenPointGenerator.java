import org.dreambot.api.methods.Calculations;
import java.awt.Point;

/**
 * Utility class for generating points outside of the screen bounds.
 * Provides customizable methods to create points in different areas around the screen.
 */
public class OffScreenPointGenerator {
    
    /**
     * Generates a random point outside the screen boundaries.
     * 
     * @param screenWidth The width of the screen
     * @param screenHeight The height of the screen
     * @return A Point object outside the screen bounds
     */
    public static Point getOffScreenPoint(int screenWidth, int screenHeight) {
        int side = Calculations.random(0, 3); // 0=top, 1=right, 2=bottom, 3=left
        return getOffScreenPoint(screenWidth, screenHeight, side);
    }
    
    /**
     * Generates a point outside the screen on a specific side.
     * 
     * @param screenWidth The width of the screen
     * @param screenHeight The height of the screen
     * @param side The side to generate the point on (0=top, 1=right, 2=bottom, 3=left)
     * @return A Point object outside the screen on the specified side
     */
    public static Point getOffScreenPoint(int screenWidth, int screenHeight, int side) {
        int x, y;
        
        switch (side) {
            case 0: // Top
                x = Calculations.random(-100, screenWidth + 100);
                y = Calculations.random(-200, -50);
                break;
            case 1: // Right
                x = Calculations.random(screenWidth + 50, screenWidth + 200);
                y = Calculations.random(-100, screenHeight + 100);
                break;
            case 2: // Bottom
                x = Calculations.random(-100, screenWidth + 100);
                y = Calculations.random(screenHeight + 50, screenHeight + 200);
                break;
            default: // Left
                x = Calculations.random(-200, -50);
                y = Calculations.random(-100, screenHeight + 100);
                break;
        }
        
        return new Point(x, y);
    }
    
    /**
     * Determines if two points are in the same quadrant relative to the screen.
     * 
     * @param p1 First point to check
     * @param p2 Second point to check
     * @param screenWidth The width of the screen
     * @param screenHeight The height of the screen
     * @return true if both points are in the same quadrant/edge, false otherwise
     */
    public static boolean arePointsInSameQuadrant(Point p1, Point p2, int screenWidth, int screenHeight) {
        boolean p1Left = p1.x < 0;
        boolean p1Top = p1.y < 0;
        boolean p1Right = p1.x > screenWidth;
        boolean p1Bottom = p1.y > screenHeight;
        
        boolean p2Left = p2.x < 0;
        boolean p2Top = p2.y < 0;
        boolean p2Right = p2.x > screenWidth;
        boolean p2Bottom = p2.y > screenHeight;
        
        // Check if both points are in the same quadrant/edge
        return (p1Left && p2Left) || (p1Right && p2Right) || 
               (p1Top && p2Top) || (p1Bottom && p2Bottom);
    }
    
    /**
     * Gets a random off-screen point that is in a different quadrant than the given point.
     * 
     * @param currentPoint The current point to avoid being in the same quadrant with
     * @param screenWidth The width of the screen
     * @param screenHeight The height of the screen
     * @return A Point object in a different quadrant than the current point
     */
    public static Point getDifferentQuadrantPoint(Point currentPoint, int screenWidth, int screenHeight) {
        Point newPoint = getOffScreenPoint(screenWidth, screenHeight);
        
        // Ensure the new point is in a different area than the current point
        int attempts = 0;
        while (arePointsInSameQuadrant(currentPoint, newPoint, screenWidth, screenHeight) && attempts < 10) {
            newPoint = getOffScreenPoint(screenWidth, screenHeight);
            attempts++;
        }
        
        return newPoint;
    }

        /**
     * Gets a random off-screen point that is in the same quadrant as the given point,
     * but at a different position.
     * 
     * @param currentPoint The current point to determine which quadrant to use
     * @param screenWidth The width of the screen
     * @param screenHeight The height of the screen
     * @return A different Point object in the same quadrant as the current point
     */
    public static Point getSameQuadrantPoint(Point currentPoint, int screenWidth, int screenHeight) {
        // Determine which side/quadrant the current point is in
        int side;
        if (currentPoint.y < 0) {
            side = 0; // Top
        } else if (currentPoint.x > screenWidth) {
            side = 1; // Right
        } else if (currentPoint.y > screenHeight) {
            side = 2; // Bottom
        } else {
            side = 3; // Left
        }
        
        // Generate a new point in the same quadrant
        Point newPoint = getOffScreenPoint(screenWidth, screenHeight, side);
        
        // Ensure the new point is not too close to the current point (at least 100px apart)
        int attempts = 0;
        double distance = Math.sqrt(Math.pow(newPoint.x - currentPoint.x, 2) + Math.pow(newPoint.y - currentPoint.y, 2));
        
        while (distance < 100 && attempts < 10) {
            newPoint = getOffScreenPoint(screenWidth, screenHeight, side);
            distance = Math.sqrt(Math.pow(newPoint.x - currentPoint.x, 2) + Math.pow(newPoint.y - currentPoint.y, 2));
            attempts++;
        }
        
        return newPoint;
    }
}