#!/usr/bin/env python3
"""Window focus and fullscreen detector.

Detects when a specific window is focused and in fullscreen mode,
then runs a loop while those conditions remain true.
"""

import time
import platform
import sys

PLATFORM = platform.system().lower()

# Target window name (partial match)
TARGET_WINDOW_NAME = "arras"  # Change this to match your target window

def get_active_window_info():
    """Get information about the currently active window.
    
    Returns:
        tuple: (window_name, is_fullscreen) or (None, False) if detection fails
    """
    if PLATFORM == 'darwin':
        # macOS implementation using AppKit
        try:
            from AppKit import NSWorkspace, NSApplicationActivationPolicyRegular
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                kCGWindowLayer,
                kCGWindowOwnerName,
                kCGWindowName,
                kCGWindowBounds,
            )
            
            # Get active application
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            app_name = active_app.get('NSApplicationName', '')
            
            # Get window list to check for fullscreen
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )
            
            # Find the frontmost window
            is_fullscreen = False
            window_name = app_name
            
            for window in window_list:
                if window.get(kCGWindowOwnerName) == app_name:
                    # Check if window layer is 0 (normal windows)
                    layer = window.get(kCGWindowLayer, 0)
                    
                    # Get window bounds
                    bounds = window.get(kCGWindowBounds, {})
                    width = bounds.get('Width', 0)
                    height = bounds.get('Height', 0)
                    
                    # Get window name if available
                    win_name = window.get(kCGWindowName, '')
                    if win_name:
                        window_name = f"{app_name} - {win_name}"
                    
                    # Simple fullscreen detection: check if window size matches screen size
                    # Note: This is approximate. True fullscreen detection is more complex.
                    from AppKit import NSScreen
                    screen = NSScreen.mainScreen()
                    screen_frame = screen.frame()
                    screen_width = screen_frame.size.width
                    screen_height = screen_frame.size.height
                    
                    # Consider fullscreen if window is within 50px of screen dimensions
                    if abs(width - screen_width) < 50 and abs(height - screen_height) < 50:
                        is_fullscreen = True
                    
                    break
            
            return (window_name, is_fullscreen)
            
        except ImportError:
            print("Error: macOS window detection requires PyObjC")
            print("Install with: pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa")
            return (None, False)
        except Exception as e:
            print(f"Error detecting window: {e}")
            return (None, False)
    
    elif PLATFORM == 'linux':
        # Linux implementation using xdotool or wmctrl
        try:
            import subprocess
            
            # Try to get active window using xdotool
            try:
                window_id = subprocess.check_output(['xdotool', 'getactivewindow']).decode().strip()
                window_name = subprocess.check_output(['xdotool', 'getwindowname', window_id]).decode().strip()
                
                # Check fullscreen state
                window_state = subprocess.check_output(['xprop', '-id', window_id, '_NET_WM_STATE']).decode()
                is_fullscreen = '_NET_WM_STATE_FULLSCREEN' in window_state
                
                return (window_name, is_fullscreen)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # xdotool not available, try wmctrl
                try:
                    output = subprocess.check_output(['wmctrl', '-lx']).decode()
                    # This is a simplified implementation
                    # You'd need to parse the output to find the active window
                    return (None, False)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("Error: Linux window detection requires xdotool or wmctrl")
                    print("Install with: sudo apt install xdotool (or) sudo apt install wmctrl")
                    return (None, False)
        except Exception as e:
            print(f"Error detecting window: {e}")
            return (None, False)
    
    elif PLATFORM == 'windows':
        # Windows implementation using win32gui
        try:
            import win32gui
            import win32process
            
            # Get foreground window
            hwnd = win32gui.GetForegroundWindow()
            window_name = win32gui.GetWindowText(hwnd)
            
            # Check if fullscreen (simplified check)
            placement = win32gui.GetWindowPlacement(hwnd)
            is_fullscreen = placement[1] == 3  # SW_MAXIMIZE
            
            return (window_name, is_fullscreen)
            
        except ImportError:
            print("Error: Windows window detection requires pywin32")
            print("Install with: pip install pywin32")
            return (None, False)
        except Exception as e:
            print(f"Error detecting window: {e}")
            return (None, False)
    
    else:
        print(f"Unsupported platform: {PLATFORM}")
        return (None, False)


def matches_target_window(window_name):
    """Check if window name matches the target.
    
    Args:
        window_name: The name of the window to check
        
    Returns:
        bool: True if window name contains target string (case-insensitive)
    """
    if not window_name:
        return False
    return TARGET_WINDOW_NAME.lower() in window_name.lower()


def main():
    """Main loop that detects window focus and fullscreen state."""
    print(f"Window detector running on {PLATFORM}")
    print(f"Target window: '{TARGET_WINDOW_NAME}'")
    print("Press Ctrl+C to exit")
    print()
    
    was_active = False
    loop_running = False
    
    try:
        while True:
            # Get current window info
            window_name, is_fullscreen = get_active_window_info()
            
            # Check if conditions are met
            is_target = matches_target_window(window_name)
            conditions_met = is_target and is_fullscreen
            
            # Debug output
            if window_name and is_target:
                status = "FULLSCREEN" if is_fullscreen else "not fullscreen"
                print(f"Target window active: {window_name} ({status})")
            
            # Handle state transitions
            if conditions_met:
                if not was_active:
                    # Just became active - wait 1 second before starting loop
                    print("Conditions met! Waiting 1 second before starting loop...")
                    time.sleep(1.0)
                    loop_running = True
                    was_active = True
                
                if loop_running:
                    # Main loop body - put your code here
                    pass
                    
                    # Small delay to prevent CPU spinning
                    time.sleep(0.1)
            else:
                if was_active:
                    # Just lost the conditions
                    print("Conditions no longer met. Stopping loop.")
                    loop_running = False
                    was_active = False
                
                # Check less frequently when not active
                time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
