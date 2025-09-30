import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController

length = 4

# Function
global size_automation, controller, dragaboosr, typeaboosr, coloraboosr, allaboosr, ballcash, mouse
arena_size_delay=50
s = 25 #ball spacing in px
size_automation = False
dragaboosr = False
typeaboosr = False
coloraboosr = False
allaboosr = False
ballcash = False
ballcrash_thread = None
braindamage = False
controller = KeyboardController()
mouse = MouseController()
pressed_keys = set()
automation_thread = None
dragaboos_thread = None
typeaboos_thread = None
coloraboos_thread = None
allaboos_thread = None
braindamage_thread = None  # Add this global variable
ball10x10_thread = None  # Add this global variable

# Add these globals near the top
ctrl6_last_time = 0
ctrl6_armed = False

def generate_even(low=2, high=1024):
    return random.choice([i for i in range(low, high + 1) if i % 2 == 0])

def arena_size_automation(interval_ms=20):
    global size_automation
    try:
        while size_automation:
            x = generate_even()
            y = generate_even()
            print(f"Sending command: $arena size {x} {y}")
            command = f"$arena size {x} {y}"
            controller.press(Key.enter)
            controller.release(Key.enter)
            time.sleep(0.05)
            controller.type(command)
            time.sleep(0.05)
            controller.press(Key.enter)
            controller.release(Key.enter)
            time.sleep(interval_ms / 1000.0)
    except KeyboardInterrupt:
        pass

def wallcrash():
    controller.press("`")
    controller.type("x"*1800)
    controller.release("`")

def nuke():
    controller.press("`")
    controller.type("wk"*400)
    controller.release("`")

def shape():
    controller.press("`")
    controller.type("f"*500)
    controller.release("`")

def ballcrash():
    controller.press("`")
    for _ in range(50):
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

def ball10x10():
    controller.press("`")
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
    time.sleep(5)
    mouse.position = init
    controller.tap("k")
    mouse.position = (init[0], init[1]+2*s)
    i2=0
    while i2 < length:
        i=0
        while i < length:
            controller.tap("k")
            time.sleep(0.04)
            i+=1
        i2+=1
        time.sleep(0.04)
    controller.release("`")

def brain_damage():
    global braindamage
    mouse = MouseController()
    while braindamage:
        mouse.position = (random.randint(0, 1710), random.randint(168, 1112))
        time.sleep(0.02)  # Add a small delay to prevent locking up your systema

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

def start_arena_automation():
    global automation_thread
    if automation_thread is None or not automation_thread.is_alive():
        automation_thread = threading.Thread(target=arena_size_automation, args=(arena_size_delay,))
        automation_thread.daemon = True
        automation_thread.start()

def start_brain_damage():
    global braindamage_thread
    if braindamage_thread is None or not braindamage_thread.is_alive():
        braindamage_thread = threading.Thread(target=brain_damage)
        braindamage_thread.daemon = True
        braindamage_thread.start()

def start_ball10x10():
    global ball10x10_thread
    if ball10x10_thread is None or not ball10x10_thread.is_alive():
        ball10x10_thread = threading.Thread(target=ball10x10)
        ball10x10_thread.daemon = True
        ball10x10_thread.start()

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

def on_press(key):
    global size_automation, braindamage, ballcash, dragaboosr, typeaboosr, coloraboosr, allaboosr
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
                typeaboosr = False
                coloraboosr = False
                allaboosr = False
                # stop all threads
        elif key == keyboard.Key.ctrl_l:
            pressed_keys.add('ctrl')
        elif key == keyboard.Key.up:
            mouse.position[1] -= 1
        elif key == keyboard.Key.down:
            mouse.position[1] += 1
        elif key == keyboard.Key.left:
            mouse.position[1] -= 1
        elif key == keyboard.Key.right:
            mouse.position[0] += 1
        elif hasattr(key, 'char') and key.char and key.char=='1':
            if 'ctrl' in pressed_keys:
                size_automation = True
                print("lol arena having a stroke")
                start_arena_automation()
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
                start_ball10x10()
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

