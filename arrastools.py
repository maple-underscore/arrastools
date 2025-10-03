import random, time, threading, os, mss, numpy as np
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseControllerm

#globals
global size_automation, controller, dragaboosr, typeaboosr, coloraboosr, allaboosr, ballcash, mouse
controller = KeyboardController()
mouse = MouseController()
pressed_keys = set()

#configs
length = 4
arena_size_delay=50
ids = ['longest', 'long', 'mcdonalds', 'constitution', 'roast', 'rage', 'random'] #etc
filepaths = []
s = 25 #ball spacing in px

# dynamic filepaths
for id2 in ids:
    filepaths.append(f"vsc/copypastas/{id2}.txt")

#defs
copypastaing = False
ctrl6_last_time = 0
ctrl6_armed = False
sct = mss.mss()
monitor = sct.monitors[1]

#thread variables
size_automation = False
copypastas = False
dragaboosr = False
typeaboosr = False
coloraboosr = False
allaboosr = False
boting = False
ballcash = False
braindamage = False
ballcash_thread = None
inputlistener_thread = None
bot_thread = None
copypasta_thread = None
automation_thread = None
dragaboos_thread = None
typeaboos_thread = None
coloraboos_thread = None
allaboos_thread = None
braindamage_thread = None
tail_thread = None

def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

def generate_even(low=2, high=1024):
    return random.choice([i for i in range(low, high + 1) if i % 2 == 0])

