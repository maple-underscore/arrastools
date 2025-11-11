import random
import time
import threading
import platform
import tkinter as tk
from tkinter import ttk
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key, Listener as KeyboardListener
from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener


# Detect platform
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows', 'android'
print(f"Running on: {PLATFORM}")

# Platform notes:
# - macOS: Ctrl hotkeys work; Option+Arrow for 1px nudges
# - Linux: Ctrl hotkeys work; Alt+Arrow for 1px nudges
# - Windows: Ctrl hotkeys work; Alt+Arrow for 1px nudges
# - Android: Limited support (pynput may not work on all devices)
if PLATFORM not in ('darwin', 'linux', 'windows'):
    print(f"Warning: Platform '{PLATFORM}' may have limited support.")
    print("Tested on macOS, Linux (Arch/Debian/Ubuntu), and Windows.")

length = 4

# Function
global size_automation, controller, randomwalld, circlecash, mouse, slowcircles, step, ctrlswap
global macros_enabled
step = 20
s = 25 #circle spacing in px
ctrlswap = False  # When True, use Cmd (macOS) instead of Ctrl for macros
macros_enabled = True  # Global flag to enable/disable all macros
size_automation = False
engispamming = False
engispam_thread = None
randomwalld = False
slowcircles = False
circlecash = False
circlecrash_thread = None
braindamage = False
controller = KeyboardController()
mouse = MouseController()
pressed_keys = set()
automation_thread = None
slowcircle_thread = None
randomwall_thread = None
braindamage_thread = None  # Add this global variable
circle_tail_legacy_thread = None  # Add this global variable
controllednuke_points = []
controllednuke_active = False

# Add these globals near the top
ctrl6_last_time = 0
ctrl6_armed = False

# ctrl+o double-press lock
ctrlo_last_time = 0
ctrlo_armed = False

# new ctrl+1 multi-press globals
ctrl1_count = 0
ctrl1_first_time = 0.0
ctrl1_thread = None

# NEW: bind slowcircles to Left Shift when enabled via Ctrl+C
slowcircle_shift_bind = False

def generate_even(low=2, high=1024):
    return random.choice([i for i in range(low, high + 1) if i % 2 == 0])

def arena_size_automation(atype = 1):
    time.sleep(2)
    global size_automation
    if atype == 1:
        while size_automation:
            x = generate_even()
            y = generate_even()
            print(f"Sending command: $arena size {x} {y}")
            command = f"$arena size {x} {y}"
            controller.tap(Key.enter)
            controller.type(command)
            controller.tap(Key.enter)
    elif atype == 2:
        while size_automation:
        # x and y go from 2 to 1024 in steps of 2
            x = 2
            y = 2
            direction_x = 2
            direction_y = 2
            while size_automation:
                print(f"Sending command: $arena size {x} {y}")
                command = f"$arena size {x} {y}"
                controller.tap(Key.enter)
                controller.type(command)
                controller.tap(Key.enter)
                x += direction_x
                y += direction_y
                if x >= 1024 or x <= 2:
                    direction_x *= -1
                if y >= 1024 or y <= 2:
                    direction_y *= -1
    elif atype == 3:
        while size_automation:
            #x goes from 2 to 1024, y goes from 1024 to 2
            x = 2
            y = 1024
            direction_x = 2
            direction_y = -2
            while size_automation:
                print(f"Sending command: $arena size {x} {y}")
                command = f"$arena size {x} {y}"
                controller.tap(Key.enter)
                controller.type(command)
                controller.tap(Key.enter)
                x += direction_x
                y += direction_y
                if x >= 1024 or x <= 2:
                    direction_x *= -1
                if y >= 1024 or y <= 2:
                    direction_y *= -1
    else:
        print(f"Unknown arena automation type: {atype}")
        
