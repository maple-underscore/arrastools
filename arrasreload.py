import mss, time, numpy as np, os
from datetime import datetime
from pynput import mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

mouse = MouseController()
controller = KeyboardController()
sct = mss.mss()
monitor = sct.monitors[1]

time.sleep(2)
def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

for _ in range(6):
    mouse.position = (133, 103)
    controller.tap(Key.enter)
    time.sleep(0.04)
    controller.type("msg")
    time.sleep(0.04)
    controller.tap(Key.enter)
    time.sleep(0.04)
    controller.tap(Key.enter)
    time.sleep(0.04)
    controller.type("msg")
    time.sleep(0.04)
    controller.tap(Key.enter)
    time.sleep(0.04)
    controller.tap(Key.enter)
    time.sleep(0.04)
    controller.type("msg")
    time.sleep(0.04)
    controller.tap(Key.enter)
    time.sleep(0.3)
    mouse.click(Button.left)
    time.sleep(0.5)
    mouse.position = (984, 666)
    time.sleep(0.04)
    mouse.click(Button.left)
    time.sleep(0.08)
    mouse.position = (928, 527)
    time.sleep(0.5)
    mouse.click(Button.left)
    time.sleep(0.03)
    mouse.click(Button.left)
    time.sleep(0.03)
    mouse.click(Button.left)
    time.sleep(0.03)
    mouse.click(Button.left)
    time.sleep(0.7)