def bot():
    import mss, time, numpy as np, os
    from datetime import datetime
    from pynput import mouse
    from pynput.keyboard import Controller as KeyboardController, Key
    from pynput.mouse import Controller as MouseController, Button
    from pathlib import Path
    from ping3 import ping

    init = time.time()
    start1 = time.time()
    print("Initializing variables")
    disconnected = True
    died = False
    start1 = time.time()-start1

    start2 = time.time()
    print("Initializing controllers")
    controller = KeyboardController()
    mouse = MouseController()
    start2 = time.time()-start2

    start3 = time.time()
    print("Defining functions")
    def getping():
        target = "arras.io"
        return ping(target)

    def get_pixel_rgb(x, y):
        bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
        img = sct.grab(bbox)
        pixel = np.array(img.pixel(0, 0))
        return tuple(int(v) for v in pixel[:3])

    def timestamp():
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    def take_screenshot(reason="periodic"):
        if not os.path.exists(SCREENSHOT_DIR):
            os.makedirs(SCREENSHOT_DIR)
        current_time = timestamp()
        filename = os.path.join(SCREENSHOT_DIR, f"{current_time}_{reason}.png")
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=filename)
        print(f"Screenshot saved: {filename} at {timestamp()}")
        with open("arrasbot.log", "a") as log_file:
            log_file.write(f"Screenshot saved: {filename} at {timestamp()}\n")
            log_file.close()
    start3 = time.time()-start3

    start4 = time.time()
    print("Creating directories")
    HOME = str(Path.home())
    foldername = f"arrasbot_{timestamp()}"
    SCREENSHOT_DIR = os.path.join(HOME, "Desktop", "arrasbot", foldername)
    start4 = time.time()-start4

    print("Creating log file")
    filename = f"arrasbot_{timestamp()}.log"
    with open(filename, "a") as log_file:
        print(f"Bot initialized at {timestamp()}")
        init = time.time()-init
        log_file.write(f"""
    =============== DEBUG ===============
    Display size: {monitor['width']}x{monitor['height']}
    Screenshot directory: {SCREENSHOT_DIR}
    Created variables in {round(start1, 3)} seconds
    Created controllers in {round(start2, 3)} seconds
    Defined functions in {round(start3, 3)} seconds
    Created directories in {round(start4, 3)} seconds
    Bot initialized in {round(init, 3)} seconds

    ================ LOG ================
    """)
        log_file.write(f"Bot initialized at {timestamp()}\n")
        lastmove = time.time()
        lastscreenshot = time.time()
        while boting:
            rgb = get_pixel_rgb(27, 930)
            if (rgb == (167, 81, 68) or rgb == (138, 27, 34) or rgb == (201, 92, 75)):
                if not disconnected:
                    take_screenshot("disconnected")
                    log_file.write(f"[DISCONNECTED] screenshot taken at {timestamp()}\n")
                print(f"Disconnected at {timestamp()}")
                log_file.write(f"Disconnected at {timestamp()}\n")
                controller.release("w")
                controller.release("a")
                if not disconnected:
                    print(f"Disconnected, attempting to reconnect at {timestamp()}")
                    log_file.write(f"Disconnected, attempting to reconnect at {timestamp()}\n")
                disconnected = True
                mouse.position = (922, 767)
                pingm = getping()
                for _ in range(200):
                    mouse.click(Button.left, 1)
                    time.sleep(pingm/1000)
            elif rgb == (176, 100, 81) and not disconnected and not died:
                print(f"Checking death at {timestamp()}")
                log_file.write(f"Checking death at {timestamp()}\n")
                time.sleep(3)
                if rgb == (176, 100, 81) and not disconnected and not died:
                    take_screenshot("died")
                    log_file.write(f"[DEATH] screenshot taken at {timestamp()}\n")
                    print(f"Died at {timestamp()}")
                    log_file.write(f"Died at {timestamp()}\n")
                    died = True
                    controller.tap(Key.enter)
                else:
                    pass
            elif rgb == (223, 116, 90) and (disconnected or died):
                take_screenshot("reconnected")
                log_file.write(f"[RECONNECTED] screenshot taken at {timestamp()}\n")
                print(f"Successfully reconnected at {timestamp()}")
                log_file.write(f"Successfully reconnected at {timestamp()}\n")
                
                disconnected = False
                died = False
                controller.tap("h")
                controller.tap("u")
                controller.tap("u")
                controller.tap("c")
                time.sleep(0.1)
                controller.press("`")
                time.sleep(0.1)
                controller.tap("i")
                time.sleep(0.1)
                controller.release("`")
            if time.time() - lastscreenshot > 60:
                take_screenshot()
                log_file.write(f"[PERIODIC] screenshot taken at {timestamp()}\n")
                lastscreenshot = time.time()
            if time.time() - lastmove > 30:
                mouse.position = (mouse.position[0]+1, mouse.position[1])
                time.sleep(0.1)
                mouse.position = (mouse.position[0]-1, mouse.position[1])
                controller.tap("a")
                controller.tap("d")
                lastmove = time.time()

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
            controller.type(f"Loaded file from filepath > [{filepath[15:len(filepath)]}] <")
            time.sleep(0.1)
            for _ in range(2):
                controller.tap(Key.enter)
                time.sleep(0.1)
            controller.type(f"Loaded > {leng} characters < | > [{file_size_kb:.2f}KB] <")
            time.sleep(0.1)
            for _ in range(2):
                controller.tap(Key.enter)
                time.sleep(0.1)
            controller.type(f"Time taken > [{round((end-start)*1000, 3)}ms] < Waiting for chat delay...")
            time.sleep(0.1)
            controller.tap(Key.enter)
            time.sleep(10)
            endf = False
            while copypastaing and not endf and copypastas:
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
                        endf = True
                        controller.type(filer[pos:(leng-1)])
                        print("End of file")
                    time.sleep(3.1)
            if copypastas:
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type(f"Copypasta of > {leng} characters < finished")
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                print(f"Copypasta of > {leng} characters < finished")
            else:
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type("copypasta_thread forced shutdown")
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                print("copypasta_thread forced shutdown")

def arena_size_automation(interval_ms=20, atype = 1):
    global size_automation
    if atype == 1:
        while size_automation:
            x = generate_even()
            y = generate_even()
            print(f"Sending command: $arena size {x} {y}")
            command = f"$arena size {x} {y}"
            controller.tap(Key.enter)
            time.sleep(0.05)
            controller.type(command)
            time.sleep(0.05)
            controller.tap(Key.enter)
            time.sleep(interval_ms / 1000.0)
    elif atype == 2:
        sup = True
        x = 2
        y = 2
        while size_automation:
            if x == 1026:
                sup = False
                x = 1024
                y = 1024
            if x == 0:
                sup = True
                x = 2
                y = 2
            command = f"$arena size {x} {y}"
            controller.tap(Key.enter)
            time.sleep(0.05)
            controller.type(command)
            time.sleep(0.05)
            controller.tap(Key.enter)
            if sup:
                x += 2
                y += 2
            else:
                x -= 2
                y -= 2
    elif atype == 3:
        sup = True
        x = 2
        y = 1024
        while size_automation:
            if x == 1026:
                sup = False
                x = 1024
                y = 2
            if x == 0:
                sup = True
                x = 2
                y = 1024
            command = f"$arena size {x} {y}"
            controller.tap(Key.enter)
            time.sleep(0.05)
            controller.type(command)
            time.sleep(0.05)
            controller.tap(Key.enter)
            if sup:
                x += 2
                y -= 2
            else:
                x -= 2
                y += 2

