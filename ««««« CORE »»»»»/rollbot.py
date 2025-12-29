from pynput.keyboard import Controller, Key, Listener
from pynput.mouse import Controller as MouseController, Button
import time, random
import math
import mss
import numpy as np

tier_thresholds = []
quantity_thresholds = []
stars = 0.00
rarest = 100.00
name = "1x T1"
index = 0
start = time.time()
count = 0
c = Controller()
mouse = MouseController()
sct = mss.mss()
running = True
paused = False
step_mode = False
last_esc_time = 0
esc_press_count = 0
load = False
simulate = True  # Set to True to simulate rolls without typing in-game
simulate_count = 7500  # Number of rolls to simulate before stopping
firefox = False  # Set to True if using Firefox, False for other browsers
MONITOR_INDEX = 1  # Adjust if needed
SCALE = 2  # 2 on Retina displays (macOS); 1 on standard displays

# Track stars and roll counts per tier for statistics
tier_stars = [0.0 for _ in range(32)]  # Stars gained from each tier
tier_roll_count = [0 for _ in range(32)]  # Number of times each tier was rolled

# Combo tracking
last_tier = 0  # Last rolled tier (0 means no previous roll)
combo_quantity = 0  # Cumulative quantity for current combo
highest_combo_quantity = 0  # Highest combo quantity achieved
highest_combo_tier = 0  # Tier of the highest combo

time.sleep(5)
if load:
    c.tap(Key.enter)
    time.sleep(0.1)
    type2("Starting rollbot...")
    time.sleep(0.1)
    c.tap(Key.enter)
    time.sleep(2.5)
    c.tap(Key.enter)
    time.sleep(0.1)
    type2("Loading save...")
    time.sleep(0.1)
    c.tap(Key.enter)
    time.sleep(2.5)
    c.tap(Key.enter)
    time.sleep(0.1)
    type2("Initializing...")
    time.sleep(0.1)
    c.tap(Key.enter)
    time.sleep(2.5)

# clear log
with open("rollbotlog.txt", "w") as f:
    f.write("")

# Screen detection functions (from arrasbot.py)
def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

def color_close(c1, c2, tol=6):
    # tolerant RGB compare
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))

def type2(text):
    for char in text:
        c.tap(char)
        time.sleep(0.02)

def check_and_respawn():
    """Check if dead/disconnected/kicked and handle respawn. Returns True if handling respawn."""
    if firefox:
        targetcolor = get_pixel_rgb(26, 930)
    else:
        targetcolor = get_pixel_rgb(28, 925)
    
    # Check for disconnect/kick (red colors)
    if (color_close(targetcolor, (167, 81, 68)) or color_close(targetcolor, (138, 27, 34)) or
        color_close(targetcolor, (201, 92, 75)) or color_close(targetcolor, (199, 118, 98)) or
        color_close(targetcolor, (213, 114, 93))):
        print("Disconnected/Kicked - clicking respawn...")
        mouse.position = (922, 767)
        mouse.click(Button.left, 1)
        time.sleep(1)
        return True
    
    # Check for death (brown color)
    if color_close(targetcolor, (176, 100, 81)):
        print("Died - respawning...")
        time.sleep(3)
        # Double-check death state
        if firefox:
            targetcolor_after = get_pixel_rgb(26, 930)
        else:
            targetcolor_after = get_pixel_rgb(28, 925)
        if color_close(targetcolor_after, (176, 100, 81)):
            c.tap(Key.enter)
            time.sleep(0.5)
            return True
    
    # Check for reconnected (orange color) - click to finalize
    if color_close(targetcolor, (223, 116, 90)):
        print("Reconnected - finalizing...")
        mouse.position = (36, 155)
        time.sleep(0.1)
        mouse.click(Button.left, 1)
        time.sleep(0.1)
        mouse.position = (9, 194)
        time.sleep(0.1)
        mouse.click(Button.left, 1)
        time.sleep(0.5)
        c.tap("c")
        time.sleep(0.1)
        c.press("`")
        time.sleep(0.1)
        c.tap("i")
        time.sleep(0.1)
        c.release("`")
        return True
    
    return False

