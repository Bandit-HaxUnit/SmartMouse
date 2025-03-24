import org.dreambot.api.Client;
import org.dreambot.api.methods.Calculations;
import org.dreambot.api.input.Mouse;
import org.dreambot.api.utilities.Logger;

import java.awt.*;

/**
 * Utility class for simulating AFK behavior with mouse movements and focus control.
 * Provides methods to move the mouse off-screen and back with configurable behavior.
 */
public class SimulateAFK {
    
    // Default delay ranges for mouse movements (in milliseconds)
    private static final int DEFAULT_MIN_DELAY_OUTSIDE = 1000;
    private static final int DEFAULT_MAX_DELAY_OUTSIDE = 2000;
    private static final int DEFAULT_MIN_DELAY_INSIDE = 4000;
    private static final int DEFAULT_MAX_DELAY_INSIDE = 6000;
    
    // Focus manipulation settings
    private static boolean shouldToggleFocus = true;
    private static int loseChance = 70;
    private static int toggleChance = 30;
    
    // Tracking current state
    private static boolean isOffScreen = false;
    private static Point lastTargetPoint = null;
    
    /**
     * Moves the mouse outside the screen to a random location.
     * 
     * @return The delay time in milliseconds before the next action should occur
     */
    public static int moveMouseOut() {
        return moveMouseOut(false);
    }
    
    /**
     * Moves the mouse outside the screen to a random location.
     * 
     * @param sameSideReentry Whether to allow re-entry on the same side
     * @return The delay time in milliseconds before the next action should occur
     */
    public static int moveMouseOut(boolean sameSideReentry) {
        Canvas canvas = Client.getCanvas();
        int screenWidth = canvas.getWidth();
        int screenHeight = canvas.getHeight();
        
        // Generate an off-screen point
        Point targetPoint = OffScreenPointGenerator.getOffScreenPoint(screenWidth, screenHeight);
        Logger.log("SimulateAFK: Moving outside screen to: " + targetPoint.x + ", " + targetPoint.y);
        
        // Randomly decide if we should lose focus
        if (shouldToggleFocus && randomChance(loseChance)) {
            loseFocus();
        }
        
        // Move the mouse and update state
        Mouse.move(targetPoint);
        lastTargetPoint = targetPoint;
        isOffScreen = true;
        
        Logger.log("SimulateAFK: Mouse moved outside screen. Focus status: " + (Client.hasFocus() ? "Focused" : "Not focused"));
        
        // Return suggested delay
        return Calculations.random(DEFAULT_MIN_DELAY_OUTSIDE, DEFAULT_MAX_DELAY_OUTSIDE);
    }
    
    /**
     * Moves the mouse to another position outside the screen.
     * 
     * @param sameSideReentry Whether to move to another position on the same side
     * @return The delay time in milliseconds before the next action should occur
     */
    public static int moveMouseToAnotherOffScreenLocation(boolean sameSideReentry) {
        if (lastTargetPoint == null) {
            return moveMouseOut(sameSideReentry);
        }
        
        Canvas canvas = Client.getCanvas();
        int screenWidth = canvas.getWidth();
        int screenHeight = canvas.getHeight();
        
        Point targetPoint;
        if (sameSideReentry) {
            // Move to another point in the same quadrant
            targetPoint = OffScreenPointGenerator.getSameQuadrantPoint(lastTargetPoint, screenWidth, screenHeight);
        } else {
            // Move to a different quadrant
            targetPoint = OffScreenPointGenerator.getDifferentQuadrantPoint(lastTargetPoint, screenWidth, screenHeight);
        }
        
        Logger.log("SimulateAFK: Moving to another off-screen point: " + targetPoint.x + ", " + targetPoint.y);
        
        // Toggle focus sometimes during off-screen movement
        if (shouldToggleFocus && randomChance(toggleChance)) {
            if (Client.hasFocus()) {
                loseFocus();
            } else {
                gainFocus();
            }
        }
        
        Mouse.move(targetPoint);
        lastTargetPoint = targetPoint;
        
        Logger.log("SimulateAFK: Mouse moved to another off-screen position. Focus status: " + 
                  (Client.hasFocus() ? "Focused" : "Not focused"));
        
        return Calculations.random(DEFAULT_MIN_DELAY_OUTSIDE, DEFAULT_MAX_DELAY_OUTSIDE);
    }
    
