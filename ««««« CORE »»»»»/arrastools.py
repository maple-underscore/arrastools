"""Hotkey-driven Arras macros and drawing helpers.

The script mirrors historical behavior; readability tweaks (docstrings,
comments) clarify intent without altering any macro logic.
"""

import random
import time
import threading
import multiprocessing
from multiprocessing import Process
import platform
import sys
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event as MpEvent
else:
    MpEvent = Any

try:
    from pynput.keyboard import Controller as KeyboardController, Key, Listener as KeyboardListener
    from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener
except ImportError:
    print("Missing dependency: pynput is required to run this script.")
    print("Install with: python3 -m pip install -r requirements.txt")
    sys.exit(1)

# Detect platform
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows', 'android'

# Platform notes:
# - macOS: Ctrl hotkeys work; Option+Arrow for 1px nudges
# - Linux: Ctrl hotkeys work; Alt+Arrow for 1px nudges
# - Windows: Ctrl hotkeys work; Alt+Arrow for 1px nudges
# - Android: Limited support (pynput may not work on all devices)

length = 4

# Function
# Centralized set of flags/shared state used across macro helpers. Values are
# kept as globals because listeners spin up background threads that need access.
global automation_working, controller, circlecrash_working, mouse, art_working, step, ctrlswap, mcrash_working
global circle_mouse_active, circle_mouse_speed, circle_mouse_radius, circle_mouse_direction
step = 20
s = 25 #circle spacing in px
ctrlswap = False  # When True, use Cmd (macOS) instead of Ctrl for macros
circle_mouse_active = False
circle_mouse_speed = 0.02  # Time delay between updates (lower = faster)
circle_mouse_radius = 100  # Radius in pixels
circle_mouse_direction = 1  # 1 for clockwise, -1 for counterclockwise

# Arena automation limits
arena_auto_terminate = True  # If True, stop after arena_auto_max_commands
arena_auto_max_commands = 600  # Number of commands before auto-termination
arena_auto_rate_limit = 150  # Maximum commands per second (0 = unlimited)

automation_working = False
engispam_working = False
mcrash_working = False
mcrash_thread = None
engispam_thread = None
art_working = False
circlecrash_working = False
circlecrash_thread = None
braindamage_working = False
controller = KeyboardController()
mouse = MouseController()
pressed_keys = set()
automation_process = None
softwallstack_process = None
art_process = None
braindamage_process = None
tail_process = None
circle_mouse_process = None
engispam_process = None
circlecrash_process = None
mcrash_process: Process | None = None

# Shared multiprocessing primitives so worker processes can mirror thread-like behavior.
automation_event = multiprocessing.Event()
engispam_event = multiprocessing.Event()
art_event = multiprocessing.Event()
braindamage_event = multiprocessing.Event()
circle_mouse_event = multiprocessing.Event()
mcrash_event = multiprocessing.Event()
circle_mouse_radius_value = multiprocessing.Value('i', circle_mouse_radius)
circle_mouse_speed_value = multiprocessing.Value('d', circle_mouse_speed)
circle_mouse_direction_value = multiprocessing.Value('i', circle_mouse_direction)

processes = ["automation", "engispam", "art", "braindamage_working", "tail", "circle_mouse", "softwallstack", "circlecrash", "mcrash"]
for process in processes:
    exec(f"{process}_process = None")
    exec(f"global {process}_process, {process}_working")

# Add these globals near the top
ctrl6_last_time = 0
ctrl6_armed = False
ctrl7_last_time = 0
ctrl7_armed = False

# new ctrl+1 multi-press globals
ctrl1_count = 0
ctrl1_first_time = 0.0

# NEW: bind art_working to Left Shift when enabled via Ctrl+C
art_shift_bind = False
mcrash_shift_bind = False

def generate_even(low=2, high=1024):
    return random.choice([i for i in range(low, high + 1) if i % 2 == 0])

