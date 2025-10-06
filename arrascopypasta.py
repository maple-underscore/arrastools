import time, threading, os, mss, numpy as np
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
#each line should be 60 chars long
global ids, copypastaing, controller, thread, filepaths
sct = mss.mss()
def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])
ids = ['longest', 'long', 'mcdonalds', 'constitution', 'roast', 'random', 'icecream', 'rage', 'bag', 'cake', 'char'] #etc
filepaths = []
for idx in ids:
    exec(f"filepaths.append('/Users/alexoh/Documents/GitHub/arrastools/copypastas/{idx}.txt')")
print(filepaths)
copypastaing = False
thread = None
time.sleep(2)
controller = KeyboardController()
def copypasta(id):
    global ids, copypastaing, filepaths, controller
    if id in ids:
        index = ids.index(id)
        filepath = filepaths[index]
        pos = 0
        copypastaing = True
        start = time.time()
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return
        with open(filepath) as file:
            filer = file.read().replace('\n', r' [newline] ')
            leng = len(filer)
            file_size_bytes = os.path.getsize(filepath)
            file_size_kb = file_size_bytes / 1024
            end = time.time()
            controller.tap(Key.enter)
            time.sleep(0.1)
            controller.type(f"Arras Copypasta Utility [ACU] > v1.5.1 < loading...")
            time.sleep(0.1)
            for _ in range(2):
                controller.tap(Key.enter)
                time.sleep(0.1)
            controller.type(f"Filepath: > [.../{filepath[53:]}] < | Loaded > {leng} chars <")
            time.sleep(0.1)
            for _ in range(2):
                controller.tap(Key.enter)
                time.sleep(0.1)
            controller.type(f"Size: > [{file_size_kb:.2f}KB] < | Time taken > [{round((end-start)*1000, 3)}ms] <")
            time.sleep(0.1)
            controller.tap(Key.enter)
            time.sleep(10)
            endf = False
            start = time.time()
            while copypastaing and not endf:
                for _ in range(3):
                    if pos+58 < leng-1:
                        rgb = get_pixel_rgb(27, 930)
                        if rgb == (176, 100, 81):
                            time.sleep(3)
                            controller.tap(Key.enter)
                        controller.tap(Key.enter)
                        time.sleep(0.1)
                        controller.type(filer[pos:pos+58])
                        time.sleep(0.1)
                        controller.tap(Key.enter)
                        pos+=58
                        rgb = get_pixel_rgb(27, 930)
                        if rgb == (176, 100, 81):
                            time.sleep(3)
                            controller.tap(Key.enter)
                    else:
                        time.sleep(0.5)
                        endf = True
                        controller.tap(Key.enter)
                        time.sleep(0.1)
                        controller.type(filer[pos:(leng-1)])
                        time.sleep(0.1)
                        controller.tap(Key.enter)
                        print("End of file")
                    time.sleep(3.3)
            print(f"Copypasta of > {leng} characters < finished")
            controller.tap(Key.enter)
            time.sleep(0.1)
            controller.type(f"Copypasta of > {leng} characters < finished")
            time.sleep(0.1)
            for _ in range(2):
                controller.tap(Key.enter)
                time.sleep(0.1)
            controller.type(f"Time taken: > {round(1000*(time.time()-start), 3)}ms <")
            time.sleep(0.1)
            controller.tap(Key.enter)
            time.sleep(0.1)
copypasta('char')