def wallcrash():
    controller.press("`")
    controller.type("x"*2000)
    controller.release("`")

def nuke():
    controller.press("`")
    controller.type("wk"*400)
    controller.release("`")

def shape():
    controller.press("`")
    controller.type("f"*1000)
    controller.release("`")

def ballcrash():
    controller.press("`")
    for _ in range(100):
        for _ in range(100):
            controller.press("c")
            controller.release("c")
            controller.press("h")
            controller.release("h")
    controller.release("`")

def balls():
    controller.press("`")
    controller.type("ch"*210)
    controller.release("`")

def walls():
    controller.press("`")
    controller.type("x"*210)
    controller.release("`")

def tail():
    controller.press("`")
    time.sleep(0.1)
    controller.tap("0")
    controller.tap("-")
    controller.tap("-")
    mouse = MouseController()
    init = mouse.position
    controller.type("ch"*int(length*33))
    time.sleep(3)
    starting_position = (init[0], init[1]+2*s)
    i2=0
    while i2 < length:
        i=0
        while i < length:
            controller.release("w")
            time.sleep(0.04)
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            time.sleep(0.04)
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            time.sleep(0.04)
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            i+=1
        i2+=1
    mouse.position = (init[0], init[1]+2*s)
    i2=0
    time.sleep(0.1)
    mouse.position = (mouse.position[0]-s, mouse.position[1])
    time.sleep(2)
    mouse.position = (mouse.position[0]+s, mouse.position[1])
    time.sleep(0.1)
    down = True
    while i2 < length:
        i=0
        while i < length:
            controller.press("j")
            time.sleep(0.04)
            if down:
                mouse.position = (mouse.position[0], mouse.position[1]+s)
                time.sleep(0.04)
                controller.release("j")
                if i == length-1:
                    mouse.position = (mouse.position[0], mouse.position[1]-s)
                    time.sleep(0.04)
                    controller.press("j")
            else:
                mouse.position = (mouse.position[0], mouse.position[1]-s)
                time.sleep(0.04)
                controller.release("j")
                if i == length-1:
                    mouse.position = (mouse.position[0], mouse.position[1]+s)
                    time.sleep(0.04)
                    controller.press("j")
            i+=1
        i2+=1
        time.sleep(0.04)
        if down:
            mouse.position = (mouse.position[0]+s, mouse.position[1])
        else:
            mouse.position = (mouse.position[0]+s, mouse.position[1])
        time.sleep(0.04)
        controller.release("j")
        down = not down
    controller.release("`")

def brain_damage():
    global braindamage
    mouse = MouseController()
    while braindamage:
        mouse.position = (random.randint(0, 1710), random.randint(168, 1112))

def score():
    controller.press("`")
    controller.type("n"*400)
    controller.release("`")

def ball():
    controller.press("`")
    controller.type("ch")
    controller.release("`")
        
def slowwall():
    controller.press("`")
    for _ in range(50):
        controller.tap("x")
        time.sleep(0.08)
    controller.release("`")

def dragaboos():
    global dragaboos
    controller.press("`")
    while dragaboosr:
        mouse.position = (random.randint(5, 1705), random.randint(173, 1107))
        time.sleep(0.02)
        pos = mouse.position
        controller.press("w")
        mouse.position = (pos[0]+random.randint(-5, 5), pos[1]+random.randint(-5, 5))
        controller.release("w")
        time.sleep(0.02)
    controller.release("`")