def run_cpp_macro(command, *args):
    """Run a C++ macro if available, return True if successful, False if need Python fallback."""
    cpp_binary = os.path.join(os.path.dirname(__file__), "..", "macro_tools")
    if os.path.exists(cpp_binary):
        try:
            cmd = [cpp_binary, command] + list(map(str, args))
            subprocess.run(cmd, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    return False

def type_unicode_blocks(hex_string: str | None = None, blocks: int = 3):
    """Type a sequence of Unicode characters encoded as 4-hex-digit code points.

    Format examples:
        "011156F2C11A" -> U+0111 U+56F2 U+C11A

    Behavior:
      - If hex_string is provided its length must be a multiple of 4; each 4-digit
        group is interpreted as a hexadecimal code point.
      - If hex_string is None, a random sequence of `blocks` code points will be
        generated (default 3 groups => 12 hex digits).
      - Surrogate range (D800-DFFF) and code points > 0x10FFFF are skipped and
        regenerated when auto-generating.
      - Null code point (0000) is replaced with a literal space to avoid issues
        with consumers treating NUL as terminator.
      - Any group that parses but produces an unsupported character will be
        replaced with '�'.

    The resulting characters are typed inside backticks to keep existing
    console-open convention consistent with other macros.
    """
    groups: list[str] = []
    if hex_string is not None:
        hex_string = hex_string.strip().upper()
        if len(hex_string) % 4 != 0:
            print("unicode blocks: invalid length (must be multiple of 4)")
            return
        for i in range(0, len(hex_string), 4):
            groups.append(hex_string[i:i+4])
    else:
        while len(groups) < blocks:
            cp = random.randint(0, 0xFFFF)
            # Skip surrogate range and prefer printable BMP subset; allow null rarely
            if 0xD800 <= cp <= 0xDFFF:
                continue
            groups.append(f"{cp:04X}")

    chars: list[str] = []
    for g in groups:
        try:
            cp = int(g, 16)
            if cp == 0:
                # Replace NUL with space to avoid termination semantics
                chars.append(' ')
                continue
            if cp > 0x10FFFF or (0xD800 <= cp <= 0xDFFF):
                chars.append('�')
                continue
            chars.append(chr(cp))
        except Exception:
            chars.append('�')

    out = ''.join(chars)
    print(f"unicode blocks: {' '.join(groups)} -> '{out}'")
    controller.type(out)

def arena_size_automation(atype: int = 1, run_event: MpEvent | None = None):
    """Spam $arena commands using ultra-optimized native C++ implementation.
    
    Falls back to Python implementation if C++ binary not found.
    Compile C++ version with: make
    """
    import os
    import subprocess
    
    global arena_auto_terminate, arena_auto_max_commands, arena_auto_rate_limit
    
    # Calculate delay between commands based on rate limit
    cmd_delay = (1.0 / arena_auto_rate_limit) if arena_auto_rate_limit > 0 else 0
    
    # Try to use the C++ binary for maximum performance (only if no rate limit)
    # C++ binary doesn't support rate limiting yet, so use Python when rate limit is set
    cpp_binary = os.path.join(os.path.dirname(__file__), "..", "arena_automation")
    
    if os.path.exists(cpp_binary) and arena_auto_rate_limit == 0:
        print(f"Using optimized C++ implementation (type {atype})")
        if arena_auto_terminate:
            print(f"Will terminate after {arena_auto_max_commands} commands")
        try:
            # Run C++ binary in subprocess - it will run until Ctrl+C or process killed
            proc = subprocess.Popen([cpp_binary, str(atype)])
            
            # Monitor run_event and terminate when cleared or max commands reached
            if run_event is not None:
                cmd_count = 0
                while run_event.is_set():
                    time.sleep(0.1)
                    if arena_auto_terminate:
                        cmd_count += 1  # Approximation: ~10 commands per 0.1s
                        if cmd_count >= arena_auto_max_commands // 10:
                            break
                proc.terminate()
                proc.wait(timeout=2)
            else:
                proc.wait()
            return
        except Exception as e:
            print(f"C++ binary failed: {e}, falling back to Python")
    
    # Fallback to Python implementation
    print(f"Using Python implementation (type {atype}). Compile C++ for 10-100x speedup: make")
    if arena_auto_terminate:
        print(f"Will terminate after {arena_auto_max_commands} commands")
    if arena_auto_rate_limit > 0:
        print(f"Rate limit: {arena_auto_rate_limit} commands/sec (delay: {cmd_delay:.3f}s)")
    
    if run_event is None:
        run_event = multiprocessing.Event()
        run_event.set()

    cmd_count = 0
    if atype == 1:
        while run_event.is_set():
            x = generate_even()
            y = generate_even()
            controller.tap(Key.enter)
            controller.type(f"$arena size {x} {y}")
            controller.tap(Key.enter)
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
    elif atype == 2:
        # x and y go from 2 to 1024 in steps of 2
        x = 2
        y = 2
        direction_x = 2
        direction_y = 2
        while run_event.is_set():
            controller.tap(Key.enter)
            controller.type(f"$arena size {x} {y}")
            controller.tap(Key.enter)
            x += direction_x
            y += direction_y
            # Clamp and reverse direction if out of bounds
            if x > 1024:
                x = 1024
                direction_x = -2
            elif x < 2:
                x = 2
                direction_x = 2
            if y > 1024:
                y = 1024
                direction_y = -2
            elif y < 2:
                y = 2
                direction_y = 2
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
    elif atype == 3:
        # x goes from 2 to 1024, y goes from 1024 to 2
        x = 2
        y = 1024
        direction_x = 2
        direction_y = -2
        while run_event.is_set():
            controller.tap(Key.enter)
            controller.type(f"$arena size {x} {y}")
            controller.tap(Key.enter)
            x += direction_x
            y += direction_y
            # Clamp and reverse direction if out of bounds
            if x > 1024:
                x = 1024
                direction_x = -2
            elif x < 2:
                x = 2
                direction_x = 2
            if y > 1024:
                y = 1024
                direction_y = -2
            elif y < 2:
                y = 2
                direction_y = 2
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
            if y >= 1024 or y <= 2:
                direction_y *= -1
        
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
    if run_cpp_macro("wallcrash"):
        return
    controller.press("`")
    controller.type("x"*1800)
    controller.release("`")

def nuke():
    if run_cpp_macro("nuke"):
        return
    controller.press("`")
    controller.type("wk"*100)
    controller.release("`")

def shape():
    if run_cpp_macro("shape"):
        return
    controller.press("`")
    controller.type("f"*5000)
    controller.release("`")

def shape2():
    if run_cpp_macro("shape2"):
        return
    controller.press("`")
    controller.type("f"*1000)
    controller.press("w")
    controller.release("`")

def circlecrash():
    if run_cpp_macro("circlecrash"):
        return
    controller.press("`")
    for _ in range(180):
        for _ in range(180):
            controller.tap("c")
            controller.tap("h")
    controller.release("`")

def minicirclecrash():
    if run_cpp_macro("minicirclecrash"):
        return
    controller.press("`")
    for _ in range(25):
        for _ in range(100):
            controller.tap("c")
            controller.tap("h")
    controller.release("`")

def circles(amt = 210):
    if run_cpp_macro("circles", amt):
        return
    controller.press("`")
    for _ in range(amt):
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def walls():
    if run_cpp_macro("walls"):
        return
    controller.press("`")
    controller.type("x"*210)
    controller.release("`")

def art(run_event: MpEvent):
    controller.press("`")
    while run_event.is_set():
        controller.tap("c")
        controller.tap("h")
        time.sleep(0.02)
    controller.release("`")

def mcrash(run_event: MpEvent):
    controller.press("`")
    while run_event.is_set():
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def tail():
    controller.press("`")
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

def brain_damage(run_event: MpEvent):
    mouse = MouseController()
    while run_event.is_set():
        mouse.position = (random.randint(0, 1710), random.randint(168, 1112))
        time.sleep(0.02)  # Add a small delay to prevent locking up your system

def circle_mouse(
    run_event: MpEvent,
    radius_value: Any,
    speed_value: Any,
    direction_value: Any,
):
    """Move mouse in circles around a center point. Press '\\' to reverse direction."""
    import math

    print("Click anywhere to set the center point for circular motion...")
    temp_points: list[tuple[int, int]] = []

    def temp_click_handler(x, y, button, pressed):
        if pressed and button == Button.left and run_event.is_set():
            temp_points.append((x, y))

    temp_listener = MouseListener(on_click=temp_click_handler)
    temp_listener.start()

    start_time = time.time()
    while len(temp_points) == 0 and run_event.is_set() and time.time() - start_time < 10:
        time.sleep(0.01)

    temp_listener.stop()

    if len(temp_points) == 0 or not run_event.is_set():
        print("Circle mouse: No point selected or cancelled")
        return

    center_x, center_y = temp_points[0]
    print(
        "Circle mouse: center (%s, %s), radius %s, speed %.4f"
        % (center_x, center_y, radius_value.value, speed_value.value)
    )

    angle = 0.0
    while run_event.is_set():
        radius = max(radius_value.value, 5)
        speed = max(speed_value.value, 0.001)
        direction = 1 if direction_value.value >= 0 else -1

        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))
        mouse.position = (x, y)

        angle_step_base = 5.0 / max(radius, 10)
        angle += direction * angle_step_base
        if angle >= 2 * math.pi:
            angle = 0.0

        time.sleep(speed)

