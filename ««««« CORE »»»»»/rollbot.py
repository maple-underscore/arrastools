from pynput.keyboard import Controller, Key, Listener
from pynput.mouse import Controller as MouseController, Button
import time, random
import math
import mss
import numpy as np
import signal
import sys
import multiprocessing
import os

# Note: GPU acceleration isn't applicable for this simulation as it's dominated by
# random number generation and branching logic which CPUs handle more efficiently.
# Multiprocessing across CPU cores provides the best performance for this workload.

tier_thresholds = []
quantity_thresholds = []
stars = 0.00
rarest = 100.00
name = "1 × T1"
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
load_save = True  # Set to False to wipe save and start fresh, True to load existing save
simulate_count = 50000  # Number of rolls to simulate before stopping
firefox = False  # Set to True if using Firefox, False for other browsers
MONITOR_INDEX = 1  # Adjust if needed
SCALE = 2  # 2 on Retina displays (macOS); 1 on standard displays

if simulate_count != 0:
    simulate = True
else:
    simulate = False

# Track stars and roll counts per tier for statistics
tier_stars = [0.0 for _ in range(32)]  # Stars gained from each tier
tier_roll_count = [0 for _ in range(32)]  # Number of times each tier was rolled

# Combo tracking
last_tier = 0  # Last rolled tier (0 means no previous roll)
combo_quantity = 0  # Cumulative quantity for current combo
highest_combo_quantity = 0  # Highest combo quantity achieved
highest_combo_tier = 0  # Tier of the highest combo

def signal_handler(sig, frame):
    """Handle Ctrl+C by saving progress before exit"""
    global tier_data, stars, count, tier_roll_count, tier_stars, rarest, name, index, highest_combo_quantity, highest_combo_tier, last_tier, combo_quantity
    print("\n\n⚠️  Ctrl+C detected - saving progress before exit...")
    try:
        with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotsave.txt", "w") as save_file:
            save_file.write(",".join(map(str, tier_data)) + "\n")  # Line 1: tier quantities
            save_file.write(str(int(stars)) + "\n")  # Line 2: total stars
            save_file.write(",".join(map(str, tier_roll_count)) + "\n")  # Line 3: roll counts per tier
            save_file.write(",".join(map(str, tier_stars)) + "\n")  # Line 4: stars gained per tier
            save_file.write(f"{count}\n")  # Line 5: total roll count
            save_file.write(f"{rarest}\n")  # Line 6: rarest roll chance
            save_file.write(f"{name}\n")  # Line 7: rarest roll name
            save_file.write(f"{index}\n")  # Line 8: rarest roll index
            save_file.write(f"{highest_combo_quantity},{highest_combo_tier}\n")  # Line 9: highest combo
            save_file.write(f"{last_tier},{combo_quantity}\n")  # Line 10: current combo state
        print(f"✅ Progress saved ({count} rolls, {stars} ★)")
    except Exception as e:
        print(f"❌ Error saving: {e}")
    print("Exiting...")
    sys.exit(0)

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

def type2(text):
    for char in text:
        c.tap(char)
        time.sleep(0.02)


if __name__ == '__main__':
    time.sleep(2)
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
    if rarity >= 1000:  # Use scientific notation for large rarities (1 in 1000+)
        return format_number(rarity)
    return str(round(rarity, 3))

def format_chance(chance):
    """Format chance percentage with scientific notation for very small values"""
    if chance <= 0:
        return "0 (≈0)"
    if chance < 0.001:  # Use scientific notation for very small percentages
        exponent = int(math.floor(math.log10(chance)))
        mantissa = chance / (10 ** exponent)
        return f"{mantissa:.3f}×10^{exponent}"
    return f"{chance:.6f}" if chance < 0.01 else f"{round(chance, 3)}"