def typeaboos():
    global typeaboosr
    controller.press("`")
    while typeaboosr:
        mouse.position = (random.randint(5, 1705), random.randint(173, 1107))
        time.sleep(0.02)
        pos = mouse.position
        controller.press("z")
        mouse.position = (pos[0]+random.randint(-20, 20), pos[1]+random.randint(-20, 20))
        time.sleep(0.05)
        controller.release("z")
        time.sleep(0.02)
    controller.release("`")

def coloraboos():
    global coloraboosr
    controller.press("`")
    while coloraboosr:
        mouse.position = (random.randint(5, 1705), random.randint(173, 1107))
        time.sleep(0.02)
        pos = mouse.position
        controller.press("c")
        mouse.position = (pos[0]+random.randint(-20, 20), pos[1]+random.randint(-20, 20))
        time.sleep(0.05)
        controller.release("c")
        time.sleep(0.02)
    controller.release("`")

def allaboos():
    global allaboosr
    controller.press("`")
    while allaboosr:
        mouse.position = (random.randint(5, 1705), random.randint(173, 1107))
        time.sleep(0.02)
        pos = mouse.position
        controller.press("w")
        mouse.position = (pos[0]+random.randint(-5, 5), pos[1]+random.randint(-5, 5))
        time.sleep(0.05)
        controller.release("w")
        time.sleep(0.02)
        pos = mouse.position
        controller.press("z")
        mouse.position = (pos[0]+random.randint(-20, 20), pos[1]+random.randint(-20, 20))
        time.sleep(0.05)
        controller.release("z")
        time.sleep(0.02)
        pos = mouse.position
        controller.press("c")
        mouse.position = (pos[0]+random.randint(-20, 20), pos[1]+random.randint(-20, 20))
        time.sleep(0.05)
        controller.release("c")
        time.sleep(0.02)
    controller.release("`")

def inputlistener():
    cmd = input("cmd > ")
    if cmd[0:10] == "!copypasta":
        start_copypasta(cmd[11:])
    if cmd[0:4] == "!bot":
        start_bot()

def start_copypasta(id2):
    global copypasta_thread
    if copypasta_thread is None or not copypasta_thread.is_alive():
        copypasta_thread = threading.Thread(target=copypasta, args=(id2))
        copypasta_thread.daemon = True
        copypasta_thread.start()

def start_arena_automation(atype):
    global automation_thread
    if automation_thread is None or not automation_thread.is_alive():
        automation_thread = threading.Thread(target=arena_size_automation, args=(arena_size_delay, atype))
        automation_thread.daemon = True
        automation_thread.start()

def start_brain_damage():
    global braindamage_thread
    if braindamage_thread is None or not braindamage_thread.is_alive():
        braindamage_thread = threading.Thread(target=brain_damage)
        braindamage_thread.daemon = True
        braindamage_thread.start()

def start_tail():
    global tail_thread
    if tail_thread is None or not tail_thread.is_alive():
        tail_thread = threading.Thread(target=tail)
        tail_thread.daemon = True
        tail_thread.start()

def start_dragaboos():
    global dragaboos_thread
    if dragaboos_thread is None or not dragaboos_thread.is_alive():
        dragaboos_thread = threading.Thread(target=dragaboos)
        dragaboos_thread.daemon = True
        dragaboos_thread.start()

def start_typeaboos():
    global typeaboos_thread
    if typeaboos_thread is None or not typeaboos_thread.is_alive():
        typeaboos_thread = threading.Thread(target=typeaboos)
        typeaboos_thread.daemon = True
        typeaboos_thread.start()

def start_bot():
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = threading.Thread(target=bot)
        bot_thread.daemon = True
        bot_thread.start()

def start_coloraboos():
    global coloraboos_thread
    if coloraboos_thread is None or not coloraboos_thread.is_alive():
        coloraboos_thread = threading.Thread(target=coloraboos)
        coloraboos_thread.daemon = True
        coloraboos_thread.start()

def start_allaboos():
    global allaboos_thread
    if allaboos_thread is None or not allaboos_thread.is_alive():
        allaboos_thread = threading.Thread(target=allaboos)
        allaboos_thread.daemon = True
        allaboos_thread.start()

def start_inputlistener():
    global inputlistener_thread
    if inputlistener_thread is None or not inputlistener_thread.is_alive():
        inputlistener_thread = threading.Thread(target=inputlistener)
        inputlistener_thread.daemon = True
        inputlistener_thread.start()

