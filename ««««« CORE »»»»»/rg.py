import time
import random
import tkinter as tk
from pynput. keyboard import Listener
from PIL import Image, ImageTk
import threading
import os
import glob
import signal
import sys

# Disable pygame/audio support
AUDIO_AVAILABLE = False

# Ignore SIGTRAP to avoid trace trap errors
signal.signal(signal.SIGTRAP, signal.SIG_IGN)

CHART_DIRECTORY = "/Users/alexoh/Documents/GitHub/arrastools/««««« CORE »»»»»/charts"
1
# Initialize Tkinter window
root = tk.Tk()
root.title("Rhythm Game")
root.attributes('-fullscreen', True)
root.configure(bg='black')

width = root.winfo_screenwidth()
height = root.winfo_screenheight()

# Create canvas for drawing
canvas = tk.Canvas(root, width=width, height=height, bg='black', highlightthickness=0)
canvas.pack()

# Constants
BAR_Y = int(0.9 * height)
NOTE_SIZE = 80
NOTE_WIDTH = 120
NOTE_HEIGHT = 30
LANE_COUNT = 8
LANE_WIDTH = width // 10  # Each lane is 1/10 of screen width (8 lanes total)
LANE_MARGIN = (width - (LANE_WIDTH * LANE_COUNT)) // 2  # Center the lanes

# Hit timing windows (in seconds)
TIMING_PERFECT = 0.05
TIMING_GREAT = 0.10
TIMING_GOOD = 0.15
TIMING_BAD = 0.20
TIMING_MISS = 0.25

# Scoring
SCORE_PERFECT = 1000
SCORE_GREAT = 700
SCORE_GOOD = 400
SCORE_BAD = 100
SCORE_MISS = 0

# Ranking thresholds (percentage of max possible score)
RANK_S = 0.90  # 95%+
RANK_A = 0.90  # 90-95%
RANK_B = 0.80  # 80-90%
RANK_C = 0.70  # 70-80%
# Below 70% = D

# Load hit sprites (optional, we'll use bars instead)
hit_sprite_images = [None, None, None, None]
slide_sprite_images = [None, None, None, None]

# Game state
chart = []
bpm_changes = []  # List of (beat, bpm) tuples
initial_bpm = 60
fps = 60
active_notes = []
active_slides = []
key_pressed_flags = {0: False, 1: False, 2: False, 3: False, 4: False, 5: False, 6: False, 7: False}
key_is_down = {0: False, 1: False, 2: False, 3: False, 4: False, 5: False, 6: False, 7: False}
judgment_display = None  # (text, end_time)
score = 0
max_possible_score = 0  # Track theoretical maximum score
combo = 0
max_combo = 0
perfect_count = 0
great_count = 0
good_count = 0
bad_count = 0
miss_count = 0
game_running = False
start_time = 0
replay_data = []  # List of (timestamp, event_type, lane) tuples
is_replay = False  # Whether currently playing a replay
replay_index = 0  # Current position in replay
current_chart_id = None
current_difficulty = None
music_playing = False

# Key mappings
KEY_MAPPINGS = {
    'q': 0,
    'w': 1,
    'e': 2,
    'r': 3,
    'u': 4,
    'i': 5,
    'o': 6,
    'p': 7,
}

# Arrow key support
from pynput.keyboard import Key
ARROW_MAPPINGS = {
    Key.left: 0,
    Key.down: 1,
    Key.up: 2,
    Key.right: 3,
}

def beats_to_seconds(beat, bpm_changes_list, initial_bpm):
    """Convert beat position to seconds"""
    if not bpm_changes_list:
        # No BPM changes, simple calculation
        return (beat / initial_bpm) * 60.0
    
    current_time = 0.0
    current_beat = 0.0
    current_bpm = initial_bpm
    
    for change_beat, new_bpm in sorted(bpm_changes_list):
        if beat <= change_beat:
            # Target beat is before this BPM change
            beats_elapsed = beat - current_beat
            current_time += (beats_elapsed / current_bpm) * 60.0
            return current_time
        else: 
            # Add time up to this BPM change
            beats_elapsed = change_beat - current_beat
            current_time += (beats_elapsed / current_bpm) * 60.0
            current_beat = change_beat
            current_bpm = new_bpm
    
    # If we're past all BPM changes
    beats_elapsed = beat - current_beat
    current_time += (beats_elapsed / current_bpm) * 60.0
    return current_time

def get_current_bpm(beat, bpm_changes_list, initial_bpm):
    """Get the BPM at a specific beat"""
    current_bpm = initial_bpm
    for change_beat, new_bpm in sorted(bpm_changes_list):
        if beat >= change_beat:
            current_bpm = new_bpm
        else:
            break
    return current_bpm

def seconds_to_beats(seconds, bpm_changes_list, initial_bpm):
    """Convert seconds to beat position (approximate)"""
    if not bpm_changes_list:
        return (seconds * initial_bpm) / 60.0
    
    current_beat = 0.0
    current_time = 0.0
    current_bpm = initial_bpm
    
    for change_beat, new_bpm in sorted(bpm_changes_list):
        change_time = beats_to_seconds(change_beat, bpm_changes_list, initial_bpm)
        if seconds <= change_time:
            time_elapsed = seconds - current_time
            current_beat += (time_elapsed * current_bpm) / 60.0
            return current_beat
        else:
            current_time = change_time
            current_beat = change_beat
            current_bpm = new_bpm
    
    # If we're past all BPM changes
    time_elapsed = seconds - current_time
    current_beat += (time_elapsed * current_bpm) / 60.0
    return current_beat