# scientific notation formatter
def format_number(num):
    """Format large numbers as x×10^y, otherwise return as-is"""
    if num >= 1000:
        exponent = int(math.log10(num))
        mantissa = num / (10 ** exponent)
        return f"{mantissa:.2f}×10^{exponent}"
    return str(round(num, 2))

# time formatter
def format_time(seconds):
    """Format elapsed time as DD:HH:MM:SS"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{days:02d}:{hours:02d}:{minutes:02d}:{secs:02d}"

def pausable_sleep(duration):
    """Sleep for duration seconds, but check for pause state every 0.1s"""
    elapsed = 0
    while elapsed < duration:
        if paused:
            # Wait until unpaused
            while paused:
                time.sleep(0.1)
                if not running:
                    return
        time.sleep(min(0.1, duration - elapsed))
        elapsed += 0.1

# keyboard listener for Esc key
def on_press(key):
    global running, paused, step_mode, last_esc_time, esc_press_count
    if key == Key.esc:
        current_time = time.time()
        
        # Reset counter if more than 1 second since last press
        if current_time - last_esc_time > 1.0:
            esc_press_count = 0
        
        esc_press_count += 1
        last_esc_time = current_time
        
        # Triple-press: toggle step mode
        if esc_press_count == 3:
            step_mode = not step_mode
            esc_press_count = 0
            if step_mode:
                print("\n⏭️  STEP MODE ENABLED (one roll at a time, press Esc to advance)")
            else:
                print("\n▶️  STEP MODE DISABLED")
        # Double-press: toggle pause
        elif esc_press_count == 2:
            paused = not paused
            if paused:
                print("\n⏸️  Bot PAUSED")
            else:
                print("\n▶️  Bot RESUMED")
        # Single press in step mode: advance one roll
        elif esc_press_count == 1 and step_mode:
            pass  # Just let the main loop continue

listener = Listener(on_press=on_press)
listener.start()

# generate thresholds
# tiers: each tier has a 1/3 chance of being rolled compared to the previous tier
# quantities: each quantity has a 1/6 chance of being rolled

def build_thresholds(base, count):
    """
    base: the denominator base (3 for tiers, 6 for quantities)
    count: how many items (32 tiers, 5 quantities)
    
    Returns:
        (cumulative thresholds, normalized weights)
    """
    # Step 1: raw weights
    weights = [(1 / (base ** i)) for i in range(count)]
    
    # Step 2: normalize
    total = sum(weights)
    normalized_weights = [w / total for w in weights]
    
    # Step 3: cumulative thresholds
    cumulative = []
    running = 0
    for w in normalized_weights:
        running += w
        cumulative.append(running)
    
    return cumulative, normalized_weights


# Build thresholds using the new function
tier_thresholds, tier_weights = build_thresholds(base=3, count=32)
quantity_thresholds, quantity_weights = build_thresholds(base=6, count=5)


def weighted_roll(thresholds):
    """
    thresholds: cumulative probability list
    Returns: index (0-based) of selected item
    """
    r = random.random()
    for i, t in enumerate(thresholds):
        if r < t:
            return i
    return len(thresholds) - 1  # fallback (should never hit)

def format_rarity(chance):
    """Safely format rarity as '1 in X', handling very small chances"""
    if chance <= 0:
        return "∞"
    rarity = 100 / chance
    if rarity >= 1e15:  # Extremely rare
        return format_number(rarity)
    return str(round(rarity, 3))


# get data from file
# format is a list containing each quantity of each tier, in order as a list ([t1, t2, etc], stars)
with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotlog.txt", "w+") as log:
    with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotsave.txt", "w+") as f:
        # read data with empty protection
        data = f.read()
        if data == "":
            tier_data = [0 for _ in range(32)]
            stars = 0
        else:
            lines = data.split("\n")
            tier_data = list(map(int, lines[0].split(",")))
            stars = int(lines[1])
        
        # Pre-simulation phase
        if simulate and simulate_count > 0:
            print(f"\n=== Starting simulation of {simulate_count} rolls ===")
            sim_start = time.time()
            for sim_i in range(simulate_count):
                tier = weighted_roll(tier_thresholds) + 1
                quantity = weighted_roll(quantity_thresholds) + 1
                
                # Update combo - track cumulative quantity
                if tier == last_tier:
                    combo_quantity += quantity
                else:
                    combo_quantity = quantity
                    last_tier = tier
                
                # Track highest combo by quantity
                if combo_quantity > highest_combo_quantity:
                    highest_combo_quantity = combo_quantity
                    highest_combo_tier = tier
                
                tier_prob = tier_weights[tier - 1]
                quantity_prob = quantity_weights[quantity - 1]
                chance = tier_prob * quantity_prob * 100
                chance = round(chance, 3)
                gained = quantity * round(3.5 ** tier, 2) - 2.5
                stars += gained
                if chance < rarest:
                    rarest = chance
                    name = f"{quantity} × T{tier}"
                    index = count
                
                count += 1
                tier_data[tier - 1] += quantity
                tier_stars[tier - 1] += gained
                tier_roll_count[tier - 1] += 1
                
                # Log simulation rolls
                rarity_value = 100 / chance if chance > 0 else float('inf')
                if rarity_value >= 1e15:
                    log.write(f"[SIM] Rolled {quantity} × T{tier} | 1/{format_rarity(chance)} | {gained} ★" + "\n")
                else:
                    log.write(f"[SIM] Rolled {quantity} × T{tier} | R%: {round(chance, 3)}% (1/{format_rarity(chance)}) | {gained} ★" + "\n")
                
                # Progress indicator every 100 rolls
                if count % 100 == 0:
                    print(f"Simulated {count}/{simulate_count} rolls...")
                    log.flush()  # Flush every 100 rolls during simulation
            
            sim_time = time.time() - sim_start
            print(f"=== Simulation complete in {format_time(sim_time)} ===")
            print(f"Total stars: {format_number(stars)} ★")
            print(f"Rarest roll: {name} | R%: {round(rarest, 3)}% (1/{format_rarity(rarest)})")

            stars = round(stars, 2)
            
            # Show detailed statistics after simulation (console)
            print(f"\n--- Simulation Statistics ---")
            print(f"{count} rolls | {stars} ★ | Uptime: {format_time(sim_time)}")
            print(f"Rarest so far: {name} | R%: {round(rarest, 3)}% (1/{format_rarity(rarest)})")
            print(f"Rarest roll ({index + 1}/{count}) gained {round(round(3.5 ** (int(name.split('× T')[1])), 3)*int(name.split('× T')[0]) - 2.5, 2)} ★")
            print(f"Highest combo: {highest_combo_quantity} × T{highest_combo_tier} | Current: {combo_quantity} × T{last_tier}")
            
            # Show tier breakdown after simulation (console)
            print(f"\n=== Tier Breakdown after {count} rolls ===")
            for tier_idx in range(32):
                tier_num = tier_idx + 1
                tier_star_total = tier_stars[tier_idx]
                tier_rolls = tier_roll_count[tier_idx]
                
                # Calculate percentage of total stars
                if stars > 0:
                    percentage = (tier_star_total / stars) * 100
                else:
                    percentage = 0
                
                # Only show tiers that have been rolled
                if tier_rolls > 0:
                    print(f"T{tier_num}: {format_number(tier_star_total)} ★ ({percentage:.2f}%) | {tier_rolls} rolls")
            
            # Type stats and breakdown in-game after simulation
            print("Typing simulation results in-game...")
            c.tap(Key.enter)
            time.sleep(0.1)
            type2(f"{count} rolls | {stars} ★ | Uptime: {format_time(sim_time)}")
            time.sleep(0.1)
            c.tap(Key.enter)
            time.sleep(2.5)
            c.tap(Key.enter)
            time.sleep(0.1)
            type2(f"Rarest so far: {name} | R%: {round(rarest, 3)}% (1/{format_rarity(rarest)})")
            time.sleep(0.1)
            c.tap(Key.enter)
            time.sleep(2.5)
            c.tap(Key.enter)
            time.sleep(0.1)
            type2(f"Rarest roll ({index + 1}/{count}) gained {round(round(3.5 ** (int(name.split('× T')[1])), 3)*int(name.split('× T')[0]) - 2.5, 2)} ★")
            time.sleep(0.1)
            c.tap(Key.enter)
            time.sleep(2.5)
            c.tap(Key.enter)
            time.sleep(0.1)
            type2(f"Highest combo: {highest_combo_quantity} × T{highest_combo_tier} | Current: {combo_quantity} × T{last_tier}")
            time.sleep(0.1)
            c.tap(Key.enter)
            time.sleep(2.5)
            
            for tier_idx in range(32):
                tier_num = tier_idx + 1
                tier_star_total = tier_stars[tier_idx]
                tier_rolls = tier_roll_count[tier_idx]
                
                # Calculate percentage of total stars
                if stars > 0:
                    percentage = (tier_star_total / stars) * 100
                else:
                    percentage = 0
                
                # Only show tiers that have been rolled
                if tier_rolls > 0:
                    c.tap(Key.enter)
                    time.sleep(0.1)
                    type2(f"T{tier_num}: {round(tier_star_total, 2)} ★ ({percentage:.4f}%) | {tier_rolls} rolls")
                    time.sleep(0.1)
                    c.tap(Key.enter)
                    time.sleep(2.5)
            
            print(f"\nStarting normal operation...\n")
            time.sleep(2)
        
        # Normal rolling loop
        while True:
            # Check if paused
            while paused:
                time.sleep(0.1)
                if not running:
                    break
            
            if not running:
                break
            
            # Check for death/disconnect/kick at start of each roll cycle
            if check_and_respawn():
                time.sleep(2)  # Brief pause after respawn
                continue  # Skip this roll cycle, proceed to next
            
            tier = weighted_roll(tier_thresholds) + 1
            quantity = weighted_roll(quantity_thresholds) + 1

            # Update combo - track cumulative quantity for same tier
            previous_combo_quantity = 0
            if tier == last_tier:
                previous_combo_quantity = combo_quantity
                combo_quantity += quantity
            else:
                combo_quantity = quantity
                last_tier = tier
            
            # Track highest combo by quantity
            if combo_quantity > highest_combo_quantity:
                highest_combo_quantity = combo_quantity
                highest_combo_tier = tier

            # format:
            # rolled quantity tier | chance of getting (multiply tier chance and quantity) | total stars
            # tier n gives int(1.5^(n)) stars each
            # calculate chance using ACTUAL normalized weights
            tier_prob = tier_weights[tier - 1]  # tier is 1-indexed, weights are 0-indexed
            quantity_prob = quantity_weights[quantity - 1]  # quantity is 1-indexed, weights are 0-indexed
            chance = tier_prob * quantity_prob * 100
            chance = round(chance, 3)
            base_gained = quantity * round(3.5 **tier, 2) - 2.5
            
            # Apply combo bonus: 40% per quantity in previous combo
            combo_bonus = previous_combo_quantity * 0.4 * base_gained if previous_combo_quantity > 0 else 0
            gained = base_gained + combo_bonus
            
            stars += gained
            if chance < rarest:
                rarest = chance
                name = f"{quantity} × T{tier}"
                index = count

            # Format with combo if applicable (show previous total / new total combo)
            if previous_combo_quantity > 0:
                combo_display = f"(+{previous_combo_quantity}/{combo_quantity}) {quantity} × T{tier}"
                bonus_display = f" [+{round(combo_bonus, 2)}]"
            else:
                combo_display = f"{quantity} × T{tier}"
                bonus_display = ""
            
            # Format rarity - skip percentage for extremely rare rolls
            rarity_value = 100 / chance if chance > 0 else float('inf')
            if rarity_value >= 1e15:
                info = f"{combo_display} | 1/{format_rarity(chance)} | {round(gained, 2)} ★{bonus_display}"
            else:
                info = f"{combo_display} | R%: {round(chance, 3)}% (1/{format_rarity(chance)}) | {round(gained, 2)} ★{bonus_display}"
            
            print(f"Roll {count + 1}: {info}")
            log.write(info + "\n")
            log.flush()  # Force write to disk
            
            c.tap(Key.enter)
            time.sleep(0.1)
            type2(info)
            time.sleep(0.1)
            c.tap(Key.enter)
            time.sleep(2.5)

            stars = round(stars, 2)
            
            count += 1
            tier_data[tier - 1] += quantity  # Update tier data every roll
            tier_stars[tier - 1] += gained  # Track stars from this tier
            tier_roll_count[tier - 1] += 1  # Track number of rolls for this tier
            
            # Step mode: wait for Esc press to continue
            if step_mode:
                print("[Step mode] Press Esc to roll next...")
                temp_esc_count = esc_press_count
                while step_mode and esc_press_count == temp_esc_count:
                    time.sleep(0.1)
                    if not running or paused or not step_mode:
                        break
            
            if count % 10 == 0:
                # every 10 rolls, save data
                with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotsave.txt", "w") as save_file:
                    save_file.write(",".join(map(str, tier_data)) + "\n")
                    save_file.write(str(int(stars)) + "\n")
                print(f"--- Saved progress after {count} rolls ---")
                # show statistics
                c.tap(Key.enter)
                pausable_sleep(0.1)
                type2(f"{count} rolls | {stars} ★ | Uptime: {format_time(time.time() - start)}")
                pausable_sleep(0.1)
                c.tap(Key.enter)
                pausable_sleep(2.5)
                c.tap(Key.enter)
                pausable_sleep(0.1)
                type2(f"Rarest so far: {name} | R%: {round(rarest, 3)}% (1/{format_rarity(rarest)})")
                pausable_sleep(0.1)
                c.tap(Key.enter)
                pausable_sleep(2.5)
                c.tap(Key.enter)
                pausable_sleep(0.1)
                type2(f"Rarest roll ({index + 1}/{count}) gained {round(round(3.5 ** (int(name.split('× T')[1])), 3)*int(name.split('× T')[0]) - 2.5, 2)} ★")
                pausable_sleep(0.1)
                c.tap(Key.enter)
                pausable_sleep(2.5)
                c.tap(Key.enter)
                pausable_sleep(0.1)
                type2(f"Highest combo: {highest_combo_quantity} × T{highest_combo_tier} | Current: {combo_quantity} × T{tier}")
                pausable_sleep(0.1)
                c.tap(Key.enter)
                pausable_sleep(2.5)
            
            # Every 100 rolls, show detailed tier breakdown
            if count % 100 == 0:
                print(f"\n=== Tier Breakdown after {count} rolls ===")
                
                for tier_idx in range(32):
                    tier_num = tier_idx + 1
                    tier_star_total = tier_stars[tier_idx]
                    tier_rolls = tier_roll_count[tier_idx]
                    
                    # Calculate percentage of total stars
                    if stars > 0:
                        percentage = (tier_star_total / stars) * 100
                    else:
                        percentage = 0
                    
                    # Only show tiers that have been rolled
                    if tier_rolls > 0:
                        stat_line = f"T{tier_num}: {format_number(tier_star_total)} ★ | {round(percentage, 2)}% | {tier_rolls} rolls"
                        print(stat_line)
                        c.tap(Key.enter)
                        pausable_sleep(0.1)
                        type2(stat_line)
                        pausable_sleep(0.1)
                        c.tap(Key.enter)
                        pausable_sleep(2.5)

            # stop loop when esc is pressed
            if not running:
                print("Bot stopped by user.")
                break