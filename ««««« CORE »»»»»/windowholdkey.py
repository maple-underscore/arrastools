#!/usr/bin/env python3
"""
Window-Specific Key Holder
Holds keys for a specific window even when it's out of focus.

Usage:
1. Run the script
2. Switch to the target window
3. Press a key - it will be held for that window only
4. Press Esc to stop holding all keys
5. Press Ctrl+C to exit

Platform Support:
- macOS: Uses AppleScript and Quartz events
- Linux: Uses xdotool (requires installation)
- Windows: Uses pywin32 (requires installation)
"""

import platform
import subprocess
import time
import threading
from pynput import keyboard
from pynput.keyboard import Key, Controller

# Platform detection
PLATFORM = platform.system().lower()

# Global state
controller = Controller()
active_window = None
held_keys = {}  # {key: thread}
running = True
holding_enabled = False


def get_active_window_macos():
    """Get the active window info on macOS."""
    try:
        # Get frontmost application
        script = '''
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set appName to name of frontApp
            set windowTitle to ""
            try
                set windowTitle to name of front window of frontApp
            end try
            return appName & "|" & windowTitle
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split('|')
            return {
                'app': parts[0] if len(parts) > 0 else '',
                'title': parts[1] if len(parts) > 1 else ''
            }
    except Exception as e:
        print(f"Error getting window: {e}")
    return None


def get_active_window_linux():
    """Get the active window info on Linux (requires xdotool)."""
    try:
        # Get window ID
        result = subprocess.run(
            ['xdotool', 'getactivewindow'],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            window_id = result.stdout.strip()
            
            # Get window name
            result2 = subprocess.run(
                ['xdotool', 'getwindowname', window_id],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result2.returncode == 0:
                return {
                    'id': window_id,
                    'title': result2.stdout.strip()
                }
    except FileNotFoundError:
        print("xdotool not found. Install with: sudo apt install xdotool")
    except Exception as e:
        print(f"Error getting window: {e}")
    return None


def get_active_window_windows():
    """Get the active window info on Windows (requires pywin32)."""
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return {
            'hwnd': hwnd,
            'title': title
        }
    except ImportError:
        print("pywin32 not found. Install with: pip install pywin32")
    except Exception as e:
        print(f"Error getting window: {e}")
    return None


def get_active_window():
    """Get the active window info (platform-specific)."""
    if PLATFORM == 'darwin':
        return get_active_window_macos()
    elif PLATFORM == 'linux':
        return get_active_window_linux()
    elif PLATFORM == 'windows':
        return get_active_window_windows()
    return None


def send_key_to_window_macos(app_name, key_char):
    """Send a key press to a specific app on macOS."""
    try:
        # Map special keys
        key_code_map = {
            'up': '126',
            'down': '125',
            'left': '123',
            'right': '124',
            'space': '49',
        }
        
        if key_char.lower() in key_code_map:
            # Use key code for special keys
            key_code = key_code_map[key_char.lower()]
            script = f'''
            tell application "{app_name}"
                activate
            end tell
            tell application "System Events"
                key code {key_code}
            end tell
            '''
        else:
            # Use keystroke for regular characters
            script = f'''
            tell application "{app_name}"
                activate
            end tell
            tell application "System Events"
                keystroke "{key_char}"
            end tell
            '''
        
        subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            timeout=0.5
        )
    except Exception as e:
        print(f"Error sending key: {e}")


def send_key_to_window_linux(window_id, key_char):
    """Send a key press to a specific window on Linux."""
    try:
        subprocess.run(
            ['xdotool', 'key', '--window', window_id, key_char],
            capture_output=True,
            timeout=0.5
        )
    except Exception as e:
        print(f"Error sending key: {e}")


def send_key_to_window_windows(hwnd, key_char):
    """Send a key press to a specific window on Windows."""
    try:
        import win32api
        import win32con
        # This is a simplified version - full implementation would need VK codes
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, ord(key_char.upper()), 0)
        time.sleep(0.05)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, ord(key_char.upper()), 0)
    except Exception as e:
        print(f"Error sending key: {e}")


def hold_key_for_window(window_info, key_str):
    """Continuously send key presses to maintain 'held' state for specific window."""
    global running
    
    print(f"Holding '{key_str}' for window: {window_info}")
    
    while running and key_str in held_keys:
        try:
            if PLATFORM == 'darwin' and 'app' in window_info:
                send_key_to_window_macos(window_info['app'], key_str)
            elif PLATFORM == 'linux' and 'id' in window_info:
                send_key_to_window_linux(window_info['id'], key_str)
            elif PLATFORM == 'windows' and 'hwnd' in window_info:
                send_key_to_window_windows(window_info['hwnd'], key_str)
            
            # Send key repeatedly to simulate holding
            time.sleep(0.05)  # 50ms interval for smooth holding
        except Exception as e:
            print(f"Error in hold loop: {e}")
            break
    
    print(f"Stopped holding '{key_str}'")


def get_key_string(key):
    """Convert pynput key to string."""
    if hasattr(key, 'char') and key.char:
        return key.char
    elif key == Key.up:
        return 'up'
    elif key == Key.down:
        return 'down'
    elif key == Key.left:
        return 'left'
    elif key == Key.right:
        return 'right'
    elif key == Key.space:
        return 'space'
    else:
        return str(key).replace('Key.', '')


def on_press(key):
    """Handle key press events."""
    global active_window, held_keys, holding_enabled
    
    # Toggle holding mode with Ctrl+H
    if key == Key.f1:
        holding_enabled = not holding_enabled
        if holding_enabled:
            active_window = get_active_window()
            print(f"\n{'='*60}")
            print(f"HOLDING ENABLED for window: {active_window}")
            print(f"{'='*60}")
            print("Press any key to toggle holding it for this window")
            print("Press Esc to stop holding all keys")
            print("Press F1 again to disable holding mode")
        else:
            print("\nHOLDING DISABLED")
            # Stop all held keys
            for key_str in list(held_keys.keys()):
                del held_keys[key_str]
            active_window = None
        return
    
    if not holding_enabled:
        return
    
    # Stop all held keys with Esc
    if key == Key.esc:
        print("\nStopping all held keys...")
        for key_str in list(held_keys.keys()):
            del held_keys[key_str]
        held_keys.clear()
        return
    
    # Toggle holding the pressed key
    if active_window:
        key_str = get_key_string(key)
        
        if key_str:
            if key_str in held_keys:
                # Stop holding this key
                print(f"Releasing: {key_str}")
                del held_keys[key_str]
            else:
                # Start holding this key
                print(f"Starting to hold: {key_str} (press again to release)")
                thread = threading.Thread(
                    target=hold_key_for_window,
                    args=(active_window, key_str),
                    daemon=True
                )
                held_keys[key_str] = thread
                thread.start()


def on_release(key):
    """Handle key release events (not used in toggle mode)."""
    pass


def print_instructions():
    """Print usage instructions."""
    print("\n" + "="*60)
    print("WINDOW-SPECIFIC KEY HOLDER")
    print("="*60)
    print(f"Platform: {PLATFORM}")
    print("\nInstructions:")
    print("1. Switch to your target window")
    print("2. Press F1 to enable holding mode")
    print("3. Press any key ONCE - it will be held indefinitely for that window")
    print("4. The key will continue being sent even if you switch windows")
    print("5. Press the same key again to stop holding it (toggle)")
    print("6. Press Esc to stop holding all keys at once")
    print("7. Press F1 again to disable holding mode")
    print("8. Press Ctrl+C to exit the script")
    print("="*60)
    
    if PLATFORM == 'linux':
        print("\nNote: Requires xdotool (install: sudo apt install xdotool)")
    elif PLATFORM == 'windows':
        print("\nNote: Requires pywin32 (install: pip install pywin32)")
    
    print("\nWaiting for F1 to enable holding mode...")


def main():
    """Main function."""
    global running
    
    print_instructions()
    
    # Start keyboard listener
    with keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    ) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            print("\n\nExiting...")
            running = False
            
            # Wait for threads to finish
            time.sleep(0.5)


if __name__ == '__main__':
    main()
