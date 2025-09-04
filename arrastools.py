import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import tkinter as tk


# Function
global size_automation, controller, ballcash
arena_size_delay=50
s = 25 # ball spacing in px
length = 4 # side length of tail square
size_automation = False
ballcash = False
ballcrash_thread = None
braindamage = False
controller = KeyboardController()
pressed_keys = set()
automation_thread = None
braindamage_thread = None  # Add this global variable

def create_number_input_window(title):
    def handle_return(event=None):
        try:
            num = float(entry.get())
            return num
        except ValueError:
            print("Invalid input. Please enter a number.")

    root = tk.Tk()
    root.title(title)
    
    label = tk.Label(root, text="Please enter a number:")
    label.pack(pady=10)

    entry = tk.Entry(root)
    entry.pack(pady=5)
    entry.bind('<Return>', handle_return)
    entry.focus()

    root.mainloop()

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


def click_positions(pos_list, delay=0.5):
    mouse = MouseController()
    for x, y in pos_list:
        mouse.position = (x, y)
        time.sleep(0.02)
        mouse.click(Button.left, 1)
        print(f"Clicked at {x}, {y}")
        time.sleep(delay)

def conq_quickstart():
    controller.type("kyyv")
    mouse = MouseController()
    click_positions([
        (53.58203125, 948.08984375),
        (167.4765625, 965.703125),
        (166.66796875, 983.11328125),
        (90.53515625, 998.28125),
        (166.09765625, 1014.546875),
        (166.71875, 1031.28125),
        (92.51953125, 1049.71875)
    ], 0)
    mouse.position=(856, 638)

def wallcrash():
    controller.press("`")
    for _ in range(1800):
        controller.type("x")
    controller.release("`")

def nuke():
    controller.press("`")
    for _ in range(400):
        controller.type("wk")
    controller.release("`")

def shape():
    controller.press("`")
    for _ in range(400):
        controller.type("f")
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
    for _ in range(210):
        controller.type("ch")
    controller.release("`")

def walls():
    controller.press("`")
    for _ in range(210):
        controller.type("X")
    controller.release("`")

def ball10x10():
    controller.press("`")
    mouse = MouseController()
    init = mouse.position
    for _ in range(int(length*33)):
        controller.type("ch")
    time.sleep(1)
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
        time.sleep(0.02)  # Add a small delay to prevent locking up your systema

def score():
    controller.press("`")
    for _ in range(400):
        controller.type("n")
    controller.release("`")

def ball():
    controller.press("`")
    controller.type("ch")
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

def on_press(key):
    global size_automation, braindamage, ballcash
    try:
        if key == keyboard.Key.esc:
            controller.type("estop")
            exit(0)
        elif key == keyboard.Key.ctrl_l:
            pressed_keys.add('ctrl')
        elif hasattr(key, 'char') and key.char and key.char=='1':
            if 'ctrl' in pressed_keys:
                size_automation = True
                print("Arena size automation is now ON.")
                start_arena_automation()
        elif hasattr(key, 'char') and key.char and key.char=='2':
            if 'ctrl' in pressed_keys:
                print("Conqueror quickstart initiated.")
                conq_quickstart()
        elif hasattr(key, 'char') and key.char and key.char=='3':
            if 'ctrl' in pressed_keys:
                braindamage = True
                print("Brain damage function called.")
                start_brain_damage()
        elif hasattr(key, 'char') and key.char and key.char=='4':
            if 'ctrl' in pressed_keys:
                ball()
        elif hasattr(key, 'char') and key.char and key.char=='5':
            if 'ctrl' in pressed_keys:
                print("ball square")
                ball10x10()
        elif hasattr(key, 'char') and key.char and key.char=='6':
            if 'ctrl' in pressed_keys:
                print("death by ball")
                ballcrash()
        elif hasattr(key, 'char') and key.char and key.char=='7':
            if 'ctrl' in pressed_keys:
                print("Wall crashing...")
                wallcrash()
        elif hasattr(key, 'char') and key.char and key.char=='8':
            if 'ctrl' in pressed_keys:
                print("shape nuke")
                shape() 
        elif hasattr(key, 'char') and key.char and key.char=='9':
            if 'ctrl' in pressed_keys:
                print("NUKE GO BRRRRRRRRRR")
                nuke()
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
        elif hasattr(key, 'char') and key.char and key.char=='0':
            if 'ctrl' in pressed_keys:
                size_automation = False
                braindamage = False
                print("All automation is now OFF.") 
    except Exception as e:
        print(f"Error: {e}")
    
def on_release(key):
    if key == keyboard.Key.ctrl_l:
        pressed_keys.discard('ctrl')
    elif key in pressed_keys:
        pressed_keys.remove(key)

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()

