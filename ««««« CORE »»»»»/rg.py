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
import pygame

# Disable pygame/audio support
AUDIO_AVAILABLE = True

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

def get_timing_windows():
    """Get timing windows based on settings"""
    mode = settings.get('timing_windows', 'normal')
    
    if mode == 'strict':
        return {
            'PERFECT': 0.035,
            'GREAT': 0.075,
            'GOOD': 0.115,
            'BAD': 0.155,
            'MISS': 0.20
        }
    elif mode == 'lenient':
        return {
            'PERFECT': 0.065,
            'GREAT': 0.125,
            'GOOD': 0.185,
            'BAD': 0.245,
            'MISS': 0.30
        }
    else:  # normal
        return {
            'PERFECT': 0.05,
            'GREAT': 0.10,
            'GOOD': 0.15,
            'BAD': 0.20,
            'MISS': 0.25
        }

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
speed_changes = []  # List of (beat, speed_multiplier) tuples for spd% option
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

# Game modes
game_mode = 'normal'  # 'normal', 'auto', or 'practice'
practice_speed = 1.0  # Practice mode speed multiplier
practice_loop_start = None  # Practice mode loop start (in seconds)
practice_loop_end = None  # Practice mode loop end (in seconds)
practice_looping = False  # Whether loop is enabled

# Particle system for hit effects
active_particles = []  # List of (x, y, size, color, end_time) tuples

# Settings
settings = {
    'scroll_speed_multiplier': 1.0,  # Global scroll speed multiplier (0.1 to 10)
    'key_bindings': ['q', 'w', 'e', 'r', 'u', 'i', 'o', 'p'],  # Customizable keys
    # Visual settings
    'note_size_multiplier': 1.0,  # Note size multiplier (0.5 to 2.0)
    'hit_bar_position': 0.9,  # Hit bar Y position as fraction of height (0.7 to 0.95)
    'background_dim': 0,  # Background dimness (0 to 255)
    'show_fps': False,  # Show FPS counter
    'show_timing_zones': False,  # Show judgment zones on hit bar
    'colorblind_mode': False,  # Use colorblind-friendly colors
    'high_contrast_mode': False,  # Use high contrast colors
    'show_late_early': True,  # Show LATE/EARLY indicators for perfect and great
    # Audio settings
    'music_volume': 100,  # Music volume (0 to 100)
    'sfx_volume': 100,  # SFX volume (0 to 100)
    'global_offset': 0,  # Global offset in milliseconds (-200 to 200)
    # Gameplay settings
    'timing_windows': 'normal',  # 'strict', 'normal', or 'lenient'
    # Performance settings
    'fps_target': 60,  # Target FPS (1 to 600)
    'renderer': 'auto',  # 'auto', 'tkinter', or 'opengl'
    'show_performance_metrics': False,  # Show detailed performance metrics
}

# Key mappings (will be rebuilt from settings)
KEY_MAPPINGS = {}

def rebuild_key_mappings():
    """Rebuild KEY_MAPPINGS from settings"""
    global KEY_MAPPINGS
    KEY_MAPPINGS = {}
    for i, key in enumerate(settings['key_bindings']):
        KEY_MAPPINGS[key] = i

rebuild_key_mappings()  # Initialize mappings

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

