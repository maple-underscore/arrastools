#!/usr/bin/env python3
"""
nodebuster.py - Zigzag mouse movement automation
Press 's' to toggle zigzag pattern on/off
Press 'Esc' to exit
"""

import time
import threading
import platform
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Listener, Key

# Configuration
MOVE_SPEED = 5000  # pixels per second (configurable)
ZIGZAG_START = (1, 61)
ZIGZAG_END_Y = 1139
ZIGZAG_END_X = 1919  # Maximum X position before resetting
ZIGZAG_STEP_X = 239
CENTER_POS = (960, 600)
WAIT_TIME = 5  # seconds between zigzag cycles

# Platform detection
PLATFORM = platform.system().lower()
print(f"Running on platform: {PLATFORM}")

# Controllers
mouse = MouseController()

# State
zigzag_active = False
zigzag_thread = None


def smooth_move(target_x, target_y, speed=MOVE_SPEED):
    """Move mouse smoothly to target position at specified speed (px/s)"""
    start_x, start_y = mouse.position
    dx = target_x - start_x
    dy = target_y - start_y
    distance = (dx**2 + dy**2) ** 0.5
    
    if distance == 0:
        return
    
    # Calculate duration based on speed
    duration = distance / speed
    steps = max(int(duration * 60), 1)  # 60 steps per second
    
    for i in range(steps + 1):
        if not zigzag_active:  # Allow interruption
            return
        t = i / steps
        x = start_x + dx * t
        y = start_y + dy * t
        mouse.position = (int(x), int(y))
        time.sleep(duration / steps)


def zigzag_pattern():
    """Execute the zigzag mouse movement pattern"""
    global zigzag_active
    
    while zigzag_active:
        # Teleport to start position at beginning of each cycle
        mouse.position = ZIGZAG_START
        
        x = ZIGZAG_START[0]
        direction = 1  # 1 for down, -1 for up
        
        # Zigzag until we reach the end X position
        while zigzag_active and x < (ZIGZAG_END_X):
            # Move vertically
            target_y = ZIGZAG_END_Y if direction == 1 else ZIGZAG_START[1]
            smooth_move(x, target_y)
            
            if not zigzag_active:
                break
            
            # Move horizontally to next column
            x += ZIGZAG_STEP_X
            if x < ZIGZAG_END_X:  # Only move horizontally if not at end
                smooth_move(x, target_y)
            
            # Flip direction for next vertical movement
            direction *= -1
        
        if not zigzag_active:
            break
        
        # Teleport to center
        mouse.position = CENTER_POS
        
        # Wait before next cycle
        for _ in range(int(WAIT_TIME * 10)):
            if not zigzag_active:
                break
            time.sleep(0.1)
            # Reset to start
            x = ZIGZAG_START[0]


def start_zigzag():
    """Start the zigzag pattern in a background thread"""
    global zigzag_thread
    
    if zigzag_thread is None or not zigzag_thread.is_alive():
        zigzag_thread = threading.Thread(target=zigzag_pattern, daemon=True)
        zigzag_thread.start()
        print("Zigzag pattern started")


def stop_zigzag():
    """Stop the zigzag pattern"""
    print("Zigzag pattern stopped")


def on_press(key):
    """Handle key press events"""
    global zigzag_active
    
    try:
        if hasattr(key, 'char') and key.char == 's':
            # Toggle zigzag
            zigzag_active = not zigzag_active
            if zigzag_active:
                start_zigzag()
            else:
                stop_zigzag()
                
        elif key == Key.esc:
            print("Exiting...")
            return False  # Stop listener
            
    except AttributeError:
        pass


def main():
    """Main entry point"""
    print("Nodebuster - Zigzag Mouse Automation")
    print("=" * 50)
    print(f"Move speed: {MOVE_SPEED} px/s")
    print(f"Zigzag pattern: ({ZIGZAG_START[0]}, {ZIGZAG_START[1]}) to (x={ZIGZAG_END_X}, y={ZIGZAG_END_Y})")
    print(f"Step X: {ZIGZAG_STEP_X} px")
    print(f"Center position: {CENTER_POS}")
    print(f"Wait time: {WAIT_TIME}s")
    print("=" * 50)
    print("Press 's' to toggle zigzag pattern")
    print("Press 'Esc' to exit")
    print("=" * 50)
    
    # Start keyboard listener
    with Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    main()
