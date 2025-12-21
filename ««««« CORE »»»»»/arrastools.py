"""Hotkey-driven Arras macros and drawing helpers.

The script mirrors historical behavior; readability tweaks (docstrings,
comments) clarify intent without altering any macro logic.
"""

import random
import time
import threading
import multiprocessing
from multiprocessing import Process
import subprocess
import platform
import sys
import os
from typing import Any, TYPE_CHECKING

# Detect platform early (needed for overlay decision)
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows', 'android'

# Optional GUI overlay (tkinter). If unavailable, overlay auto-disables.
# On macOS, tkinter windows MUST be created on the main thread, so we disable
# the overlay by default on macOS to avoid NSInternalInconsistencyException crashes.
DISABLE_OVERLAY_ON_MACOS = PLATFORM == 'darwin'

try:
    import tkinter as tk
    overlay_import_error = None
    # If overlay would be disabled on macOS, set it to disabled now
    if DISABLE_OVERLAY_ON_MACOS:
        tk = None
        overlay_import_error = "Overlay disabled on macOS (tkinter threading issue)"
except Exception as exc:  # ModuleNotFoundError or Tcl/Tk missing
    tk = None
    overlay_import_error = exc

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

try:
    import mss
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("Warning: OCR dependencies (mss, pytesseract, Pillow) not available.")
    print("Text scanning features will be disabled.")
    print("Install with: pip install mss pytesseract pillow")


class RobustKeyboardListener(KeyboardListener):
    """Wrapper around pynput's KeyboardListener that handles Unicode decode errors.
    
    On macOS, certain keyboard events can trigger UnicodeDecodeError in pynput's
    internal event handler. This wrapper catches those errors gracefully.
    """
    
    def _handle_message(self, proxy: Any, event_type: Any, event: Any, refcon: Any, is_injected: Any) -> None:
        """Override pynput's message handler to catch Unicode decode errors.
        
        This is called from the C callback handler and processes keyboard events.
        On macOS, some special keys can cause UnicodeDecodeError in _event_to_key().
        """
        try:
            super()._handle_message(proxy, event_type, event, refcon, is_injected)
        except UnicodeDecodeError:
            # Silently ignore Unicode decode errors from special keys on macOS
            # These don't indicate a problem and shouldn't crash the listener
            pass
        except Exception as e:
            # Log but don't crash on other unexpected errors
            print(f"Keyboard listener error (suppressed): {type(e).__name__}: {e}")


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
arena_auto_max_commands = 576  # Number of commands before auto-termination
arena_auto_rate_limit = 150  # Maximum commands per second (0 = unlimited)
arena_size_step = 8  # Step size for arena size changes (must be even, default: 2)

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
overlay_thread: threading.Thread | None = None
overlay_stop_event = threading.Event()
overlay_visible = False
overlay_user_disabled = False
overlay_refresh_ms = 250
arena_current_type = 1

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
ctrl6_last_time = 0.0
ctrl6_armed = False
ctrl7_last_time = 0.0
ctrl7_armed = False

# new ctrl+1 multi-press globals
ctrl1_count = 0
ctrl1_first_time = 0.0

# NEW: bind art_working to Left Shift when enabled via Ctrl+C
art_shift_bind = False
mcrash_shift_bind = False

def generate_even(low: int = 2, high: int = 1024) -> int:
    return random.choice([i for i in range(low, high + 1) if i % 2 == 0])


