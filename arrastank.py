import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import tkinter as tk
controller = KeyboardController()

time.sleep(2)
start = time.time()
while time.time()-start < 10:
    controller.tap(",")
    controller.tap("y")
    controller.tap("i")
    controller.press("`")
    controller.press(".")
    controller.press(".")
    controller.press("a")
    controller.press("c")
    controller.release("`")
    controller.press(Key.space)
    time.sleep(0.25)
    controller.release(Key.space)
    controller.press("`")
    controller.press("q")
    controller.release("`")