def get_current_speed_multiplier(beat, speed_changes_list):
    """Get the speed multiplier at a specific beat (from spd% option)"""
    speed_mult = 1.0
    for change_beat, new_speed in sorted(speed_changes_list):
        if beat >= change_beat:
            speed_mult = new_speed
        else:
            break
    return speed_mult

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
    global chart, bpm_changes, speed_changes, initial_bpm
    chart_path = f"{CHART_DIRECTORY}/{id}_{difficulty}.txt"
    with open(chart_path, "r") as f:
        lines = f.readlines()

    chart = []
    bpm_changes = []
    speed_changes = []

    is_percent_format = any('%' in line for line in lines)

    if is_percent_format:
        initial_bpm = float(id.split("_")[1])

        # Calculate beat offset for 2-second delay
        # At BPM X: 2 seconds = (2 * X) / 60 beats
        beat_offset = (2.0 * initial_bpm) / 60.0

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
                    # BPM changes at the last processed beat (with offset)
                    bpm_changes.append((last_beat + beat_offset, new_bpm))
                    continue
                except:
                    pass

            # Check for speed change (format: spd%{percentage})
            if parts[0].strip() == "spd":
                try:
                    speed_percent = float(parts[1].strip())
                    # Speed changes at the last processed beat (with offset)
                    speed_changes.append((last_beat + beat_offset, speed_percent / 100.0))
                    continue
                except:
                    pass

            beat = float(parts[0]) + beat_offset  # Add offset for 2-second delay
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

            # Check for speed change at specific beat (format: {beat}%spd{percentage})
            if note_data.strip().startswith("spd"):
                # Format: {beat}%spd{percentage}
                try:
                    speed_percent = float(note_data.strip().replace("spd", "").strip())
                    speed_changes.append((beat, speed_percent / 100.0))
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
                        'beat': beat,
                        'lane': lane,
                        'type': 'tap',
                        'multiplier': 2,
                        'id': f"tap_{beat}_{lane}_{random.randint(1000, 9999)}"
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
                            'multiplier': multiplier,
                            'id': f"slide_{start_beat}_{lane}_{random.randint(1000, 9999)}"
                        })
                        del slide_starts[lane]
                    else:
                        print(f"Warning: Slide end without start in lane {lane} at beat {beat}")

                char_index += 1

        # Warn about unclosed slides
        for lane, (start_beat, _) in slide_starts.items():
            print(f"Warning: Slide start without end in lane {lane} at beat {start_beat}")
    else:
        initial_bpm = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            if line.lower().startswith("bpm="):
                try:
                    initial_bpm = float(line.split("=", 1)[1].strip())
                    break
                except Exception:
                    pass

        if initial_bpm is None:
            try:
                initial_bpm = float(id.split("_")[1])
            except Exception:
                initial_bpm = 60

        beat_offset = (2.0 * initial_bpm) / 60.0

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue

            lower = line.lower()
            if lower.startswith("bpm="):
                continue

            if lower.startswith("bpm_change"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    try:
                        beat = float(parts[1]) + beat_offset
                        new_bpm = float(parts[2])
                        bpm_changes.append((beat, new_bpm))
                    except Exception:
                        pass
                continue

            if lower.startswith("spd"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    try:
                        beat = float(parts[1]) + beat_offset
                        mult = float(parts[2])
                        speed_changes.append((beat, mult))
                    except Exception:
                        pass
                continue

            if lower.startswith("tap"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    try:
                        lane = int(parts[1])
                        beat = float(parts[2]) + beat_offset
                        multiplier = 1
                        if len(parts) >= 4 and parts[3].lower().startswith("x"):
                            try:
                                multiplier = int(parts[3][1:])
                            except Exception:
                                multiplier = 1

                        note_time = beats_to_seconds(beat, bpm_changes, initial_bpm)
                        chart.append({
                            'time': note_time,
                            'beat': beat,
                            'lane': lane,
                            'type': 'tap',
                            'multiplier': multiplier,
                            'id': f"tap_{beat}_{lane}_{random.randint(1000, 9999)}"
                        })
                    except Exception:
                        pass
                continue

            if lower.startswith("slide"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    try:
                        lane = int(parts[1])
                        start_beat = float(parts[2]) + beat_offset
                        end_beat = float(parts[3]) + beat_offset
                        multiplier = 1
                        if len(parts) >= 5 and parts[4].lower().startswith("x"):
                            try:
                                multiplier = int(parts[4][1:])
                            except Exception:
                                multiplier = 1

                        start_time = beats_to_seconds(start_beat, bpm_changes, initial_bpm)
                        end_time = beats_to_seconds(end_beat, bpm_changes, initial_bpm)

                        chart.append({
                            'time': start_time,
                            'end_time': end_time,
                            'beat': start_beat,
                            'end_beat': end_beat,
                            'lane': lane,
                            'type': 'slide',
                            'multiplier': multiplier,
                            'id': f"slide_{start_beat}_{lane}_{random.randint(1000, 9999)}"
                        })
                    except Exception:
                        pass
                continue

    chart.sort(key=lambda x: x['time'])
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
    
    # Draw timing zones if enabled
    if settings.get('show_timing_zones', False):
        windows = get_timing_windows()
        # Calculate pixel heights for each timing window
        # Assuming 600 pixels per second scroll speed as base
        base_speed = 600
        
        # Draw zones (from bottom to top: MISS, BAD, GOOD, GREAT, PERFECT)
        zone_colors = {
            'MISS': '#550000',
            'BAD': '#553300', 
            'GOOD': '#555500',
            'GREAT': '#005500',
            'PERFECT': '#005555'
        }
        
        if settings.get('colorblind_mode', False):
            zone_colors = {
                'MISS': '#330000',
                'BAD': '#440044',
                'GOOD': '#442200',
                'GREAT': '#444400',
                'PERFECT': '#004444'
            }
        
        # Draw zones as semi-transparent overlays
        for zone_name in ['MISS', 'BAD', 'GOOD', 'GREAT', 'PERFECT']:
            zone_height = int(windows[zone_name] * base_speed)
            zone_y_start = BAR_Y - zone_height
            zone_y_end = BAR_Y + zone_height
            
            # Draw behind the hit bar
            canvas.create_rectangle(bar_start, zone_y_start, bar_end, zone_y_end,
                                  fill=zone_colors[zone_name], outline='',
                                  tags='timing_zone', stipple='gray25')
    
    # Draw lane indicators at the hit bar
    colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'blue', 'purple', 'magenta']
    if settings.get('colorblind_mode', False):
        # Colorblind-friendly lane colors
        colors = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7', '#999999']
    
    for i in range(LANE_COUNT):
        x = LANE_MARGIN + i * LANE_WIDTH + LANE_WIDTH // 2
        canvas.create_rectangle(x - 40, BAR_Y - 10, x + 40, BAR_Y + 10,
                              outline=colors[i], width=3, tags='hitbar')

def draw_key_labels():
    """Draw key labels at top of lanes (updates with key presses)"""
    canvas.delete('keylabel')
    colors = ['red', 'orange', 'yellow', 'lime', 'cyan', 'blue', 'purple', 'magenta']
    # Use custom key bindings from settings
    key_labels = [key.upper() for key in settings['key_bindings']]
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
    
    # When not holding, draw from hit bar to end marker
    # When holding, draw from start position (locked at hit bar) to end marker
    if not is_holding:
        # Clamp y_start to not go below hit bar
        display_y_start = min(y_start, BAR_Y)
    else:
        display_y_start = y_start
    
    # Draw the translucent hold area with true 50% opacity
    rect_width = NOTE_WIDTH
    if y_end < display_y_start:
        rect_height = int(display_y_start - y_end)
        rect_y = int(y_end)
    else:
        rect_height = int(y_end - display_y_start)
        rect_y = int(display_y_start)
    
    if rect_height > 0 and rect_width > 0:
        # Create semi-transparent image
        img = Image.new('RGBA', (rect_width, rect_height), (*hold_rgb, 128))  # 128 = 50% opacity
        photo = ImageTk.PhotoImage(img)
        canvas.create_image(x, rect_y + rect_height // 2, image=photo, tags=f'note_{note_id}')
        # Keep reference to prevent garbage collection
        if not hasattr(canvas, '_slide_images'):
            canvas._slide_images = {}
        canvas._slide_images[note_id] = photo
    
    # Draw start marker (thick bar) - ONLY if not being held AND above hit bar
    if not is_holding and y_start < BAR_Y:
        canvas.create_rectangle(x - NOTE_WIDTH//2, y_start - NOTE_HEIGHT//2,
                              x + NOTE_WIDTH//2, y_start + NOTE_HEIGHT//2,
                              fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}')
    
    # If holding, draw a marker at the hit bar
    if is_holding:
        canvas.create_rectangle(x - NOTE_WIDTH//2, int(BAR_Y) - NOTE_HEIGHT//2,
                              x + NOTE_WIDTH//2, int(BAR_Y) + NOTE_HEIGHT//2,
                              fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}')
    
    # Draw end marker (thick bar)
    canvas.create_rectangle(x - NOTE_WIDTH//2, y_end - NOTE_HEIGHT//2,
                          x + NOTE_WIDTH//2, y_end + NOTE_HEIGHT//2,
                          fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}')

def show_judgment(judgment, offset_ms=None, auto_miss=False):
    """Display judgment text for 400ms with optional offset and LATE/EARLY indicators"""
    global judgment_display
    
    # Get colors based on settings
    if settings.get('colorblind_mode', False):
        # Colorblind-friendly colors
        colors = {
            'PERFECT': '#00D9FF',  # Bright cyan
            'GREAT': '#FFD700',    # Gold
            'GOOD': '#FF6B35',     # Orange-red
            'BAD': '#A020F0',      # Purple
            'MISS': '#FF1744'      # Deep red
        }
    elif settings.get('high_contrast_mode', False):
        # High contrast colors
        colors = {
            'PERFECT': 'white',
            'GREAT': 'yellow',
            'GOOD': 'orange',
            'BAD': 'red',
            'MISS': 'red'
        }
    else:
        # Default colors
        colors = {
            'PERFECT': 'cyan',
            'GREAT': 'lime',
            'GOOD': 'yellow',
            'BAD': 'orange',
            'MISS': 'red'
        }
    
    # Add offset display and LATE/EARLY indicators
    display_text = judgment
    if judgment == 'MISS' and auto_miss:
        display_text = "MISS (N/A)"
    elif offset_ms is not None:
        # Add LATE/EARLY indicators for PERFECT and GREAT
        if settings.get('show_late_early', True) and judgment in ['PERFECT', 'GREAT']:
            if offset_ms > 5:  # More than 5ms late
                late_early = " LATE"
            elif offset_ms < -5:  # More than 5ms early
                late_early = " EARLY"
            else:
                late_early = ""
            display_text = f"{judgment}{late_early} ({offset_ms:+.0f}ms)"
        else:
            display_text = f"{judgment} ({offset_ms:+.0f}ms)"
    
    end_time = time.time() + 0.4  # 400ms
    judgment_display = (display_text, end_time, colors.get(judgment, 'white'))

def spawn_particle(lane, judgment):
    """Spawn a hit particle effect at the hit bar in the given lane"""
    global active_particles
    
    colors = {
        'PERFECT': 'cyan',
        'GREAT': 'lime',
        'GOOD': 'yellow',
        'BAD': 'orange',
        'MISS': 'red'
    }
    
    x = LANE_MARGIN + lane * LANE_WIDTH + LANE_WIDTH // 2
    y = BAR_Y
    color = colors.get(judgment, 'white')
    end_time = time.time() + 0.3  # 300ms lifetime
    
    # Create particle as (x, y, initial_size, color, end_time, spawn_time)
    active_particles.append((x, y, 20, color, end_time, time.time()))

def draw_particles():
    """Draw all active particles with expanding/fading animation"""
    current_time = time.time()
    particles_to_remove = []
    
    for i, particle in enumerate(active_particles):
        x, y, initial_size, color, end_time, spawn_time = particle
        
        if current_time >= end_time:
            particles_to_remove.append(i)
            continue
        
        # Calculate animation progress (0.0 to 1.0)
        progress = (current_time - spawn_time) / 0.3
        
        # Expand size over time
        size = int(initial_size + (60 * progress))
        
        # Calculate opacity (fade out)
        opacity = int(255 * (1.0 - progress))
        
        # Draw particle as expanding circle
        # Use stipple pattern to simulate transparency (tkinter limitation)
        stipple_patterns = ['', 'gray75', 'gray50', 'gray25']
        stipple_index = min(int(progress * 4), 3)
        stipple = stipple_patterns[stipple_index]
        
        if stipple:
            canvas.create_oval(x - size, y - size, x + size, y + size,
                             outline=color, width=2, fill='', 
                             stipple=stipple, tags='particle')
        else:
            canvas.create_oval(x - size, y - size, x + size, y + size,
                             outline=color, width=2, fill='',
                             tags='particle')
    
    # Remove expired particles
    for i in reversed(particles_to_remove):
        active_particles.pop(i)

def calculate_accuracy():
    """Calculate current accuracy percentage"""
    total_notes_hit = perfect_count + great_count + good_count + bad_count
    if total_notes_hit == 0:
        return 100.0
    
    # Formula: (perfect*100 + great*70 + good*40 + bad*10) / (total notes hit * 100)
    weighted_score = (perfect_count * 100 + great_count * 70 + 
                     good_count * 40 + bad_count * 10)
    accuracy = weighted_score / (total_notes_hit * 100.0)
    return accuracy * 100.0

def judge_timing(time_diff):
    """Return judgment, score, and offset in ms based on timing difference"""
    global perfect_count, great_count, good_count, bad_count, miss_count
    
    # Get timing windows from settings
    windows = get_timing_windows()
    
    abs_diff = abs(time_diff)
    offset_ms = time_diff * 1000  # Convert to ms
    
    if abs_diff <= windows['PERFECT']:
        perfect_count += 1
        return 'PERFECT', SCORE_PERFECT, offset_ms
    elif abs_diff <= windows['GREAT']:
        great_count += 1
        return 'GREAT', SCORE_GREAT, offset_ms
    elif abs_diff <= windows['GOOD']: 
        good_count += 1
        return 'GOOD', SCORE_GOOD, offset_ms
    elif abs_diff <= windows['BAD']:
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
        spawn_particle(lane, judgment)  # Add particle effect
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
                        spawn_particle(lane, judgment)  # Add particle effect
                        hit = True
                    else: 
                        combo = 0
                        slide['hit'] = True  # Mark for deletion
                        show_judgment('MISS')
                        spawn_particle(lane, 'MISS')  # Add particle effect for miss
    
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
                    # Only register miss if we haven't reached the end yet
                    # Don't mark slides for removal if they're past all beat ticks but before end time
                    if current_time < slide['end_time']:
                        # Released too early during the slide
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
                    spawn_particle(lane, judgment)  # Add particle effect
                else:
                    # Released too early
                    combo = 0
                    miss_count += 1
                    slide['remove'] = True  # Mark for removal
                    show_judgment('MISS')
                    spawn_particle(lane, 'MISS')  # Add particle effect

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
    global practice_speed, practice_loop_start, practice_loop_end, practice_looping
    
    print(f"DEBUG tkinter_press: keysym={event.keysym}, char={event.char}, game_running={game_running}")
    
    if event.keysym == 'Escape':
        game_running = False
        return
    
    # Practice mode controls
    if game_mode == 'practice':
        if event.char == '[':
            # Set loop start
            current_time = time.time() - start_time
            practice_loop_start = current_time
            print(f"Practice loop start set at {current_time:.2f}s")
            return
        elif event.char == ']':
            # Set loop end
            current_time = time.time() - start_time
            practice_loop_end = current_time
            print(f"Practice loop end set at {current_time:.2f}s")
            return
        elif event.char and event.char.lower() == 'l':
            # Toggle looping
            practice_looping = not practice_looping
            print(f"Practice looping: {practice_looping}")
            return
        elif event.char == '-':
            # Decrease speed
            practice_speed = max(0.25, practice_speed - 0.25)
            print(f"Practice speed: {practice_speed:.2f}x")
            return
        elif event.char == '=':
            # Increase speed
            practice_speed = min(2.0, practice_speed + 0.25)
            print(f"Practice speed: {practice_speed:.2f}x")
            return
    
    # Get lane from key
    lane = None
    if event.char and event.char.lower() in KEY_MAPPINGS:
        lane = KEY_MAPPINGS[event.char.lower()]
    
    if lane is not None:
        key_is_down[lane] = True
        if not is_replay and game_running and game_mode != 'auto':
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
        if not is_replay and game_running and game_mode != 'auto':
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
    """Draw score bar, accuracy, combo, and judgment"""
    canvas.delete('ui')
    canvas.delete('particle')  # Clear old particles
    draw_key_labels()  # Update key press feedback
    draw_particles()  # Draw active particles
    
    # Left margin - Score, Accuracy, and Score Bar
    left_x = 50
    
    # Score at top left
    canvas.create_text(left_x, 30, text=f"Score: {score}",
                      fill='white', font=('Arial', 24, 'bold'), tags='ui', anchor='w')
    
    # Accuracy percentage at top left (below score)
    accuracy = calculate_accuracy()
    canvas.create_text(left_x, 65, text=f"Accuracy: {accuracy:.2f}%",
                      fill='cyan', font=('Arial', 20, 'bold'), tags='ui', anchor='w')
    
    # Vertical Score Bar (shows progress towards ranks)
    bar_x = left_x + 10
    bar_y_top = 120
    bar_height = 400
    bar_width = 30
    
    # Background bar
    canvas.create_rectangle(bar_x, bar_y_top, bar_x + bar_width, bar_y_top + bar_height,
                           fill='#222222', outline='white', width=2, tags='ui')
    
    # Calculate score percentage
    score_percentage = min(1.0, score / max_possible_score) if max_possible_score > 0 else 0
    
    # Fill bar based on score
    fill_height = int(bar_height * score_percentage)
    if fill_height > 0:
        # Color based on current rank
        if score_percentage >= RANK_S:
            fill_color = '#FFD700'  # Gold
        elif score_percentage >= RANK_A:
            fill_color = '#00FF00'  # Green
        elif score_percentage >= RANK_B:
            fill_color = '#00BFFF'  # Blue
        elif score_percentage >= RANK_C:
            fill_color = '#FFA500'  # Orange
        else:
            fill_color = '#FF4500'  # Red
        
        canvas.create_rectangle(bar_x, bar_y_top + bar_height - fill_height,
                               bar_x + bar_width, bar_y_top + bar_height,
                               fill=fill_color, outline='', tags='ui')
    
    # Draw rank threshold lines
    rank_thresholds = [
        (RANK_S, 'S', '#FFD700'),
        (RANK_A, 'A', '#00FF00'),
        (RANK_B, 'B', '#00BFFF'),
        (RANK_C, 'C', '#FFA500'),
    ]
    
    for threshold, label, color in rank_thresholds:
        y = bar_y_top + bar_height - int(bar_height * threshold)
        canvas.create_line(bar_x, y, bar_x + bar_width, y,
                          fill=color, width=2, tags='ui')
        canvas.create_text(bar_x + bar_width + 5, y, text=label,
                          fill=color, font=('Arial', 14, 'bold'), tags='ui', anchor='w')
    
    # Right margin - Combo and Auto Play text
    right_x = width - 50
    
    # Combo counter at top right
    if combo > 0:
        canvas.create_text(right_x, 30, text=f"{combo}",
                          fill='yellow', font=('Arial', 48, 'bold'), tags='ui', anchor='e')
        canvas.create_text(right_x, 75, text="COMBO",
                          fill='yellow', font=('Arial', 20, 'bold'), tags='ui', anchor='e')
    
    # Draw judgment display (centered at top)
    if judgment_display:
        judgment_text, end_time, color = judgment_display
        if time.time() < end_time:
            canvas.create_text(width // 2, 100, text=judgment_text,
                             fill=color, font=('Arial', 48, 'bold'), tags='ui')
    
    # Watermarks for special modes (right margin)
    if game_mode == 'auto':
        canvas.create_text(right_x, 150, text="AUTO PLAY",
                         fill='#666666', font=('Arial', 32, 'bold'), tags='ui', anchor='e')
    elif game_mode == 'practice':
        practice_text = f"PRACTICE MODE\nSpeed: {practice_speed:.2f}x"
        if practice_looping and practice_loop_start is not None and practice_loop_end is not None:
            practice_text += "\n[LOOP]"
        canvas.create_text(right_x, 150, text=practice_text,
                         fill='#666666', font=('Arial', 24, 'bold'), tags='ui', anchor='e')
        # Show controls
        canvas.create_text(width // 2, height - 70, 
                         text="[ = Loop Start  |  ] = Loop End  |  L = Toggle Loop  |  - = Slower  |  + = Faster",
                         fill='#555555', font=('Arial', 14), tags='ui')

def get_pixel_speed(current_beat):
    """Get the current pixel speed based on BPM, spd% changes, and global multiplier"""
    current_bpm = get_current_bpm(current_beat, bpm_changes, initial_bpm)
    speed_mult = get_current_speed_multiplier(current_beat, speed_changes)
    global_mult = settings['scroll_speed_multiplier']
    return current_bpm * 10 * speed_mult * global_mult

def update_notes(current_time):
    """Update note positions and spawn new notes"""
    global active_notes, active_slides, chart, combo
    
    # Calculate current beat for pixel speed
    current_beat = seconds_to_beats(current_time, bpm_changes, initial_bpm)
    pixel_ps = get_pixel_speed(current_beat)
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
        
        # Calculate pixel speed based on slide's beat position
        slide_pixel_ps = get_pixel_speed(slide['beat'])
            
        # If slide is being held, lock the start position to the hit bar
        if slide.get('holding', False):
            y_start = int(BAR_Y)
            y_end = BAR_Y - ((slide['end_time'] - current_time) * slide_pixel_ps)
        else:
            y_start = BAR_Y - ((slide['time'] - current_time) * slide_pixel_ps)
            y_end = BAR_Y - ((slide['end_time'] - current_time) * slide_pixel_ps)
        
        # Check if slide is complete
        if slide.get('holding', False) and current_time >= slide['end_time']:
            # Auto-complete if still holding at the end
            if key_is_down[slide['lane']]: 
                check_slide_hold(slide['lane'], current_time, False)
            # If already marked for removal after auto-complete, skip to next iteration
            if slide.get('remove', False):
                continue
        
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
        
        # Always redraw if holding, OR if any part is visible on screen, OR if slide was just completed (has remove flag but not yet removed)
        # This ensures the final state is drawn before removal
        if slide.get('holding', False) or (0 <= y_start <= height or 0 <= y_end <= height) or slide.get('remove', False):
            canvas.delete(f"note_{slide['id']}")
            if hasattr(canvas, '_slide_images') and slide['id'] in canvas._slide_images:
                del canvas._slide_images[slide['id']]
            draw_slide(slide['lane'], int(y_start), int(y_end), slide['id'],
                      slide.get('holding', False), slide.get('multiplier', 1))

def save_replay(chart_id, difficulty, score, accuracy, inputs, rank):
    """Save replay data to file in JSON format"""
    import json
    from datetime import datetime
    
    # Create replays directory if it doesn't exist
    replay_dir = os.path.join(os.path.dirname(__file__), "replays")
    os.makedirs(replay_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{chart_id}_{difficulty}_{timestamp}.replay"
    filepath = os.path.join(replay_dir, filename)
    
    # Prepare replay data
    replay_info = {
        "chart_id": chart_id,
        "difficulty": difficulty,
        "score": score,
        "accuracy": accuracy,
        "rank": rank,
        "max_combo": max_combo,
        "perfect": perfect_count,
        "great": great_count,
        "good": good_count,
        "bad": bad_count,
        "miss": miss_count,
        "timestamp": timestamp,
        "inputs": inputs  # List of (time, event_type, lane) tuples
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(replay_info, f, indent=2)
        print(f"Replay saved to {filepath}")
    except Exception as e:
        print(f"Error saving replay: {e}")

def load_progress():
    """Load progress data from file"""
    import json
    
    progress_file = os.path.join(os.path.dirname(__file__), "progress.json")
    if not os.path.exists(progress_file):
        # Create default progress file
        default_progress = {
            "username": "Player",
            "total_charts_played": 0,
            "total_score": 0,
            "total_playtime_seconds": 0,
            "total_perfects": 0,
            "total_greats": 0,
            "total_goods": 0,
            "total_bads": 0,
            "total_misses": 0,
            "best_scores": {},
            "recently_played": [],
            "achievements": {}
        }
        try:
            with open(progress_file, 'w') as f:
                json.dump(default_progress, f, indent=2)
        except:
            pass
        return default_progress
    
    try:
        with open(progress_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading progress: {e}")
        return None

def save_progress_data(progress):
    """Save progress data to file"""
    import json
    
    progress_file = os.path.join(os.path.dirname(__file__), "progress.json")
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
        print(f"Progress saved")
    except Exception as e:
        print(f"Error saving progress: {e}")

def update_progress(chart_id, difficulty, score, rank, accuracy, playtime_seconds):
    """Update progress after completing a chart"""
    from datetime import datetime
    
    progress = load_progress()
    if not progress:
        return
    
    # Update totals
    progress['total_charts_played'] += 1
    progress['total_score'] += score
    progress['total_playtime_seconds'] += int(playtime_seconds)
    progress['total_perfects'] += perfect_count
    progress['total_greats'] += great_count
    progress['total_goods'] += good_count
    progress['total_bads'] += bad_count
    progress['total_misses'] += miss_count
    
    # Update best score for this chart/difficulty
    chart_key = f"{chart_id}_{difficulty}"
    if 'best_scores' not in progress:
        progress['best_scores'] = {}
    
    if chart_key not in progress['best_scores'] or score > progress['best_scores'][chart_key].get('score', 0):
        progress['best_scores'][chart_key] = {
            'score': score,
            'rank': rank,
            'accuracy': accuracy,
            'max_combo': max_combo,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    
    # Update recently played (keep last 10)
    if 'recently_played' not in progress:
        progress['recently_played'] = []
    
    recent_entry = {
        'chart_id': chart_id,
        'difficulty': difficulty,
        'score': score,
        'rank': rank,
        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
    }
    
    # Remove if already in list
    progress['recently_played'] = [r for r in progress['recently_played'] 
                                   if not (r['chart_id'] == chart_id and r['difficulty'] == difficulty)]
    
    # Add to front
    progress['recently_played'].insert(0, recent_entry)
    
    # Keep only last 10
    progress['recently_played'] = progress['recently_played'][:10]
    
    # Check for achievements
    if 'achievements' not in progress:
        progress['achievements'] = {}
    
    # Achievement: First clear
    if 'first_clear' not in progress['achievements']:
        progress['achievements']['first_clear'] = {
            'name': 'First Clear',
            'description': 'Complete your first chart',
            'unlocked': datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    
    # Achievement: 10 charts played
    if progress['total_charts_played'] >= 10 and '10_charts' not in progress['achievements']:
        progress['achievements']['10_charts'] = {
            'name': '10 Charts',
            'description': 'Play 10 charts',
            'unlocked': datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    
    # Achievement: First S rank
    if rank == 'S' and 's_rank' not in progress['achievements']:
        progress['achievements']['s_rank'] = {
            'name': 'S Rank',
            'description': 'Achieve an S rank',
            'unlocked': datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    
    # Achievement: Full combo
    if miss_count == 0 and (perfect_count + great_count + good_count + bad_count) > 0:
        if 'full_combo' not in progress['achievements']:
            progress['achievements']['full_combo'] = {
                'name': 'Full Combo',
                'description': 'Complete a chart with no misses',
                'unlocked': datetime.now().strftime("%Y%m%d_%H%M%S")
            }
    
    # Achievement: All perfect
    total_notes = perfect_count + great_count + good_count + bad_count + miss_count
    if perfect_count == total_notes and perfect_count > 0:
        if 'all_perfect' not in progress['achievements']:
            progress['achievements']['all_perfect'] = {
                'name': 'All Perfect',
                'description': 'Complete a chart with all perfect hits',
                'unlocked': datetime.now().strftime("%Y%m%d_%H%M%S")
            }
    
    save_progress_data(progress)
    return progress

def load_replay_file(filepath):
    """Load replay data from file"""
    import json
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading replay: {e}")
        return None

def get_available_replays():
    """Scan replays directory and return list of replay files"""
    replay_dir = os.path.join(os.path.dirname(__file__), "replays")
    if not os.path.exists(replay_dir):
        return []
    
    replays = []
    for filename in os.listdir(replay_dir):
        if filename.endswith('.replay'):
            filepath = os.path.join(replay_dir, filename)
            replay_data = load_replay_file(filepath)
            if replay_data:
                replays.append({
                    'filename': filename,
                    'filepath': filepath,
                    'data': replay_data
                })
    
    # Sort by timestamp (newest first)
    replays.sort(key=lambda x: x['data'].get('timestamp', ''), reverse=True)
    return replays

def auto_play_ai(current_time):
    """AI that plays notes perfectly in auto mode - directly scores without simulating keypresses"""
    global score, combo, max_combo, perfect_count
    
    # Auto-hit tap notes - wider window to catch high-BPM notes
    for note in active_notes[:]:
        if note['type'] == 'tap' and not note.get('hit', False):
            time_diff = current_time - note['time']
            # Expanded window: catch notes slightly before and well after their time
            # This ensures we don't miss any notes at high BPM (e.g., 250 BPM)
            if -0.05 <= time_diff <= (2.0 / fps):
                # Award perfect score directly
                multiplier = note.get('multiplier', 1)
                score += SCORE_PERFECT * multiplier
                combo += 1
                max_combo = max(max_combo, combo)
                perfect_count += 1
                note['hit'] = True
                show_judgment('PERFECT', 0.0)
                spawn_particle(note['lane'], 'PERFECT')
    
    # Auto-hit and hold slides
    for slide in active_slides[:]:
        # Start slide at perfect timing
        if not slide.get('hit_start', False):
            time_diff = current_time - slide['time']
            # Expanded window for slides too
            if -0.05 <= time_diff <= (2.0 / fps):
                # Start the slide with perfect timing
                multiplier = slide.get('multiplier', 1)
                score += SCORE_PERFECT * multiplier
                combo += 1
                max_combo = max(max_combo, combo)
                perfect_count += 1
                slide['hit_start'] = True
                slide['holding'] = True
                slide['next_tick'] = slide['beat'] + 1.0
                show_judgment('PERFECT', 0.0)
                spawn_particle(slide['lane'], 'PERFECT')
        
        # Auto-complete slide at end
        if slide.get('holding', False) and not slide.get('auto_completed', False):
            time_diff = current_time - slide['end_time']
            # Use same expanded window for slide completion
            if -0.05 <= time_diff <= (2.0 / fps):
                # Complete the slide with perfect timing
                multiplier = slide.get('multiplier', 1)
                score += SCORE_PERFECT * multiplier
                combo += 1
                max_combo = max(max_combo, combo)
                perfect_count += 1
                slide['auto_completed'] = True
                slide['remove'] = True
                show_judgment('PERFECT', 0.0)
                spawn_particle(slide['lane'], 'PERFECT')

def game_loop():
    """Main game loop"""
    global start_time, game_running, chart, music_playing, active_particles
    global score, combo, max_combo, perfect_count, great_count, good_count, bad_count, miss_count
    global active_notes, active_slides, key_pressed_flags, key_is_down
    
    # Reset all game state
    active_particles = []
    active_notes = []
    active_slides = []
    score = 0
    combo = 0
    max_combo = 0
    perfect_count = 0
    great_count = 0
    good_count = 0
    bad_count = 0
    miss_count = 0
    
    # Reset key states
    for i in range(LANE_COUNT):
        key_pressed_flags[i] = False
        key_is_down[i] = False
    
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
    # Set start_time 2 seconds in the future so current_time starts at -2.0
    # This gives a 2 second delay before notes start spawning
    start_time = time.time() + 2.0
    game_running = True
    
    # Draw static elements
    draw_lane_separators()
    draw_hit_bar()
    draw_key_labels()  # Initial key labels
    
    # Continue while there are notes/slides to process OR slides being held
    while game_running and (chart or active_notes or active_slides):
        frame_start = time.time()
        current_time = frame_start - start_time
        
        # Practice mode loop check
        if game_mode == 'practice' and practice_looping:
            if practice_loop_start is not None and practice_loop_end is not None:
                if current_time >= practice_loop_end:
                    # Loop back to start
                    # This is simplified - ideally we'd reset all game state
                    start_time += (practice_loop_end - practice_loop_start)
                    current_time = practice_loop_start
        
        # Auto-play AI
        if game_mode == 'auto':
            auto_play_ai(current_time)
        
        # Check slide holds for currently pressed keys (normal gameplay)
        if game_mode != 'auto':
            for lane in range(LANE_COUNT):
                if key_is_down.get(lane, False):
                    check_slide_hold(lane, current_time, True)
        
        # Update slide combo (awards score per beat for held slides)
        update_slide_combo(current_time)
        
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
    
    # Save replay to file (only if not already a replay and not in auto mode)
    if not is_replay and game_mode != 'auto' and current_chart_id and current_difficulty:
        save_replay(current_chart_id, current_difficulty, score, 
                   calculate_accuracy(), replay_data, rank)
    
    # Update progress (only if not replay and not auto mode)
    if not is_replay and game_mode != 'auto' and current_chart_id and current_difficulty:
        playtime = time.time() - start_time
        updated_progress = update_progress(current_chart_id, current_difficulty, 
                                          score, rank, calculate_accuracy(), playtime)
        
        # Check for new achievements
        if updated_progress:
            new_achievements = []
            for ach_key, ach_data in updated_progress.get('achievements', {}).items():
                # Check if achievement was just unlocked (within last 10 seconds)
                from datetime import datetime, timedelta
                unlock_time = datetime.strptime(ach_data['unlocked'], "%Y%m%d_%H%M%S")
                if datetime.now() - unlock_time < timedelta(seconds=10):
                    new_achievements.append(ach_data)
            
            # Show new achievements
            if new_achievements:
                canvas.delete('all')
                canvas.configure(bg='black')
                
                canvas.create_text(width // 2, height // 2 - 150, 
                                 text="ACHIEVEMENT UNLOCKED!",
                                 fill='gold', font=('Arial', 48, 'bold'))
                
                y_pos = height // 2 - 50
                for ach in new_achievements:
                    canvas.create_text(width // 2, y_pos, 
                                     text=ach['name'],
                                     fill='yellow', font=('Arial', 36, 'bold'))
                    y_pos += 50
                    canvas.create_text(width // 2, y_pos, 
                                     text=ach['description'],
                                     fill='white', font=('Arial', 20))
                    y_pos += 70
                
                root.update()
                time.sleep(2.5)
    
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
    global active_notes, active_slides, chart, key_is_down, key_pressed_flags, active_particles
    
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
    active_particles = []  # Reset particles
    miss_count = 0
    active_notes = []
    active_slides = []
    key_is_down = {0: False, 1: False, 2: False, 3: False}
    key_pressed_flags = {0: False, 1: False, 2: False, 3: False}
    
    # Reload chart
    load_chart(current_chart_id, current_difficulty)
    
    # Calculate total duration from last note/replay event
    total_duration = 0
    if replay_data:
        total_duration = replay_data[-1][0] + 2.0  # Add buffer
    elif chart:
        # Fallback to chart duration
        total_duration = max(note['time'] for note in chart) + 2.0
    
    # Start replay game loop
    frame_dur = 1 / fps
    start_time = time.time()
    game_running = True
    replay_exit = False
    paused = False  # Pause state for frame-by-frame
    current_frame = 0  # Frame counter for paused display
    
    canvas.delete('all')
    canvas.configure(bg='black')
    
    # Draw static elements
    draw_lane_separators()
    draw_hit_bar()
    draw_key_labels()
    
    # Replay control state
    def seek_to_time(target_time):
        """Seek replay to a specific time"""
        global replay_index, score, combo, max_combo
        global perfect_count, great_count, good_count, bad_count, miss_count
        global active_notes, active_slides, key_is_down, key_pressed_flags
        
        # Reset state
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
        
        # Fast-forward to target time
        while replay_index < len(replay_data) and replay_data[replay_index][0] <= target_time:
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
        
        # Update notes to current time
        update_notes(target_time)
    
    def on_replay_key(event):
        """Handle key presses during replay"""
        global game_running, start_time
        nonlocal replay_exit, paused, current_frame
        
        if event.keysym == 'Escape':
            game_running = False
            replay_exit = True
        elif event.char and event.char == ' ':
            # Toggle pause
            paused = not paused
            if not paused:
                # Resume - adjust start_time to account for pause
                start_time = time.time() - (current_frame / fps)
        elif event.char and event.char == ',':
            # Step backward one frame (when paused)
            if paused:
                current_frame = max(0, current_frame - 1)
                target_time = current_frame / fps
                seek_to_time(target_time)
                start_time = time.time() - target_time
        elif event.char and event.char == '.':
            # Step forward one frame (when paused)
            if paused:
                current_frame += 1
                target_time = current_frame / fps
                seek_to_time(target_time)
                start_time = time.time() - target_time
        elif event.keysym == 'Left':
            # Jump back 5 seconds
            current_time = time.time() - start_time
            new_time = max(0, current_time - 5.0)
            seek_to_time(new_time)
            start_time = time.time() - new_time
            if paused:
                current_frame = int(new_time * fps)
        elif event.keysym == 'Right':
            # Jump forward 5 seconds
            current_time = time.time() - start_time
            new_time = min(total_duration, current_time + 5.0)
            seek_to_time(new_time)
            start_time = time.time() - new_time
            if paused:
                current_frame = int(new_time * fps)
    
    root.bind('<KeyPress>', on_replay_key)
    
    while game_running and (chart or active_notes or active_slides):
        if not paused:
            frame_start = time.time()
            current_time = frame_start - start_time
            current_frame = int(current_time * fps)
        else:
            # When paused, use the stored frame number
            frame_start = time.time()
            current_time = current_frame / fps
        
        # Process replay events (only if not paused)
        if not paused:
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
        
        # Add "REPLAY" watermark or "PAUSED" indicator
        if paused:
            canvas.create_text(width // 2, height - 80, text=f"PAUSED - Frame {current_frame}",
                             fill='#FF6666', font=('Arial', 24, 'bold'), tags='ui')
        else:
            canvas.create_text(width // 2, height - 80, text="REPLAY",
                             fill='#666666', font=('Arial', 24, 'bold'), tags='ui')
        
        # Draw playback bar at bottom
        bar_width = width - 200
        bar_x = 100
        bar_y = height - 40
        bar_height = 10
        
        # Background bar
        canvas.create_rectangle(bar_x, bar_y - bar_height // 2,
                              bar_x + bar_width, bar_y + bar_height // 2,
                              fill='#333333', outline='#666666', width=2, tags='ui')
        
        # Progress bar
        if total_duration > 0:
            progress = min(1.0, current_time / total_duration)
            progress_width = int(bar_width * progress)
            canvas.create_rectangle(bar_x, bar_y - bar_height // 2,
                                  bar_x + progress_width, bar_y + bar_height // 2,
                                  fill='#00AAFF' if not paused else '#FF6666', 
                                  outline='', tags='ui')
        
        # Time display
        time_text = f"{int(current_time // 60):02d}:{int(current_time % 60):02d} / {int(total_duration // 60):02d}:{int(total_duration % 60):02d}"
        canvas.create_text(width // 2, bar_y + 20, text=time_text,
                         fill='white', font=('Arial', 16), tags='ui')
        
        # Controls hint
        if paused:
            canvas.create_text(width // 2, height - 10, 
                             text="SPACE Resume  |  , Previous Frame  |  . Next Frame  |  ESC Exit",
                             fill='#888888', font=('Arial', 14), tags='ui')
        else:
            canvas.create_text(width // 2, height - 10, 
                             text="SPACE Pause  |  ← Jump Back 5s  |  → Jump Forward 5s  |  ESC Exit Replay",
                             fill='#888888', font=('Arial', 14), tags='ui')
        
        # Maintain frame rate (only if not paused)
        if not paused:
            elapsed = time.time() - frame_start
            sleep_time = frame_dur - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        else:
            # When paused, just update at a lower rate
            time.sleep(0.05)
        
        root.update()
    
    root.unbind('<KeyPress>')
    
    # Show game over screen again (unless user pressed ESC to exit)
    is_replay = False
    if not replay_exit:
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

def show_replay_menu():
    """Display replay selection menu"""
    global current_chart_id, current_difficulty, replay_data, is_replay
    
    menu_running = True
    current_page = 0
    replays_per_page = 10
    
    def draw_menu():
        canvas.delete('all')
        canvas.configure(bg='black')
        
        # Title
        canvas.create_text(width // 2, 50, text="WATCH REPLAY",
                         fill='white', font=('Arial', 48, 'bold'))
        
        # Instructions
        canvas.create_text(width // 2, 120, text="Use number keys or click to select | ←→ to change page | ESC to go back",
                         fill='gray', font=('Arial', 16))
        
        replays = get_available_replays()
        if not replays:
            canvas.create_text(width // 2, height // 2,
                             text="No replays found",
                             fill='red', font=('Arial', 24))
            root.update()
            return
        
        # Calculate pagination
        total_pages = (len(replays) + replays_per_page - 1) // replays_per_page
        nonlocal current_page
        current_page = max(0, min(current_page, total_pages - 1))
        
        start_idx = current_page * replays_per_page
        end_idx = min(start_idx + replays_per_page, len(replays))
        page_replays = replays[start_idx:end_idx]
        
        # Display page indicator
        if total_pages > 1:
            canvas.create_text(width // 2, 150, text=f"Page {current_page + 1} of {total_pages}",
                             fill='white', font=('Arial', 18))
        
        # Display replays
        y_pos = 200
        for i, replay_info in enumerate(page_replays):
            data = replay_info['data']
            chart_id = data.get('chart_id', 'Unknown')
            difficulty = data.get('difficulty', 'Unknown')
            rank = data.get('rank', 'D')
            score = data.get('score', 0)
            accuracy = data.get('accuracy', 0)
            timestamp = data.get('timestamp', '')
            
            # Format timestamp for display
            if len(timestamp) >= 13:
                date_str = f"{timestamp[4:6]}/{timestamp[6:8]}"
                time_str = f"{timestamp[9:11]}:{timestamp[11:13]}"
                display_time = f"{date_str} {time_str}"
            else:
                display_time = timestamp
            
            text = f"{i + 1}. {chart_id} [{difficulty}] - Rank {rank} - {accuracy:.1f}% - {display_time}"
            canvas.create_text(width // 2, y_pos, text=text,
                             fill='cyan', font=('Arial', 18), tags=f'replay_{i}')
            y_pos += 35
        
        root.update()
    
    def on_tkinter_key(event):
        """Handle tkinter key events for menu"""
        nonlocal menu_running, current_page
        
        if event.keysym == 'Escape':
            menu_running = False
            return
        
        # Left/Right arrows for pagination
        if event.keysym == 'Left':
            replays = get_available_replays()
            total_pages = (len(replays) + replays_per_page - 1) // replays_per_page
            if current_page > 0:
                current_page -= 1
                draw_menu()
            return
        
        if event.keysym == 'Right':
            replays = get_available_replays()
            total_pages = (len(replays) + replays_per_page - 1) // replays_per_page
            if current_page < total_pages - 1:
                current_page += 1
                draw_menu()
            return
        
        # Number key selection
        if event.char and event.char.isdigit():
            num = int(event.char)
            if num > 0:
                replays = get_available_replays()
                start_idx = current_page * replays_per_page
                page_replays = replays[start_idx:start_idx + replays_per_page]
                if num <= len(page_replays):
                    # Load and play selected replay
                    replay_info = page_replays[num - 1]
                    data = replay_info['data']
                    
                    current_chart_id = data['chart_id']
                    current_difficulty = data['difficulty']
                    replay_data = [tuple(event) for event in data['inputs']]
                    
                    menu_running = False
                    root.unbind('<KeyPress>')
                    root.unbind('<Button-1>')
                    
                    # Start replay
                    load_chart(current_chart_id, current_difficulty)
                    play_replay()
    
    def on_mouse_click(event):
        """Handle mouse clicks in replay menu"""
        # Get clicked item
        items = canvas.find_overlapping(event.x - 10, event.y - 10, event.x + 10, event.y + 10)
        for item in items:
            tags = canvas.gettags(item)
            for tag in tags:
                if tag.startswith('replay_'):
                    replay_index = int(tag.split('_')[1])
                    replays = get_available_replays()
                    start_idx = current_page * replays_per_page
                    page_replays = replays[start_idx:start_idx + replays_per_page]
                    if replay_index < len(page_replays):
                        # Load and play selected replay
                        replay_info = page_replays[replay_index]
                        data = replay_info['data']
                        
                        global current_chart_id, current_difficulty, replay_data
                        current_chart_id = data['chart_id']
                        current_difficulty = data['difficulty']
                        replay_data = [tuple(event) for event in data['inputs']]
                        
                        nonlocal menu_running
                        menu_running = False
                        root.unbind('<KeyPress>')
                        root.unbind('<Button-1>')
                        
                        # Start replay
                        load_chart(current_chart_id, current_difficulty)
                        play_replay()
                    return
    
    draw_menu()
    root.bind('<KeyPress>', on_tkinter_key)
    root.bind('<Button-1>', on_mouse_click)
    
    while menu_running:
        root.update()
        time.sleep(0.01)
    
    root.unbind('<KeyPress>')
    root.unbind('<Button-1>')

def show_chart_menu():
    """Display chart selection menu"""
    global current_chart_id, current_difficulty
    
    selected_chart = None
    selected_difficulty = None
    menu_running = True
    current_page = 0
    charts_per_page = 10
    refresh_text_alpha = 0  # For fading effect
    refresh_text_time = 0
    
    def refresh_menu():
        nonlocal current_page, refresh_text_alpha, refresh_text_time
        current_page = 0
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
        canvas.create_text(width // 2, 120, text="Use number keys or click to select | R to refresh | ←→ to change page | ESC to quit",
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
        
        # Calculate pagination
        chart_list = sorted(charts.keys())
        total_pages = (len(chart_list) + charts_per_page - 1) // charts_per_page
        nonlocal current_page
        current_page = max(0, min(current_page, total_pages - 1))
        
        start_idx = current_page * charts_per_page
        end_idx = min(start_idx + charts_per_page, len(chart_list))
        page_charts = chart_list[start_idx:end_idx]
        
        # Display page indicator
        if total_pages > 1:
            canvas.create_text(width // 2, 150, text=f"Page {current_page + 1} of {total_pages}",
                             fill='white', font=('Arial', 18))
        
        # Display charts
        y_pos = 200
        index = 0
        for chart_id in page_charts:
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
                             fill='cyan', font=('Arial', 20), tags=f'chart_{index}')
            y_pos += 40
            index += 1
        
        root.update()
    
    def on_tkinter_key(event):
        """Handle tkinter key events for menu"""
        nonlocal menu_running, selected_chart, selected_difficulty, current_page
        
        print(f"DEBUG tkinter_key: {event.keysym}, {event.char}")
        
        if event.keysym == 'Escape':
            menu_running = False
            return
        
        if event.char and event.char.lower() == 'r':
            refresh_menu()
            return
        
        # Left/Right arrows for pagination
        if event.keysym == 'Left':
            charts = get_available_charts()
            total_pages = (len(charts) + charts_per_page - 1) // charts_per_page
            if current_page > 0:
                current_page -= 1
                draw_menu()
            return
        
        if event.keysym == 'Right':
            charts = get_available_charts()
            total_pages = (len(charts) + charts_per_page - 1) // charts_per_page
            if current_page < total_pages - 1:
                current_page += 1
                draw_menu()
            return
        
        # Number key selection
        if event.char and event.char.isdigit():
            num = int(event.char)
            if num > 0:
                charts = get_available_charts()
                chart_list = sorted(charts.keys())
                start_idx = current_page * charts_per_page
                page_charts = chart_list[start_idx:start_idx + charts_per_page]
                if num <= len(page_charts):
                    selected_chart = page_charts[num - 1]
                    # Show difficulty selection
                    select_difficulty(selected_chart, charts[selected_chart])
    
    def on_mouse_click(event):
        """Handle mouse clicks in chart menu"""
        nonlocal selected_chart
        
        # Get clicked item
        items = canvas.find_overlapping(event.x - 10, event.y - 10, event.x + 10, event.y + 10)
        for item in items:
            tags = canvas.gettags(item)
            for tag in tags:
                if tag.startswith('chart_'):
                    chart_index = int(tag.split('_')[1])
                    charts = get_available_charts()
                    chart_list = sorted(charts.keys())
                    start_idx = current_page * charts_per_page
                    page_charts = chart_list[start_idx:start_idx + charts_per_page]
                    if chart_index < len(page_charts):
                        selected_chart = page_charts[chart_index]
                        select_difficulty(selected_chart, charts[selected_chart])
                    return

    def select_difficulty(chart_id, difficulties):
        nonlocal menu_running, selected_chart, selected_difficulty
        global current_chart_id, current_difficulty, game_mode
        
        canvas.delete('all')
        canvas.configure(bg='black')
        
        canvas.create_text(width // 2, 100, text=f"Select Mode for {chart_id}",
                         fill='white', font=('Arial', 36, 'bold'))
        
        y_pos = 200
        
        # Show special modes first
        canvas.create_text(width // 2, y_pos, text="A. Auto Play",
                         fill='cyan', font=('Arial', 24), tags='mode_auto')
        y_pos += 50
        
        canvas.create_text(width // 2, y_pos, text="P. Practice Mode",
                         fill='lime', font=('Arial', 24), tags='mode_practice')
        y_pos += 70
        
        # Show regular difficulties
        canvas.create_text(width // 2, y_pos, text="--- Regular Difficulties ---",
                         fill='gray', font=('Arial', 18))
        y_pos += 50
        
        for i, diff in enumerate(sorted(difficulties)):
            mp3_file = f"{CHART_DIRECTORY}/{chart_id}_{diff}.mp3"
            audio_icon = " ♫" if os.path.exists(mp3_file) else ""
            
            canvas.create_text(width // 2, y_pos, text=f"{i + 1}. {diff}{audio_icon}",
                             fill='yellow', font=('Arial', 24), tags=f'diff_{i}')
            y_pos += 50
        
        canvas.create_text(width // 2, height - 50, text="Press number/letter or click to select | ESC to go back",
                         fill='gray', font=('Arial', 16))
        root.update()
        
        def on_diff_tkinter_key(event):
            nonlocal selected_difficulty, menu_running
            global current_chart_id, current_difficulty, game_mode
            
            print(f"DEBUG diff_tkinter_key: {event.keysym}, {event.char}")
            
            if event.keysym == 'Escape':
                root.unbind('<KeyPress>')
                root.unbind('<Button-1>')
                draw_menu()
                root.bind('<KeyPress>', on_tkinter_key)
                root.bind('<Button-1>', on_mouse_click)
                return
            
            # Check for Auto mode
            if event.char and event.char.lower() == 'a':
                # Use first available difficulty for auto mode
                selected_difficulty = sorted(difficulties)[0]
                current_chart_id = chart_id
                current_difficulty = selected_difficulty
                game_mode = 'auto'
                menu_running = False
                root.unbind('<KeyPress>')
                root.unbind('<Button-1>')
                print(f"DEBUG: Selected AUTO mode with chart_id={current_chart_id}, difficulty={current_difficulty}")
                return
            
            # Check for Practice mode
            if event.char and event.char.lower() == 'p':
                # Use first available difficulty for practice mode
                selected_difficulty = sorted(difficulties)[0]
                current_chart_id = chart_id
                current_difficulty = selected_difficulty
                game_mode = 'practice'
                menu_running = False
                root.unbind('<KeyPress>')
                root.unbind('<Button-1>')
                print(f"DEBUG: Selected PRACTICE mode with chart_id={current_chart_id}, difficulty={current_difficulty}")
                return
            
            # Regular difficulty selection
            if event.char.isdigit():
                num = int(event.char)
                if 0 < num <= len(difficulties):
                    selected_difficulty = sorted(difficulties)[num - 1]
                    current_chart_id = chart_id
                    current_difficulty = selected_difficulty
                    game_mode = 'normal'
                    menu_running = False
                    root.unbind('<KeyPress>')
                    root.unbind('<Button-1>')
                    print(f"DEBUG: Selected chart_id={current_chart_id}, difficulty={current_difficulty}")
        
        def on_diff_mouse_click(event):
            nonlocal selected_difficulty, menu_running
            global current_chart_id, current_difficulty, game_mode
            
            # Get clicked item
            items = canvas.find_overlapping(event.x - 10, event.y - 10, event.x + 10, event.y + 10)
            for item in items:
                tags = canvas.gettags(item)
                for tag in tags:
                    if tag == 'mode_auto':
                        selected_difficulty = sorted(difficulties)[0]
                        current_chart_id = chart_id
                        current_difficulty = selected_difficulty
                        game_mode = 'auto'
                        menu_running = False
                        root.unbind('<KeyPress>')
                        root.unbind('<Button-1>')
                        print(f"DEBUG: Selected AUTO mode")
                        return
                    elif tag == 'mode_practice':
                        selected_difficulty = sorted(difficulties)[0]
                        current_chart_id = chart_id
                        current_difficulty = selected_difficulty
                        game_mode = 'practice'
                        menu_running = False
                        root.unbind('<KeyPress>')
                        root.unbind('<Button-1>')
                        print(f"DEBUG: Selected PRACTICE mode")
                        return
                    elif tag.startswith('diff_'):
                        diff_index = int(tag.split('_')[1])
                        if diff_index < len(difficulties):
                            selected_difficulty = sorted(difficulties)[diff_index]
                            current_chart_id = chart_id
                            current_difficulty = selected_difficulty
                            game_mode = 'normal'
                            menu_running = False
                            root.unbind('<KeyPress>')
                            root.unbind('<Button-1>')
                            print(f"DEBUG: Selected chart_id={current_chart_id}, difficulty={current_difficulty}")
                        return
        
        # Unbind menu keys and bind difficulty keys
        root.unbind('<KeyPress>')
        root.unbind('<Button-1>')
        root.bind('<KeyPress>', on_diff_tkinter_key)
        root.bind('<Button-1>', on_diff_mouse_click)
    
    draw_menu()
    
    # Bind tkinter keys for menu
    print("DEBUG: Binding tkinter keys for menu...")
    root.bind('<KeyPress>', on_tkinter_key)
    root.bind('<Button-1>', on_mouse_click)
    
    while menu_running:
        # Redraw if refresh text is fading
        if refresh_text_alpha > 0:
            draw_menu()
        root.update()
        time.sleep(0.01)
    
    # Unbind menu keys
    root.unbind('<KeyPress>')
    root.unbind('<Button-1>')
    print(f"DEBUG: Returning from menu, chart_id={current_chart_id}")
    
    return current_chart_id is not None

def save_settings():
    """Save settings to file"""
    import json
    settings_file = "settings.json"
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"Settings saved to {settings_file}")
    except Exception as e:
        print(f"Error saving settings: {e}")

def load_settings():
    """Load settings from file"""
    import json
    settings_file = "settings.json"
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                loaded = json.load(f)
                settings.update(loaded)
                rebuild_key_mappings()
            print(f"Settings loaded from {settings_file}")
        except Exception as e:
            print(f"Error loading settings: {e}")

def show_options_menu():
    """Display options menu for changing settings"""
    menu_running = True
    selected_option = 0
    current_page = 0  # 0 = Main, 1 = Visual, 2 = Audio, 3 = Gameplay, 4 = Performance
    options_pages = {
        0: ['Visual Settings', 'Audio Settings', 'Gameplay Settings', 'Performance Settings', 'Change Keys', 'Scroll Speed', 'Export Settings', 'Import Settings', 'Save & Back'],
        1: ['Note Size', 'Hit Bar Position', 'Background Dim', 'Show FPS', 'Show Timing Zones', 'Colorblind Mode', 'High Contrast Mode', 'Show Late/Early', 'Back'],
        2: ['Music Volume', 'SFX Volume', 'Global Offset', 'Back'],
        3: ['Timing Windows', 'Back'],
        4: ['FPS Target', 'Renderer', 'Show Performance Metrics', 'Back']
    }
    options = options_pages[current_page]  # Current options list
    
    # State for key remapping
    remapping_index = None
    
    def draw_options():
        nonlocal options
        canvas.delete('all')
        canvas.configure(bg='black')
        
        page_titles = {0: 'OPTIONS', 1: 'VISUAL SETTINGS', 2: 'AUDIO SETTINGS', 3: 'GAMEPLAY SETTINGS', 4: 'PERFORMANCE SETTINGS'}
        canvas.create_text(width // 2, 50, text=page_titles.get(current_page, 'OPTIONS'),
                         fill='white', font=('Arial', 48, 'bold'))
        
        if remapping_index is not None:
            # Key remapping mode
            canvas.create_text(width // 2, 150, 
                             text=f"Press key for lane {remapping_index + 1} (currently: {settings['key_bindings'][remapping_index]})",
                             fill='yellow', font=('Arial', 20))
            canvas.create_text(width // 2, 200, text="Press ESC to cancel",
                             fill='gray', font=('Arial', 16))
        else:
            # Normal menu
            canvas.create_text(width // 2, 120, text="Use ↑↓ to navigate, ENTER or click to select, ←→ to adjust values, ESC to go back",
                             fill='gray', font=('Arial', 14))
            
            y_pos = 200
            options = options_pages[current_page]
            for i, option in enumerate(options):
                color = 'yellow' if i == selected_option else 'white'
                
                # Format text based on option
                if option == 'Change Keys':
                    keys_text = ''.join(settings['key_bindings'])
                    text = f"{option}: {keys_text}"
                elif option == 'Scroll Speed':
                    text = f"{option}: {settings['scroll_speed_multiplier']:.1f}x"
                elif option == 'Note Size':
                    text = f"{option}: {settings.get('note_size_multiplier', 1.0):.1f}x"
                elif option == 'Hit Bar Position':
                    text = f"{option}: {settings.get('hit_bar_position', 0.9):.2f}"
                elif option == 'Background Dim':
                    text = f"{option}: {settings.get('background_dim', 0)}"
                elif option == 'Show FPS':
                    text = f"{option}: {'ON' if settings.get('show_fps', False) else 'OFF'}"
                elif option == 'Show Timing Zones':
                    text = f"{option}: {'ON' if settings.get('show_timing_zones', False) else 'OFF'}"
                elif option == 'Colorblind Mode':
                    text = f"{option}: {'ON' if settings.get('colorblind_mode', False) else 'OFF'}"
                elif option == 'High Contrast Mode':
                    text = f"{option}: {'ON' if settings.get('high_contrast_mode', False) else 'OFF'}"
                elif option == 'Show Late/Early':
                    text = f"{option}: {'ON' if settings.get('show_late_early', True) else 'OFF'}"
                elif option == 'Music Volume':
                    text = f"{option}: {settings.get('music_volume', 100)}%"
                elif option == 'SFX Volume':
                    text = f"{option}: {settings.get('sfx_volume', 100)}%"
                elif option == 'Global Offset':
                    text = f"{option}: {settings.get('global_offset', 0)}ms"
                elif option == 'Timing Windows':
                    text = f"{option}: {settings.get('timing_windows', 'normal').upper()}"
                elif option == 'FPS Target':
                    text = f"{option}: {settings.get('fps_target', 60)} FPS"
                elif option == 'Renderer':
                    text = f"{option}: {settings.get('renderer', 'auto').upper()}"
                elif option == 'Show Performance Metrics':
                    text = f"{option}: {'ON' if settings.get('show_performance_metrics', False) else 'OFF'}"
                else:
                    text = option
                
                canvas.create_text(width // 2, y_pos, text=text,
                                 fill=color, font=('Arial', 22), tags=f'option_{i}')
                y_pos += 50
        
        root.update()
    
    def on_options_key(event):
        nonlocal menu_running, selected_option, remapping_index, options, current_page
        
        if remapping_index is not None:
            # Key remapping mode
            if event.keysym == 'Escape':
                remapping_index = None
                draw_options()
                return
            
            # Check if key is a valid single character
            if len(event.char) == 1 and event.char.isprintable():
                new_key = event.char.lower()
                # Check if key is already used (except in current slot)
                if new_key not in [settings['key_bindings'][i] for i in range(8) if i != remapping_index]:
                    settings['key_bindings'][remapping_index] = new_key
                    rebuild_key_mappings()
                    remapping_index = None
                    draw_options()
            return
        
        # Normal menu navigation
        if event.keysym == 'Escape':
            menu_running = False
            return
        
        if event.keysym == 'Up':
            selected_option = (selected_option - 1) % len(options)
            draw_options()
        elif event.keysym == 'Down':
            selected_option = (selected_option + 1) % len(options)
            draw_options()
        elif event.keysym == 'Return':
            option_name = options[selected_option]
            if option_name == 'Change Keys':
                # Start key remapping for each lane
                show_key_remap_screen()
            elif option_name in ['Show FPS', 'Show Timing Zones', 'Colorblind Mode', 'High Contrast Mode', 'Show Late/Early', 'Show Performance Metrics']:
                # Toggle boolean settings
                setting_key = {
                    'Show FPS': 'show_fps',
                    'Show Timing Zones': 'show_timing_zones',
                    'Colorblind Mode': 'colorblind_mode',
                    'High Contrast Mode': 'high_contrast_mode',
                    'Show Late/Early': 'show_late_early',
                    'Show Performance Metrics': 'show_performance_metrics'
                }[option_name]
                settings[setting_key] = not settings.get(setting_key, False)
                draw_options()
            elif option_name == 'Renderer':
                # Cycle through renderer options
                renderers = ['auto', 'tkinter', 'opengl']
                current = settings.get('renderer', 'auto')
                current_idx = renderers.index(current) if current in renderers else 0
                settings['renderer'] = renderers[(current_idx + 1) % len(renderers)]
                draw_options()
            elif option_name == 'Save & Back':
                save_settings()
                menu_running = False
            elif option_name in ['Visual Settings', 'Audio Settings', 'Gameplay Settings', 'Performance Settings']:
                # Navigate to subpage
                if option_name == 'Visual Settings':
                    current_page = 1
                elif option_name == 'Audio Settings':
                    current_page = 2
                elif option_name == 'Gameplay Settings':
                    current_page = 3
                elif option_name == 'Performance Settings':
                    current_page = 4
                selected_option = 0
                options = options_pages[current_page]
                draw_options()
            elif option_name == 'Back':
                # Return to main page
                current_page = 0
                selected_option = 0
                options = options_pages[current_page]
                draw_options()
        elif event.keysym == 'Left':
            # Handle left arrow for adjustable values
            option_name = options[selected_option]
            if option_name == 'Scroll Speed':
                settings['scroll_speed_multiplier'] = max(0.1, settings['scroll_speed_multiplier'] - 0.1)
                draw_options()
            elif option_name == 'FPS Target':
                # Decrease by 10, min 1
                settings['fps_target'] = max(1, settings.get('fps_target', 60) - 10)
                draw_options()
        elif event.keysym == 'Right':
            # Handle right arrow for adjustable values
            option_name = options[selected_option]
            if option_name == 'Scroll Speed':
                settings['scroll_speed_multiplier'] = min(10.0, settings['scroll_speed_multiplier'] + 0.1)
                draw_options()
            elif option_name == 'FPS Target':
                # Increase by 10, max 600
                settings['fps_target'] = min(600, settings.get('fps_target', 60) + 10)
                draw_options()
    
    def on_options_mouse_click(event):
        nonlocal menu_running, selected_option, remapping_index, options
        
        if remapping_index is not None:
            # Ignore clicks during key remapping
            return
        
        # Get clicked item
        items = canvas.find_overlapping(event.x - 10, event.y - 10, event.x + 10, event.y + 10)
        for item in items:
            tags = canvas.gettags(item)
            for tag in tags:
                if tag.startswith('option_'):
                    option_index = int(tag.split('_')[1])
                    if options[option_index] == 'Change Keys':
                        show_key_remap_screen()
                    elif options[option_index] == 'Scroll Speed':
                        # Toggle through some common values on click
                        current = settings['scroll_speed_multiplier']
                        presets = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
                        if current in presets:
                            idx = (presets.index(current) + 1) % len(presets)
                            settings['scroll_speed_multiplier'] = presets[idx]
                        else:
                            settings['scroll_speed_multiplier'] = 1.0
                        draw_options()
                    elif options[option_index] == 'Save & Back':
                        save_settings()
                        menu_running = False
                    return
    
    def show_key_remap_screen():
        """Show screen for remapping all keys"""
        nonlocal remapping_index
        for i in range(8):
            remapping_index = i
            draw_options()
            
            # Wait for key press
            waiting = True
            def wait_key(event):
                nonlocal waiting, remapping_index
                if event.keysym == 'Escape':
                    remapping_index = None
                    waiting = False
                    return
                
                if len(event.char) == 1 and event.char.isprintable():
                    new_key = event.char.lower()
                    # Check if key is already used
                    if new_key not in [settings['key_bindings'][j] for j in range(8) if j != i]:
                        settings['key_bindings'][i] = new_key
                        rebuild_key_mappings()
                        waiting = False
            
            root.unbind('<KeyPress>')
            root.bind('<KeyPress>', wait_key)
            
            while waiting:
                root.update()
                time.sleep(0.01)
            
            if remapping_index is None:
                # User cancelled
                break
        
        remapping_index = None
        root.unbind('<KeyPress>')
        root.bind('<KeyPress>', on_options_key)
        draw_options()
    
    draw_options()
    root.bind('<KeyPress>', on_options_key)
    root.bind('<Button-1>', on_options_mouse_click)
    
    while menu_running:
        root.update()
        time.sleep(0.01)
    
    root.unbind('<KeyPress>')
    root.unbind('<Button-1>')

def show_profile_menu():
    """Display profile/stats menu"""
    menu_running = True
    
    def draw_profile():
        canvas.delete('all')
        canvas.configure(bg='black')
        
        # Load progress data
        progress = load_progress()
        if not progress:
            canvas.create_text(width // 2, height // 2, 
                             text="No progress data found",
                             fill='red', font=('Arial', 24))
            root.update()
            return
        
        # Title
        canvas.create_text(width // 2, 50, 
                         text=f"Profile: {progress.get('username', 'Player')}",
                         fill='white', font=('Arial', 48, 'bold'))
        
        # Stats
        y_pos = 150
        total_plays = progress.get('total_charts_played', 0)
        total_notes = (progress.get('total_perfects', 0) + 
                      progress.get('total_greats', 0) + 
                      progress.get('total_goods', 0) + 
                      progress.get('total_bads', 0) + 
                      progress.get('total_misses', 0))
        
        if total_notes > 0:
            weighted_score = (progress.get('total_perfects', 0) * 100 + 
                            progress.get('total_greats', 0) * 70 + 
                            progress.get('total_goods', 0) * 40 + 
                            progress.get('total_bads', 0) * 10)
            avg_accuracy = weighted_score / (total_notes * 100.0) * 100.0
        else:
            avg_accuracy = 0.0
        
        # Get best rank
        best_scores = progress.get('best_scores', {})
        best_rank = 'D'
        for chart_key, chart_data in best_scores.items():
            rank = chart_data.get('rank', 'D')
            if rank == 'S' or (rank == 'A' and best_rank not in ['S']) or \
               (rank == 'B' and best_rank not in ['S', 'A']) or \
               (rank == 'C' and best_rank == 'D'):
                best_rank = rank
        
        # Stats display
        stats = [
            f"Total Plays: {total_plays}",
            f"Total Score: {progress.get('total_score', 0):,}",
            f"Average Accuracy: {avg_accuracy:.2f}%",
            f"Best Rank: {best_rank}",
            f"Total Playtime: {progress.get('total_playtime_seconds', 0) // 60} minutes",
            "",
            f"Perfect: {progress.get('total_perfects', 0)}  |  Great: {progress.get('total_greats', 0)}",
            f"Good: {progress.get('total_goods', 0)}  |  Bad: {progress.get('total_bads', 0)}  |  Miss: {progress.get('total_misses', 0)}"
        ]
        
        for stat in stats:
            canvas.create_text(width // 2, y_pos, text=stat,
                             fill='cyan', font=('Arial', 24))
            y_pos += 40
        
        # Achievements
        y_pos += 20
        canvas.create_text(width // 2, y_pos, text="--- Achievements ---",
                         fill='yellow', font=('Arial', 28, 'bold'))
        y_pos += 50
        
        achievements = progress.get('achievements', {})
        if achievements:
            for ach_key, ach_data in list(achievements.items())[:5]:  # Show first 5
                canvas.create_text(width // 2, y_pos, 
                                 text=f"🏆 {ach_data['name']}: {ach_data['description']}",
                                 fill='gold', font=('Arial', 18))
                y_pos += 35
        else:
            canvas.create_text(width // 2, y_pos, text="No achievements yet",
                             fill='gray', font=('Arial', 18))
        
        canvas.create_text(width // 2, height - 50, 
                         text="Press ESC or click anywhere to go back",
                         fill='gray', font=('Arial', 16))
        root.update()
    
    def on_profile_key(event):
        nonlocal menu_running
        if event.keysym == 'Escape':
            menu_running = False
    
    def on_profile_click(event):
        nonlocal menu_running
        menu_running = False
    
    draw_profile()
    root.bind('<KeyPress>', on_profile_key)
    root.bind('<Button-1>', on_profile_click)
    
    while menu_running:
        root.update()
        time.sleep(0.01)
    
    root.unbind('<KeyPress>')
    root.unbind('<Button-1>')

def show_main_menu():
    """Display main menu"""
    menu_running = True
    selected_option = 0
    options = ['Play', 'Watch Replay', 'Profile', 'Options', 'Quit']
    
    def draw_menu():
        canvas.delete('all')
        canvas.configure(bg='black')
        
        canvas.create_text(width // 2, 100, text="random game",
                         fill='white', font=('Arial', 32, 'bold'))
        
        canvas.create_text(width // 2, 200, text="Use ↑↓ to navigate, ENTER or click to select",
                         fill='gray', font=('Arial', 16))
        
        y_pos = 300
        for i, option in enumerate(options):
            color = 'yellow' if i == selected_option else 'white'
            canvas.create_text(width // 2, y_pos, text=option,
                             fill=color, font=('Arial', 36), tags=f'main_{i}')
            y_pos += 80
        
        root.update()
    
    def on_main_key(event):
        nonlocal menu_running, selected_option
        
        if event.keysym == 'Escape':
            selected_option = 4  # Quit (index updated for new menu item)
            menu_running = False
            return
        
        if event.keysym == 'Up':
            selected_option = (selected_option - 1) % len(options)
            draw_menu()
        elif event.keysym == 'Down':
            selected_option = (selected_option + 1) % len(options)
            draw_menu()
        elif event.keysym == 'Return':
            menu_running = False
    
    def on_main_mouse_click(event):
        nonlocal menu_running, selected_option
        
        # Get clicked item
        items = canvas.find_overlapping(event.x - 10, event.y - 10, event.x + 10, event.y + 10)
        for item in items:
            tags = canvas.gettags(item)
            for tag in tags:
                if tag.startswith('main_'):
                    selected_option = int(tag.split('_')[1])
                    menu_running = False
                    return
    
    draw_menu()
    root.bind('<KeyPress>', on_main_key)
    root.bind('<Button-1>', on_main_mouse_click)
    
    while menu_running:
        root.update()
        time.sleep(0.01)
    
    root.unbind('<KeyPress>')
    root.unbind('<Button-1>')
    
    return options[selected_option]

def show_pregame_setup(chart_id, difficulty):
    """Show pre-game setup GUI for speed, calibration, and mode selection"""
    global game_mode, settings
    
    setup_running = True
    start_game_flag = False  # Track if user wants to start (Enter) or go back (Esc)
    current_speed = settings.get('scroll_speed_multiplier', 1.0)
    selected_mode = game_mode if game_mode in ['auto', 'practice'] else 'normal'
    calibrating = False
    metronome_beats = []
    last_beat_time = 0  # For visual flash effect
    
    def draw_setup():
        canvas.delete('all')
        canvas.configure(bg='black')
        
        # Title
        canvas.create_text(width // 2, 50, text=f"Setup: {chart_id} - {difficulty}",
                         fill='white', font=('Arial', 32, 'bold'))
        
        # Speed selector
        y_pos = 150
        canvas.create_text(width // 2, y_pos, text="Note Speed Multiplier",
                         fill='cyan', font=('Arial', 24, 'bold'))
        y_pos += 50
        
        # Speed preview bar
        bar_x = width // 2 - 200
        bar_width = 400
        canvas.create_rectangle(bar_x, y_pos, bar_x + bar_width, y_pos + 30,
                              fill='#333333', outline='white', width=2)
        
        # Current speed indicator
        speed_pos = bar_x + int((current_speed - 0.5) / 4.0 * bar_width)
        canvas.create_rectangle(speed_pos - 5, y_pos - 5, speed_pos + 5, y_pos + 35,
                              fill='yellow', outline='white', width=2)
        
        canvas.create_text(width // 2, y_pos + 50, 
                         text=f"{current_speed:.1f}x (←→ to adjust, 0.5x - 4.5x)",
                         fill='white', font=('Arial', 18))
        
        # Mode selection
        y_pos += 120
        canvas.create_text(width // 2, y_pos, text="Game Mode",
                         fill='cyan', font=('Arial', 24, 'bold'))
        y_pos += 40
        
        modes = [('Normal', 'normal'), ('Auto Play', 'auto'), ('Practice', 'practice')]
        for i, (mode_name, mode_key) in enumerate(modes):
            x_pos = width // 2 - 200 + i * 200
            color = 'yellow' if mode_key == selected_mode else 'white'
            canvas.create_text(x_pos, y_pos, text=f"{i+1}. {mode_name}",
                             fill=color, font=('Arial', 20), tags=f'mode_{mode_key}')
        
        # Calibration section
        y_pos += 80
        canvas.create_text(width // 2, y_pos, text="Offset Calibration",
                         fill='cyan', font=('Arial', 24, 'bold'))
        y_pos += 40
        
        current_offset = settings.get('global_offset', 0)
        canvas.create_text(width // 2, y_pos, 
                         text=f"Current Offset: {current_offset}ms",
                         fill='white', font=('Arial', 18))
        y_pos += 35
        
        if calibrating:
            # Show calibration progress with visual indicators
            canvas.create_text(width // 2, y_pos, 
                             text=f"Tap SPACE to the beat! ({len(metronome_beats)}/8)",
                             fill='lime', font=('Arial', 20, 'bold'))
            y_pos += 50
            
            # Draw beat indicators (circles for each tap)
            circle_y = y_pos
            circle_spacing = 60
            start_x = width // 2 - (7 * circle_spacing) // 2
            
            for i in range(8):
                x = start_x + i * circle_spacing
                if i < len(metronome_beats):
                    # Filled circle for completed beats
                    # Flash effect: check if this was the last beat tapped
                    time_since_beat = time.time() - last_beat_time
                    if i == len(metronome_beats) - 1 and time_since_beat < 0.15:
                        # Flash yellow for the most recent beat
                        color = 'yellow'
                        size = 25
                    else:
                        color = 'lime'
                        size = 20
                    canvas.create_oval(x - size, circle_y - size, x + size, circle_y + size,
                                     fill=color, outline='white', width=3)
                else:
                    # Empty circle for pending beats
                    canvas.create_oval(x - 15, circle_y - 15, x + 15, circle_y + 15,
                                     fill='', outline='gray', width=2)
            
            y_pos += 60
            
            # Show interval consistency if we have at least 2 beats
            if len(metronome_beats) >= 2:
                intervals = []
                for i in range(1, len(metronome_beats)):
                    intervals.append(metronome_beats[i] - metronome_beats[i-1])
                avg_interval = sum(intervals) / len(intervals)
                bpm = 60.0 / avg_interval
                
                # Show detected BPM
                canvas.create_text(width // 2, y_pos,
                                 text=f"Detected tempo: {bpm:.1f} BPM",
                                 fill='cyan', font=('Arial', 16))
                y_pos += 30
                
                # Show consistency indicator
                if len(intervals) >= 2:
                    variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                    std_dev = variance ** 0.5
                    consistency = max(0, 1 - (std_dev / avg_interval) * 5)  # 0 to 1
                    
                    # Draw consistency bar
                    bar_width = 300
                    bar_x = width // 2 - bar_width // 2
                    canvas.create_rectangle(bar_x, y_pos, bar_x + bar_width, y_pos + 20,
                                          fill='#333333', outline='white', width=1)
                    fill_width = int(bar_width * consistency)
                    bar_color = 'lime' if consistency > 0.7 else 'yellow' if consistency > 0.4 else 'red'
                    if fill_width > 0:
                        canvas.create_rectangle(bar_x, y_pos, bar_x + fill_width, y_pos + 20,
                                              fill=bar_color, outline='')
                    canvas.create_text(width // 2, y_pos + 30,
                                     text=f"Consistency: {consistency*100:.0f}%",
                                     fill='white', font=('Arial', 14))
        else:
            canvas.create_text(width // 2, y_pos, 
                             text="Press C to auto-calibrate (tap 8 beats)",
                             fill='gray', font=('Arial', 16))
        
        # Manual offset adjustment
        y_pos += 50
        canvas.create_text(width // 2, y_pos, 
                         text="Manual: [ = -10ms  ] = +10ms  \\ = Reset",
                         fill='gray', font=('Arial', 16))
        
        # Instructions
        canvas.create_text(width // 2, height - 100,
                         text="ENTER to start  |  ESC to go back",
                         fill='white', font=('Arial', 20, 'bold'))
        
        root.update()
    
    def on_setup_key(event):
        nonlocal setup_running, start_game_flag, current_speed, selected_mode, calibrating, metronome_beats, last_beat_time
        
        if event.keysym == 'Escape':
            setup_running = False
            start_game_flag = False
            return
        elif event.keysym == 'Return':
            # Save settings and start game
            settings['scroll_speed_multiplier'] = current_speed
            global game_mode
            game_mode = selected_mode
            setup_running = False
            start_game_flag = True
            return
        
        # Speed adjustment
        if event.keysym == 'Left':
            current_speed = max(0.5, current_speed - 0.1)
            draw_setup()
        elif event.keysym == 'Right':
            current_speed = min(4.5, current_speed + 0.1)
            draw_setup()
        
        # Mode selection
        if event.char and event.char.isdigit():
            num = int(event.char)
            if num == 1:
                selected_mode = 'normal'
            elif num == 2:
                selected_mode = 'auto'
            elif num == 3:
                selected_mode = 'practice'
            draw_setup()
        
        # Calibration
        if event.char and event.char.lower() == 'c':
            calibrating = True
            metronome_beats = []
            draw_setup()
        
        # Manual offset adjustment
        if event.char == '[':
            settings['global_offset'] = settings.get('global_offset', 0) - 10
            draw_setup()
        elif event.char == ']':
            settings['global_offset'] = settings.get('global_offset', 0) + 10
            draw_setup()
        elif event.char == '\\':
            settings['global_offset'] = 0
            draw_setup()
        
        # Metronome tap for calibration
        if calibrating and event.char == ' ':
            current_time = time.time()
            metronome_beats.append(current_time)
            last_beat_time = current_time  # For visual flash effect
            if len(metronome_beats) >= 8:
                # Calculate average interval and set offset
                intervals = []
                for i in range(1, len(metronome_beats)):
                    intervals.append(metronome_beats[i] - metronome_beats[i-1])
                avg_interval = sum(intervals) / len(intervals)
                # Assume 120 BPM target, calculate offset
                expected_interval = 60.0 / 120.0  # 0.5 seconds per beat
                offset_seconds = avg_interval - expected_interval
                settings['global_offset'] = int(offset_seconds * 1000)
                calibrating = False
                metronome_beats = []
            draw_setup()
    
    draw_setup()
    root.bind('<KeyPress>', on_setup_key)
    
    while setup_running:
        # Continuously redraw if calibrating to show flash animation
        if calibrating:
            draw_setup()
        root.update()
        time.sleep(0.01)
    
    root.unbind('<KeyPress>')
    return start_game_flag  # True means start, False means go back

def start_game(chart_id, difficulty):
    """Initialize and start the game"""
    global current_chart_id, current_difficulty, replay_data, game_running
    global practice_speed, practice_loop_start, practice_loop_end, practice_looping
    
    # Show pre-game setup
    if not show_pregame_setup(chart_id, difficulty):
        return  # User pressed ESC to go back
    
    current_chart_id = chart_id
    current_difficulty = difficulty
    replay_data = []  # Clear any previous replay data
    game_running = True  # Enable keyboard input
    
    # Reset practice mode variables
    practice_speed = 1.0
    practice_loop_start = None
    practice_loop_end = None
    practice_looping = False
    
    print(f"DEBUG: Starting game with chart {chart_id}, difficulty {difficulty}, mode {game_mode}")
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
    load_settings()  # Load settings at startup
    
    while True:
        # Show main menu
        choice = show_main_menu()
        
        if choice == 'Play':
            # Show chart selection menu
            if show_chart_menu():
                start_game(current_chart_id, current_difficulty)
        elif choice == 'Watch Replay':
            # Show replay selection menu
            show_replay_menu()
        elif choice == 'Profile':
            # Show profile/stats menu
            show_profile_menu()
        elif choice == 'Options':
            show_options_menu()
        elif choice == 'Quit':
            break