def simulate_worker(worker_id, num_rolls, tier_thresholds, tier_weights, quantity_thresholds, quantity_weights, progress_queue, roll_offset):
    """Worker function to simulate rolls in parallel"""
    # Set unique random seed for this worker
    random.seed(int(time.time() * 1000) + worker_id * 12345)
    
    # Local tracking variables
    local_tier_data = [0 for _ in range(32)]
    local_tier_stars = [0.0 for _ in range(32)]
    local_tier_roll_count = [0 for _ in range(32)]
    local_stars = 0.0
    local_rarest = 100.0
    local_name = "1 × T1"
    local_index = 0
    local_last_tier = 0
    local_combo_quantity = 0
    local_highest_combo_quantity = 0
    local_highest_combo_tier = 0
    local_roll_logs = []  # Collect log entries for each roll
    
    for i in range(num_rolls):
        tier = weighted_roll(tier_thresholds) + 1
        quantity = weighted_roll(quantity_thresholds) + 1
        
        # Track previous combo for this roll
        previous_combo_quantity = 0
        if tier == local_last_tier:
            previous_combo_quantity = local_combo_quantity
            local_combo_quantity += quantity
        else:
            previous_combo_quantity = 0
            local_combo_quantity = quantity
            local_last_tier = tier
        
        # Track highest combo
        if local_combo_quantity > local_highest_combo_quantity:
            local_highest_combo_quantity = local_combo_quantity
            local_highest_combo_tier = tier
        
        tier_prob = tier_weights[tier - 1]
        quantity_prob = quantity_weights[quantity - 1]
        chance = tier_prob * quantity_prob * 100  # Keep full precision, don't round
        base_gained = quantity * round(3.5 ** tier, 2) - 2.5
        
        # Apply combo bonus: 40% per quantity in previous combo
        combo_bonus = previous_combo_quantity * 0.4 * base_gained if previous_combo_quantity > 0 else 0
        gained = base_gained + combo_bonus
        
        local_stars += gained
        
        if chance < local_rarest:
            local_rarest = chance
            local_name = f"{quantity} × T{tier}"
            local_index = i
        
        local_tier_data[tier - 1] += quantity
        local_tier_stars[tier - 1] += gained
        local_tier_roll_count[tier - 1] += 1
        
        # Format log entry (same as normal rolling loop)
        if previous_combo_quantity > 0:
            combo_display = f"(+{previous_combo_quantity}/{local_combo_quantity}) {quantity} × T{tier}"
            bonus_display = f" [+{round(combo_bonus, 2)}]"
        else:
            combo_display = f"{quantity} × T{tier}"
            bonus_display = ""
        
        if chance < 0.0001:
            info = f"{combo_display} | R%: 1 in {format_rarity(chance)} | {round(gained, 2)} ★{bonus_display}"
        else:
            info = f"{combo_display} | R%: {format_chance(chance)}% (1 in {format_rarity(chance)}) | {round(gained, 2)} ★{bonus_display}"
        
        # Add to log with global roll number
        local_roll_logs.append(f"Roll {roll_offset + i + 1}: {info}")
        
        # Report progress periodically
        if (i + 1) % max(1, num_rolls // 10) == 0:
            progress_queue.put(1)
    
    return {
        'tier_data': local_tier_data,
        'tier_stars': local_tier_stars,
        'tier_roll_count': local_tier_roll_count,
        'stars': local_stars,
        'rarest': local_rarest,
        'name': local_name,
        'index': local_index,
        'highest_combo_quantity': local_highest_combo_quantity,
        'highest_combo_tier': local_highest_combo_tier,
        'roll_logs': local_roll_logs
    }


if __name__ == '__main__':
    # get data from file
    # format is a list containing each quantity of each tier, in order as a list ([t1, t2, etc], stars)
    with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotlog.txt", "w+") as log:
        # Load save file if load_save is True
        if load_save:
            try:
                with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotsave.txt", "r") as f:
                    data = f.read()
            except FileNotFoundError:
                data = ""
        else:
            # Wipe save file and start fresh
            print("⚠️  load_save=False: Wiping save and starting fresh...")
            data = ""
            # Clear the save file
            try:
                with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotsave.txt", "w") as f:
                    f.write("")  # Empty file
            except:
                pass
        
        if data == "":
            tier_data = [0 for _ in range(32)]
            stars = 0
            # tier_roll_count, tier_stars already initialized globally
            count = 0
            # rarest, name, index already initialized globally
            # highest_combo_quantity, highest_combo_tier already initialized globally
            # last_tier, combo_quantity already initialized globally
        else:
            lines = data.strip().split("\n")
            tier_data = list(map(int, lines[0].split(",")))
            stars = int(lines[1])
            
            # Load extended data if available (backward compatible)
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
                state_parts = lines[9].split(",")
                last_tier = int(state_parts[0])
                combo_quantity = int(state_parts[1])
            else:
                # Old format - initialize defaults
                count = 0
        
        # Pre-simulation phase
        if simulate and simulate_count > 0:
            print(f"\n=== Starting simulation of {simulate_count} rolls ===")
            num_cores = multiprocessing.cpu_count()
            print(f"Using {num_cores} CPU cores for parallel simulation")
            sim_start = time.time()
            
            # Split work across cores
            rolls_per_worker = simulate_count // num_cores
            remaining_rolls = simulate_count % num_cores
            
            # Create progress queue and manager
            manager = multiprocessing.Manager()
            progress_queue = manager.Queue()
            
            # Create worker pool
            with multiprocessing.Pool(processes=num_cores) as pool:
                # Launch workers
                worker_args = []
                current_offset = 0
                for worker_id in range(num_cores):
                    num_rolls = rolls_per_worker + (1 if worker_id < remaining_rolls else 0)
                    worker_args.append((worker_id, num_rolls, tier_thresholds, tier_weights, 
                                       quantity_thresholds, quantity_weights, progress_queue, current_offset))
                    current_offset += num_rolls
                
                # Start async workers
                print("Launching workers...")
                results_async = pool.starmap_async(simulate_worker, worker_args)
                
                # Monitor progress
                total_progress = 0
                progress_interval = max(1, simulate_count // 1000)
                while not results_async.ready():
                    try:
                        progress_queue.get(timeout=0.1)
                        total_progress += rolls_per_worker // 10
                        if total_progress % progress_interval < (rolls_per_worker // 10):
                            print(f"Simulation progress: ~{total_progress}/{simulate_count} rolls (~{total_progress*100//simulate_count}%)")
                    except:
                        pass
                
                # Get results
                results = results_async.get()
            
            # Aggregate results from all workers
            print("Aggregating results from workers...")
            all_roll_logs = []
            for result in results:
                for i in range(32):
                    tier_data[i] += result['tier_data'][i]
                    tier_stars[i] += result['tier_stars'][i]
                    tier_roll_count[i] += result['tier_roll_count'][i]
                
                stars += result['stars']
                
                # Collect roll logs from this worker
                all_roll_logs.extend(result['roll_logs'])
                
                # Track global rarest
                if result['rarest'] < rarest:
                    rarest = result['rarest']
                    name = result['name']
                    index = count + result['index']
                
                # Track global highest combo
                if result['highest_combo_quantity'] > highest_combo_quantity:
                    highest_combo_quantity = result['highest_combo_quantity']
                    highest_combo_tier = result['highest_combo_tier']
            
            count = simulate_count

            
            sim_time = time.time() - sim_start
            print(f"=== Simulation complete in {format_time(sim_time)} ===")
            print(f"Total stars: {format_number(stars)} ★")
            print(f"Rarest roll: {name} | R%: {format_chance(rarest)}% (1/{format_rarity(rarest)})")

            stars = round(stars, 2)
            
            # Write all roll logs and summary to rollbotsimlog.txt
            print("Writing simulation logs...")
            with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotsimlog.txt", "w") as simlog:
                # Write individual roll logs
                for log_entry in all_roll_logs:
                    simlog.write(log_entry + "\n")
                
                # Write summary statistics
                simlog.write(f"\n=== Simulation Results ===\n")
                simlog.write(f"{count} rolls | {stars} ★ | Uptime: {format_time(sim_time)}\n")
                simlog.write(f"Rarest so far: {name} | R%: {format_chance(rarest)}% (1/{format_rarity(rarest)})\n")
                simlog.write(f"Rarest roll ({index + 1}/{count}) gained {round(round(3.5 ** (int(name.split('× T')[1])), 3)*int(name.split('× T')[0]) - 2.5, 2)} ★\n")
                simlog.write(f"Highest combo: {highest_combo_quantity} × T{highest_combo_tier} | Current: {combo_quantity} × T{last_tier}\n")
                simlog.write(f"\n=== Tier Breakdown after {count} rolls ===\n")
                
                # Find highest tier with any data
                max_tier = 0
                for tier_idx in range(31, -1, -1):  # Search backwards
                    if tier_roll_count[tier_idx] > 0 or tier_data[tier_idx] > 0:
                        max_tier = tier_idx + 1
                        break
                
                for tier_idx in range(max_tier):  # Show all tiers up to max
                    tier_num = tier_idx + 1
                    tier_star_total = tier_stars[tier_idx]
                    tier_rolls = tier_roll_count[tier_idx]
                    
                    # Calculate percentage of total stars
                    if stars > 0:
                        percentage = (tier_star_total / stars) * 100
                    else:
                        percentage = 0
                    
                    # Show all tiers (including 0 rolls) up to max tier
                    simlog.write(f"T{tier_num}: {format_number(tier_star_total)} ★ ({percentage:.4f}%) | {tier_rolls} rolls\n")
            
            # Show detailed statistics after simulation (console)
            print(f"\n--- Simulation Statistics ---")
            print(f"{count} rolls | {stars} ★ | Uptime: {format_time(sim_time)}")
            print(f"Rarest so far: {name} | R%: {format_chance(rarest)}% (1/{format_rarity(rarest)})")
            print(f"Rarest roll ({index + 1}/{count}) gained {round(round(3.5 ** (int(name.split('× T')[1])), 3)*int(name.split('× T')[0]) - 2.5, 2)} ★")
            print(f"Highest combo: {highest_combo_quantity} × T{highest_combo_tier} | Current: {combo_quantity} × T{last_tier}")
            
            # Show tier breakdown after simulation (console)
            print(f"\n=== Tier Breakdown after {count} rolls ===")
            # Find highest tier with any data (already calculated above, reuse max_tier)
            
            for tier_idx in range(max_tier):  # Show all tiers up to max
                tier_num = tier_idx + 1
                tier_star_total = tier_stars[tier_idx]
                tier_rolls = tier_roll_count[tier_idx]
                
                # Calculate percentage of total stars
                if stars > 0:
                    percentage = (tier_star_total / stars) * 100
                else:
                    percentage = 0
                
                # Show all tiers (including 0 rolls) up to max tier
                print(f"T{tier_num}: {format_number(tier_star_total)} ★ ({percentage:.4f}%) | {tier_rolls} rolls")
            
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
            type2(f"Rarest so far: {name} | R%: {format_chance(rarest)}% (1/{format_rarity(rarest)})")
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
            
            for tier_idx in range(max_tier):  # Show all tiers up to max
                tier_num = tier_idx + 1
                tier_star_total = tier_stars[tier_idx]
                tier_rolls = tier_roll_count[tier_idx]
                
                # Calculate percentage of total stars
                if stars > 0:
                    percentage = (tier_star_total / stars) * 100
                else:
                    percentage = 0
                
                # Show all tiers (including 0 rolls) up to max tier
                c.tap(Key.enter)
                time.sleep(0.1)
                type2(f"T{tier_num}: {round(tier_star_total, 2)} ★ ({percentage:.4f}%) | {tier_rolls} rolls")
                time.sleep(0.1)
                c.tap(Key.enter)
                time.sleep(2.5)
            
            # Save simulation results to file
            print("Saving simulation results...")
            with open("/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/rollbotsave.txt", "w") as save_file:
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
            print("✅ Simulation data saved")
            
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
            chance = tier_prob * quantity_prob * 100  # Keep full precision
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
            
            # Format rarity - use scientific notation for very small chances
            rarity_value = 100 / chance if chance > 0 else float('inf')
            if chance < 0.0001:
                # For very rare rolls (< 0.0001%), only show "1 in X" format
                info = f"{combo_display} | R%: 1 in {format_rarity(chance)} | {round(gained, 2)} ★{bonus_display}"
            else:
                info = f"{combo_display} | R%: {format_chance(chance)}% (1 in {format_rarity(chance)}) | {round(gained, 2)} ★{bonus_display}"
            
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
                    save_file.write(",".join(map(str, tier_roll_count)) + "\n")
                    save_file.write(",".join(map(str, tier_stars)) + "\n")
                    save_file.write(f"{count}\n")
                    save_file.write(f"{rarest}\n")
                    save_file.write(f"{name}\n")
                    save_file.write(f"{index}\n")
                    save_file.write(f"{highest_combo_quantity},{highest_combo_tier}\n")
                    save_file.write(f"{last_tier},{combo_quantity}\n")
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
                type2(f"Rarest so far: {name} | R%: {format_chance(rarest)}% (1/{format_rarity(rarest)})")
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