# -------- Overlay helpers -------- #
def _overlay_lines() -> list[str]:
    """Build overlay text for long-running macros."""
    dir_text = 'cw' if circle_mouse_direction_value.value >= 0 else 'ccw'
    rate_text = '∞' if arena_auto_rate_limit == 0 else str(arena_auto_rate_limit)
    lines: list[str] = [
        "Arras macro HUD (Ctrl+0 to hide)",
        f"Arena: {'ON' if automation_event.is_set() else 'off'} type={arena_current_type} step={arena_size_step} rate={rate_text}/s",
        f"Engispam: {'ON' if engispam_event.is_set() else 'off'}",
        f"Art: {'ON' if art_event.is_set() else 'off'} (shift-bind={'ON' if art_shift_bind else 'off'})",
        f"Mcrash: {'ON' if (mcrash_event.is_set() or mcrash_working) else 'off'} (shift-bind={'ON' if mcrash_shift_bind else 'off'})",
        f"Brain damage: {'ON' if braindamage_event.is_set() else 'off'}",
        f"Circle mouse: {'ON' if circle_mouse_event.is_set() else 'off'} r={circle_mouse_radius_value.value} v={circle_mouse_speed_value.value:.3f} dir={dir_text}",
        f"Tail: {'ON' if (tail_process is not None and tail_process.is_alive()) else 'off'}",
        f"Softwall: {'ON' if (softwallstack_process is not None and softwallstack_process.is_alive()) else 'off'}",
        f"Armed: circle={'YES' if ctrl6_armed else 'no'} wall={'YES' if ctrl7_armed else 'no'}",
        f"Ctrl swap: {'Cmd' if ctrlswap and PLATFORM == 'darwin' else 'Ctrl'}",
    ]
    return lines


def _overlay_worker() -> None:
    """Background TK loop that draws the overlay."""
    global overlay_visible, overlay_user_disabled
    if tk is None:
        print(f"Overlay disabled (tk unavailable): {overlay_import_error}")
        overlay_visible = False
        overlay_user_disabled = True
        return
    
    # On macOS, we need to handle Tkinter carefully. Create a new root window in this thread.
    # This thread is separate from the main thread, so we create a new event loop here.
    root = None
    try:
        # On macOS with tkinter from Homebrew, we need to be in a separate thread from the keyboard listener
        root = tk.Tk()
        root.withdraw()
        root.title("Arras HUD")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-alpha", 0.85)
        except Exception:
            pass
        root.configure(bg="black")

        label = tk.Label(root, text="", fg="#8cff8c", bg="black", font=("Menlo", 12), justify="left")
        label.pack(anchor="w", padx=6, pady=6)
        root.geometry("360x220+20+20")
        root.deiconify()

        def refresh():
            if overlay_stop_event.is_set():
                try:
                    root.destroy()
                except Exception:
                    pass
                return
            try:
                label.configure(text="\n".join(_overlay_lines()))
            except Exception:
                pass
            try:
                root.after(overlay_refresh_ms, refresh)
            except Exception:
                pass

        refresh()
        overlay_visible = True
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Overlay mainloop error: {e}")
    except Exception as exc:
        print(f"Overlay disabled (tk init failed): {exc}")
        overlay_visible = False
        overlay_user_disabled = True
    finally:
        overlay_visible = False
        try:
            if root is not None:
                root.destroy()
        except Exception:
            pass


def start_overlay() -> None:
    """Show the overlay unless the user explicitly disabled it."""
    global overlay_thread, overlay_visible, overlay_user_disabled
    if overlay_user_disabled:
        return
    if tk is None:
        print(f"Overlay disabled (tk unavailable): {overlay_import_error}")
        overlay_user_disabled = True
        return
    if overlay_thread is not None and overlay_thread.is_alive():
        overlay_visible = True
        return
    overlay_stop_event.clear()
    overlay_thread = threading.Thread(target=_overlay_worker, daemon=True)
    overlay_thread.start()


def stop_overlay(user_request: bool = True) -> None:
    """Hide the overlay. If user-requested, prevent auto-respawn."""
    global overlay_thread, overlay_visible, overlay_user_disabled
    overlay_stop_event.set()
    if user_request:
        overlay_user_disabled = True
    if overlay_thread is not None:
        overlay_thread.join(timeout=1.5)
        overlay_thread = None
    overlay_visible = False


def ensure_overlay_running(reason: str = "") -> None:
    """Start overlay when a long-running macro kicks in (unless user hid it)."""
    if overlay_user_disabled:
        return
    if not overlay_visible:
        start_overlay()
        if reason:
            print(f"overlay on ({reason})")


def toggle_overlay() -> None:
    """User-facing toggle used by hotkeys."""
    global overlay_user_disabled
    if overlay_visible:
        stop_overlay(user_request=True)
        print("overlay off")
    else:
        if tk is None:
            print(f"overlay unavailable (tk not installed): {overlay_import_error}")
            overlay_user_disabled = True
            return
        overlay_user_disabled = False
        start_overlay()
        print("overlay on")

def type_unicode_blocks(hex_string: str | None = None, blocks: int = 3) -> None:
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

