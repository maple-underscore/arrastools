import mss, time, numpy as np, random, threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

global controller, mouse
controller = KeyboardController
mouse = MouseController
sct = mss.mss()
monitor = sct.monitors[1]

data = "[100-100]"
# walls
# n = normal, k = kill, h = heal, b = bounce, l = large, s = small, z = zoom, ^ > v < = one-way
# f = fake, S = sticky, p = paint, f = filter, t = team, b = base, P = portal, r = respawn
# 
# colors
# n = normal, b = blue, g = green, r = red, m = magenta, y = yellow, r = rogue, e = egg, s = square, t = triangle, p = pentagon
# h = hexagon, P = pink, s = shiny, l = legendary, w = wall 1, o = outline, W = wall 2, c = white, f = fallen, B = black
# 
# example string:
# nn-nn-nn-kn-kn-kn-nn-hn-hn-nn-nn-bn-bn-bn

def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

def readdata(data):
    x = data[1:4]
    y = data[5:8]
    pos = 9
    while pos + 3 <= len(data) - 9:
        chunk = data[pos:pos+3]
        walltype = chunk[0]
        wallcolor = chunk[1]
        # chunk[2] is a buffer character
        controller.tap("x")