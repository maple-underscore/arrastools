from pynput import keyboard
from pynput import mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import threading, time
controller = KeyboardController()
time.sleep(2)
controller.press("`")
controller.press("k")