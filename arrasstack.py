from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Key, Listener as KeyboardListener
import time, threading, math

time.sleep(3)

# Define sequence as (angle_degrees, radius)
# 0° = right, 90° = down, 180° = left, 270° = up
radius = 10  # Distance from center in pixels
stacks = [
    (0, radius),      # right
    (15, radius),     # down
    (30, radius),    # left
    (45, radius),    # up
]

stop_flag = False

def on_press(key):
    global stop_flag
    if key == Key.esc:
        stop_flag = True
        return False  # Stop listener

# Start keyboard listener in background
listener = KeyboardListener(on_press=on_press)
listener.daemon = True
listener.start()

mouse = MouseController()
keyboard = KeyboardController()
print("Stack macro running. Press ESC to stop.")

while not stop_flag:
    pos = mouse.position
    for angle_deg, r in stacks:
        if stop_flag:
            break
        # Convert angle to radians and calculate position
        angle_rad = math.radians(angle_deg)
        x = pos[0] + int(r * math.cos(angle_rad))
        y = pos[1] + int(r * math.sin(angle_rad))
        mouse.position = (x, y)
        time.sleep(0.1)

print("Stack macro stopped.")