def arena_size_automation(atype: int = 1, run_event: MpEvent | None = None) -> None:
    """Spam $arena commands to resize the arena.
    
    Args:
        atype: Type of automation (1=random, 2=bouncing, 3=inverse bouncing)
        run_event: Multiprocessing event to control when to stop
    """
    global arena_auto_terminate, arena_auto_max_commands, arena_auto_rate_limit, arena_size_step
    
    # Ensure step is even
    step = arena_size_step if arena_size_step % 2 == 0 else 2
    if step != arena_size_step:
        print(f"Warning: arena_size_step must be even, using {step} instead of {arena_size_step}")
    
    # Calculate delay between commands based on rate limit
    cmd_delay = (1.0 / arena_auto_rate_limit) if arena_auto_rate_limit > 0 else 0
    
    print(f"Arena automation type {atype} (step={step})")
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
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
            x = generate_even(2, 1024)
            y = generate_even(2, 1024)
            controller.tap(Key.enter)
            controller.type(f"$arena size {x} {y}")
            controller.tap(Key.enter)
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
    elif atype == 2:
        # x and y go from 2 to 1024 in steps of arena_size_step
        x = 2
        y = 2
        direction_x = step
        direction_y = step
        while run_event.is_set():
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
            controller.tap(Key.enter)
            controller.type(f"$arena size {x} {y}")
            controller.tap(Key.enter)
            x += direction_x
            y += direction_y
            # Clamp and reverse direction if out of bounds
            if x > 1024:
                x = 1024
                direction_x = -step
            elif x < 2:
                x = 2
                direction_x = step
            if y > 1024:
                y = 1024
                direction_y = -step
            elif y < 2:
                y = 2
                direction_y = step
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
    elif atype == 3:
        # x goes from 2 to 1024, y goes from 1024 to 2
        x = 2
        y = 1024
        direction_x = step
        direction_y = -step
        while run_event.is_set():
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
            controller.tap(Key.enter)
            controller.type(f"$arena size {x} {y}")
            controller.tap(Key.enter)
            x += direction_x
            y += direction_y
            # Clamp and reverse direction if out of bounds
            if x > 1024:
                x = 1024
                direction_x = -step
            elif x < 2:
                x = 2
                direction_x = step
            if y > 1024:
                y = 1024
                direction_y = -step
            elif y < 2:
                y = 2
                direction_y = step
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
        
def click_positions(pos_list: list[tuple[float, float]], delay: float = 0.5) -> None:
    mouse = MouseController()
    for x, y in pos_list:
        mouse.position = (x, y)
        time.sleep(0.02)
        mouse.click(Button.left, 1)
        print(f"Clicked at {x}, {y}")
        time.sleep(delay)

def conq_quickstart() -> None:
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

def wallcrash() -> None:
    controller.press("`")
    controller.type("x"*1800)
    controller.release("`")

def nuke() -> None:
    controller.press("`")
    controller.type("wk"*100)
    controller.release("`")

def shape() -> None:
    controller.press("`")
    controller.type("f"*5000)
    controller.release("`")

def circlecrash() -> None:
    controller.press("`")
    for _ in range(180):
        for _ in range(180):
            controller.tap("c")
            controller.tap("h")
    controller.release("`")

def minicirclecrash() -> None:
    controller.press("`")
    for _ in range(50):
        for _ in range(100):
            controller.tap("c")
            controller.tap("h")
    controller.release("`")

def circles(amt: int = 210) -> None:
    controller.press("`")
    for _ in range(amt):
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def walls() -> None:
    controller.press("`")
    controller.type("x"*210)
    controller.release("`")

def art(run_event: MpEvent) -> None:
    controller.press("`")
    while run_event.is_set():
        controller.tap("c")
        controller.tap("h")
        time.sleep(0.02)
    controller.release("`")

def mcrash(run_event: MpEvent) -> None:
    controller.press("`")
    while run_event.is_set():
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def tail() -> None:
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

def brain_damage(run_event: MpEvent) -> None:
    mouse = MouseController()
    while run_event.is_set():
        mouse.position = (random.randint(0, 1710), random.randint(168, 1112))
        time.sleep(0.02)  # Add a small delay to prevent locking up your system

