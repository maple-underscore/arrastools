from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Controller as MouseController, Button
import time
mouse = MouseController()

c = KeyboardController()

time.sleep(1)  # Short delay to switch to target window
for _ in range(10):
    c.press(Key.cmd)
    c.tap("t")
    c.release(Key.cmd)
    time.sleep(0.3)
    c.type("arras.io/#wpd")
    c.tap(Key.enter)
    time.sleep(1)
for _ in range(10):
    c.press(Key.ctrl)
    c.press(Key.shift)
    time.sleep(0.01)
    c.tap(Key.tab)
    c.release(Key.shift)
    c.release(Key.ctrl)
    time.sleep(0.5)
for _ in range(10):
    c.press(Key.ctrl)
    time.sleep(0.01)
    c.tap(Key.tab)
    c.release(Key.ctrl)
    time.sleep(0.5)
mouse.position = (960, 532)
time.sleep(1)
for _ in range(10):
    mouse.click(Button.left, 1)
    c.press(Key.ctrl)
    c.press(Key.shift)
    time.sleep(0.01)
    c.tap(Key.tab)
    c.release(Key.shift)
    c.release(Key.ctrl)
    time.sleep(0.01)