def calculate_max_score():
    """Calculate the maximum possible score from the chart"""
    global max_possible_score
    max_possible_score = 0
    
    for note in chart:
        if note['type'] == 'tap':
            multiplier = note. get('multiplier', 1)
            max_possible_score += SCORE_PERFECT * multiplier
        elif note['type'] == 'slide':
            multiplier = note.get('multiplier', 1)
            # Score for start
            max_possible_score += SCORE_PERFECT * multiplier
            # Score for each beat held
            beat_duration = note['end_beat'] - note['beat']
            max_possible_score += (SCORE_PERFECT * 0.1 * beat_duration) * multiplier
            # Score for release
            max_possible_score += SCORE_PERFECT * multiplier

def load_chart(id, difficulty):
    global chart, bpm_changes, initial_bpm
    with open(f"{CHART_DIRECTORY}/{id}_{difficulty}.txt", "r") as f:
        f.seek(0)
        lines = f.readlines()
        chart = []
        bpm_changes = []
        initial_bpm = float(id.split("_")[1])
        
        slide_starts = {}  # Track slide start positions by lane:  {lane:  (beat, multiplier)}
        last_beat = 0  # Track last beat for BPM changes
        
        for line in lines:
            if '%' not in line:
                continue
            
            parts = line.split("%")
            
            # Check for BPM change first (format: bpm%{new_bpm})
            if parts[0].strip() == "bpm":
                try:
                    new_bpm = float(parts[1].strip())
                    # BPM changes at the last processed beat
                    bpm_changes.append((last_beat, new_bpm))
                    continue
                except:
                    pass
            
            beat = float(parts[0])
            last_beat = beat  # Update last beat
            note_data = parts[1] if len(parts) > 1 else ""
            
            # Check for BPM change at specific beat (format: {beat}%bpm{new_bpm})
            if note_data.strip().startswith("bpm"):
                # Format: {beat}%bpm{new_bpm}
                try:
                    new_bpm = float(note_data.strip().replace("bpm", "").strip())
                    bpm_changes.append((beat, new_bpm))
                    continue
                except: 
                    pass
            
            char_index = 0
            for char in note_data:
                lane = char_index % LANE_COUNT
                
                if char == "X":
                    # Regular tap note
                    note_time = beats_to_seconds(beat, bpm_changes, initial_bpm)
                    chart.append({
                        'time': note_time,
                        'beat': beat,
                        'lane': lane,
                        'type': 'tap',
                        'multiplier': 1,
                        'id': f"tap_{beat}_{lane}_{random.randint(1000, 9999)}"
                    })
                
                elif char == "x":
                    # Double score tap note
                    note_time = beats_to_seconds(beat, bpm_changes, initial_bpm)
                    chart.append({
                        'time': note_time,
                        'beat':  beat,
                        'lane':  lane,
                        'type':  'tap',
                        'multiplier': 2,
                        'id': f"tap_{beat}_{lane}_{random. randint(1000, 9999)}"
                    })
                
                elif char == "s":
                    # Slide start
                    if lane in slide_starts:
                        print(f"Warning: Overlapping slide starts in lane {lane} at beat {beat}")
                    slide_starts[lane] = (beat, 1)  # Normal slide
                
                elif char == "S":
                    # Double score slide start (uppercase S)
                    if lane in slide_starts:
                        print(f"Warning: Overlapping slide starts in lane {lane} at beat {beat}")
                    slide_starts[lane] = (beat, 2)  # Double score slide
                
                elif char == "e":
                    # Slide end
                    if lane in slide_starts:
                        start_beat, multiplier = slide_starts[lane]
                        end_beat = beat
                        start_time = beats_to_seconds(start_beat, bpm_changes, initial_bpm)
                        end_time = beats_to_seconds(end_beat, bpm_changes, initial_bpm)
                        
                        chart.append({
                            'time': start_time,
                            'end_time': end_time,
                            'beat': start_beat,
                            'end_beat': end_beat,
                            'lane': lane,
                            'type': 'slide',
                            'multiplier':  multiplier,
                            'id': f"slide_{start_beat}_{lane}_{random.randint(1000, 9999)}"
                        })
                        del slide_starts[lane]
                    else:
                        print(f"Warning: Slide end without start in lane {lane} at beat {beat}")
                
                char_index += 1
        
        # Warn about unclosed slides
        for lane, (start_beat, _) in slide_starts.items():
            print(f"Warning: Slide start without end in lane {lane} at beat {start_beat}")
        
        f.close()
        chart. sort(key=lambda x: x['time'])
        bpm_changes.sort(key=lambda x: x[0])
        
        # Calculate max possible score
        calculate_max_score()

def draw_lane_separators():
    """Draw vertical lines separating lanes"""
    for i in range(LANE_COUNT + 1):
        x = LANE_MARGIN + i * LANE_WIDTH
        canvas.create_line(x, 0, x, height, fill='gray', width=2, tags='separator')

def draw_hit_bar():
    """Draw the horizontal bar where notes should be hit"""
    bar_start = LANE_MARGIN
    bar_end = LANE_MARGIN + (LANE_WIDTH * LANE_COUNT)
    canvas.create_rectangle(bar_start, BAR_Y - 5, bar_end, BAR_Y + 5,
                          fill='white', outline='yellow', width=3, tags='hitbar')
    
    # Draw lane indicators at the hit bar
    colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'blue', 'purple', 'magenta']
    for i in range(LANE_COUNT):
        x = LANE_MARGIN + i * LANE_WIDTH + LANE_WIDTH // 2
        canvas.create_rectangle(x - 40, BAR_Y - 10, x + 40, BAR_Y + 10,
                              outline=colors[i], width=3, tags='hitbar')

