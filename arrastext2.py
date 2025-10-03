import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import tkinter as tk

s = 12

def ball(pos = mouse.position):
    mouse.position = pos
    controller.press("`")
    for _ in range(3):
        controller.tap("c")
        controler.tap("h")
    controller.release("`")



with open('bitmap.txt') as bitmap:
    while True:
        towrite = input("enter text > ")
        towrite2 = ""
        start = mouse.position
        for char in towrite:
            towrite2 += char.lower()
        for char in towrite2:
            try:
                pos = 0
                while pos < len(bitmap.readlines())
                    bitmap.seek(pos)
                    if bitmap.read(pos)[0] == char:
                        if len(bitmap.read(pos)) == 5:
                            xl = range(bitmap.read(pos)[2:3])
                            yl = range(bitmap.read(pos)[4:5])
                        else:
                            xl = 7
                            yl = 9
                        for x in xl:
                            for y in yl:
                                bitmap.seek(pos + 1 + y)
                                leng = bitmap.read(pos + 1 + y)
                                for charpair in bitmap.read(pos + 1 + y):
                                    if charpair == "X":
                                        ball()
                            mouse.position = (start[0] + (x * s), start[1] + (y * s)
                    else:
                        pos += (bitmap.read(pos)[4:6] + 1)
            except Exception as e:
                print(f"exception as {e}")