from playwright.sync_api import sync_playwright
from PIL import Image
import io, time, random, math, sys, signal, multiprocessing, os
from pathlib import Path
from pynput.keyboard import Key, Listener

# Mapping from pynput Key to Playwright key strings
KEY_MAP = {
    Key.enter: b"Enter",
    Key.shift: "Shift",
    Key.shift_l: "Shift",
    Key.shift_r: "Shift",
    Key.ctrl: "Control",
    Key.ctrl_l: "Control",
    Key.ctrl_r: "Control",
    Key.alt: "Alt",
    Key.alt_l: "Alt",
    Key.alt_r: "Alt",
    Key.cmd: "Meta",
    Key.cmd_l: "Meta",
    Key.cmd_r: "Meta",
    Key.space: "Space",
    Key.tab: "Tab",
    Key.backspace: "Backspace",
    Key.delete: "Delete",
    Key.esc: "Escape",
    Key.up: "ArrowUp",
    Key.down: "ArrowDown",
    Key.left: "ArrowLeft",
    Key.right: "ArrowRight",
}

# Configuration
CORE_DIR = Path(__file__).parent
load_save = True  # Set to False to wipe save and start fresh, True to load existing save
simulate_count = 50000  # Number of rolls to simulate before stopping

# Global state
tier_data = [0 for _ in range(32)]
tier_thresholds = []
quantity_thresholds = []
stars = 0.00
rarest = 100.00
name = "1 × T1"
index = 0
start = time.time()
count = 0
running = True
paused = False
step_mode = False
last_esc_time = 0
esc_press_count = 0

# Track stars and roll counts per tier for statistics
tier_stars = [0.0 for _ in range(32)]
tier_roll_count = [0 for _ in range(32)]

# Combo tracking
last_tier = 0
combo_quantity = 0
highest_combo_quantity = 0
highest_combo_tier = 0

simulate = (simulate_count != 0)