def score():
    if run_cpp_macro("score"):
        return
    controller.press("`")
    controller.type("n"*20000)
    controller.release("`")

def benchmark(amt = 5000):
    if run_cpp_macro("benchmark", amt):
        return
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

def engispam(run_event: MpEvent):
    while run_event.is_set():
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

def softwallstack():
    walls()
    start = mouse.position
    stackpos = (start[0] - s, start[1] + 4 * s)
    controller.press("`")
    for _ in range(200):
        mouse.position = (start[0] + 2 * s, start[1])
        controller.tap("w")
        time.sleep(0.03)
        controller.press("c")
        time.sleep(0.03)
        controller.release("c")
        time.sleep(0.03)
        controller.tap("y")
        time.sleep(0.03)
        controller.press("w")
        mouse.position = stackpos
        time.sleep(0.03)
        controller.release("w")
    controller.release("`")


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

def controllednuke():
    global step
    mouse = MouseController()
    print("Controlled Nuke: You have 10 seconds to select two points.")
    print(f"Click two points with the left mouse button. Step size: {step}")

    selected: list[tuple[int, int]] = []

    def click_handler(x, y, button, pressed):
        if pressed and button == Button.left:
            selected.append((int(x), int(y)))
            print(f"cnuke point: {len(selected)} at ({int(x)}, {int(y)})")

    listener = MouseListener(on_click=click_handler)
    listener.start()

    start_time = time.time()
    while len(selected) < 2 and time.time() - start_time < 10:
        time.sleep(0.01)

    listener.stop()
    if len(selected) < 2:
        print("Timed out waiting for points.")
        return

    (x1, y1), (x2, y2) = selected
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
    global automation_process, automation_working
    automation_working = True
    automation_event.set()
    if automation_process is None or not automation_process.is_alive():
        automation_process = multiprocessing.Process(
            target=arena_size_automation,
            args=(atype, automation_event),
        )
        automation_process.daemon = True
        automation_process.start()