def draw_key_labels():
    """Draw key labels at top of lanes (updates with key presses)"""
    canvas.delete('keylabel')
    colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'blue', 'purple', 'magenta']
    key_labels = ['W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O']
    for i in range(LANE_COUNT):
        x = LANE_MARGIN + i * LANE_WIDTH + LANE_WIDTH // 2
        # Dim the label if key is pressed
        if key_is_down.get(i, False):
            canvas.create_text(x, 30, text=key_labels[i],
                              fill='#404040', font=('Arial', 36, 'bold'), tags='keylabel')
        else:
            canvas.create_text(x, 30, text=key_labels[i],
                              fill=colors[i], font=('Arial', 36, 'bold'), tags='keylabel')

def draw_note(lane, y_pos, note_id, multiplier=1, simultaneous_lanes=None):
    """Draw a tap note as a white/gold bar"""
    x = LANE_MARGIN + lane * LANE_WIDTH + LANE_WIDTH // 2
    
    # Gold for double score, white for normal
    color = '#FFD700' if multiplier == 2 else 'white'
    outline_color = '#FFA500' if multiplier == 2 else '#CCCCCC'
    
    # Draw gray bars connecting simultaneous notes
    if simultaneous_lanes:
        for other_lane in simultaneous_lanes:
            if other_lane != lane:
                other_x = LANE_MARGIN + other_lane * LANE_WIDTH + LANE_WIDTH // 2
                # Draw thin gray connecting bar
                canvas.create_line(x, y_pos, other_x, y_pos,
                                 fill='gray', width=2, tags=f'note_{note_id}')
    
    # Draw as a horizontal bar
    canvas.create_rectangle(x - NOTE_WIDTH//2, y_pos - NOTE_HEIGHT//2,
                          x + NOTE_WIDTH//2, y_pos + NOTE_HEIGHT//2,
                          fill=color, outline=outline_color, width=3, tags=f'note_{note_id}')

