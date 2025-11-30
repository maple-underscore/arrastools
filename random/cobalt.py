from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Controller as MouseController, Button
import time, mss, numpy as np

controller = KeyboardController()
mouse = MouseController()
sct = mss.mss()

time.sleep(2)

def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

with open("downloadqueue.txt", "r") as f:
    f.seek(0)
    lines = f.readlines()
    i=1
    for url in lines:
        downloaded = False
        while not downloaded:
            mouse.position = (807, 681)
            time.sleep(0.1)
            mouse.click(Button.left, 1)
            time.sleep(0.1)
            controller.type(url.strip())
            time.sleep(0.1)
            mouse.position = (1189, 683)
            time.sleep(0.1)
            mouse.click(Button.left, 1)
            time.sleep(3)
            print(get_pixel_rgb(903, 340))
            print(get_pixel_rgb(770, 743))
            print(get_pixel_rgb(690.26, 584.27))
            print(get_pixel_rgb(872, 462))
            if get_pixel_rgb(903, 340) == (255, 255, 255) and all(c > 200 for c in get_pixel_rgb(770, 743)):
                print("Youtube downloading temporarily disabled. Waiting for 5 minutes...")
                time.sleep(0.1)
                mouse.position = (770, 748)
                time.sleep(0.1)
                mouse.click(Button.left, 1)
                time.sleep(0.1)
                print("Reloading...")
                mouse.position = (1179, 66)
                time.sleep(0.1)
                mouse.click(Button.left, 1)
                time.sleep(300) # delay for youtube cooldown
                downloaded = False
            elif get_pixel_rgb(690.26, 584.27) == (98, 98, 98) and get_pixel_rgb(872, 462) == (255, 255, 255):
                print("Invalid link. Reloading...")
                mouse.position = (1179, 66)
                time.sleep(0.1)
                mouse.click(Button.left, 1)
                downloaded = False
            else:
                print(f"Downloading video {i}/{len(lines)}...")
                downloaded = True
                time.sleep(60) # delay for downloading
        i+=1