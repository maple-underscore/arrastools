#!/usr/bin/env python3
"""
Keylogger for monitoring script keytaps.
Logs all keypresses to a timestamped text file in logsk/ directory.
Press Esc to stop logging and exit.
"""

import platform
from pathlib import Path
from datetime import datetime
import sys

try:
    from pynput import keyboard
except ImportError:
    print("Missing dependency: pynput is required to run the keylogger.")
    print("Install with: python3 -m pip install pynput")
    sys.exit(1)

# Platform detection
PLATFORM = platform.system().lower()
print(f"Running on platform: {PLATFORM}")

# Resolve workspace paths relative to this script to avoid CWD surprises
CORE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CORE_DIR.parent
LOGS_DIR = REPO_ROOT / "logsk"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Create timestamped log file
def timestamp():
    """Generate timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

LOG_FILE = LOGS_DIR / f"keylog_{timestamp()}.txt"
print(f"Logging keypresses to: {LOG_FILE}")

# Global flag for stopping
running = True

def format_key(key):
    """Format key for logging with pynput code representation."""
    try:
        # Regular character keys
        char = key.char
        # Generate pynput code for character keys
        if char:
            pynput_code = f"'{char}'"
        else:
            pynput_code = "None"
        return f"{char} (pynput: {pynput_code})"
    except AttributeError:
        # Special keys - these are Key enum values
        key_str = str(key).replace("Key.", "")
        # Generate pynput code for special keys
        pynput_code = f"Key.{key_str.lower()}"
        return f"[{key_str}] (pynput: {pynput_code})"

def on_press(key):
    """Handle key press events."""
    global running
    
    # Stop on Esc
    if key == keyboard.Key.esc:
        print("\nEsc pressed - stopping keylogger...")
        running = False
        return False
    
    # Format and log the key
    key_formatted = format_key(key)
    
    # Write to file
    with open(LOG_FILE, "a") as f:
        f.write(key_formatted)
    
    # Also print to console for real-time monitoring
    print(key_formatted, end="", flush=True)

def main():
    """Main keylogger loop."""
    print("Keylogger started. Press Esc to stop.")
    print("-" * 50)
    
    # Write header to log file
    with open(LOG_FILE, "w") as f:
        f.write(f"Keylogger started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n")
    
    # Start keyboard listener
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
    
    # Write footer
    with open(LOG_FILE, "a") as f:
        f.write(f"\n{'-' * 50}\n")
        f.write(f"Keylogger stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"\n{'-' * 50}")
    print(f"Log saved to: {LOG_FILE}")
    print("Keylogger stopped.")

if __name__ == "__main__":
    main()