def circle_mouse(
    run_event: MpEvent,
    radius_value: Any,
    speed_value: Any,
    direction_value: Any,
) -> None:
    """Move mouse in circles around a center point. Press '\\' to reverse direction."""
    import math

    print("Click anywhere to set the center point for circular motion...")
    temp_points: list[tuple[int, int]] = []

    def temp_click_handler(x: int, y: int, button: Button, pressed: bool) -> None:
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

def score() -> None:
    controller.press("`")
    controller.type("n"*20000)
    controller.release("`")

def benchmark(amt: int = 5000) -> None:
    shift_pressed = threading.Event()

    def on_press(key: Key) -> None:
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

def score50m() -> None:
    controller.press("`")
    controller.type("f"*20)
    controller.release("`")

def engispam(run_event: MpEvent) -> None:
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

def circle() -> None:
    controller.press("`")
    controller.type("ch")
    controller.release("`")
        
def slowwall() -> None:
    controller.press("`")
    for _ in range(50):
        controller.tap("x")
        time.sleep(0.08)
    controller.release("`")

def softwallstack() -> None:
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


def simpletail(amt: int = 20) -> None:
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

def controllednuke() -> None:
    global step
    mouse = MouseController()
    print("Controlled Nuke: You have 10 seconds to select two points.")
    print(f"Click two points with the left mouse button. Step size: {step}")

    selected: list[tuple[int, int]] = []

    def click_handler(x: int, y: int, button: Button, pressed: bool) -> None:
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

def start_arena_automation(atype: int = 1) -> None:
    global automation_process, automation_working
    global arena_current_type
    arena_current_type = int(atype)
    automation_working = True
    automation_event.set()
    ensure_overlay_running("arena")
    if automation_process is None or not automation_process.is_alive():
        automation_process = multiprocessing.Process(
            target=arena_size_automation,
            args=(atype, automation_event),
        )
        automation_process.daemon = True
        automation_process.start()

def start_engispam() -> None:
    global engispam_process
    engispam_event.set()
    ensure_overlay_running("engispam")
    if engispam_process is None or not engispam_process.is_alive():
        engispam_process = multiprocessing.Process(target=engispam, args=(engispam_event,))
        engispam_process.daemon = True
        engispam_process.start()

def start_brain_damage() -> None:
    global braindamage_process
    braindamage_event.set()
    ensure_overlay_running("brain damage")
    if braindamage_process is None or not braindamage_process.is_alive():
        braindamage_process = multiprocessing.Process(target=brain_damage, args=(braindamage_event,))
        braindamage_process.daemon = True
        braindamage_process.start()

def start_tail() -> None:
    global tail_process
    if tail_process is None or not tail_process.is_alive():
        tail_process = multiprocessing.Process(target=tail)
        tail_process.daemon = True
        tail_process.start()
        ensure_overlay_running("tail")

def start_circle_mouse() -> None:
    global circle_mouse_process
    circle_mouse_event.set()
    circle_mouse_radius_value.value = circle_mouse_radius
    circle_mouse_speed_value.value = circle_mouse_speed
    circle_mouse_direction_value.value = circle_mouse_direction
    ensure_overlay_running("circle mouse")
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

def stop_circle_mouse() -> None:
    """Gracefully stop the circle mouse process."""
    global circle_mouse_process
    circle_mouse_event.clear()
    if circle_mouse_process is not None:
        circle_mouse_process.join(timeout=1)
        if circle_mouse_process.is_alive():
            circle_mouse_process.terminate()
        circle_mouse_process = None

def _monitor_circle_mouse(proc: Process) -> None:
    """Reset circle-mouse state when its process exits."""
    global circle_mouse_process, circle_mouse_active
    if proc is None:
        return
    proc.join()
    if circle_mouse_process is proc:
        circle_mouse_event.clear()
        circle_mouse_active = False
        circle_mouse_process = None

def start_art() -> None:
    global art_process
    art_event.set()
    ensure_overlay_running("art")
    if art_process is None or not art_process.is_alive():
        art_process = multiprocessing.Process(target=art, args=(art_event,))
        art_process.daemon = True
        art_process.start()

def start_softwallstack() -> None:
    global softwallstack_process
    if softwallstack_process is None or not softwallstack_process.is_alive():
        softwallstack_process = multiprocessing.Process(target=softwallstack)
        softwallstack_process.daemon = True
        softwallstack_process.start()
        ensure_overlay_running("softwall")

