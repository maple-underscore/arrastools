from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
controller = KeyboardController()
import time
time.sleep(2)
controller.press("`")
time.sleep(0.5)
controller.press("2")
time.sleep(0.1)
controller.release("2")
controller.release("`")