def start_engispam():
    global engispam_process
    engispam_event.set()
    if engispam_process is None or not engispam_process.is_alive():
        engispam_process = multiprocessing.Process(target=engispam, args=(engispam_event,))
        engispam_process.daemon = True
        engispam_process.start()

def start_brain_damage():
    global braindamage_process
    braindamage_event.set()
    if braindamage_process is None or not braindamage_process.is_alive():
        braindamage_process = multiprocessing.Process(target=brain_damage, args=(braindamage_event,))
        braindamage_process.daemon = True
        braindamage_process.start()

def start_tail():
    global tail_process
    if tail_process is None or not tail_process.is_alive():
        tail_process = multiprocessing.Process(target=tail)
        tail_process.daemon = True
        tail_process.start()

def start_circle_mouse():
    global circle_mouse_process
    circle_mouse_event.set()
    circle_mouse_radius_value.value = circle_mouse_radius
    circle_mouse_speed_value.value = circle_mouse_speed
    circle_mouse_direction_value.value = circle_mouse_direction
    if circle_mouse_process is None or not circle_mouse_process.is_alive():
        circle_mouse_process = multiprocessing.Process(
            target=circle_mouse,
            args=(
                circle_mouse_event,
                circle_mouse_radius_value,
                circle_mouse_speed_value,
                circle_mouse_direction_value,
            ),
        )
        circle_mouse_process.daemon = True
        circle_mouse_process.start()
        monitor = threading.Thread(target=_monitor_circle_mouse, args=(circle_mouse_process,))
        monitor.daemon = True
        monitor.start()