def click_positions(pos_list, delay=0.5):
    mouse = MouseController()
    for x, y in pos_list:
        mouse.position = (x, y)
        time.sleep(0.02)
        mouse.click(Button.left, 1)
        print(f"Clicked at {x}, {y}")
        time.sleep(delay)

def conq_quickstart():
    for _ in range(50):
        controller.tap("n")
    controller.type("kyyv")
    mouse = MouseController()
    pos = mouse.position
    click_positions([
        (53.58203125, 948.08984375),
        (167.4765625, 965.703125),
        (166.66796875, 983.11328125),
        (90.53515625, 998.28125),
        (166.09765625, 1014.546875),
        (166.71875, 1031.28125),
        (92.51953125, 1049.71875)
    ], 0)
    mouse.position=pos

def wallcrash():
    controller.press("`")
    controller.type("x"*1800)
    controller.release("`")

def nuke():
    controller.press("`")
    controller.type("wk"*40)
    controller.release("`")

def shape():
    controller.press("`")
    controller.type("f"*500)
    #controller.release("`")

def circlecrash():
    controller.press("`")
    for _ in range(150):
        for _ in range(150):
            controller.tap("c")
            controller.tap("h")
    controller.release("`")

def minicirclecrash():
    controller.press("`")
    for _ in range(50):
        for _ in range(100):
            controller.tap("c")
            controller.tap("h")
    controller.release("`")

def circles(amt = 210):
    controller.press("`")
    for _ in range(amt):
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def walls():
    controller.press("`")
    controller.type("x"*210)
    controller.release("`")

def slowcircle():
    global slowcircles
    controller.press("`")
    while slowcircles:
        controller.tap("c")
        controller.tap("h")
        time.sleep(0.04)
    controller.release("`")

def circle_tail_legacy():
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
            controller.tap("c")
            time.sleep(0.1)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            time.sleep(0.04)
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            controller.tap("c")
            time.sleep(0.1)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            controller.tap("c")
            time.sleep(0.1)
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
        time.sleep(0.02)  # Add a small delay to prevent locking up your systema

def score():
    controller.press("`")
    controller.type("n"*20000)
    controller.release("`")

def benchmark(amt = 5000):
    shift_pressed = threading.Event()

    def on_press(key):
        if key == Key.shift or key == Key.shift_r:
            shift_pressed.set()
            print("Benchmark stopped by Shift key press.")

    # Start the benchmark
    start = time.time()
    circles(amt)
    print("Press any Shift key to stop the benchmark timer...")
    # Start keyboard listener
    with KeyboardListener(on_press=on_press) as listener:
        shift_pressed.wait()  # Wait until Shift is pressed
        listener.stop()
    elapsed = time.time() - start
    print(f"{amt} circles in {round(elapsed*1000, 3)} ms")
    controller.tap(Key.enter)
    time.sleep(0.15)
    controller.type(f"> [{round(elapsed * 1000, 3)}ms] <")
    time.sleep(0.1)
    for _ in range(2):
        controller.tap(Key.enter)
        time.sleep(0.1)
    bps = round(amt * (1 / elapsed), 3) if elapsed > 0 else 0
    controller.type(f"> [{bps}] <")
    time.sleep(0.1)
    controller.tap(Key.enter)
    time.sleep(0.1)

def score50m():
    controller.press("`")
    controller.type("f"*20)
    controller.release("`")

def engispam():
    global engispamming
    while engispamming:
        controller.tap(",")
        controller.tap("y")
        controller.tap("i")
        controller.press("`")
        controller.press("a")
        controller.press("c")
        controller.release("`")
        controller.press(Key.space)
        time.sleep(0.25)
        controller.release(Key.space)
        controller.press("`")
        controller.press("q")
        controller.release("`")

def circle():
    controller.press("`")
    controller.type("ch")
    controller.release("`")
        
def slowwall():
    controller.press("`")
    for _ in range(50):
        controller.tap("x")
        time.sleep(0.08)
    controller.release("`")

