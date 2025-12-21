import mss, numpy as np, time
from pynput import mouse
from PIL import Image
from pynput.keyboard import Controller, Key
controller = Controller()

def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])
def on_click(x, y, button, pressed):
    if pressed:
        rgb = get_pixel_rgb(x, y)
        print(f"Clicked at ({x}, {y}) | sRGB: {rgb}")
        controller.tap(Key.enter)
        time.sleep(0.1)
        controller.type(str(rgb))
        time.sleep(0.1)
        controller.tap(Key.enter)

# Capture screen once using mss
with mss.mss() as sct:
    monitor = sct.monitors[1]  # Primary monitor
    screenshot = sct.grab(monitor)
    image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

# Start mouse listener
with mouse.Listener(on_click=on_click) as listener:
    print("Click anywhere on the screen to inspect pixel color (Press Ctrl+C to exit)...")
    listener.join()