def stop_circle_mouse():
    """Gracefully stop the circle mouse process."""
    global circle_mouse_process
    circle_mouse_event.clear()
    if circle_mouse_process is not None:
        circle_mouse_process.join(timeout=1)
        if circle_mouse_process.is_alive():
            circle_mouse_process.terminate()
        circle_mouse_process = None

def _monitor_circle_mouse(proc: Process):
    """Reset circle-mouse state when its process exits."""
    global circle_mouse_process, circle_mouse_active
    if proc is None:
        return
    proc.join()
    if circle_mouse_process is proc:
        circle_mouse_event.clear()
        circle_mouse_active = False
        circle_mouse_process = None

def start_art():
    global art_process
    art_event.set()
    if art_process is None or not art_process.is_alive():
        art_process = multiprocessing.Process(target=art, args=(art_event,))
        art_process.daemon = True
        art_process.start()

def start_softwallstack():
    global softwallstack_process
    if softwallstack_process is None or not softwallstack_process.is_alive():
        softwallstack_process = multiprocessing.Process(target=softwallstack)
        softwallstack_process.daemon = True
        softwallstack_process.start()

def start_controllednuke():
    proc = multiprocessing.Process(target=controllednuke)
    proc.daemon = True
    proc.start()

def start_mcrash():
    global mcrash_process, mcrash_working
    mcrash_event.set()
    mcrash_working = True
    if mcrash_process is None or not mcrash_process.is_alive():
        mcrash_process = multiprocessing.Process(target=mcrash, args=(mcrash_event,))
        mcrash_process.daemon = True
        mcrash_process.start()

def _ctrl1_waiter():
    global ctrl1_count, ctrl1_first_time
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

# Normalize modifier detection across platforms
def is_ctrl(k):
    """Check if key is Ctrl (or Cmd if ctrlswap=True on macOS)"""
    global ctrlswap
    if ctrlswap and PLATFORM == 'darwin':
        # Use Cmd key on macOS when ctrlswap is enabled
        return k in (Key.cmd, Key.cmd_l, Key.cmd_r)
    else:
        # Use Ctrl key normally
        return k in (Key.ctrl, Key.ctrl_l, Key.ctrl_r)

def is_alt(k):
    # On macOS, Option is alt; on other platforms, Alt is alt
    return k in (Key.alt, Key.alt_l, Key.alt_r)

def stopallthreads():
    global automation_process, engispam_process, art_process, braindamage_process
    global tail_process, circle_mouse_process, softwallstack_process, circlecrash_process, mcrash_process
    global automation_working, engispam_working, art_working, braindamage_working, mcrash_working
    global circle_mouse_active
    
    # Set all flags to False
    automation_working = False
    engispam_working = False
    art_working = False
    braindamage_working = False
    circle_mouse_active = False
    mcrash_working = False
    automation_event.clear()
    engispam_event.clear()
    art_event.clear()
    braindamage_event.clear()
    circle_mouse_event.clear()
    mcrash_event.clear()
    stop_circle_mouse()
    
    # Terminate all processes
    for proc in [automation_process, engispam_process, art_process, braindamage_process,
                 tail_process, softwallstack_process, circlecrash_process, mcrash_process]:
        if proc is not None and proc.is_alive():
            proc.terminate()
            proc.join(timeout=1)
    
    # Reset all process references
    automation_process = None
    engispam_process = None
    art_process = None
    braindamage_process = None
    tail_process = None
    circle_mouse_process = None
    softwallstack_process = None
    circlecrash_process = None
    mcrash_process = None
    mcrash_process = None

