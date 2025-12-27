import time
import platform
from datetime import datetime
from pathlib import Path
import threading
import pychrome
import subprocess
import os

# Resolve project paths
CORE_DIR = Path(__file__).resolve().parent
REPO_ROOT = CORE_DIR.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DESKTOP_ROOT = Path.home() / "Desktop" / "abss"
DESKTOP_ROOT.mkdir(parents=True, exist_ok=True)

# Chrome debugging data directory
CHROME_DEBUG_DIR = REPO_ROOT / ".chrome_debug_profile"
CHROME_DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# Detect platform
PLATFORM = platform.system().lower()
print(f"Arrasbot2 (CDP) running on: {PLATFORM}")

if PLATFORM not in ('darwin', 'linux', 'windows'):
    print(f"Warning: Platform '{PLATFORM}' may have limited support.")

time.sleep(1)

# Global state
working = True
disconnected = True
died = False
banned = False

# Chrome DevTools Protocol connection
browser = None
tab = None

def timestamp():
    """Generate timestamp string"""
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def color_close(c1, c2, tol=6):
    """Tolerant RGB comparison"""
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))

def get_pixel_rgb_cdp(x, y):
    """Get pixel RGB value at coordinates using CDP screenshot"""
    try:
        # Capture screenshot via CDP
        result = tab.Page.captureScreenshot(format="png", fromSurface=True)
        screenshot_data = result['data']
        
        # Decode and get pixel
        import base64
        from PIL import Image
        import io
        
        img_data = base64.b64decode(screenshot_data)
        img = Image.open(io.BytesIO(img_data))
        
        # Get pixel RGB
        if 0 <= x < img.width and 0 <= y < img.height:
            pixel = img.getpixel((x, y))
            return pixel[:3] if len(pixel) >= 3 else pixel
        return (0, 0, 0)
    except Exception as e:
        print(f"Error getting pixel: {e}")
        return (0, 0, 0)

def take_screenshot_cdp(reason="periodic"):
    """Take screenshot using CDP"""
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        current_time = timestamp()
        filename = SCREENSHOT_DIR / f"{current_time}_{reason}.png"
        
        result = tab.Page.captureScreenshot(format="png", fromSurface=True)
        screenshot_data = result['data']
        
        import base64
        with open(filename, 'wb') as f:
            f.write(base64.b64decode(screenshot_data))
        
        print(f"Screenshot saved: {filename} at {timestamp()}")
        with ARRASBOT_LOG.open("a", encoding="utf-8") as log_file:
            log_file.write(f"Screenshot saved: {filename} at {timestamp()}\n")
    except Exception as e:
        print(f"Error taking screenshot: {e}")

def roll():
    """Placeholder function for roll action"""
    pass

def inputlistener():
    """CLI command listener"""
    global working, disconnected, died, banned
    while working:
        try:
            inp = input("cmd > ")
            if inp.lower() == "stop":
                working = False
                print("Stopping bot...")
            elif inp.lower() == "screenshot":
                take_screenshot_cdp("manual")
            elif inp.lower() == "status":
                print(f"Working: {working}, Disconnected: {disconnected}, Died: {died}, Banned: {banned}")
            elif inp.lower() == "forcedisconnect":
                disconnected = True
                print("Forcing disconnect state...")
            elif inp.lower() == "forcedeath":
                died = True
                print("Forcing death state...")
            elif inp.lower() == "forcereconnect":
                disconnected = False
                died = False
                print("Forcing reconnect state...")
            elif inp.lower().startswith("probe"):
                # probe x y - check pixel at coordinates
                parts = inp.split()
                if len(parts) == 3:
                    try:
                        x, y = int(parts[1]), int(parts[2])
                        rgb = get_pixel_rgb_cdp(x, y)
                        print(f"Pixel at ({x}, {y}): {rgb}")
                    except ValueError:
                        print("Usage: probe <x> <y>")
                else:
                    print("Usage: probe <x> <y>")
            elif inp.lower() == "check":
                # Force a pixel check right now
                print("Running pixel check...")
                check_pixels()
        except EOFError:
            break
        except Exception as e:
            print(f"Input error: {e}")

def start_input_listener():
    """Start input listener thread"""
    threading.Thread(target=inputlistener, daemon=True).start()