def start_controllednuke() -> None:
    proc = multiprocessing.Process(target=controllednuke)
    proc.daemon = True
    proc.start()

def start_mcrash() -> None:
    global mcrash_process, mcrash_working
    mcrash_event.set()
    mcrash_working = True
    ensure_overlay_running("mcrash")
    if mcrash_process is None or not mcrash_process.is_alive():
        mcrash_process = multiprocessing.Process(target=mcrash, args=(mcrash_event,))
        mcrash_process.daemon = True
        mcrash_process.start()

def _ctrl1_waiter() -> None:
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
def is_ctrl(k: Key) -> bool:
    """Check if key is Ctrl (or Cmd if ctrlswap=True on macOS)"""
    global ctrlswap
    if ctrlswap and PLATFORM == 'darwin':
        # Use Cmd key on macOS when ctrlswap is enabled
        return k in (Key.cmd, Key.cmd_l, Key.cmd_r)
    else:
        # Use Ctrl key normally
        return k in (Key.ctrl, Key.ctrl_l, Key.ctrl_r)

def is_alt(k: Key) -> bool:
    # On macOS, Option is alt; on other platforms, Alt is alt
    return k in (Key.alt, Key.alt_l, Key.alt_r)

def scan_screen_for_text(search_text: str, monitor_index: int = 1) -> tuple[bool, tuple[int, int] | None]:
    """Scan the screen for the given text using OCR.
    
    Args:
        search_text: The text to search for on screen (case-insensitive)
        monitor_index: Monitor index to capture (1 = primary, 2 = secondary, etc.)
    
    Returns:
        A tuple of (found: bool, center: tuple[int, int] | None)
        - found: True if text was found, False otherwise
        - center: (x, y) coordinates of the center of the text bounding box, or None if not found
    
    Example:
        found, center = scan_screen_for_text("Hello World")
        if found:
            print(f"Text found at center: {center}")
            # Can use mouse.position = center to move mouse to text
    """
    if not HAS_OCR:
        print("Error: OCR dependencies not installed. Cannot scan screen for text.")
        print("Install with: pip install mss pytesseract pillow")
        return (False, None)
    
    try:
        with mss.mss() as sct:
            # Get the monitor (1-indexed for user, 0-indexed for mss)
            if monitor_index < 1 or monitor_index > len(sct.monitors) - 1:
                print(f"Error: Monitor index {monitor_index} out of range (1 to {len(sct.monitors) - 1})")
                return (False, None)
            
            monitor = sct.monitors[monitor_index]
            
            # Capture the screen
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            
            # Perform OCR to get bounding boxes and text
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            # Search for the text (case-insensitive)
            search_lower = search_text.lower().strip()
            
            # Try to find the text in the OCR results
            for i, text in enumerate(ocr_data['text']):
                if text.lower().strip() == search_lower:
                    # Found exact match
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    # Calculate center point
                    # Add monitor offset to get absolute screen coordinates
                    center_x = monitor['left'] + x + w // 2
                    center_y = monitor['top'] + y + h // 2
                    
                    return (True, (center_x, center_y))
            
            # Also try partial matching (in case search_text is part of a larger word)
            for i, text in enumerate(ocr_data['text']):
                if search_lower in text.lower():
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    center_x = monitor['left'] + x + w // 2
                    center_y = monitor['top'] + y + h // 2
                    
                    return (True, (center_x, center_y))
            
            # Text not found
            return (False, None)
            
    except Exception as e:
        print(f"Error scanning screen for text: {e}")
        return (False, None)

def stopallthreads() -> None:
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
    
    # Terminate all processes and clean up resources
    for proc in [automation_process, engispam_process, art_process, braindamage_process,
                 tail_process, softwallstack_process, circlecrash_process, mcrash_process]:
        if proc is not None:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=1)
                if proc.is_alive():
                    proc.kill()
                    proc.join(timeout=0.5)
            # Close the process to release resources (semaphores, etc.)
            try:
                proc.close()
            except Exception:
                pass

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
    
    def is_modifier_for_arrow_nudge(k: Key) -> bool:
        """
        Platform-specific:
        - macOS: Option (alt)
        - Windows/Linux: Alt
        - Android: Alt (if supported)
        """
        return is_alt(k)

