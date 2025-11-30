import time
import numpy as np
from datetime import datetime
import os
from pathlib import Path
import mss, mss.tools
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

sct = mss.mss()

def rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

def on_press(key):
    global running
    if key == Key.esc:
        running = False
        return False  # Stop listener


time.sleep(3)
running = True
#end loop with esc
controller = KeyboardController()
while running:
    if rgb(805, 633)[0] > 200 and rgb(805, 633)[1] < 100 and rgb(805, 633)[2] < 100:
        controller.press("d")
        time.sleep(0.04)
        controller.release("d")
    if rgb(905, 633)[0] > 200 and rgb(905, 633)[1] < 100 and rgb(905, 633)[2] < 100:
        controller.press("a")
        time.sleep(0.04)
        controller.release("a")
    if rgb(855, 583)[0] > 200 and rgb(855, 583)[1] < 100 and rgb(855, 583)[2] < 100:
        controller.press("s")
        time.sleep(0.04)
        controller.release("s")
    if rgb(855, 683)[0] > 200 and rgb(855, 683)[1] < 100 and rgb(855, 683)[2] < 100:
        controller.press("w")
        time.sleep(0.04)
        controller.release("w")