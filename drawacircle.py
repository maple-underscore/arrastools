import math
import threading
import time
import numpy as np
import mss

from pynput import mouse
from pynput.mouse import Controller as MouseController, Button

# Circle radius in pixels
s = 400  # adjust as needed

# Drawing settings
circle_duration = 0  # seconds to complete one circle
min_steps = 0       # minimum number of segments in the circle

mousec = MouseController()
sct = mss.mss()

_drawing = False
_lock = threading.Lock()
_triggered = threading.Event()
_listener = None

# Two-point rectangle selection
_first_click = None
_second_click = None

def _find_white_center(left, top, width, height, thr=200):
    # Capture region
    bbox = {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}
    shot = sct.grab(bbox)
    # shot pixels are BGRA
    arr = np.frombuffer(shot.raw, dtype=np.uint8).reshape(shot.height, shot.width, 4)
    rgb = arr[:, :, :3][:, :, ::-1]  # to RGB

    # Threshold for "white"
    mask = (rgb[:, :, 0] >= thr) & (rgb[:, :, 1] >= thr) & (rgb[:, :, 2] >= thr)

    if not mask.any():
        # Loosen threshold, then fallback to rect center
        thr2 = max(150, thr - 50)
        mask = (rgb[:, :, 0] >= thr2) & (rgb[:, :, 1] >= thr2) & (rgb[:, :, 2] >= thr2)
        if not mask.any():
            cx = width / 2.0
            cy = height / 2.0
            return (left + cx, top + cy)

    ys, xs = np.nonzero(mask)
    cx = xs.mean()
    cy = ys.mean()
    return (left + cx, top + cy)

def _draw_circle(center, radius, duration, steps):
    global _drawing
    with _lock:
        if _drawing:
            return
        _drawing = True
    try:
        cx, cy = int(center[0]), int(center[1])

        # Move to starting point on circumference (angle = 0)
        start_x = int(cx + radius)
        start_y = int(cy)
        mousec.position = (start_x, start_y)
        time.sleep(0.01)

        # Hold mouse button and trace the circle
        mousec.press(Button.left)
        try:
            steps = max(steps, int(2 * math.pi * radius))
            sleep_per_step = max(0.0005, duration / steps)

            for i in range(1, steps + 1):
                theta = 2 * math.pi * (i / steps)
                x = int(cx + radius * math.cos(theta))
                y = int(cy + radius * math.sin(theta))
                mousec.position = (x, y)
                time.sleep(sleep_per_step)
        finally:
            mousec.release(Button.left)
    finally:
        with _lock:
            _drawing = False

def _maybe_process_rectangle():
    global _first_click, _second_click, _listener
    if _first_click is None or _second_click is None:
        return
    if _triggered.is_set():
        return
    _triggered.set()

    x1, y1 = _first_click
    x2, y2 = _second_click
    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    if width == 0 or height == 0:
        # Fallback to single point; draw around it
        center = (left, top)
    else:
        center = _find_white_center(left, top, width, height, thr=200)

    t = threading.Thread(
        target=_draw_circle,
        args=(center, s, circle_duration, min_steps),
        daemon=False
    )
    t.start()

    if _listener is not None:
        _listener.stop()

def on_click(x, y, button, pressed):
    global _first_click, _second_click
    if button is Button.left and not pressed and not _triggered.is_set():
        if _first_click is None:
            _first_click = (int(x), int(y))
            print(f"First corner: {_first_click}. Click second corner.")
        else:
            _second_click = (int(x), int(y))
            print(f"Second corner: {_second_click}. Processing...")
            _maybe_process_rectangle()

if __name__ == "__main__":
    print(f"Click two opposite corners of a rectangle that contains a white circle (RGB >= 200).")
    print(f"A single circle of radius {s}px will be drawn centered on the detected circle.")
    with mouse.Listener(on_click=on_click) as listener:
        _listener = listener
        listener.join()