def is_modifier_for_arrow_nudge(k):
    """Return True if this key should trigger 1px arrow nudges.
    
    Platform-specific:
    - macOS: Option (alt)
    - Windows/Linux: Alt
    - Android: Alt (if supported)
    """
    return is_alt(k)

def on_press(key):
    global automation_working, braindamage_working, circlecrash_working, art_working, engispam_working, mcrash_working
    global ctrl6_last_time, ctrl6_armed, ctrl7_last_time, ctrl7_armed
    global ctrl1_count, ctrl1_first_time
    global art_shift_bind, mcrash_shift_bind, ctrlswap
    global circle_mouse_active, circle_mouse_speed, circle_mouse_radius, circle_mouse_direction
    try:
        # Workaround for pynput macOS Unicode decode bug - some special keys trigger this
        if key is None:
            return
        # Use Right Shift instead of Escape to stop scripts
        if key == Key.shift_r:
            if 'ctrl' in pressed_keys:
                print("estop")
                exit(0)
            else:
                automation_working = False
                braindamage_working = False
                art_working = False
                engispam_working = False
                art_shift_bind = False
                mcrash_shift_bind = False
                circle_mouse_active = False
                stopallthreads()
                print("nstop")
        elif is_ctrl(key):
            pressed_keys.add('ctrl')
        elif is_alt(key):
            pressed_keys.add('alt')
            # print("alt down")  # uncomment to debug
        # Handle actual Cmd key presses (for toggling ctrlswap on macOS)
        elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
            if ctrlswap:
                pressed_keys.add('ctrl')  # Treat Cmd as Ctrl when ctrlswap is enabled
        elif key in (Key.up, Key.down, Key.left, Key.right):
            if 'alt' in pressed_keys:
                x, y = mouse.position
                if key == Key.up:
                    mouse.position = (x, y - 1)
                elif key == Key.down:
                    mouse.position = (x, y + 1)
                elif key == Key.left:
                    mouse.position = (x - 1, y)
                elif key == Key.right:
                    mouse.position = (x + 1, y)
                return
        # NEW: pressing Left Shift starts art_working if binding is enabled
        elif key == Key.shift_l:
            if art_shift_bind:
                if not art_working:
                    print("art on")
                art_working = True
                start_art()
                if mcrash_shift_bind:
                    if not mcrash_working:
                        print("mcrash on")
                    mcrash_working = True
                    start_mcrash()
        elif hasattr(key, 'char') and key.char and key.char == "'":
            if 'ctrl' in pressed_keys:
                print("unicode blocks macro")
                type_unicode_blocks("027103B103C1056C1D07005B000BFFFC007F2400000B005D")
        elif hasattr(key, 'char') and key.char and key.char == ";":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.type("«∑∏¯ˇ†∫–⁄∞∆µ•‰ª¬∂Ω◊ﬂı®»")
        elif hasattr(key, 'char') and key.char and key.char == ",":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.type("«∑∫–µ¬∂Ωı»")
        elif hasattr(key, 'char') and key.char and key.char == ".":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type("«∑⫍ʩ∏₻‖₰¯ˇ†₢ƒ₥∫ø–⁄∞₯※˚")
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type("∆µ•‰৻৲©Íʨ⏔ʧª¬æ∂Ω⋾ↈ◊‘ﬂı®π↹")
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type("⁂⋣௹⁞ß૱ɧ⊯å⁛ɮ⏓⁊⁒Ϡç⁁⌁ϐÂͳϟ֏»")
                time.sleep(0.1)
                controller.tap(Key.enter)
        elif hasattr(key, 'char') and key.char and key.char == "/":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.type("₥ἆȵɪꜻƈ [𒈙]")
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
                    # spawn waiter thread (still using thread for timing)
                    waiter = threading.Thread(target=_ctrl1_waiter)
                    waiter.daemon = True
                    waiter.start()
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
                        waiter = threading.Thread(target=_ctrl1_waiter)
                        waiter.daemon = True
                        waiter.start()
                        print("arena script")
        elif hasattr(key, 'char') and key.char and key.char=='2':
            if 'ctrl' in pressed_keys:
                print("conq")
                conq_quickstart()
        elif hasattr(key, 'char') and key.char and key.char=='v':
            if 'ctrl' in pressed_keys:
                mcrash_shift_bind = True
                mcrash_working = False
                mcrash_event.clear()
                print("toggle mcrash")
        elif hasattr(key, 'char') and key.char and key.char=='3':
            if 'ctrl' in pressed_keys:
                braindamage_working = True
                print("bdmg")
                start_brain_damage()
        elif hasattr(key, 'char') and key.char and key.char=='4':
            if 'ctrl' in pressed_keys:
                circle()
        elif hasattr(key, 'char') and key.char and key.char=='5':
            if 'ctrl' in pressed_keys:
                print("circle square")
                start_tail()
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
                now = time.time()
                # double-tap lock: first tap arms, second tap within 5s triggers
                if ctrl7_armed and (now - ctrl7_last_time <= 5):
                    print("death by wall")
                    wallcrash()
                    ctrl7_armed = False
                else:
                    print("wallcrash armed")
                    ctrl7_armed = True
                    ctrl7_last_time = now
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
        elif hasattr(key, 'char') and key.char and key.char=='j':
            if 'ctrl' in pressed_keys:
                print("shape nuke2")
                shape2()
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
        elif hasattr(key, 'char') and key.char and key.char=='z':
            if 'ctrl' in pressed_keys:
                slowwall()
        elif hasattr(key, 'char') and key.char and key.char=='c':
            if 'ctrl' in pressed_keys:
                # NEW: enable binding to Left Shift instead of starting immediately
                art_shift_bind = True
                art_working = False  # ensure idle until Left Shift is pressed
                art_event.clear()
                print("toggle art")
        elif hasattr(key, 'char') and key.char and key.char=='m':
            if 'ctrl' in pressed_keys:
                print("benchmarking...")
                benchmark()
        elif hasattr(key, 'char') and key.char and key.char=='o':
            if 'ctrl' in pressed_keys:
                print("minicirclecrash")
                minicirclecrash()
        elif hasattr(key, 'char') and key.char and key.char=='e':
            if 'ctrl' in pressed_keys:
                print("engispam")
                engispam_working = True
                start_engispam()
        elif hasattr(key, 'char') and key.char and key.char=='l':
            if 'ctrl' in pressed_keys:
                print("50m score")
                score50m()
        elif hasattr(key, 'char') and key.char and key.char=='h':
            if 'ctrl' in pressed_keys:
                if not run_cpp_macro("heal"):
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
        elif hasattr(key, 'char') and key.char and key.char=='g':
            if 'ctrl' in pressed_keys:
                start_softwallstack()
        elif hasattr(key, 'char') and key.char and key.char=='s':
            if 'ctrl' in pressed_keys:
                time.sleep(0.1)
                print("quicksetup")
                controller.press("`")
                time.sleep(0.05)
                for _ in range(50):
                    controller.tap("n")
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
        elif hasattr(key, 'char') and key.char and key.char=='[':
            if 'ctrl' in pressed_keys:
                if not run_cpp_macro("shape_small"):
                    controller.press("`")
                    for _ in range(500):
                        controller.tap("f")
                    controller.release("`")
            else:
                circle_mouse_radius = max(circle_mouse_radius - 5, 5)
                circle_mouse_radius_value.value = circle_mouse_radius
                print(f"circle radius: {circle_mouse_radius}")
        elif hasattr(key, 'char') and key.char and key.char==']':
            if 'ctrl' in pressed_keys:
                if not run_cpp_macro("shape_large"):
                    controller.press("`")
                    for _ in range(5000):
                        controller.tap("f")
                    controller.release("`")
            else:
                circle_mouse_radius = min(circle_mouse_radius + 5, 1000)
                circle_mouse_radius_value.value = circle_mouse_radius
                print(f"circle radius: {circle_mouse_radius}")
        elif hasattr(key, 'char') and key.char and key.char=='u':
            if 'ctrl' in pressed_keys:
                circle_mouse_active = not circle_mouse_active
                if circle_mouse_active:
                    circle_mouse_direction = 1  # reset to default on start
                    circle_mouse_direction_value.value = circle_mouse_direction
                    print(f"circle mouse on (radius: {circle_mouse_radius}, speed: {circle_mouse_speed})")
                    start_circle_mouse()
                else:
                    print("circle mouse off")
                    stop_circle_mouse()
        elif hasattr(key, 'char') and key.char and key.char=='\\':
            # Toggle direction of circle while active
            if circle_mouse_active:
                circle_mouse_direction *= -1
                circle_mouse_direction_value.value = circle_mouse_direction
                dir_text = 'clockwise' if circle_mouse_direction == 1 else 'counterclockwise'
                print(f"circle direction -> {dir_text}")
        elif hasattr(key, 'char') and key.char and key.char=='k':
            if 'ctrl' in pressed_keys:
                controller.tap(Key.enter)
                time.sleep(0.05)
                controller.type("$arena team 1")
                controller.tap(Key.enter)
                controller.tap(Key.enter)
                time.sleep(0.05)
                controller.type("$arena spawnpoint 0 0")
                controller.tap(Key.enter)
        if hasattr(key, 'char') and key.char and key.char=='-':
            circle_mouse_speed = min(circle_mouse_speed + 0.001, 0.5)
            circle_mouse_speed_value.value = circle_mouse_speed
            print(f"circle speed: {round(circle_mouse_speed, 4)} (slower)")
        if hasattr(key, 'char') and key.char and key.char=='=':
            circle_mouse_speed = max(circle_mouse_speed - 0.001, 0.001)
            circle_mouse_speed_value.value = circle_mouse_speed
            print(f"circle speed: {round(circle_mouse_speed, 4)} (faster)")
    except UnicodeDecodeError:
        # Silently ignore pynput Unicode decode errors (macOS keyboard event bug)
        pass
    except Exception as e:
        print(f"Error: {e}")
    
