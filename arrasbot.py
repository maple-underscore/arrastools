import mss, time, numpy as np
from datetime import datetime
from pynput import mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import os
from pathlib import Path

init = time.time()
start1 = time.time()
print("Initializing variables")
sct = mss.mss()
disconnected = True
died = False
monitor = sct.monitors[1]  # Primary monitor
start1 = time.time()-start1

start2 = time.time()
print("Initializing controllers")
controller = KeyboardController()
mouse = MouseController()
start2 = time.time()-start2

start3 = time.time()
print("Defining functions")
def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

def timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def take_screenshot(reason="periodic"):
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
    current_time = timestamp()
    filename = os.path.join(SCREENSHOT_DIR, f"{current_time}_{reason}.png")
    screenshot = sct.grab(monitor)
    mss.tools.to_png(screenshot.rgb, screenshot.size, output=filename)
    print(f"Screenshot saved: {filename} at {timestamp()}")
    with open("arrasbot.log", "a") as log_file:
        log_file.write(f"Screenshot saved: {filename} at {timestamp()}\n")
        log_file.close()
start3 = time.time()-start3

start4 = time.time()
print("Creating directories")
HOME = str(Path.home())
foldername = f"arrasbot_{timestamp()}"
SCREENSHOT_DIR = os.path.join(HOME, "Desktop", foldername)
start4 = time.time()-start4

print("Creating log file")
filename = f"arrasbot_{timestamp()}.log"
with open(filename, "a") as log_file:
    print(f"Bot initialized at {timestamp()}")
    init = time.time()-init
    log_file.write(f"""
=============== DEBUG ===============
Display size: {monitor['width']}x{monitor['height']}
Screenshot directory: {SCREENSHOT_DIR}
Created variables in {round(start1, 3)} seconds
Created controllers in {round(start2, 3)} seconds
Defined functions in {round(start3, 3)} seconds
Created directories in {round(start4, 3)} seconds
Bot initialized in {round(init, 3)} seconds

================ LOG ================
""")
    log_file.write(f"Bot initialized at {timestamp()}\n")
    lastmove = time.time()
    lastscreenshot = time.time()
    while True:
        rgb = get_pixel_rgb(27, 930)
        if (rgb == (167, 81, 68) or rgb == (138, 27, 34) or rgb == (201, 92, 75)):
            if not disconnected:
                take_screenshot("disconnected")
            print(f"Disconnected at {timestamp()}")
            log_file.write(f"Disconnected at {timestamp()}\n")
            controller.release("w")
            controller.release("a")
            if not disconnected:
                print(f"Disconnected, attempting to reconnect at {timestamp()}")
                log_file.write(f"Disconnected, attempting to reconnect at {timestamp()}\n")
            disconnected = True
            mouse.position = (922, 767)
            for _ in range(200):
                mouse.click(Button.left, 1)
                time.sleep(0.03)
        elif rgb == (176, 100, 81) and not disconnected and not died:
            print(f"Checking death at {timestamp()}")
            log_file.write(f"Checking death at {timestamp()}\n")
            time.sleep(3)
            if rgb == (176, 100, 81) and not disconnected and not died:
                take_screenshot("died")
                print(f"Died at {timestamp()}")
                log_file.write(f"Died at {timestamp()}\n")
                died = True
                controller.tap(Key.enter)
            else:
                pass
        elif rgb == (223, 116, 90) and (disconnected or died):
            take_screenshot("reconnected")
            print(f"Successfully reconnected at {timestamp()}")
            log_file.write(f"Successfully reconnected at {timestamp()}\n")
            disconnected = False
            died = False
            controller.tap("j")
            controller.tap("i")
            controller.tap("y")
            controller.tap("c")
            time.sleep(0.1)
            controller.tap(Key.enter)
            controller.type("$arena team 1")
            controller.tap(Key.enter)
            time.sleep(0.1)
            controller.tap(Key.enter)
            controller.type("$arena size 500 500")
            controller.tap(Key.enter)
            time.sleep(0.1)
            controller.tap(Key.enter)
            controller.type("$arena spawnpoint 0 0")
            controller.tap(Key.enter)
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
        if time.time() - lastscreenshot > 60:
            take_screenshot()
            lastscreenshot = time.time()
        if time.time() - lastmove > 30:
            mouse.position = (mouse.position[0]+1, mouse.position[1])
            time.sleep(0.1)
            mouse.position = (mouse.position[0]-1, mouse.position[1])
            lastmove = time.time()