def signal_handler(sig, frame):
    """Handle Ctrl+C by saving progress before exit"""
    global tier_data, stars, count, tier_roll_count, tier_stars, rarest, name, index, highest_combo_quantity, highest_combo_tier, last_tier, combo_quantity
    print("\n\n⚠️  Ctrl+C detected - saving progress before exit...")
    try:
        with open(CORE_DIR / "rollbotsave.txt", "w") as save_file:
            save_file.write(",".join(map(str, tier_data)) + "\n")
            save_file.write(str(int(stars)) + "\n")
            save_file.write(",".join(map(str, tier_roll_count)) + "\n")
            save_file.write(",".join(map(str, tier_stars)) + "\n")
            save_file.write(f"{count}\n")
            save_file.write(f"{rarest}\n")
            save_file.write(f"{name}\n")
            save_file.write(f"{index}\n")
            save_file.write(f"{highest_combo_quantity},{highest_combo_tier}\n")
            save_file.write(f"{last_tier},{combo_quantity}\n")
        print(f"✅ Progress saved ({count} rolls, {stars} ★)")
    except Exception as e:
        print(f"❌ Error saving: {e}")
    print("Exiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def format_number(num):
    """Format large numbers as x×10^y"""
    if num >= 1000:
        exponent = int(math.log10(num))
        mantissa = num / (10 ** exponent)
        return f"{mantissa:.2f}×10^{exponent}"
    return str(round(num, 2))

def format_time(seconds):
    """Format elapsed time as DD:HH:MM:SS"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{days:02d}:{hours:02d}:{minutes:02d}:{secs:02d}"

def format_rarity(chance):
    """Safely format rarity as '1 in X'"""
    if chance <= 0:
        return "∞"
    rarity = 100 / chance
    if rarity >= 1000:
        return format_number(rarity)
    return str(round(rarity, 3))

def format_chance(chance):
    """Format chance percentage with scientific notation for very small values"""
    if chance <= 0:
        return "0 (≈0)"
    if chance < 0.001:
        exponent = int(math.floor(math.log10(chance)))
        mantissa = chance / (10 ** exponent)
        return f"{mantissa:.3f}×10^{exponent}"
    return f"{chance:.6f}" if chance < 0.01 else f"{round(chance, 3)}"

def build_thresholds(base, count):
    """Build cumulative thresholds and normalized weights"""
    weights = [(1 / (base ** i)) for i in range(count)]
    total = sum(weights)
    normalized_weights = [w / total for w in weights]
    cumulative = []
    running_sum = 0
    for w in normalized_weights:
        running_sum += w
        cumulative.append(running_sum)
    return cumulative, normalized_weights

def weighted_roll(thresholds):
    """Returns index (0-based) of selected item"""
    r = random.random()
    for i, t in enumerate(thresholds):
        if r < t:
            return i
    return len(thresholds) - 1

def pausable_sleep(duration):
    """Sleep for duration seconds, checking pause state"""
    elapsed = 0
    while elapsed < duration:
        if paused:
            while paused:
                time.sleep(0.1)
        time.sleep(min(0.1, duration - elapsed))
        elapsed += 0.1

def on_press(key):
    """Keyboard listener for Esc key"""
    global running, paused, step_mode, last_esc_time, esc_press_count
    if key == Key.esc:
        current_time = time.time()
        if current_time - last_esc_time > 1.0:
            esc_press_count = 0
        esc_press_count += 1
        last_esc_time = current_time
        
        if esc_press_count == 3:
            step_mode = not step_mode
            esc_press_count = 0
            print(f"{'⏯️  Step mode ON' if step_mode else '▶️  Step mode OFF'}")
        elif esc_press_count == 2:
            paused = not paused
            print(f"{'⏸️  PAUSED' if paused else '▶️  RESUMED'}")
        elif esc_press_count == 1 and step_mode:
            pass

tier_thresholds, tier_weights = build_thresholds(base=3, count=32)
quantity_thresholds, quantity_weights = build_thresholds(base=6, count=5)

class ChromePageController:
    def __init__(self, url: str, headless: bool = False):
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            channel="chrome",
            headless=headless,
            args=[
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
            ],
        )

        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1.0
        )

        self.page = self.context.new_page()
        self.page.goto(url)

    # ------------------------
    # INPUT SIMULATION
    # ------------------------

    def click(self, x: int, y: int):
        """
        Click at page-relative coordinates
        """
        self.page.mouse.click(x, y)

    def type_text(self, text: str, delay_ms: int = 50):
        """
        Type text into the active element
        """
        self.page.keyboard.type(str(text), delay=delay_ms)
    
    def type_slow(self, text: str):
        """Type text character by character with 20ms delay (like type2 in rollbot.py)"""
        for char in text:
            self.page.keyboard.press(char)
            time.sleep(0.02)

    def press_key(self, key):
        """
        Press a single key using pynput Key (e.g. Key.enter, Key.shift) or string
        """
        if isinstance(key, Key):
            # Convert pynput Key to Playwright key string
            playwright_key = KEY_MAP.get(key)
            if playwright_key is None:
                raise ValueError(f"Unsupported pynput Key: {key}")
            self.page.keyboard.press(playwright_key)
        else:
            # Fallback to string for backward compatibility
            self.page.keyboard.press(key)

    # ------------------------
    # PIXEL SAMPLING
    # ------------------------

    def get_pixel_color(self, x: int, y: int):
        """
        Returns (R, G, B) at page-relative coordinates
        """
        screenshot_bytes = self.page.screenshot(full_page=False)
        image = Image.open(io.BytesIO(screenshot_bytes))
        pixel = image.getpixel((x, y))
        return pixel[:3]  # RGB
    
    def color_close(self, c1, c2, tol=6):
        """Tolerant RGB compare"""
        return all(abs(a - b) <= tol for a, b in zip(c1, c2))
    
    def check_and_respawn(self):
        """Check if dead/disconnected/kicked and handle respawn. Returns True if handling respawn."""
        targetcolor = self.get_pixel_color(28, 925)
        
        # Check for disconnect/kick (red colors)
        if (self.color_close(targetcolor, (167, 81, 68)) or self.color_close(targetcolor, (138, 27, 34)) or
            self.color_close(targetcolor, (201, 92, 75)) or self.color_close(targetcolor, (199, 118, 98)) or
            self.color_close(targetcolor, (213, 114, 93))):
            print("Disconnected/Kicked - clicking respawn...")
            self.click(922, 767)
            time.sleep(1)
            return True
        
        # Check for death (brown color)
        if self.color_close(targetcolor, (176, 100, 81)):
            print("Died - respawning...")
            time.sleep(3)
            targetcolor_after = self.get_pixel_color(28, 925)
            if self.color_close(targetcolor_after, (176, 100, 81)):
                self.press_key(Key.enter)
                time.sleep(0.5)
                return True
        
        # Check for reconnected (orange color) - click to finalize
        if self.color_close(targetcolor, (223, 116, 90)):
            print("Reconnected - finalizing...")
            self.click(36, 155)
            time.sleep(0.1)
            self.click(9, 194)
            time.sleep(0.1)
            self.page.keyboard.press("c")
            time.sleep(0.1)
            self.page.keyboard.press("`")
            time.sleep(0.1)
            self.page.keyboard.press("i")
            time.sleep(0.1)
            return True
        
        return False

    # ------------------------
    # UTILITY
    # ------------------------

    def wait(self, seconds: float):
        self.page.wait_for_timeout(seconds * 1000)

    def close(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()


# ------------------------
# MAIN ROLLING LOGIC
# ------------------------

if __name__ == "__main__":
    # Clear log
    with open(CORE_DIR / "rollbotlog.txt", "w") as f:
        f.write("")
    
    # Load save file if load_save is True
    if load_save:
        try:
            with open(CORE_DIR / "rollbotsave.txt", "r") as f:
                data = f.read()
        except FileNotFoundError:
            print("No save file found - starting fresh")
            data = ""
    else:
        print("⚠️  load_save=False: Wiping save and starting fresh...")
        data = ""
        try:
            with open(CORE_DIR / "rollbotsave.txt", "w") as f:
                f.write("")
        except:
            pass
    
    if data == "":
        tier_data = [0 for _ in range(32)]
        stars = 0
        count = 0
    else:
        lines = data.strip().split("\n")
        tier_data = list(map(int, lines[0].split(",")))
        stars = int(lines[1])
        
        if len(lines) >= 10:
            tier_roll_count = list(map(int, lines[2].split(",")))
            tier_stars = list(map(float, lines[3].split(",")))
            count = int(lines[4])
            rarest = float(lines[5])
            name = lines[6]
            index = int(lines[7])
            combo_parts = lines[8].split(",")
            highest_combo_quantity = int(combo_parts[0])
            highest_combo_tier = int(combo_parts[1])
            current_combo_parts = lines[9].split(",")
            last_tier = int(current_combo_parts[0])
            combo_quantity = int(current_combo_parts[1])
        else:
            print("Save file is old format - initializing new tracking data")
    
    # Initialize Chrome controller
    print("Launching Chrome...")
    controller = ChromePageController("https://arras.io/#wpd", headless=False)
    controller.wait(2)
    
    # Start keyboard listener
    listener = Listener(on_press=on_press)
    listener.start()
    
    # Simulation phase
    if simulate and simulate_count > 0:
        print(f"\n=== Starting simulation of {simulate_count} rolls ===")
        sim_start = time.time()
        
        for i in range(simulate_count):
            tier = weighted_roll(tier_thresholds) + 1
            quantity = weighted_roll(quantity_thresholds) + 1
            
            previous_combo_quantity = 0
            if tier == last_tier:
                previous_combo_quantity = combo_quantity
                combo_quantity += quantity
            else:
                combo_quantity = quantity
                last_tier = tier
            
            if combo_quantity > highest_combo_quantity:
                highest_combo_quantity = combo_quantity
                highest_combo_tier = tier
            
            tier_prob = tier_weights[tier - 1]
            quantity_prob = quantity_weights[quantity - 1]
            chance = tier_prob * quantity_prob * 100
            base_gained = quantity * round(3.5 ** tier, 2) - 2.5
            combo_bonus = previous_combo_quantity * 0.4 * base_gained if previous_combo_quantity > 0 else 0
            gained = base_gained + combo_bonus
            
            stars += gained
            
            if chance < rarest:
                rarest = chance
                name = f"{quantity} × T{tier}"
                index = i
            
            tier_data[tier - 1] += quantity
            tier_stars[tier - 1] += gained
            tier_roll_count[tier - 1] += 1
            
            if (i + 1) % max(1, simulate_count // 10) == 0:
                print(f"Progress: {i + 1}/{simulate_count} rolls ({(i+1)/simulate_count*100:.1f}%)")
        
        count = simulate_count
        sim_time = time.time() - sim_start
        print(f"=== Simulation complete in {format_time(sim_time)} ===")
        print(f"Total stars: {format_number(stars)} ★")
        print(f"Rarest roll: {name} | R%: {format_chance(rarest)}% (1/{format_rarity(rarest)})")
        
        # Type stats in-game
        controller.press_key(Key.enter)
        time.sleep(0.1)
        controller.type_slow(f"{count} rolls | {stars} ★ | Uptime: {format_time(sim_time)}")
        time.sleep(0.1)
        controller.press_key(Key.enter)
        time.sleep(1)
        
        # Save and exit after simulation
        signal_handler(None, None)
    
    # Normal rolling loop
    print("\n=== Starting rolling loop ===")
    print("Press Esc once to pause, twice to resume, three times for step mode")
    
    start = time.time()
    
    try:
        while True:
            # Check for pause
            if paused:
                time.sleep(0.1)
                continue
            
            # Check for step mode
            if step_mode:
                print("⏯️  Step mode: Press Esc to advance one roll")
                while step_mode and esc_press_count == 0:
                    time.sleep(0.1)
                esc_press_count = 0
            
            # Check for respawn
            if controller.check_and_respawn():
                time.sleep(2)
                continue
            
            # Perform roll
            tier = weighted_roll(tier_thresholds) + 1
            quantity = weighted_roll(quantity_thresholds) + 1
            
            previous_combo_quantity = 0
            if tier == last_tier:
                previous_combo_quantity = combo_quantity
                combo_quantity += quantity
            else:
                combo_quantity = quantity
                last_tier = tier
            
            if combo_quantity > highest_combo_quantity:
                highest_combo_quantity = combo_quantity
                highest_combo_tier = tier
            
            tier_prob = tier_weights[tier - 1]
            quantity_prob = quantity_weights[quantity - 1]
            chance = tier_prob * quantity_prob * 100
            base_gained = quantity * round(3.5 ** tier, 2) - 2.5
            combo_bonus = previous_combo_quantity * 0.4 * base_gained if previous_combo_quantity > 0 else 0
            gained = base_gained + combo_bonus
            
            stars += gained
            count += 1
            
            if chance < rarest:
                rarest = chance
                name = f"{quantity} × T{tier}"
                index = count - 1
            
            tier_data[tier - 1] += quantity
            tier_stars[tier - 1] += gained
            tier_roll_count[tier - 1] += 1
            
            # Log roll
            if previous_combo_quantity > 0:
                combo_display = f"(+{previous_combo_quantity}/{combo_quantity}) {quantity} × T{tier}"
                bonus_display = f" [+{round(combo_bonus, 2)}]"
            else:
                combo_display = f"{quantity} × T{tier}"
                bonus_display = ""
            
            if chance < 0.0001:
                info = f"{combo_display} | R%: 1 in {format_rarity(chance)} | {round(gained, 2)} ★{bonus_display}"
            else:
                info = f"{combo_display} | R%: {format_chance(chance)}% (1 in {format_rarity(chance)}) | {round(gained, 2)} ★{bonus_display}"
            
            print(f"Roll {count}: {info}")
            
            # Type in-game every 100 rolls or on rare rolls
            if count % 100 == 0 or chance < 1.0:
                elapsed = time.time() - start
                controller.press_key(Key.enter)
                time.sleep(0.05)
                controller.type_slow(f"[{count}] {info} | Total: {round(stars, 2)} ★ | {format_time(elapsed)}")
                time.sleep(0.05)
                controller.press_key(Key.enter)
            
            # Save every 500 rolls
            if count % 500 == 0:
                with open(CORE_DIR / "rollbotsave.txt", "w") as save_file:
                    save_file.write(",".join(map(str, tier_data)) + "\n")
                    save_file.write(str(int(stars)) + "\n")
                    save_file.write(",".join(map(str, tier_roll_count)) + "\n")
                    save_file.write(",".join(map(str, tier_stars)) + "\n")
                    save_file.write(f"{count}\n")
                    save_file.write(f"{rarest}\n")
                    save_file.write(f"{name}\n")
                    save_file.write(f"{index}\n")
                    save_file.write(f"{highest_combo_quantity},{highest_combo_tier}\n")
                    save_file.write(f"{last_tier},{combo_quantity}\n")
                print(f"💾 Autosaved at {count} rolls")
            
            pausable_sleep(0.1)
    
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        print(f"Error: {e}")
        signal_handler(None, None)
    finally:
        controller.close()
