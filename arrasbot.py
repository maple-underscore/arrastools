import mss, time, numpy as np
from datetime import datetime
from pynput import mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
sct = mss.mss()
disconnected = True
died = False
monitor = sct.monitors[1]  # Primary monitor
controller = KeyboardController()
mouse = MouseController()

def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

def timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")

print(f"Bot initialized at {timestamp()}")

lastmove = time.time()
while True:
    rgb = get_pixel_rgb(27, 930)
    if (rgb == (167, 81, 68) or rgb == (138, 27, 34) or rgb == (201, 92, 75)):
        print(f"Disconnected at {timestamp()}")
        controller.release("w")
        controller.release("a")
        if not disconnected:
            print("Disconnected, attempting to reconnect")
        disconnected = True
        mouse.position = (922, 767)
        for _ in range(100):
            mouse.click(Button.left, 1)
            time.sleep(0.002)
    elif rgb == (176, 100, 81) and not disconnected and not died:
        print("Checking death")
        time.sleep(3)
        if rgb == (176, 100, 81) and not disconnected and not died:
            print(f"Died at {timestamp()}")
            died = True
            controller.press(Key.enter)
            time.sleep(0.1)
            controller.release(Key.enter)
            time.sleep(0.1)
        else:
            pass
    elif rgb == (223, 116, 90) and (disconnected or died):
        print(f"Successfully reconnected at {timestamp()}")
        disconnected = False
        died = False
        controller.tap("j")
        controller.tap("i")
        controller.tap("y")
        controller.tap("c")
        time.sleep(0.1)
        controller.press("`")
        time.sleep(0.1)
        controller.tap("i")
        time.sleep(0.1)
        controller.release("`")
        time.sleep(0.1)
        controller.press("w")
        time.sleep(0.1)
        controller.press("a")
        time.sleep(0.1)
    if time.time() - lastmove > 30:
        mouse.position = (mouse.position[0]+1, mouse.position[1])
        time.sleep(0.1)
        mouse.position = (mouse.position[0]-1, mouse.position[1])
        lastmove = time.time()
        mouse.click(Button.left, 1)