def on_press(key: Key | None) -> None:
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
        elif hasattr(key, 'char') and key.char and key.char=='v':
            if 'ctrl' in pressed_keys:
                mcrash_shift_bind = True
                mcrash_working = False
                mcrash_event.clear()
                print("toggle mcrash")
        elif hasattr(key, 'char') and key.char and key.char=='2':
            if 'ctrl' in pressed_keys:
                braindamage_working = True
                print("bdmg")
                start_brain_damage()
        elif hasattr(key, 'char') and key.char and key.char=='3':
            if 'ctrl' in pressed_keys:
                circle()
        elif hasattr(key, 'char') and key.char and key.char=='4':
            if 'ctrl' in pressed_keys:
                print("circle square")
                start_tail()
        elif hasattr(key, 'char') and key.char and key.char=='5':
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
        elif hasattr(key, 'char') and key.char and key.char=='x':
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
        elif hasattr(key, 'char') and key.char and key.char=='6':
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
        elif hasattr(key, 'char') and key.char and key.char=='j':
            if 'ctrl' in pressed_keys:
                start = mouse.position
                controller.press("`")
                for _ in range(400):
                    mouse.position = (start[0] + random.randint(-25, 25), start[1] + random.randint(-25, 25))
                    time.sleep(0.01)
                    controller.press("j")
                    mouse.position = (start[0] + random.randint(-25, 25), start[1] + random.randint(-25, 25))
                    time.sleep(0.01)
                    controller.release("j")
                controller.release("`")
                mouse.position = start
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
        elif hasattr(key, 'char') and key.char and key.char=='q':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                controller.tap("d")
                controller.type("fy"*10)
                controller.type(("f"*50+"h")*2)
                controller.release("`")
                controller.press("`")
                controller.tap("d")
                controller.press("d")
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='a':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                controller.tap("d")
                controller.type("fy"*10)
                controller.type(("f"*50+"h")*6)
                controller.release("`")
                controller.press("`")
                controller.tap("d")
                controller.press("d")
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='z':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                controller.tap("d")
                controller.type("fy"*10)
                controller.type(("f"*50+"h")*10)
                controller.release("`")
                controller.press("`")
                controller.tap("d")
                controller.press("d")
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='y':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                controller.tap("d")
                controller.type("fy"*10)
                controller.type(("f"*50+"h")*2)
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='u':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                controller.tap("d")
                controller.type("fy"*10)
                controller.type(("f"*50+"h")*6)
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='i':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                controller.tap("d")
                controller.type("fy"*10)
                controller.type(("f"*50+"h")*10)
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='[':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                for _ in range(100):
                    controller.tap("f")
                controller.release("`")
            else:
                circle_mouse_radius = max(circle_mouse_radius - 5, 5)
                circle_mouse_radius_value.value = circle_mouse_radius
                print(f"circle radius: {circle_mouse_radius}")
        elif hasattr(key, 'char') and key.char and key.char==']':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                for _ in range(500):
                    controller.tap("f")
                controller.release("`")
            else:
                circle_mouse_radius = min(circle_mouse_radius + 5, 1000)
                circle_mouse_radius_value.value = circle_mouse_radius
                print(f"circle radius: {circle_mouse_radius}")
        elif hasattr(key, 'char') and key.char and key.char=='o':
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
        elif hasattr(key, 'char') and key.char and key.char=='0':
            if 'ctrl' in pressed_keys:
                toggle_overlay()
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
    
def on_release(key: Key | None) -> None:
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
    def safe_on_press(key: Key | None) -> None:
        try:
            on_press(key)
        except UnicodeDecodeError:
            pass  # Ignore Unicode decode errors from special keys
    
    def safe_on_release(key: Key | None) -> None:
        try:
            on_release(key)
        except UnicodeDecodeError:
            pass  # Ignore Unicode decode errors from special keys
    
    listener = RobustKeyboardListener(on_press=safe_on_press, on_release=safe_on_release)
    listener.start()
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        listener.stop()
        stopallthreads()
        
        # Clean up overlay thread if running
        if overlay_thread is not None and overlay_thread.is_alive():
            overlay_stop_event.set()
            overlay_thread.join(timeout=1.0)

