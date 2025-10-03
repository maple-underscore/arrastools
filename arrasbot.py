import mss, time, numpy as np, os
from datetime import datetime
from pynput import mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
from pathlib import Path
from ping3 import ping

init = time.time()
start1 = time.time()
print("Initializing variables")
sct = mss.mss()
disconnected = True
died = False
banned = False
monitor = sct.monitors[1]  # Primary monitor
start1 = time.time()-start1

start2 = time.time()
print("Initializing controllers")
controller = KeyboardController()
mouse = MouseController()
start2 = time.time()-start2

start3 = time.time()
print("Defining functions")
def getping():
    target = "arras.io"
    return ping(target)

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
SCREENSHOT_DIR = os.path.join(HOME, "Desktop", "arrasbot", foldername)
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
    lastdeath = time.time()
    lastdisconnect = time.time()
    while True:
        if get_pixel_rgb(1021, 716) == (152, 232, 241):
            disconnected = True
            log_file.write(f"Backroom crashed at {timestamp()}\n")
            print(f"Backroom crashed at {timestamp()}")
            mouse.position = (1021, 716)
            time.sleep(0.1)
            mouse.click(Button.left, 1)
            time.sleep(0.1)
            mouse.position = (132, 105)
            time.sleep(0.1)
            mouse.click(Button.left, 1)
            time.sleep(2)
            mouse.position = (923, 526)
            time.sleep(0.1)
            mouse.click(Button.left, 1)
        if get_pixel_rgb(855, 255) == (150, 150, 159):
            log_file.write(f"Detected backroom crash at {timestamp()}\n")
            print(f"Detected backroom crash at {timestamp()}")
            controller.press("`")
            time.sleep(0.1)
            controller.tap("j")
            time.sleep(0.1)
            controller.release("`")
        rgb = get_pixel_rgb(27, 930)
        if (rgb == (167, 81, 68) or rgb == (138, 27, 34) or rgb == (201, 92, 75) or rgb == (199, 118, 98) or rgb == (213, 114, 93)):
            if get_pixel_rgb(686, 650) == (231, 137, 109) or get_pixel_rgb(837, 675) == (231, 137, 109):
                log_file.write(f"Temporarily banned at {timestamp()}\n")
                print(f"Temporarily banned at {timestamp()}")
                banned = True
                mouse.position = (922, 767)
                while banned:
                    if not get_pixel_rgb(700, 674) == (231, 137, 109):
                        banned = False
                    else:
                        time.sleep(10)
                        mouse.click(Button.left, 1)
            else:
                if not disconnected:
                    take_screenshot("disconnected")
                    log_file.write(f"[DISCONNECTED] screenshot taken at {timestamp()}\n")
                    lastdisconnect = time.time()
                if time.time() - lastdisconnect >= 20:
                    log_file.write(f"Temporarily banned at {timestamp()}\n")
                    print(f"Temporarily banned at {timestamp()}")
                    banned = True
                    mouse.position = (922, 767)
                    rgb = get_pixel_rgb(700, 674)
                    while banned:
                        if not rgb == (167, 81, 68) or rgb == (138, 27, 34) or rgb == (201, 92, 75) or rgb == (199, 118, 98) or rgb == (213, 114, 93):
                            banned = False
                        else:
                            time.sleep(10)
                            mouse.click(Button.left, 1)
                print(f"Disconnected at {timestamp()}")
                log_file.write(f"Disconnected at {timestamp()}\n")
                controller.release("w")
                controller.release("a")
                if not disconnected:
                    print(f"Disconnected, attempting to reconnect at {timestamp()}")
                    log_file.write(f"Disconnected, attempting to reconnect at {timestamp()}\n")
                disconnected = True
                mouse.position = (922, 767)
                pingm = getping()
                for _ in range(200):
                    mouse.click(Button.left, 1)
                    time.sleep(pingm/1000)
        elif rgb == (176, 100, 81) and ((not disconnected or not died) or ((time.time() - lastdeath) > 5 and died)):
            print(f"Checking death at {timestamp()}")
            log_file.write(f"Checking death at {timestamp()}\n")
            time.sleep(3)
            if rgb == (176, 100, 81) and not disconnected and not died or ((time.time() - lastdeath) > 5 and died):
                take_screenshot("died")
                log_file.write(f"[DEATH] screenshot taken at {timestamp()}\n")
                print(f"Died at {timestamp()}")
                log_file.write(f"Died at {timestamp()}\n")
                died = True
                lastdeath = time.time()
                controller.tap(Key.enter)
            else:
                pass
        elif rgb == (223, 116, 90) and (disconnected or died):
            if disconnected:
               mouse.position = (4, 221)
               time.sleep(0.2)
               mouse.click(Button.left, 1)
               time.sleep(1)
               mouse.position = (250, 271)
               for _ in range(5):
                   mouse.click(Button.left, 1)
                   time.sleep(0.1)
               mouse.position = (250, 245)
               for _ in range(5):
                   mouse.click(Button.left, 1)
                   time.sleep(0.1)
            take_screenshot("reconnected")
            log_file.write(f"[RECONNECTED] screenshot taken at {timestamp()}\n")
            print(f"Successfully reconnected at {timestamp()}")
            log_file.write(f"Successfully reconnected at {timestamp()}\n")
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
        if time.time() - lastscreenshot > 60:
            take_screenshot()
            log_file.write(f"[PERIODIC] screenshot taken at {timestamp()}\n")
            lastscreenshot = time.time()
        if time.time() - lastmove > 30:
            mouse.position = (mouse.position[0]+1, mouse.position[1])
            time.sleep(0.1)
            mouse.position = (mouse.position[0]-1, mouse.position[1])
            lastmove = time.time()