def randomwall():
    global randomwalld
    controller.press("`")
    while randomwalld:
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
    controller.release("`")

def shapel():
    controller.press("`")
    for _ in range(10):
        controller.tap("f")
        time.sleep(0.04)
        controller.tap("b")

def random_mouse_w():
    global randomwalld
    randomwalld = True
    while randomwalld:
        mouse.position = (random.randint(5, 1705), random.randint(173, 1107))
        time.sleep(0.02)
        pos = mouse.position
        controller.press("w")
        mouse.position = (pos[0]+random.randint(-5, 5), pos[1]+random.randint(-5, 5))
        time.sleep(0.05)
        controller.release("w")
        time.sleep(0.02)

def simpletail(amt=20):
    controller.press("`")
    delay = 0.04
    s2 = 25
    time.sleep(delay)
    for _ in range(amt):
        for _ in range(3):
            circle()
        controller.press("`")
        time.sleep(delay)
        controller.press("c")
        time.sleep(delay*3)
        controller.release("c")
        mouse.position = (mouse.position[0] + s2, mouse.position[1])
        time.sleep(delay * 2.5)
    mouse.position = (mouse.position[0] + 2 * s2, mouse.position[1])
    pos = mouse.position
    mouse.position = (pos[0] + 30, pos[1])
    controller.press("`")
    time.sleep(2)
    mouse.position = (pos[0] - s2, pos[1])
    for _ in range(amt - 1):
        controller.press("j")
        time.sleep(delay)
        mouse.position = (mouse.position[0] - s2, mouse.position[1])
        time.sleep(delay)
        controller.release("j")
        time.sleep(delay)
    controller.release("`")

def controllednuke():
    global controllednuke_points, controllednuke_active, step
    controllednuke_points = []
    controllednuke_active = True
    mouse = MouseController()
    print(f"Controlled Nuke: You have 10 seconds to select two points.")
    print(f"Click two points with the left mouse button. Step size: {step}")
    start_time = time.time()
    while len(controllednuke_points) < 2 and time.time() - start_time < 10:
        time.sleep(0.01)
    controllednuke_active = False  # Stop collecting more points
    if len(controllednuke_points) < 2:
        print("Timed out waiting for points.")
        return
    (x1, y1), (x2, y2) = controllednuke_points
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    print(f"Controlled Nuke: Rectangle from ({x1}, {y1}) to ({x2}, {y2}) with step {step}")
    controller.press("`")
    time.sleep(2)
    min_x, max_x = sorted([x1, x2])
    min_y, max_y = sorted([y1, y2])
    for x in range(min_x, max_x + 1, step):
        for y in range(min_y, max_y + 1, step):
            mouse.position = (x, y)
            time.sleep(0.05)
            controller.tap("k")
    print("Controlled Nuke complete.")
    controller.release("`")

def start_arena_automation(atype = 1):
    global automation_thread, size_automation
    # ensure the running flag is set before starting the thread
    size_automation = True
    if automation_thread is None or not automation_thread.is_alive():
        automation_thread = threading.Thread(target=arena_size_automation, args=(atype,))
        automation_thread.daemon = True
        automation_thread.start()

def start_engispam():
    global engispam_thread
    if engispam_thread is None or not engispam_thread.is_alive():
        engispam_thread = threading.Thread(target=engispam)
        engispam_thread.daemon = True
        engispam_thread.start()

def start_brain_damage():
    global braindamage_thread
    if braindamage_thread is None or not braindamage_thread.is_alive():
        braindamage_thread = threading.Thread(target=brain_damage)
        braindamage_thread.daemon = True
        braindamage_thread.start()

def start_circle_tail_legacy():
    global circle_tail_legacy_thread
    if circle_tail_legacy_thread is None or not circle_tail_legacy_thread.is_alive():
        circle_tail_legacy_thread = threading.Thread(target=circle_tail_legacy)
        circle_tail_legacy_thread.daemon = True
        circle_tail_legacy_thread.start()

