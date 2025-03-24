import org.dreambot.api.Client;
import org.dreambot.api.script.AbstractScript;
import org.dreambot.api.script.Category;
import org.dreambot.api.script.ScriptManifest;
import org.dreambot.api.utilities.Logger;
import org.dreambot.api.input.Mouse;
import org.dreambot.api.utilities.Sleep;

import java.awt.*;
import java.util.LinkedList;
import java.util.Random;

@ScriptManifest(name = "RandomMouseMover", description = "Moves mouse to random points with various movement behaviors.", author = "Vexus", version = 2.0, category = Category.MISC)
public class RandomMouseMover extends AbstractScript {
    private static final int TRAIL_SIZE = 200;
    private final LinkedList<Point> mouseTrail = new LinkedList<>();
    private final Random random = new Random();
    private Point targetPoint;
    
    private boolean useSameQuadrant = true;
    private int offscreenMoveCount = 0;
    private int maxOffscreenMoves = 2;

    @Override
    public void onStart() {
        Mouse.setMouseAlgorithm(new SmartMouseMultiDir());
        new Thread(this::updateMouseTrail).start();
        
        // Configure the SimulateAFK class settings
        SimulateAFK.setFocusManipulation(true);
        SimulateAFK.setFocusChances(70, 30);
        
        log("Starting RandomMouseMover script v2.0 with SimulateAFK integration...");
    }

    @Override
    public int onLoop() {

        if (!SimulateAFK.isMouseOffScreen()) {
            Mouse.move(getRandomTargetPoint());
            Sleep.sleep(333, 666);
            Mouse.move(getRandomTargetPoint());
            Sleep.sleep(333, 666);
            Mouse.move(getRandomTargetPoint());
            Sleep.sleep(333, 666);

            // We're on-screen, move off-screen
            targetPoint = Mouse.getPosition(); // Store current position before moving
            offscreenMoveCount = 0;
            return SimulateAFK.moveMouseOut(useSameQuadrant);
        } else {
            // We're off-screen, either move to another off-screen point or come back inside
            offscreenMoveCount++;
            
            if (offscreenMoveCount < maxOffscreenMoves) {
                // Move to another off-screen location before coming back
                return SimulateAFK.moveMouseToAnotherOffScreenLocation(useSameQuadrant);
            } else {
                // Come back on screen
                return SimulateAFK.moveMouseIn();
            }
        }

    }

    @Override
    public void onExit() {
        log("Stopping RandomMouseMover script...");
    }

    /**
     * Continuously updates the mouse trail for visualization.
     */
    private void updateMouseTrail() {
        while (true) {
            try {
                synchronized (mouseTrail) { // Synchronize access to mouseTrail
                    mouseTrail.add(Mouse.getPosition());
                    if (mouseTrail.size() > TRAIL_SIZE) {
                        mouseTrail.removeFirst();
                    }
                }
                Thread.sleep(10);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Generates a random target point within the screen area.
     *
     * @return A new random Point.
     */
    private Point getRandomTargetPoint() {
		Canvas canvas = Client.getCanvas();
        int x = random.nextInt(canvas.getWidth() - 200) + 100;
        int y = random.nextInt(canvas.getHeight() - 200) + 100;
        return new Point(x, y);
    }

    @Override
    public void onPaint(Graphics g) {
        // Draw the mouse trail
        g.setColor(Color.CYAN);
        Point prevPoint = null;

        synchronized (mouseTrail) { // Synchronize access to mouseTrail
            for (Point point : mouseTrail) {
                if (prevPoint != null) {
                    g.drawLine(prevPoint.x, prevPoint.y, point.x, point.y);
                }
                prevPoint = point;
            }
        }

        // Display status text with focus information
        g.setColor(Color.WHITE);
        g.drawString("Status: " + (SimulateAFK.isMouseOffScreen() ? "Off-screen" : "On-screen") + 
                     " | Focus: " + (Client.hasFocus() ? "Yes" : "No"), 10, 20);
        g.drawString("Move count: " + offscreenMoveCount + " / " + maxOffscreenMoves + 
                     " | Same quadrant: " + (useSameQuadrant ? "Yes" : "No"), 10, 40);
    }
}