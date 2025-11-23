#!/usr/bin/env python3
"""
Keylogger for monitoring script keytaps.
Logs all keypresses to a timestamped text file in logsk/ directory.
Press Esc to stop logging and exit.
"""

import platform
from pynput import keyboard
from pathlib import Path
from datetime import datetime

# Platform detection
PLATFORM = platform.system().lower()
print(f"Running on platform: {PLATFORM}")

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logsk")
LOGS_DIR.mkdir(exist_ok=True)

# Create timestamped log file
def timestamp():
    """Generate timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

LOG_FILE = LOGS_DIR / f"keylog_{timestamp()}.txt"
print(f"Logging keypresses to: {LOG_FILE}")

# Global flag for stopping
running = True

def format_key(key):
    """Format key for logging."""
    try:
        # Regular character keys
        return key.char
    except AttributeError:
        # Special keys
        key_str = str(key).replace("Key.", "")
        return f"[{key_str}]"

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