def start_randomwall():
    global randomwall_thread
    if randomwall_thread is None or not randomwall_thread.is_alive():
        randomwall_thread = threading.Thread(target=randomwall)
        randomwall_thread.daemon = True
        randomwall_thread.start()

def start_slowcircle():
    global slowcircle_thread
    if slowcircle_thread is None or not slowcircle_thread.is_alive():
        slowcircle_thread = threading.Thread(target=slowcircle)
        slowcircle_thread.daemon = True
        slowcircle_thread.start()

def start_controllednuke():
    thread = threading.Thread(target=controllednuke)
    thread.daemon = True
    thread.start()

def start_random_mouse_w():
    global randomwall_thread
    if randomwall_thread is None or not randomwall_thread.is_alive():
        randomwall_thread = threading.Thread(target=random_mouse_w)
        randomwall_thread.daemon = True
        randomwall_thread.start()

def _ctrl1_waiter():
    global ctrl1_count, ctrl1_first_time, ctrl1_thread
    # wait 2 seconds from first press, then act on count
    first = ctrl1_first_time
    time.sleep(2.0)
    # ensure no newer sequence started
    if time.time() - first >= 2.0:
        atype = min(max(ctrl1_count, 1), 3)  # clamp 1..3
        print(f"Detected {ctrl1_count} ctrl+1 presses -> starting arena automation type {atype}")
        start_arena_automation(int(atype))
        ctrl1_count = 0
        ctrl1_first_time = 0.0
        ctrl1_thread = None

# Normalize modifier detection across platforms
def is_ctrl(k):
    """Check if key is Ctrl (or Cmd if ctrlswap=True on macOS)"""
    global ctrlswap
    if ctrlswap and PLATFORM == 'darwin':
        # Use Cmd key on macOS when ctrlswap is enabled
        return k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)
    else:
        # Use Ctrl key normally
        return k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)

def is_alt(k):
    # On macOS, Option is alt; on other platforms, Alt is alt
    return k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)

def is_modifier_for_arrow_nudge(k):
    """Return True if this key should trigger 1px arrow nudges.
    
    Platform-specific:
    - macOS: Option (alt)
    - Windows/Linux: Alt
    - Android: Alt (if supported)
    """
    return is_alt(k)