def on_press(key):
    global size_automation, braindamage, ballcash, dragaboosr, typeaboosr, coloraboosr, allaboosr, copypastas
    global ctrl6_last_time, ctrl6_armed
    try:
        if key == keyboard.Key.esc:
            if 'ctrl' in pressed_keys:
                print("estop")
                exit(0)
            else:
                size_automation = False
                braindamage = False
                dragaboosr = False
                boting = False
                typeaboosr = False
                coloraboosr = False
                copypastas = False
                allaboosr = False
                # stop all threads
        elif key == keyboard.Key.ctrl_l:
            pressed_keys.add('ctrl')
        elif key = keyboard.Key.up:
            if 'ctrl' in pressed_keys:
                mouse.position[1] -= 1
        elif key = keyboard.Key.up:
            if 'ctrl' in pressed_keys:
                mouse.position[1] += 1
        elif key = keyboard.Key.up:
            if 'ctrl' in pressed_keys:
                mouse.position[1] -= 1
        elif key = keyboard.Key.up:
            if 'ctrl' in pressed_keys:
                mouse.position[0] += 1
        elif hasattr(key, 'char') and key.char and key.char=='1':
            if 'ctrl' in pressed_keys:
                atype = random.randint(1, 3)
                size_automation = True
                print("lol arena having a stroke")
                start_arena_automation(atype)
        elif hasattr(key, 'char') and key.char and key.char=='3':
            if 'ctrl' in pressed_keys:
                braindamage = True
                print("brain dmg")
                start_brain_damage()
        elif hasattr(key, 'char') and key.char and key.char=='4':
            if 'ctrl' in pressed_keys:
                ball()
        elif hasattr(key, 'char') and key.char and key.char=='5':
            if 'ctrl' in pressed_keys:
                print("ball square")
                start_tail()
        elif hasattr(key, 'char') and key.char and key.char=='6':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrl6_armed and (now - ctrl6_last_time <= 5):
                    print("death by ball")
                    ballcrash()
                    ctrl6_armed = False
                else:
                    print("press ctrl 6 again fr")
                    ctrl6_armed = True
                    ctrl6_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='7':
            if 'ctrl' in pressed_keys:
                print("wall crash l l")
                wallcrash()
        elif hasattr(key, 'char') and key.char and key.char=='9':
            if 'ctrl' in pressed_keys:
                print("NUKE GO BRRRRRRRRRR")
                nuke()
        elif hasattr(key, 'char') and key.char and key.char=='f':
            if 'ctrl' in pressed_keys:
                print("shape nuke")
                shape() 
        elif hasattr(key, 'char') and key.char and key.char=='n':
            if 'ctrl' in pressed_keys:
                print("score")
                score()
        elif hasattr(key, 'char') and key.char and key.char=='b':
            if 'ctrl' in pressed_keys:
                print("200 balls")
                balls()
        elif hasattr(key, 'char') and key.char and key.char=='w':
            if 'ctrl' in pressed_keys:
                print("200 walls")
                walls()
        elif hasattr(key, 'char') and key.char and key.char=='s':
            if 'ctrl' in pressed_keys:
                slowwall()
        elif hasattr(key, 'char') and key.char and key.char=='d':
            if 'ctrl' in pressed_keys:
                dragaboosr = True
                print("drag aboos")
                start_dragaboos()
        elif hasattr(key, 'char') and key.char and key.char=='z':
            if 'ctrl' in pressed_keys:
                typeaboosr = True
                print("type aboos")
                start_typeaboos()
        elif hasattr(key, 'char') and key.char and key.char=='c':
            if 'ctrl' in pressed_keys:
                coloraboosr = True
                print("color aboos")
                start_coloraboos()
        elif hasattr(key, 'char') and key.char and key.char=='a':
            if 'ctrl' in pressed_keys:
                allaboosr = True
                print("all aboos")
                start_allaboos()
    except Exception as e:
        print(f"Error: {e}")
    
def on_release(key):
    if key == keyboard.Key.ctrl_l:
        pressed_keys.discard('ctrl')
    elif key in pressed_keys:
        pressed_keys.remove(key)

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()