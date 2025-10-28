import mss, time, numpy as np, os
import mss.tools
import platform
from datetime import datetime
from pynput import mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import threading
from threading import Thread
from pathlib import Path
from ping3 import ping

# Detect platform
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows'
print(f"Arrasbot running on: {PLATFORM}")

# Platform notes
if PLATFORM not in ('darwin', 'linux', 'windows'):
    print(f"Warning: Platform '{PLATFORM}' may have limited support.")
    print("Tested on macOS, Linux (Arch/Debian/Ubuntu), and Windows.")

time.sleep(2)

global disconnected, banned, died, working
init = time.time()
start1 = time.time()
print("Initializing variables")
sct = mss.mss()
working = True
disconnected = True
died = False
banned = False
MONITOR_INDEX = 1          # 1 = main; use dbgmon to list all
SCALE = 2                  # 2 on Retina displays (macOS); 1 on standard displays (Windows/Linux/non-Retina)
                           # Adjust based on your display's pixel density
monitor = sct.monitors[MONITOR_INDEX]
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

def color_close(c1, c2, tol=6):
    # tolerant RGB compare
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))

def timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def take_screenshot(reason="periodic"):
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
    current_time = timestamp()
    filename = os.path.join(SCREENSHOT_DIR, f"{current_time}_{reason}.png")
    screenshot = sct.grab(sct.monitors[MONITOR_INDEX])
    mss.tools.to_png(screenshot.rgb, screenshot.size, output=filename)
    print(f"Screenshot saved: {filename} at {timestamp()}")
    with open("arrasbot.log", "a") as log_file:
        log_file.write(f"Screenshot saved: {filename} at {timestamp()}\n")
        log_file.close()

def inputlistener():
    global working, disconnected, died, banned
    inp = input("cmd > ")
    if inp.lower() == "stop":
        working = False
        print("Stopping bot...")
    elif inp.lower().startswith("setscale"):
        try:
            _, val = inp.split()
            val = int(val)
            globals()["SCALE"] = val
            print(f"SCALE set to {SCALE}")
        except Exception:
            print("Usage: setscale <1|2>")
    elif inp.lower().startswith("setmon"):
        try:
            _, idx = inp.split()
            idx = int(idx)
            if 0 <= idx < len(sct.monitors):
                globals()["MONITOR_INDEX"] = idx
                print(f"MONITOR_INDEX set to {MONITOR_INDEX} -> {sct.monitors[MONITOR_INDEX]}")
            else:
                print(f"Invalid index. Available: 0..{len(sct.monitors)-1}")
        except Exception:
            print("Usage: setmon <index>")
    elif inp.lower() == "dbgmon":
        for i, mon in enumerate(sct.monitors):
            print(f"[{i}] left={mon['left']} top={mon['top']} w={mon['width']} h={mon['height']}")
    elif inp.lower() == "screenshot":
        take_screenshot("manual")
    elif inp.lower() == "status":
        print(f"Working: {working}, Disconnected: {disconnected}, Died: {died}, Banned: {banned}")
    elif inp.lower() == "ping":
        pingm = getping()
        print(f"Ping to arras.io: {pingm*1000:.2f}ms")
    elif inp.lower() == "forcedisconnect":
        disconnected = True
        print("Forcing disconnect state...")
    elif inp.lower() == "forcedeath":
        died = True
        print("Forcing death state...")
    elif inp.lower() == "forcereconnect":
        disconnected = False
        died = False
        print("Forcing reconnect state...")
    elif inp.lower() == "probe":
        pos = mouse.position
        # mouse.position is global points; convert to local (monitor-relative) coords
        mon = sct.monitors[MONITOR_INDEX]
        local_x = (pos[0] - mon["left"]) / max(SCALE, 1)
        local_y = (pos[1] - mon["top"]) / max(SCALE, 1)
        rgb = get_pixel_rgb(int(local_x), int(local_y))
        print(f"Probe at global {pos} -> local ({int(local_x)},{int(local_y)}) -> RGB {rgb}")

def start_input_listener():
    threading.Thread(target=inputlistener, daemon=True).start()

start3 = time.time()-start3

start4 = time.time()
print("Creating directories")
HOME = str(Path.home())
foldername = f"abss_{timestamp()}"
SCREENSHOT_DIR = os.path.join(HOME, "Desktop", "abss", foldername)
start4 = time.time()-start4

print("Creating log file")
filename = f"logs/abss_{timestamp()}.log"
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
    controller.tap(Key.enter)
    time.sleep(0.1)
    controller.type("Arras Bot [arrasbot.py] > v2.14.3 < loading...")
    time.sleep(0.1)
    for _ in range(2):
        controller.tap(Key.enter)
        time.sleep(0.1)
    controller.type(f"SSD: > [.../arrasbot/{foldername}/] <")
    time.sleep(0.1)
    for _ in range(2):
        controller.tap(Key.enter)
        time.sleep(0.1)
    controller.type(f"Bot initialized; started at > [{timestamp()}] <")
    time.sleep(0.1)
    controller.tap(Key.enter)
    while working:
        p27930 = get_pixel_rgb(27, 930)  # cache once
        print(p27930)
        time.sleep(1)

        if color_close(get_pixel_rgb(1021, 716), (152, 232, 241)):
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

        if color_close(get_pixel_rgb(855, 255), (150, 150, 159)):
            log_file.write(f"Detected backroom crash at {timestamp()}\n")
            print(f"Detected backroom crash at {timestamp()}")
            controller.press("`")
            time.sleep(0.1)
            controller.tap("j")
            time.sleep(0.1)
            controller.release("`")

        if (color_close(p27930, (167, 81, 68)) or color_close(p27930, (138, 27, 34)) or
            color_close(p27930, (201, 92, 75)) or color_close(p27930, (199, 118, 98)) or
            color_close(p27930, (213, 114, 93))):
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
                    rgb2 = get_pixel_rgb(700, 674)
                    while banned:
                        if not rgb2 == (167, 81, 68) or rgb2 == (138, 27, 34) or rgb2 == (201, 92, 75) or rgb2 == (199, 118, 98) or get_pixel_rgb(27, 930) == (213, 114, 93):
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
        if color_close(p27930, (176, 100, 81)) and ((not disconnected or not died) or ((time.time() - lastdeath) > 5 and died)):
            print(f"Checking death at {timestamp()}")
            log_file.write(f"Checking death at {timestamp()}\n")
            time.sleep(3)
            p27930_after = get_pixel_rgb(27, 930)
            if color_close(p27930_after, (176, 100, 81)) and (not disconnected and not died or ((time.time() - lastdeath) > 5 and died)):
                take_screenshot("died")
                log_file.write(f"[DEATH] screenshot taken at {timestamp()}\n")
                print(f"Died at {timestamp()}")
                log_file.write(f"Died at {timestamp()}\n")
                died = True
                lastdeath = time.time()
                controller.tap(Key.enter)

        # Reconnect detection (tolerant)
        if color_close(p27930, (223, 116, 90)) and (disconnected or died):
            take_screenshot("reconnected")
            log_file.write(f"[RECONNECTED] screenshot taken at {timestamp()}\n")
            print(f"Successfully reconnected at {timestamp()}")
            log_file.write(f"Successfully reconnected at {timestamp()}\n")
            disconnected = False
            died = False
            controller.tap("i")
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