def on_release(key):
    global art_working, art_shift_bind, mcrash_working, mcrash_shift_bind
    try:
        # Workaround for pynput macOS Unicode decode bug
        if key is None:
            return
    except UnicodeDecodeError:
        return
    
    if is_ctrl(key):
        pressed_keys.discard('ctrl')
    elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
        if ctrlswap:
            pressed_keys.discard('ctrl')  # Release Cmd when ctrlswap is enabled
    elif is_alt(key):
        pressed_keys.discard('alt')
        # print("alt up")  # uncomment to debug
    # NEW: releasing Left Shift stops art_working if binding is enabled
    elif key == Key.shift_l:
        if art_shift_bind and art_working:
            print("art off")
        if art_shift_bind:
            art_working = False
            art_event.clear()
        if mcrash_shift_bind and mcrash_working:
            print("mcrash off")
        if mcrash_shift_bind:
            mcrash_working = False
            mcrash_event.clear()
    elif key in pressed_keys:
        pressed_keys.remove(key)

if __name__ == '__main__':
    # Required for multiprocessing on macOS and Windows
    multiprocessing.set_start_method('spawn', force=True)
    
    print(f"Running on: {PLATFORM}")
    if PLATFORM not in ('darwin', 'linux', 'windows'):
        print(f"Warning: Platform '{PLATFORM}' may have limited support.")
        print("Tested on macOS, Linux (Arch/Debian/Ubuntu), and Windows.")
    
    # Wrapper to suppress pynput Unicode decode errors on macOS
    def safe_on_press(key):
        try:
            on_press(key)
        except UnicodeDecodeError:
            pass  # Ignore Unicode decode errors from special keys
    
    def safe_on_release(key):
        try:
            on_release(key)
        except UnicodeDecodeError:
            pass  # Ignore Unicode decode errors from special keys
    
    listener = KeyboardListener(on_press=safe_on_press, on_release=safe_on_release)
    listener.start()
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        listener.stop()
        stopallthreads()