def on_press(key):
    global size_automation, braindamage, circlecash, slowcircles, randomwalld, engispamming
    global ctrl6_last_time, ctrl6_armed
    global ctrlo_last_time, ctrlo_armed
    global controllednuke_points, controllednuke_active
    global ctrl1_count, ctrl1_first_time, ctrl1_thread
    global slowcircle_shift_bind, ctrlswap, macros_enabled
    try:
        # Use Right Shift instead of Escape to stop scripts
        if key == keyboard.Key.shift_r:
            if 'ctrl' in pressed_keys:
                print("estop")
                exit(0)
            else:
                size_automation = False
                braindamage = False
                randomwalld = False
                slowcircles = False
                engispamming = False
                slowcircle_shift_bind = False
                print("nstop")
                # stop all threads
        elif is_ctrl(key):
            pressed_keys.add('ctrl')
        elif is_alt(key):
            pressed_keys.add('alt')
            # print("alt down")  # uncomment to debug
        # Handle actual Cmd key presses (for toggling ctrlswap on macOS)
        elif key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            if ctrlswap:
                pressed_keys.add('ctrl')  # Treat Cmd as Ctrl when ctrlswap is enabled
        elif key in (keyboard.Key.up, keyboard.Key.down, keyboard.Key.left, keyboard.Key.right):
            if 'alt' in pressed_keys:
                x, y = mouse.position
                if key == keyboard.Key.up:
                    mouse.position = (x, y - 1)
                elif key == keyboard.Key.down:
                    mouse.position = (x, y + 1)
                elif key == keyboard.Key.left:
                    mouse.position = (x - 1, y)
                elif key == keyboard.Key.right:
                    mouse.position = (x + 1, y)
                return
        
        # Check if macros are enabled before processing hotkeys
        if not macros_enabled:
            return
            
        # NEW: pressing Left Shift starts slowcircles if binding is enabled
        if key == keyboard.Key.shift_l:
            if slowcircle_shift_bind:
                if not slowcircles:
                    print("art on")
                slowcircles = True
                start_slowcircle()
        elif hasattr(key, 'char') and key.char and key.char == 'y':
            if 'ctrl' in pressed_keys:
                print("cnuke")
                start_controllednuke()
        elif hasattr(key, 'char') and key.char and key.char=='1':
            if 'ctrl' in pressed_keys:
                # count ctrl+1 presses within 2 seconds to select atype 1/2/3
                now = time.time()
                if ctrl1_count == 0:
                    ctrl1_first_time = now
                    ctrl1_count = 1
                    # spawn waiter thread
                    ctrl1_thread = threading.Thread(target=_ctrl1_waiter)
                    ctrl1_thread.daemon = True
                    ctrl1_thread.start()
                    print("arena scrip")
                else:
                    # if within 2s of first press, increment count (cap at 3)
                    if now - ctrl1_first_time <= 2.0:
                        ctrl1_count = min(ctrl1_count + 1, 3)
                        print(f"ctrl+1 detected ({ctrl1_count})")
                    else:
                        # too late, start new sequence
                        ctrl1_first_time = now
                        ctrl1_count = 1
                        # restart waiter thread if previous finished
                        if ctrl1_thread is None or not ctrl1_thread.is_alive():
                            ctrl1_thread = threading.Thread(target=_ctrl1_waiter)
                            ctrl1_thread.daemon = True
                            ctrl1_thread.start()
                        print("arena script")
        elif hasattr(key, 'char') and key.char and key.char=='2':
            if 'ctrl' in pressed_keys:
                print("conq")
                conq_quickstart()
        elif hasattr(key, 'char') and key.char and key.char=='3':
            if 'ctrl' in pressed_keys:
                braindamage = True
                print("bdmg")
                start_brain_damage()
        elif hasattr(key, 'char') and key.char and key.char=='4':
            if 'ctrl' in pressed_keys:
                circle()
        elif hasattr(key, 'char') and key.char and key.char=='5':
            if 'ctrl' in pressed_keys:
                print("circle square")
                start_circle_tail_legacy()
        elif hasattr(key, 'char') and key.char and key.char=='6':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrl6_armed and (now - ctrl6_last_time <= 5):
                    print("death by circle")
                    circlecrash()
                    ctrl6_armed = False
                else:
                    print("crasharmed")
                    ctrl6_armed = True
                    ctrl6_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='7':
            if 'ctrl' in pressed_keys:
                print("wallcrash")
                wallcrash()
        elif hasattr(key, 'char') and key.char and key.char=='8':
            if 'ctrl' in pressed_keys:
                print("simple tail")
                simpletail()
        elif hasattr(key, 'char') and key.char and key.char=='9':
            if 'ctrl' in pressed_keys:
                print("NUKE GO BRRRRRRRRRR")
                nuke()
        elif hasattr(key, 'char') and key.char and key.char=='f':
            if 'ctrl' in pressed_keys:
                print("shape nuke")
                shape() 
        elif hasattr(key, 'char') and key.char and key.char=='d':
            if 'ctrl' in pressed_keys:
                print("randomdrag")
                start_random_mouse_w()
        elif hasattr(key, 'char') and key.char and key.char=='n':
            if 'ctrl' in pressed_keys:
                print("score")
                score()
        elif hasattr(key, 'char') and key.char and key.char=='b':
            if 'ctrl' in pressed_keys:
                print("200 circles")
                circles()
        elif hasattr(key, 'char') and key.char and key.char=='w':
            if 'ctrl' in pressed_keys:
                print("200 walls")
                walls()
        elif hasattr(key, 'char') and key.char and key.char=='v':
            if 'ctrl' in pressed_keys:
                print("shapel")
                shapel()
        elif hasattr(key, 'char') and key.char and key.char=='z':
            if 'ctrl' in pressed_keys:
                slowwall()
        elif hasattr(key, 'char') and key.char and key.char=='c':
            if 'ctrl' in pressed_keys:
                # NEW: enable binding to Left Shift instead of starting immediately
                slowcircle_shift_bind = True
                slowcircles = False  # ensure idle until Left Shift is pressed
                print("toggle art")
        elif hasattr(key, 'char') and key.char and key.char=='m':
            if 'ctrl' in pressed_keys:
                print("benchmarking...")
                benchmark()
        elif hasattr(key, 'char') and key.char and key.char=='a':
            if 'ctrl' in pressed_keys:
                randomwalld = True
                print("all abuse")
                start_randomwall()
        elif hasattr(key, 'char') and key.char and key.char=='o':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrlo_armed and (now - ctrlo_last_time <= 5):
                    print("minicirclecrash")
                    minicirclecrash()
                    ctrlo_armed = False
                else:
                    print("minicrash armed")
                    ctrlo_armed = True
                    ctrlo_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='e':
            if 'ctrl' in pressed_keys:
                print("engispam")
                engispamming = True
                start_engispam()
        elif hasattr(key, 'char') and key.char and key.char=='l':
            if 'ctrl' in pressed_keys:
                print("50m score")
                score50m()
        elif hasattr(key, 'char') and key.char and key.char=='h':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                for _ in range(3000):
                    controller.tap("h")
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='r':
            if 'ctrl' in pressed_keys:
                for _ in range(200):
                    controller.tap(Key.enter)
                    controller.type("$arena close")
                    controller.tap(Key.enter)
        elif hasattr(key, 'char') and key.char and key.char=='s':
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                print("quicksetup")
                controller.press("`")
                time.sleep(0.05)
                controller.tap("i")
                controller.press("s")
                for _ in range(20):
                    controller.tap("h")
                time.sleep(0.05)
                controller.tap("m")
                controller.release("s")
                controller.tap("s")
                time.sleep(0.05)
                controller.press("a")
                time.sleep(0.05)
                controller.tap("c")
                controller.tap("w")
                controller.tap("e")
                controller.tap("t")
                controller.tap("o")
                controller.release("a")
                controller.release("`")
    except Exception as e:
        print(f"Error: {e}")
    