    /**
     * Moves the mouse back inside the screen to a random location.
     * 
     * @return The delay time in milliseconds before the next action should occur
     */
    public static int moveMouseIn() {
        // Generate a random point within the screen
        Point targetPoint = getRandomInScreenPoint();
        Logger.log("SimulateAFK: Moving back inside screen to: " + targetPoint.x + ", " + targetPoint.y);
        
        // Gain focus when returning to screen if not already focused
        if (shouldToggleFocus && !Client.hasFocus()) {
            gainFocus();
        }
        
        Mouse.move(targetPoint);
        isOffScreen = false;
        lastTargetPoint = targetPoint;
        
        Logger.log("SimulateAFK: Mouse moved back inside screen. Focus status: " + 
                  (Client.hasFocus() ? "Focused" : "Not focused"));
        
        return Calculations.random(DEFAULT_MIN_DELAY_INSIDE, DEFAULT_MAX_DELAY_INSIDE);
    }
    
    /**
     * Checks if the mouse is currently off-screen.
     * 
     * @return true if the mouse is off-screen, false otherwise
     */
    public static boolean isMouseOffScreen() {
        return !Mouse.isMouseInScreen();
    }
    
    /**
     * Sets whether focus manipulation should be enabled.
     * 
     * @param toggle true to enable focus manipulation, false to disable
     */
    public static void setFocusManipulation(boolean toggle) {
        shouldToggleFocus = toggle;
    }
    
    /**
     * Sets the chance percentages for focus manipulation.
     * 
     * @param loseFocusChance The percentage chance to lose focus when moving off-screen (0-100)
     * @param toggleFocusChance The percentage chance to toggle focus during off-screen movements (0-100)
     */
    public static void setFocusChances(int loseFocusChance, int toggleFocusChance) {
        loseChance = Math.min(100, Math.max(0, loseFocusChance));
        toggleChance = Math.min(100, Math.max(0, toggleFocusChance));
    }
    
    /**
     * Sets custom delay ranges for mouse movements.
     * 
     * @param minOutsideDelay Minimum delay when outside screen (ms)
     * @param maxOutsideDelay Maximum delay when outside screen (ms)
     * @param minInsideDelay Minimum delay when inside screen (ms)
     * @param maxInsideDelay Maximum delay when inside screen (ms)
     */
    public static void setDelayRanges(int minOutsideDelay, int maxOutsideDelay, int minInsideDelay, int maxInsideDelay) {
        // Implementation would set the static delay range fields
    }
    
    /**
     * Generates a random point within the screen area away from edges.
     *
     * @return A new random Point within screen bounds
     */
    private static Point getRandomInScreenPoint() {
        Canvas canvas = Client.getCanvas();
        int screenWidth = canvas.getWidth();
        int screenHeight = canvas.getHeight();

        // Ensure we don't end up near the edge
        int margin = 150;
        int x = Calculations.random(margin, screenWidth - margin);
        int y = Calculations.random(margin, screenHeight - margin);
        
        return new Point(x, y);
    }
    
    /**
     * Checks if the RuneScape client currently has focus.
     *
     * @return True if client is focused, otherwise false.
     */
    private static boolean hasFocus() {
        boolean focused = Client.hasFocus();
        return focused;
    }

    /**
     * Attempts to gain focus for the client if it doesn't already have it.
     */
    private static void gainFocus() {
        if (!Client.hasFocus()) {
            Logger.log("SimulateAFK: Attempting to gain client focus");
            Client.getInstance().getApplet().requestFocusInWindow();
            Client.gainFocus();
            Logger.log("SimulateAFK: Focus gained: " + Client.hasFocus());
        }
    }

    /**
     * Causes the client to lose focus if it currently has it.
     */
    private static void loseFocus() {
        if (Client.hasFocus()) {
            Logger.log("SimulateAFK: Attempting to lose client focus");
            Client.loseFocus();
            Logger.log("SimulateAFK: Focus lost: " + !Client.hasFocus());
        }
    }
    
    /**
     * Returns true with the given percentage chance.
     */
    private static boolean randomChance(int percentage) {
        return Calculations.random(1, 100) <= percentage;
    }
}