def launch_chrome_debug():
    """Launch Chrome with remote debugging enabled"""
    chrome_paths = {
        'darwin': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        'linux': 'google-chrome',
        'windows': r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    }
    
    chrome_cmd = chrome_paths.get(PLATFORM)
    if not chrome_cmd:
        print(f"Chrome path not configured for platform: {PLATFORM}")
        return None
    
    # Check if Chrome is already running with debug port
    try:
        browser_test = pychrome.Browser(url="http://127.0.0.1:9222")
        browser_test.list_tab()
        print("Chrome is already running with remote debugging enabled.")
        return None
    except:
        pass
    
    # Launch Chrome with debugging enabled
    cmd = [
        chrome_cmd,
        f"--remote-debugging-port=9222",
        f"--user-data-dir={CHROME_DEBUG_DIR}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    print(f"Launching Chrome with remote debugging...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        if PLATFORM == 'darwin':
            # On macOS, use subprocess.Popen to detach from terminal
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give Chrome time to start
        time.sleep(3)
        return process
    except Exception as e:
        print(f"Failed to launch Chrome: {e}")
        return None

def print_chrome_instructions():
    """Print instructions for manually launching Chrome"""
    print("\n" + "="*60)
    print("CHROME REMOTE DEBUGGING SETUP")
    print("="*60)
    
    if PLATFORM == 'darwin':
        print("\nRun this command in a separate terminal:")
        print(f'/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\')
        print(f'  --remote-debugging-port=9222 \\')
        print(f'  --user-data-dir="{CHROME_DEBUG_DIR}"')
    elif PLATFORM == 'linux':
        print("\nRun this command in a separate terminal:")
        print(f'google-chrome \\')
        print(f'  --remote-debugging-port=9222 \\')
        print(f'  --user-data-dir="{CHROME_DEBUG_DIR}"')
    elif PLATFORM == 'windows':
        print("\nRun this command in a separate terminal:")
        print(f'"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^')
        print(f'  --remote-debugging-port=9222 ^')
        print(f'  --user-data-dir="{CHROME_DEBUG_DIR}"')
    
    print("\nThen navigate to arras.io in that Chrome window.")
    print("="*60 + "\n")

def monitor_loop():
    """Main monitoring loop - checks pixels every 3 seconds"""
    global working, disconnected, died, banned
    
    print("Starting monitor loop...")
    
    while working:
        try:
            # Run pixel checks
            check_pixels()
            
            # Call roll function
            roll()
            
            # Wait 3 seconds before next check
            time.sleep(3)
            
        except KeyboardInterrupt:
            print("\nBot interrupted by user")
            working = False
            break
        except Exception as e:
            print(f"Error in monitor loop: {e}")
            with ARRASBOT_LOG.open("a", encoding="utf-8") as log_file:
                log_file.write(f"Error in monitor loop at {timestamp()}: {e}\n")
            time.sleep(3)  # Continue after error

def check_pixels():
    """Perform pixel checks similar to original arrasbot"""
    global disconnected, died, banned
    
    # Check disconnect (red pixel at bottom)
    targetcolor = get_pixel_rgb_cdp(28, 925)
    
    # Debug output every check
    print(f"[DEBUG] Pixel at (28, 925): {targetcolor} | Disconnected: {disconnected} | Died: {died}")
    
    # Check for disconnect/death/reconnect states
    if color_close(targetcolor, (167, 81, 68)) or color_close(targetcolor, (138, 27, 34)) or \
       color_close(targetcolor, (201, 92, 75)) or color_close(targetcolor, (199, 118, 98)) or \
       color_close(targetcolor, (213, 114, 93)):
        if not disconnected:
            print(f"Disconnected at {timestamp()} - color: {targetcolor}")
            with ARRASBOT_LOG.open("a", encoding="utf-8") as log_file:
                log_file.write(f"Disconnected at {timestamp()}\n")
            take_screenshot_cdp("disconnected")
            disconnected = True
    
    # Check for death (brown pixel)
    if color_close(targetcolor, (176, 100, 81)) and not died:
        print(f"Checking death at {timestamp()} - color: {targetcolor}")
        time.sleep(3)
        targetcolor_after = get_pixel_rgb_cdp(28, 925)
        if color_close(targetcolor_after, (176, 100, 81)):
            print(f"Died at {timestamp()}")
            with ARRASBOT_LOG.open("a", encoding="utf-8") as log_file:
                log_file.write(f"Died at {timestamp()}\n")
            take_screenshot_cdp("died")
            died = True
    
    # Check for reconnect (orange pixel)
    if color_close(targetcolor, (223, 116, 90)) and (disconnected or died):
        print(f"Successfully reconnected at {timestamp()} - color: {targetcolor}")
        with ARRASBOT_LOG.open("a", encoding="utf-8") as log_file:
            log_file.write(f"Successfully reconnected at {timestamp()}\n")
        take_screenshot_cdp("reconnected")
        disconnected = False
        died = False

def main():
    """Main entry point"""
    global browser, tab, SCREENSHOT_DIR, ARRASBOT_LOG
    
    print("Initializing Arrasbot2 with CDP...")
    
    # Create directories
    foldername = f"abss_{timestamp()}"
    SCREENSHOT_DIR = DESKTOP_ROOT / foldername
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create log file
    ARRASBOT_LOG = LOGS_DIR / f"abss_{timestamp()}.log"
    
    try:
        # Try to connect to existing Chrome instance
        print("Checking for Chrome with remote debugging...")
        try:
            browser = pychrome.Browser(url="http://127.0.0.1:9222")
            tabs = browser.list_tab()
            if tabs:
                print(f"Found {len(tabs)} Chrome tab(s)")
        except:
            print("Chrome not found with remote debugging enabled.")
            print("\nAttempting to launch Chrome automatically...")
            
            chrome_process = launch_chrome_debug()
            
            if chrome_process is None:
                print_chrome_instructions()
                print("\nWaiting for Chrome connection (30 seconds)...")
                
                # Wait for manual Chrome launch
                for i in range(30):
                    try:
                        browser = pychrome.Browser(url="http://127.0.0.1:9222")
                        tabs = browser.list_tab()
                        if tabs:
                            print(f"\nConnected! Found {len(tabs)} tab(s)")
                            break
                    except:
                        pass
                    time.sleep(1)
                    if i % 5 == 0 and i > 0:
                        print(f"  Still waiting... ({30-i}s remaining)")
                else:
                    print("\nTimeout: Could not connect to Chrome.")
                    print("Please launch Chrome manually and restart the bot.")
                    return
            else:
                # Wait for auto-launched Chrome
                print("Waiting for Chrome to initialize...")
                for i in range(10):
                    try:
                        browser = pychrome.Browser(url="http://127.0.0.1:9222")
                        tabs = browser.list_tab()
                        if tabs:
                            print(f"Connected! Found {len(tabs)} tab(s)")
                            break
                    except:
                        pass
                    time.sleep(1)
                else:
                    print("Failed to connect to auto-launched Chrome.")
                    return
        
        # Get list of tabs
        tabs = browser.list_tab()
        if not tabs:
            print("No Chrome tabs found. Please open a tab and try again.")
            return
        
        # Use the first tab (or find arras.io tab by checking tab info)
        tab = None
        for t in tabs:
            # Check tab info dict which is available without starting
            tab_url = t.get('url', '') if isinstance(t, dict) else getattr(t, 'webSocketDebuggerUrl', '')
            if 'arras' in str(tab_url).lower():
                tab = t
                print(f"Found arras.io tab!")
                break
        
        if not tab:
            tab = tabs[0]
            print(f"Using first available tab")
        
        # Start the tab
        tab.start()
        
        # Now we can access tab properties safely
        try:
            current_url = tab.Page.getNavigationHistory()
            if current_url and 'currentIndex' in current_url:
                url = current_url['entries'][current_url['currentIndex']]['url']
                print(f"Tab URL: {url}")
                if 'arras' not in url.lower():
                    print("\nWARNING: This doesn't appear to be arras.io!")
                    print("Please navigate to arras.io and restart the bot.")
        except:
            print("Connected to Chrome tab")
        
        # Enable Page domain for screenshots
        tab.Page.enable()
        
        # Write initialization to log
        with ARRASBOT_LOG.open("a", encoding="utf-8") as log_file:
            log_file.write(f"""
=============== DEBUG ===============
Screenshot directory: {SCREENSHOT_DIR}
Bot initialized at {timestamp()}
Using Chrome DevTools Protocol

================ LOG ================
Bot initialized at {timestamp()}
""")
        
        print(f"\nBot initialized successfully!")
        print(f"Screenshots will be saved to: {SCREENSHOT_DIR}")
        print("\nAvailable commands:")
        print("  stop - Stop the bot")
        print("  screenshot - Take a manual screenshot")
        print("  status - Show current bot status")
        print("  check - Force a pixel check now")
        print("  probe <x> <y> - Check pixel color at coordinates")
        print("  forcedisconnect/forcedeath/forcereconnect - Force state changes")
        print("="*60 + "\n")
        
        # Start input listener
        start_input_listener()
        
        # Start monitor loop
        monitor_loop()
        
    except Exception as e:
        print(f"Error initializing bot: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if tab:
            try:
                tab.stop()
            except:
                pass
        print("Bot stopped.")

if __name__ == "__main__":
    main()
