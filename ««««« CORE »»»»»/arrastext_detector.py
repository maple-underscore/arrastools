"""Text detector script that monitors for '!start' and types 'detected'.

This script continuously scans the screen for the text '!start' using OCR.
When detected, it automatically types 'detected' in the active window.
Press Esc to stop the script.
"""

import time
import sys
import platform

# Platform detection
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows'
print(f"Running on platform: {PLATFORM}")

try:
    from pynput.keyboard import Controller as KeyboardController, Key, Listener as KeyboardListener
except ImportError:
    print("Missing dependency: pynput is required to run this script.")
    print("Install with: python3 -m pip install pynput")
    sys.exit(1)

try:
    import mss
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("Error: OCR dependencies (mss, pytesseract, Pillow) not available.")
    print("Text scanning features will not work.")
    print("Install with: pip install mss pytesseract pillow")
    sys.exit(1)

# Initialize controllers
controller = KeyboardController()

# Global flag for clean exit
running = True


def scan_screen_for_text(search_text: str, monitor_index: int = 1) -> tuple[bool, tuple[int, int] | None]:
    """Scan the screen for the given text using OCR.
    
    Args:
        search_text: The text to search for on screen (case-insensitive)
        monitor_index: Monitor index to capture (1 = primary, 2 = secondary, etc.)
    
    Returns:
        A tuple of (found: bool, center: tuple[int, int] | None)
        - found: True if text was found, False otherwise
        - center: (x, y) coordinates of the center of the text bounding box, or None if not found
    """
    if not HAS_OCR:
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
        print(f"Error during screen scan: {type(e).__name__}: {e}")
        return (False, None)
    

def on_press(key):
    """Handle key press events."""
    global running
    
    # Press Esc to stop the script
    if key == Key.esc:
        print("\nEsc pressed. Stopping text detector...")
        running = False
        return False  # Stop listener


def main():
    """Main loop that monitors for '!start' text."""
    global running
    
    print("Text Detector Started")
    print("=" * 50)
    print("Monitoring for: '!start'")
    print("Action: Type 'detected' when found")
    print("Press Esc to stop")
    print("=" * 50)
    
    # Start keyboard listener for exit control
    listener = KeyboardListener(on_press=on_press)
    listener.start()
    
    # Configuration
    search_text = "!start"
    monitor_index = 1  # Primary monitor
    scan_interval = 0.1  # Scan every 0.1 second
    
    last_detected_time = 0
    cooldown_period = 5.0  # Avoid spamming "detected" - wait 5 seconds between detections
    
    try:
        while running:
            # Scan screen for the text
            found, position = scan_screen_for_text(search_text, monitor_index)
            
            if found:
                current_time = time.time()
                
                # Check if enough time has passed since last detection (cooldown)
                if current_time - last_detected_time >= cooldown_period:
                    print(f"\n✓ Detected '{search_text}' at position {position}")
                    print("  Typing: detected")
                    
                    # Type the response
                    controller.tap(Key.enter)
                    controller.type("detected")
                    controller.tap(Key.enter)
                    
                    # Update last detected time
                    last_detected_time = current_time
                else:
                    # Found but still in cooldown
                    remaining = cooldown_period - (current_time - last_detected_time)
                    print(f"  Found '{search_text}' but in cooldown ({remaining:.1f}s remaining)")
            else:
                # Not found - print status
                print(".", end="", flush=True)
            
            # Wait before next scan
            time.sleep(scan_interval)
            
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Stopping...")
    except Exception as e:
        print(f"\nUnexpected error: {type(e).__name__}: {e}")
    finally:
        running = False
        listener.stop()
        print("\nText detector stopped.")


if __name__ == "__main__":
    if not HAS_OCR:
        print("Cannot start: OCR dependencies missing")
        sys.exit(1)
    
    main()