def on_release(key):
    global slowcircles, slowcircle_shift_bind
    if is_ctrl(key):
        pressed_keys.discard('ctrl')
    elif key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
        if ctrlswap:
            pressed_keys.discard('ctrl')  # Release Cmd when ctrlswap is enabled
    elif is_alt(key):
        pressed_keys.discard('alt')
        # print("alt up")  # uncomment to debug
    # NEW: releasing Left Shift stops slowcircles if binding is enabled
    elif key == keyboard.Key.shift_l:
        if slowcircle_shift_bind and slowcircles:
            print("art off")
        if slowcircle_shift_bind:
            slowcircles = False
    elif key in pressed_keys:
        pressed_keys.remove(key)

def on_click(x, y, button, pressed):
    global controllednuke_points, controllednuke_active
    if controllednuke_active and pressed and button == Button.left:
        controllednuke_points.append((x, y))
        print(f"cnuke point: {len(controllednuke_points)} at ({x}, {y})")

# GUI Class for Macro Control Panel
class MacroGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Arras Macro Control Panel")
        self.root.configure(bg='black')
        self.root.geometry("400x600")
        
        # Macro button configurations: (title, function, state_var_name, is_boolean)
        # is_boolean=True means the macro toggles on/off, False means one-shot execution
        self.macros = [
            ("Arena Automation Type 1", lambda: self.trigger_macro(start_arena_automation, 1), 'size_automation', True),
            ("Arena Automation Type 2", lambda: self.trigger_macro(start_arena_automation, 2), 'size_automation', True),
            ("Arena Automation Type 3", lambda: self.trigger_macro(start_arena_automation, 3), 'size_automation', True),
            ("Conqueror", lambda: self.trigger_macro(conq_quickstart), None, False),
            ("Brain Damage", lambda: self.trigger_boolean_macro('braindamage'), 'braindamage', True),
            ("Circle", lambda: self.trigger_macro(circle), None, False),
            ("Tail (Legacy)", lambda: self.trigger_macro(start_circle_tail_legacy), None, False),
            ("Circle Crash", lambda: self.trigger_macro(circlecrash), None, False),
            ("Wall Crash", lambda: self.trigger_macro(wallcrash), None, False),
            ("Simple Tail", lambda: self.trigger_macro(simpletail), None, False),
            ("Nuke", lambda: self.trigger_macro(nuke), None, False),
            ("Shape Nuke", lambda: self.trigger_macro(shape), None, False),
            ("Score", lambda: self.trigger_macro(score), None, False),
            ("200 Circles", lambda: self.trigger_macro(circles), None, False),
            ("200 Walls", lambda: self.trigger_macro(walls), None, False),
            ("Slow Wall", lambda: self.trigger_macro(slowwall), None, False),
            ("Art (Shift)", lambda: self.trigger_boolean_macro('slowcircle_shift_bind'), 'slowcircle_shift_bind', True),
            ("Benchmark", lambda: self.trigger_macro(benchmark), None, False),
            ("Mini Circle Crash", lambda: self.trigger_macro(minicirclecrash), None, False),
            ("Engi Spam", lambda: self.trigger_boolean_macro('engispamming'), 'engispamming', True),
            ("50M Score", lambda: self.trigger_macro(score50m), None, False),
            ("Controlled Nuke", lambda: self.trigger_macro(start_controllednuke), None, False),
        ]
        
        # Create scrollable frame
        canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='black')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Toggle all macros button at top
        self.toggle_all_btn = tk.Button(
            scrollable_frame,
            text="DISABLE ALL MACROS",
            command=self.toggle_all_macros,
            bg='green',
            fg='white',
            font=('Arial', 12, 'bold'),
            height=2
        )
        self.toggle_all_btn.pack(fill='x', padx=10, pady=5)
        
        # Create buttons
        self.buttons = []
        for title, func, state_var, is_boolean in self.macros:
            btn = tk.Button(
                scrollable_frame,
                text=title,
                command=func,
                bg='green',
                fg='white',
                font=('Arial', 10),
                height=2
            )
            btn.pack(fill='x', padx=10, pady=2)
            self.buttons.append((btn, state_var, is_boolean))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Start periodic update
        self.update_button_colors()
    
    def toggle_boolean_macro(self, state_var_name):
        """Toggle a boolean macro on/off"""
        global size_automation, braindamage, randomwalld, slowcircles, engispamming, slowcircle_shift_bind, macros_enabled
        
        # Can't start new macros when disabled, but can stop running ones
        if not macros_enabled:
            current_state = globals().get(state_var_name, False)
            if not current_state:
                print(f"Cannot start {state_var_name}: macros are disabled!")
                return
            else:
                print(f"Stopping {state_var_name}...")
        
        # Toggle the state
        if state_var_name == 'size_automation':
            size_automation = not size_automation
            if size_automation:
                start_arena_automation(1)
        elif state_var_name == 'braindamage':
            braindamage = not braindamage
            if braindamage:
                start_brain_damage()
        elif state_var_name == 'randomwalld':
            randomwalld = not randomwalld
            if randomwalld:
                start_randomwall()
        elif state_var_name == 'slowcircles':
            slowcircles = not slowcircles
            if slowcircles:
                start_slowcircle()
        elif state_var_name == 'engispamming':
            engispamming = not engispamming
            if engispamming:
                start_engispam()
        elif state_var_name == 'slowcircle_shift_bind':
            slowcircle_shift_bind = not slowcircle_shift_bind
        
        current_state = globals().get(state_var_name, False)
        status = "ON" if current_state else "OFF"
        print(f"{state_var_name}: {status}")
        
    def toggle_slowcircle_bind(self):
        """Toggle slowcircle shift bind"""
        global slowcircle_shift_bind
        slowcircle_shift_bind = not slowcircle_shift_bind
        print(f"Slowcircle shift bind: {slowcircle_shift_bind}")
    
    def trigger_macro(self, func, *args):
        """Trigger a macro with 1 second delay"""
        global macros_enabled
        if not macros_enabled:
            print("Macros are disabled!")
            return
        else:
            print(f"Triggering macro: {func.__name__}")
            
        def delayed_trigger():
            time.sleep(1)
            if macros_enabled:  # Check again after delay
                func(*args)
        
        thread = threading.Thread(target=delayed_trigger)
        thread.daemon = True
        thread.start()
    
    def toggle_all_macros(self):
        """Toggle all macros on/off"""
        global macros_enabled, size_automation, braindamage, randomwalld, slowcircles, engispamming
        macros_enabled = not macros_enabled
        
        if not macros_enabled:
            # Don't stop running macros - let them continue but show as yellow
            self.toggle_all_btn.config(text="ENABLE ALL MACROS", bg='red')
            print("All macros DISABLED (running macros will continue but show as yellow)")
        else:
            self.toggle_all_btn.config(text="DISABLE ALL MACROS", bg='green')
            print("All macros ENABLED")
    
    def update_button_colors(self):
        """Update button colors based on state
        - Green: Ready (macros enabled, not running)
        - Blue: Active (macros enabled, running)
        - Red: Disabled (macros disabled, not running)
        - Yellow: Running but disabled (macros disabled, still running)
        """
        global macros_enabled, size_automation, braindamage, randomwalld, slowcircles, engispamming, slowcircle_shift_bind
        
        for btn, state_var, is_boolean in self.buttons:
            is_active = False
            
            # Check if this macro is active (only for boolean macros)
            if state_var and is_boolean:
                if state_var == 'size_automation':
                    is_active = size_automation
                elif state_var == 'braindamage':
                    is_active = braindamage
                elif state_var == 'randomwalld':
                    is_active = randomwalld
                elif state_var == 'slowcircles':
                    is_active = slowcircles
                elif state_var == 'engispamming':
                    is_active = engispamming
                elif state_var == 'slowcircle_shift_bind':
                    is_active = slowcircle_shift_bind
            
            # Set color based on state
            if is_active and not macros_enabled:
                # Running but macros disabled = yellow
                btn.config(bg='yellow', fg='black')
            elif is_active and macros_enabled:
                # Running and macros enabled = blue
                btn.config(bg='blue', fg='white')
            elif not is_active and not macros_enabled:
                # Not running and macros disabled = red
                btn.config(bg='red', fg='white')
            else:
                # Not running and macros enabled = green (ready)
                btn.config(bg='green', fg='white')
        
        # Schedule next update
        self.root.after(100, self.update_button_colors)
    
    def run(self):
        """Run the GUI main loop"""
        self.root.mainloop()

# Start GUI in separate thread
def start_gui():
    gui = MacroGUI()
    gui.run()

gui_thread = threading.Thread(target=start_gui)
gui_thread.daemon = True
gui_thread.start()

# Start mouse listener glocircley (after your keyboard listener setup)
mouse_listener = MouseListener(on_click=on_click)
mouse_listener.daemon = True
mouse_listener.start()

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()

