import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import tkinter as tk

controller = KeyboardController()
mouse = MouseController()

s = 12

def ball(pos):
    mouse.position = pos
    controller.press("`")
    for _ in range(3):
        controller.tap("c")
        controller.tap("h")
    controller.release("`")



with open('bitmap.txt', 'r') as bitmap:
    start_time = time.time()
    lines = bitmap.readlines()
    # Optionally format lines if needed (not writing back to file here)
    print(f"bitmap loaded in {round((time.time() - start_time) * 1000, 3)}ms")

while True:
    towrite = input("enter text > ")
    time.sleep(2)
    towrite2 = towrite.lower()
    start_pos = mouse.position
    for char in towrite2:
        try:
            found = False
            for idx, line in enumerate(lines):
                if not line.strip():
                    continue
                if line[0].lower() == char:
                    # Example: parse dimensions if present, else default to 7x7
                    if len(line) >= 6 and line[2].isdigit() and line[4].isdigit():
                        xl = range(int(line[2]))
                        yl = range(int(line[4]))
                        offset = 1
                    else:
                        xl = range(7)
                        yl = range(7)
                        offset = 1
                    for y in yl:
                        bitmap_line_idx = idx + offset + y
                        if bitmap_line_idx < len(lines):
                            bitmap_line = lines[bitmap_line_idx].strip()
                            for x in xl:
                                if x < len(bitmap_line) and bitmap_line[x].lower() == "x":
                                    pos = (start_pos[0] + (x * s), start_pos[1] + (y * s))
                                    ball(pos)
                    found = True
                    break
            if not found:
                print(f"Character '{char}' not found in bitmap.")
            mouse.position = (start_pos[0] + (2 * s), start_pos[1])
        except Exception as e:
            print(f"exception as {e}")
    time.sleep(5)
    print(f"generated text {towrite2}")