import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

controller = KeyboardController()
mouse = MouseController()

global ball_spacing
ball_spacing = 25
size = 3, 5
text = ""

def ball(x, y):
    controller.press("`")
    mouse.position = (x, y)
    time.sleep(0.04)
    for _ in range(3):
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def textplacer(text, x, y, pos, sizex, sizey):
    try:
        if not isinstance(text, str) or (sizex < 3 or sizey < 5):
            return False
        localx = x
        localy = y
        for letter in text:
            if letter == "a":
                for _ in range(sizex-1):
                    localx+=ball_spacing
                    ball(localx, localy)
                localx-=ball_spacing*(sizex-1)
                for _ in range(sizey-1):
                    localy+=ball_spacing
                    ball(localx, localy)
                for _ in range(sizex-1):
                    localx+=ball_spacing
                    ball(localx, localy)
                localx-=ball_spacing*(sizex-1)
                localy-=ball_spacing*(sizey-3)
                for _ in range(sizex-1):
                    localx+=ball_spacing
                    ball(localx, localy)
            return True
            print(f"Placed letter {letter}")
    except Exception as e:
        print(f"Uncaught exception {e}")
        return False


pos = mouse.position
textplacer(text, pos[0], pos[1]+2*ball_spacing, pos, size[0], size[1])