def draw_slide(lane, y_start, y_end, note_id, is_holding=False, multiplier=1):
    """Draw a slide note as a green/gold bar with translucent hold area"""
    x = LANE_MARGIN + lane * LANE_WIDTH + LANE_WIDTH // 2
    
    # Gold for double score, green for normal
    if multiplier == 2:
        bar_color = '#FFD700'
        hold_rgb = (255, 230, 128)  # Light gold with 50% opacity
        outline_color = '#FFA500'
    else: 
        bar_color = '#00FF00' if not is_holding else '#00DD00'
        hold_rgb = (144, 238, 144)  # Light green with 50% opacity
        outline_color = '#00CC00'
    
    # Draw the translucent hold area (entire slide length) with true 50% opacity
    rect_width = NOTE_WIDTH
    if y_end < y_start:
        rect_height = int(y_start - y_end)
        rect_y = int(y_end)
    else:
        rect_height = int(y_end - y_start)
        rect_y = int(y_start)
    
    if rect_height > 0 and rect_width > 0:
        # Create semi-transparent image
        img = Image.new('RGBA', (rect_width, rect_height), (*hold_rgb, 128))  # 128 = 50% opacity
        photo = ImageTk.PhotoImage(img)
        canvas.create_image(x, rect_y + rect_height // 2, image=photo, tags=f'note_{note_id}')
        # Keep reference to prevent garbage collection
        if not hasattr(canvas, '_slide_images'):
            canvas._slide_images = {}
        canvas._slide_images[note_id] = photo
    
    # Draw start marker (thick bar) - ONLY if not being held
    if not is_holding:
        canvas.create_rectangle(x - NOTE_WIDTH//2, y_start - NOTE_HEIGHT//2,
                              x + NOTE_WIDTH//2, y_start + NOTE_HEIGHT//2,
                              fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}')
    
    # Draw end marker (thick bar)
    canvas.create_rectangle(x - NOTE_WIDTH//2, y_end - NOTE_HEIGHT//2,
                          x + NOTE_WIDTH//2, y_end + NOTE_HEIGHT//2,
                          fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}')

def show_judgment(judgment, offset_ms=None, auto_miss=False):
    """Display judgment text for 400ms with optional offset"""
    global judgment_display
    
    colors = {
        'PERFECT': 'cyan',
        'GREAT': 'lime',
        'GOOD': 'yellow',
        'BAD': 'orange',
        'MISS': 'red'
    }
    
    # Add offset display
    display_text = judgment
    if judgment == 'MISS' and auto_miss:
        display_text = "MISS (N/A)"
    elif offset_ms is not None:
        display_text = f"{judgment} ({offset_ms:+.0f}ms)"
    
    end_time = time.time() + 0.4  # 400ms
    judgment_display = (display_text, end_time, colors.get(judgment, 'white'))

def judge_timing(time_diff):
    """Return judgment, score, and offset in ms based on timing difference"""
    global perfect_count, great_count, good_count, bad_count, miss_count
    
    abs_diff = abs(time_diff)
    offset_ms = time_diff * 1000  # Convert to ms
    
    if abs_diff <= TIMING_PERFECT:
        perfect_count += 1
        return 'PERFECT', SCORE_PERFECT, offset_ms
    elif abs_diff <= TIMING_GREAT:
        great_count += 1
        return 'GREAT', SCORE_GREAT, offset_ms
    elif abs_diff <= TIMING_GOOD: 
        good_count += 1
        return 'GOOD', SCORE_GOOD, offset_ms
    elif abs_diff <= TIMING_BAD:
        bad_count += 1
        return 'BAD', SCORE_BAD, offset_ms
    else:
        miss_count += 1
        return 'MISS', SCORE_MISS, offset_ms

def check_hit(lane, current_time):
    """Check if a note was hit in the lane"""
    global score, combo, max_combo, active_notes, active_slides
    
    hit = False
    best_note = None
    best_diff = float('inf')
    
    # Check tap notes
    for note in active_notes[: ]:
        if note['lane'] == lane and note['type'] == 'tap':
            time_diff = current_time - note['time']
            abs_diff = abs(time_diff)
            
            if abs_diff <= TIMING_MISS and abs_diff < best_diff: 
                best_diff = abs_diff
                best_note = note
    
    if best_note:
        judgment, points, offset_ms = judge_timing(best_diff)
        multiplier = best_note. get('multiplier', 1)
        
        if judgment != 'MISS':
            score += points * multiplier
            combo += 1
            max_combo = max(max_combo, combo)
            hit = True
        else:
            combo = 0
        
        # Mark for deletion (will be deleted by main thread)
        best_note['hit'] = True
        best_note['judgment'] = judgment
        show_judgment(judgment, offset_ms)
        return hit
    
    # Check slide notes
    for slide in active_slides[:]:
        if slide['lane'] == lane: 
            # Check if we're at the start of the slide
            if not slide. get('holding', False):
                time_diff = current_time - slide['time']
                abs_diff = abs(time_diff)
                
                if abs_diff <= TIMING_MISS: 
                    judgment, points, offset_ms = judge_timing(abs_diff)
                    multiplier = slide.get('multiplier', 1)
                    
                    if judgment != 'MISS':
                        slide['holding'] = True
                        slide['hit_start'] = True
                        slide['last_beat_combo'] = slide['beat']
                        score += points * multiplier
                        combo += 1
                        max_combo = max(max_combo, combo)
                        show_judgment(judgment, offset_ms)
                        hit = True
                    else: 
                        combo = 0
                        slide['hit'] = True  # Mark for deletion
                        show_judgment('MISS')
    
    return hit

def update_slide_combo(current_time):
    """Update combo for slides being held - +1 per beat, awards 1/10 of perfect score OR register miss"""
    global combo, max_combo, score, miss_count
    
    for slide in active_slides[:]: 
        # Only process slides that have been started
        if slide.get('hit_start', False):
            # Calculate current beat
            current_beat = seconds_to_beats(current_time, bpm_changes, initial_bpm)
            multiplier = slide.get('multiplier', 1)
            
            # Initialize next_tick on first call
            if 'next_tick' not in slide:
                slide['next_tick'] = slide['beat'] + 1.0
            
            # Check if we've passed the next beat tick
            while current_beat >= slide['next_tick'] and slide['next_tick'] <= slide['end_beat']:
                if slide.get('holding', False):
                    # Award score for holding correctly
                    combo += 1
                    max_combo = max(max_combo, combo)
                    # Award 1/10 of perfect score per beat
                    score += int(SCORE_PERFECT * 0.1 * multiplier)
                    slide['next_tick'] += 1.0
                else:
                    # Register miss for not holding
                    combo = 0
                    miss_count += 1
                    show_judgment('MISS')
                    slide['remove'] = True  # Mark for deletion
                    break  # Stop processing this slide

def check_slide_hold(lane, current_time, is_holding):
    """Check if a slide is being held correctly"""
    global score, combo, max_combo, active_slides, miss_count
    
    for slide in active_slides[: ]:
        if slide['lane'] == lane and slide. get('holding', False):
            if not is_holding:
                # Released the key
                if current_time >= slide['end_time']:
                    # Slide completed successfully! 
                    time_diff = current_time - slide['end_time']
                    judgment, points, offset_ms = judge_timing(time_diff)
                    multiplier = slide.get('multiplier', 1)
                    score += points * multiplier
                    combo += 1
                    max_combo = max(max_combo, combo)
                    slide['remove'] = True  # Mark for removal
                    show_judgment(judgment, offset_ms)
                else:
                    # Released too early
                    combo = 0
                    miss_count += 1
                    slide['remove'] = True  # Mark for removal
                    show_judgment('MISS')

def on_press(key):
    """Handle key press - only register if key wasn't already down"""
    global key_pressed_flags, key_is_down, game_running
    
    print(f"DEBUG on_press: key={key}, game_running={game_running}")
    
    if key == Key. esc:
        game_running = False
        root.quit()
        return False
    
    # Get lane from key
    lane = None
    try:
        if hasattr(key, 'char') and key.char in KEY_MAPPINGS:
            lane = KEY_MAPPINGS[key.char]
    except:
        pass
    
    if lane is None and key in ARROW_MAPPINGS:
        lane = ARROW_MAPPINGS[key]
    
    if lane is not None:
        # Only register as a new press if the key wasn't already down
        if not key_is_down[lane]:
            key_is_down[lane] = True
            key_pressed_flags[lane] = True
            # Record in replay (only if not currently replaying)
            if not is_replay and game_running:
                current_time = time.time() - start_time
                replay_data.append((current_time, 'press', lane))
            check_hit(lane, time.time() - start_time)

def on_release(key):
    """Handle key release"""
    global key_pressed_flags, key_is_down
    
    print(f"DEBUG: Key released: {key}")
    
    # Get lane from key
    lane = None
    try:
        if hasattr(key, 'char') and key.char in KEY_MAPPINGS:
            lane = KEY_MAPPINGS[key.char]
    except:
        pass
    
    if lane is None and key in ARROW_MAPPINGS:
        lane = ARROW_MAPPINGS[key]
    
    if lane is not None:
        key_is_down[lane] = False
        key_pressed_flags[lane] = False
        # Record in replay (only if not currently replaying)
        if not is_replay and game_running:
            current_time = time.time() - start_time
            replay_data.append((current_time, 'release', lane))
        # Check if we released during a slide
        check_slide_hold(lane, time.time() - start_time, False)

def on_tkinter_press(event):
    """Handle tkinter key press events during gameplay"""
    global key_pressed_flags, key_is_down, game_running
    
    print(f"DEBUG tkinter_press: keysym={event.keysym}, char={event.char}, game_running={game_running}")
    
    if event.keysym == 'Escape':
        game_running = False
        return
    
    # Get lane from key
    lane = None
    if event.char and event.char.lower() in KEY_MAPPINGS:
        lane = KEY_MAPPINGS[event.char.lower()]
    
    if lane is not None:
        key_is_down[lane] = True
        if not is_replay and game_running:
            if not key_pressed_flags[lane]:
                key_pressed_flags[lane] = True
                current_time = time.time() - start_time
                replay_data.append((current_time, 'press', lane))
                check_hit(lane, current_time)

def on_tkinter_release(event):
    """Handle tkinter key release events during gameplay"""
    global key_pressed_flags, key_is_down, game_running
    
    print(f"DEBUG tkinter_release: keysym={event.keysym}, char={event.char}")
    
    # Get lane from key
    lane = None
    if event.char and event.char.lower() in KEY_MAPPINGS:
        lane = KEY_MAPPINGS[event.char.lower()]
    
    if lane is not None:
        key_pressed_flags[lane] = False
        key_is_down[lane] = False
        if not is_replay and game_running:
            current_time = time.time() - start_time
            replay_data.append((current_time, 'release', lane))
            check_slide_hold(lane, current_time, False)

def get_rank(score, max_score):
    """Calculate rank based on percentage of max possible score"""
    if max_score == 0:
        return 'D'
    
    percentage = score / max_score
    
    if percentage >= RANK_S:
        return 'S'
    elif percentage >= RANK_A:
        return 'A'
    elif percentage >= RANK_B:
        return 'B'
    elif percentage >= RANK_C: 
        return 'C'
    else:
        return 'D'

def get_rank_color(rank):
    """Get color for rank display"""
    colors = {
        'S': '#FFD700',  # Gold
        'A': '#00FF00',  # Green
        'B': '#00BFFF',  # Blue
        'C': '#FFA500',  # Orange
        'D': '#FF0000'   # Red
    }
    return colors.get(rank, 'white')

def draw_ui():
    """Draw score bar and judgment"""
    canvas.delete('ui')
    draw_key_labels()  # Update key press feedback
    
    # Score at top left
    canvas.create_text(80, 30, text=f"Score: {score}",
                      fill='white', font=('Arial', 24, 'bold'), tags='ui', anchor='w')
    
    # Draw judgment display (centered at top)
    if judgment_display:
        judgment_text, end_time, color = judgment_display
        if time.time() < end_time:
            canvas.create_text(width // 2, 100, text=judgment_text,
                             fill=color, font=('Arial', 48, 'bold'), tags='ui')

def get_pixel_speed(current_beat):
    """Get the current pixel speed based on BPM"""
    current_bpm = get_current_bpm(current_beat, bpm_changes, initial_bpm)
    return current_bpm * 10

def update_notes(current_time):
    """Update note positions and spawn new notes"""
    global active_notes, active_slides, chart, combo
    
    # Calculate current beat for pixel speed
    current_bpm = initial_bpm
    if bpm_changes:
        for change_beat, new_bpm in bpm_changes:
            change_time = beats_to_seconds(change_beat, bpm_changes, initial_bpm)
            if current_time >= change_time: 
                current_bpm = new_bpm
    
    pixel_ps = current_bpm * 10
    
    # Update slide combo (per beat)
    update_slide_combo(current_time)
    
    # Spawn new notes
    while chart and chart[0]['time'] <= current_time + 2:
        note = chart.pop(0)
        if note['type'] == 'tap':
            active_notes.append(note)
        elif note['type'] == 'slide':
            active_slides. append(note)
    
    # Update and draw tap notes
    for note in active_notes[:]:
        # Remove hit notes
        if note.get('hit', False):
            canvas.delete(f"note_{note['id']}")
            active_notes.remove(note)
            continue
            
        y_pos = BAR_Y - ((note['time'] - current_time) * pixel_ps)
        
        if y_pos > height + 100:
            canvas.delete(f"note_{note['id']}")
            active_notes.remove(note)
            combo = 0
            global miss_count
            miss_count += 1
            show_judgment('MISS', auto_miss=True)
        elif 0 <= y_pos <= height:
            canvas.delete(f"note_{note['id']}")
            # Check for simultaneous notes
            simultaneous_lanes = []
            for other_note in active_notes:
                if other_note != note and other_note.get('type') == 'tap':
                    if abs(other_note['time'] - note['time']) < 0.01:  # Within 10ms
                        simultaneous_lanes.append(other_note['lane'])
            draw_note(note['lane'], int(y_pos), note['id'], note. get('multiplier', 1), simultaneous_lanes if simultaneous_lanes else None)
    
    # Update and draw slide notes
    for slide in active_slides[:]:
        # Remove marked slides
        if slide.get('remove', False):
            canvas.delete(f"note_{slide['id']}")
            # Clean up image reference
            if hasattr(canvas, '_slide_images') and slide['id'] in canvas._slide_images:
                del canvas._slide_images[slide['id']]
            active_slides.remove(slide)
            continue
        
        # Calculate pixel speed based on slide's BPM
        slide_bpm = get_current_bpm(slide['beat'], bpm_changes, initial_bpm)
        pixel_ps = slide_bpm * 10
            
        # If slide is being held, lock the start position to the hit bar
        if slide.get('holding', False):
            y_start = int(BAR_Y)
            y_end = BAR_Y - ((slide['end_time'] - current_time) * pixel_ps)
        else:
            y_start = BAR_Y - ((slide['time'] - current_time) * pixel_ps)
            y_end = BAR_Y - ((slide['end_time'] - current_time) * pixel_ps)
        
        # Check if slide is complete
        if slide.get('holding', False) and current_time >= slide['end_time']:
            # Auto-complete if still holding at the end
            if key_is_down[slide['lane']]: 
                check_slide_hold(slide['lane'], current_time, False)
        
        # Remove unhit slides that scrolled past
        if not slide.get('holding', False) and not slide.get('hit_start', False) and y_start > height + 100:
            canvas.delete(f"note_{slide['id']}")
            if hasattr(canvas, '_slide_images') and slide['id'] in canvas._slide_images:
                del canvas._slide_images[slide['id']]
            active_slides.remove(slide)
            combo = 0
            miss_count += 1
            show_judgment('MISS', auto_miss=True)
            continue
        
        # Always redraw if holding, OR if any part is visible on screen
        if slide.get('holding', False) or (0 <= y_start <= height or 0 <= y_end <= height):
            canvas.delete(f"note_{slide['id']}")
            if hasattr(canvas, '_slide_images') and slide['id'] in canvas._slide_images:
                del canvas._slide_images[slide['id']]
            draw_slide(slide['lane'], int(y_start), int(y_end), slide['id'],
                      slide.get('holding', False), slide.get('multiplier', 1))

def show_countdown():
    """Display 3-2-1 countdown before game starts"""
    canvas.delete('all')
    canvas.configure(bg='black')
    
    # Draw static elements during countdown
    draw_lane_separators()
    draw_hit_bar()
    draw_key_labels()
    
    for count in [3, 2, 1]:
        canvas.delete('countdown')
        canvas.create_text(width // 2, height // 2, text=str(count),
                         fill='white', font=('Arial', 120, 'bold'), tags='countdown')
        root.update()
        time.sleep(1.0)
    
    canvas.delete('countdown')
    root.update()

def game_loop():
    """Main game loop"""
    global start_time, game_running, chart, music_playing
    
    # Show countdown
    show_countdown()
    
    # Start music if available
    if AUDIO_AVAILABLE and current_chart_id and current_difficulty:
        music_file = f"{CHART_DIRECTORY}/{current_chart_id}_{current_difficulty}.mp3"
        if os.path.exists(music_file):
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(music_file)
                pygame.mixer.music.play()
                music_playing = True
            except Exception as e:
                print(f"Could not play music: {e}")
    
    frame_dur = 1 / fps
    start_time = time.time()
    game_running = True
    
    # Draw static elements
    draw_lane_separators()
    draw_hit_bar()
    draw_key_labels()  # Initial key labels
    
    # Continue while there are notes/slides to process OR slides being held
    while game_running and (chart or active_notes or active_slides):
        frame_start = time.time()
        current_time = frame_start - start_time
        
        # Clear dynamic elements
        canvas.delete('note')
        
        # Update game state
        update_notes(current_time)
        draw_ui()
        
        # Maintain frame rate
        elapsed = time.time() - frame_start
        sleep_time = max(0, frame_dur - elapsed)
        time.sleep(sleep_time)
        
        root.update()
    
    # Delay after last note
    time.sleep(0.5)
    
    # Calculate rank
    rank = get_rank(score, max_possible_score)
    rank_color = get_rank_color(rank)
    percentage = (score / max_possible_score * 100) if max_possible_score > 0 else 0
    
    # Stop music
    if AUDIO_AVAILABLE and music_playing:
        pygame.mixer.music.stop()
    
    # Achievement display
    achievements = []
    all_perfect = perfect_count == (perfect_count + great_count + good_count + bad_count + miss_count) and perfect_count > 0
    
    if all_perfect:
        achievements.append(("ALL PERFECT!", "#00FFFF", 72))
    else:
        # Only show these if not all perfect
        if miss_count == 0 and (perfect_count + great_count + good_count + bad_count) > 0:
            achievements.append(("FULL COMBO!", "#FFD700", 60))
        if (perfect_count + great_count + good_count + bad_count + miss_count) > 0:
            achievements.append(("CHART CLEAR", "#00FF00", 48))
    
    # Show achievements
    if achievements:
        canvas.delete('all')
        canvas.configure(bg='black')
        
        for i, (text, color, size) in enumerate(achievements):
            y_pos = height // 2 - 100 + (i * 100)
            canvas.create_text(width // 2, y_pos, text=text,
                             fill=color, font=('Arial', size, 'bold'))
        
        root.update()
        time.sleep(2.0)  # Display for 2 seconds
    
    # Game over screen
    canvas.delete('all')
    canvas.configure(bg='black')
    
    # Display rank (huge!)
    canvas.create_text(width // 2, height // 2 - 150,
                      text=rank,
                      fill=rank_color, font=('Arial', 200, 'bold'))
    
    # Display score and stats
    canvas.create_text(width // 2, height // 2 + 50,
                      text=f"Score: {score: ,} / {max_possible_score:,}",
                      fill='white', font=('Arial', 32, 'bold'))
    
    canvas.create_text(width // 2, height // 2 + 100,
                      text=f"Accuracy: {percentage:.2f}%",
                      fill='white', font=('Arial', 28))
    
    canvas.create_text(width // 2, height // 2 + 140,
                      text=f"Max Combo: {max_combo}",
                      fill='yellow', font=('Arial', 24))
    
    # Display judgment breakdown
    y_start = height // 2 + 190
    canvas.create_text(width // 2, y_start,
                      text=f"Perfect: {perfect_count}  |  Great: {great_count}  |  Good: {good_count}  |  Bad:  {bad_count}  |  Miss: {miss_count}",
                      fill='white', font=('Arial', 20))
    
    canvas.create_text(width // 2, height - 100,
                      text="Press R to replay  |  Press M to menu  |  Press ESC to exit",
                      fill='gray', font=('Arial', 20))
    
    root.update()
    
    # Wait for user input using tkinter bindings
    waiting = [True]  # Use list to allow modification in nested function
    action = [None]  # 'replay', 'menu', or None
    
    def on_end_tkinter_key(event):
        if event.keysym == 'Escape':
            waiting[0] = False
            action[0] = 'exit'
        elif event.char and event.char.lower() == 'r':
            waiting[0] = False
            action[0] = 'replay'
        elif event.char and event.char.lower() == 'm':
            waiting[0] = False
            action[0] = 'menu'
    
    root.bind('<KeyPress>', on_end_tkinter_key)
    
    while waiting[0]:
        root.update()
        time.sleep(0.01)
    
    root.unbind('<KeyPress>')
    
    # Execute the action
    if action[0] == 'replay':
        play_replay()
    elif action[0] == 'exit':
        root.quit()

def play_replay():
    """Play back the recorded replay"""
    global is_replay, replay_index, game_running, start_time
    global score, combo, max_combo, perfect_count, great_count, good_count, bad_count, miss_count
    global active_notes, active_slides, chart, key_is_down, key_pressed_flags
    
    # Reset game state
    is_replay = True
    replay_index = 0
    score = 0
    combo = 0
    max_combo = 0
    perfect_count = 0
    great_count = 0
    good_count = 0
    bad_count = 0
    miss_count = 0
    active_notes = []
    active_slides = []
    key_is_down = {0: False, 1: False, 2: False, 3: False}
    key_pressed_flags = {0: False, 1: False, 2: False, 3: False}
    
    # Reload chart
    load_chart(current_chart_id, current_difficulty)
    
    # Start replay game loop
    frame_dur = 1 / fps
    start_time = time.time()
    game_running = True
    
    canvas.delete('all')
    canvas.configure(bg='black')
    
    # Draw static elements
    draw_lane_separators()
    draw_hit_bar()
    draw_key_labels()
    
    while game_running and (chart or active_notes or active_slides):
        frame_start = time.time()
        current_time = frame_start - start_time
        
        # Process replay events
        while replay_index < len(replay_data) and replay_data[replay_index][0] <= current_time:
            event_time, event_type, lane = replay_data[replay_index]
            
            if event_type == 'press':
                key_is_down[lane] = True
                key_pressed_flags[lane] = True
                check_hit(lane, event_time)
            elif event_type == 'release':
                key_is_down[lane] = False
                key_pressed_flags[lane] = False
                check_slide_hold(lane, event_time, False)
            
            replay_index += 1
        
        # Clear dynamic elements
        canvas.delete('note')
        
        # Update game state
        update_notes(current_time)
        draw_ui()
        
        # Add "REPLAY" watermark
        canvas.create_text(width // 2, height - 30, text="REPLAY",
                         fill='#666666', font=('Arial', 24, 'bold'), tags='ui')
        
        # Maintain frame rate
        elapsed = time.time() - frame_start
        sleep_time = frame_dur - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        root.update()
    
    # Show game over screen again
    is_replay = False
    game_loop()  # This will show the results screen again

def get_available_charts():
    """Scan directory for available charts"""
    charts = {}
    if not os.path.exists(CHART_DIRECTORY):
        return charts
    
    chart_files = glob.glob(f"{CHART_DIRECTORY}/*.txt")
    for file_path in chart_files:
        filename = os.path.basename(file_path)
        # Parse filename: chartid_difficulty.txt
        if '_' in filename:
            parts = filename.replace('.txt', '').rsplit('_', 1)
            if len(parts) == 2:
                chart_id, difficulty = parts
                if chart_id not in charts:
                    charts[chart_id] = []
                charts[chart_id].append(difficulty)
    
    return charts

def show_chart_menu():
    """Display chart selection menu"""
    global current_chart_id, current_difficulty
    
    selected_chart = None
    selected_difficulty = None
    menu_running = True
    scroll_offset = 0
    refresh_text_alpha = 0  # For fading effect
    refresh_text_time = 0
    
    def refresh_menu():
        nonlocal scroll_offset, refresh_text_alpha, refresh_text_time
        scroll_offset = 0
        refresh_text_alpha = 1.0
        refresh_text_time = time.time()
        draw_menu()
    
    def draw_menu():
        canvas.delete('all')
        canvas.configure(bg='black')
        
        # Title
        canvas.create_text(width // 2, 50, text="SELECT CHART",
                         fill='white', font=('Arial', 48, 'bold'))
        
        # Instructions
        canvas.create_text(width // 2, 120, text="Use number keys to select | R to refresh | ESC to quit",
                         fill='gray', font=('Arial', 16))
        
        # Fading refresh text
        nonlocal refresh_text_alpha, refresh_text_time
        if refresh_text_alpha > 0:
            elapsed = time.time() - refresh_text_time
            refresh_text_alpha = max(0, 1.0 - elapsed / 1.5)  # Fade over 1.5 seconds
            if refresh_text_alpha > 0:
                # Convert alpha to color brightness
                brightness = int(255 * refresh_text_alpha)
                color = f'#{brightness:02x}{brightness:02x}{brightness:02x}'
                canvas.create_text(width // 2, 170, text="Refreshed!",
                                 fill=color, font=('Arial', 20, 'bold'))
        
        charts = get_available_charts()
        if not charts:
            canvas.create_text(width // 2, height // 2,
                             text="No charts found in directory",
                             fill='red', font=('Arial', 24))
            root.update()
            return
        
        # Display charts
        y_pos = 180
        index = 0
        for chart_id in sorted(charts.keys())[scroll_offset:]:
            if y_pos > height - 100:
                break
            
            difficulties = sorted(charts[chart_id])
            diff_text = ", ".join(difficulties)
            
            # Check if audio available
            audio_icon = ""
            for diff in difficulties:
                mp3_file = f"{CHART_DIRECTORY}/{chart_id}_{diff}.mp3"
                if os.path.exists(mp3_file):
                    audio_icon = " ♫"
                    break
            
            text = f"{index + 1}. {chart_id} [{diff_text}]{audio_icon}"
            canvas.create_text(width // 2, y_pos, text=text,
                             fill='cyan', font=('Arial', 20))
            y_pos += 40
            index += 1
        
        root.update()
    
    def on_tkinter_key(event):
        """Handle tkinter key events for menu"""
        nonlocal menu_running, selected_chart, selected_difficulty, scroll_offset
        
        print(f"DEBUG tkinter_key: {event.keysym}, {event.char}")
        
        if event.keysym == 'Escape':
            menu_running = False
            return
        
        if event.char and event.char.lower() == 'r':
            refresh_menu()
            return
        
        # Number key selection
        if event.char and event.char.isdigit():
            num = int(event.char)
            if num > 0:
                charts = get_available_charts()
                chart_list = sorted(charts.keys())[scroll_offset:]
                if num <= len(chart_list):
                    selected_chart = chart_list[num - 1]
                    # Show difficulty selection
                    select_difficulty(selected_chart, charts[selected_chart])

    def select_difficulty(chart_id, difficulties):
        nonlocal menu_running, selected_chart, selected_difficulty
        global current_chart_id, current_difficulty
        
        canvas.delete('all')
        canvas.configure(bg='black')
        
        canvas.create_text(width // 2, 100, text=f"Select Difficulty for {chart_id}",
                         fill='white', font=('Arial', 36, 'bold'))
        
        y_pos = 200
        for i, diff in enumerate(sorted(difficulties)):
            mp3_file = f"{CHART_DIRECTORY}/{chart_id}_{diff}.mp3"
            audio_icon = " ♫" if os.path.exists(mp3_file) else ""
            
            canvas.create_text(width // 2, y_pos, text=f"{i + 1}. {diff}{audio_icon}",
                             fill='yellow', font=('Arial', 24))
            y_pos += 60
        
        canvas.create_text(width // 2, height - 50, text="Press number to select | ESC to go back",
                         fill='gray', font=('Arial', 16))
        root.update()
        
        def on_diff_tkinter_key(event):
            nonlocal selected_difficulty, menu_running
            global current_chart_id, current_difficulty
            
            print(f"DEBUG diff_tkinter_key: {event.keysym}, {event.char}")
            
            if event.keysym == 'Escape':
                root.unbind('<KeyPress>')
                draw_menu()
                root.bind('<KeyPress>', on_tkinter_key)
                return
            
            if event.char.isdigit():
                num = int(event.char)
                if 0 < num <= len(difficulties):
                    selected_difficulty = sorted(difficulties)[num - 1]
                    current_chart_id = chart_id
                    current_difficulty = selected_difficulty
                    menu_running = False
                    root.unbind('<KeyPress>')
                    print(f"DEBUG: Selected chart_id={current_chart_id}, difficulty={current_difficulty}")
        
        # Unbind menu keys and bind difficulty keys
        root.unbind('<KeyPress>')
        root.bind('<KeyPress>', on_diff_tkinter_key)
    
    draw_menu()
    
    # Bind tkinter keys for menu
    print("DEBUG: Binding tkinter keys for menu...")
    root.bind('<KeyPress>', on_tkinter_key)
    
    while menu_running:
        # Redraw if refresh text is fading
        if refresh_text_alpha > 0:
            draw_menu()
        root.update()
        time.sleep(0.01)
    
    # Unbind menu keys
    root.unbind('<KeyPress>')
    print(f"DEBUG: Returning from menu, chart_id={current_chart_id}")
    
    return current_chart_id is not None

def start_game(chart_id, difficulty):
    """Initialize and start the game"""
    global current_chart_id, current_difficulty, replay_data, game_running
    current_chart_id = chart_id
    current_difficulty = difficulty
    replay_data = []  # Clear any previous replay data
    game_running = True  # Enable keyboard input
    
    print(f"DEBUG: Starting game with chart {chart_id}, difficulty {difficulty}")
    print(f"DEBUG: game_running set to {game_running}")
    
    load_chart(chart_id, difficulty)
    
    # Bind arrow keys and number keys for gameplay
    print("DEBUG: Binding tkinter keys for gameplay...")
    root.bind('<KeyPress>', on_tkinter_press)
    root.bind('<KeyRelease>', on_tkinter_release)
    print("DEBUG: Tkinter keys bound")
    
    # Start game loop
    game_loop()
    
    # Unbind keys after game ends
    root.unbind('<KeyPress>')
    root.unbind('<KeyRelease>')

# Example usage
if __name__ == "__main__":
    while True:
        # Show chart selection menu
        if show_chart_menu():
            start_game(current_chart_id, current_difficulty)
        else:
            break  # User pressed ESC to quit