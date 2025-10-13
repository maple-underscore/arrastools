import time
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
time.sleep(1)
mouse = MouseController()
controller = KeyboardController()
mouse.position = (922, 767)
while True:
    mouse.position = (mouse.position[0], mouse.position[1]+100)
    time.sleep(0.5)
    mouse.position = (mouse.position[0], mouse.position[1]-100)
    time.sleep(0.5)
    mouse.click(Button.left, 1)