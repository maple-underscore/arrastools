import time, threading, os, mss, numpy as np
import platform
from pathlib import Path
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import re

# Detect platform
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows'
print(f"Arras Copypasta running on: {PLATFORM}")

# Platform notes
if PLATFORM not in ('darwin', 'linux', 'windows'):
    print(f"Warning: Platform '{PLATFORM}' may have limited support.")
    print("Tested on macOS, Linux (Arch/Debian/Ubuntu), and Windows.")

#each line should be 60 chars long
global ids, copypastaing, controller, thread, filepaths, current_chars, current_percent
sct = mss.mss()
def get_pixel_rgb(x, y):
    bbox = {"top": int(y), "left": int(x), "width": 1, "height": 1}
    img = sct.grab(bbox)
    pixel = np.array(img.pixel(0, 0))
    return tuple(int(v) for v in pixel[:3])

# Use pathlib for cross-platform file paths
# Get script directory and locate copypastas folder relative to it
script_dir = Path(__file__).parent
copypasta_dir = script_dir / 'copypastas'

# Ensure copypastas directory exists
if not copypasta_dir.exists():
    print(f"Warning: copypastas directory not found at {copypasta_dir}")
    print("Creating directory...")
    copypasta_dir.mkdir(parents=True, exist_ok=True)

ids = []
filepaths = []
for fpath in copypasta_dir.glob('*.txt'):
    if fpath.is_file():
        ids.append(fpath.stem)  # Get filename without extension
        filepaths.append(str(fpath))  # Convert Path to string for compatibility
copypastaing = False
thread = None
controller = KeyboardController()
current_chars = 0
current_percent = 0

def interruptible_sleep(duration):
    global copypastaing
    interval = 0.05  # 50ms
    elapsed = 0
    while copypastaing and elapsed < duration:
        time.sleep(interval)
        elapsed += interval

def split_sentences(filepath, max_length=60, disable_space_breaking=False, disable_line_breaks=False):
    sentences = []
    with open(filepath, encoding='utf-8') as file:
        lines = file.readlines()
        
        # If disable_line_breaks is True, merge all lines into one continuous text
        if disable_line_breaks:
            lines = [' '.join(line.rstrip() for line in lines if line.strip())]
        
        for line in lines:
            line = line.rstrip()
            if not line.strip():
                continue
            if disable_space_breaking:
                # Break only at max_length, preserving all characters including spaces
                buffer = line
                while len(buffer) > max_length:
                    chunk = buffer[:max_length]
                    sentences.append(chunk)
                    print(f"[DEBUG] No-space chunk ({len(chunk)} chars): '{chunk}'")  # Debug
                    buffer = buffer[max_length:]
                if buffer:
                    sentences.append(buffer)
                    print(f"[DEBUG] No-space final ({len(buffer)} chars): '{buffer}'")  # Debug
            else:
                # Break at spaces, but always start a new sentence at each line
                words = line.split()
                buffer = ""
                for word in words:
                    if buffer:
                        if len(buffer) + 1 + len(word) > max_length:
                            sentences.append(buffer)
                            print(f"[DEBUG] Space-broken chunk ({len(buffer)} chars): '{buffer}'")  # Debug
                            buffer = word
                        else:
                            buffer += " " + word
                    else:
                        if len(word) > max_length:
                            sentences.append(word[:max_length])
                            print(f"[DEBUG] Long word chunk ({len(word[:max_length])} chars): '{word[:max_length]}'")  # Debug
                            buffer = word[max_length:]
                        else:
                            buffer = word
                if buffer:
                    sentences.append(buffer)
                    print(f"[DEBUG] Space-broken final ({len(buffer)} chars): '{buffer}'")  # Debug
    return sentences

pause_event = threading.Event()
pause_event.set()  # Start as running

def replace_emojis(text):
    # Emoji unicode ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # geometric shapes extended
        "\U0001F800-\U0001F8FF"  # supplemental arrows-c
        "\U0001F900-\U0001F9FF"  # supplemental symbols & pictographs
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols & pictographs extended-a
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(':e:', text)

def copypasta(id, prepare=False, disable_space_breaking=False, disable_finish_text=False, disable_line_breaks=False):
    time.sleep(2)
    global ids, copypastaing, filepaths, controller, pause_event, current_chars, current_percent
    if id in ids:
        index = ids.index(id)
        filepath = filepaths[index]
        copypastaing = True
        start = time.time()
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return
        sentences = split_sentences(filepath, disable_space_breaking=disable_space_breaking, disable_line_breaks=disable_line_breaks)
        leng = sum(len(replace_emojis(s)) for s in sentences)
        pos = 0
        if prepare:
            file_size_bytes = os.path.getsize(filepath)
            file_size_kb = file_size_bytes / 1024
            end = time.time()
            # Extract just the copypastas/filename.txt part for display
            path_obj = Path(filepath)
            relative_path = f"copypastas/{path_obj.name}"
            controller.tap(Key.enter)
            interruptible_sleep(0.1)
            controller.type(f"Arras Copypasta Utility [ACU] > v02.04.11-beta.4 < loading")
            interruptible_sleep(0.1)
            for _ in range(2):
                controller.tap(Key.enter)
                interruptible_sleep(0.1)
            controller.type(f"Filepath: > [.../{relative_path}] < | Loaded > {leng} chars <")
            interruptible_sleep(0.1)
            for _ in range(2):
                controller.tap(Key.enter)
                interruptible_sleep(0.1)
            controller.type(f"Size: > [{file_size_kb:.2f}KB] < | Time taken > [{round((end-start)*1000, 3)}ms] <")
            interruptible_sleep(0.1)
            controller.tap(Key.enter)
            interruptible_sleep(10)
        endf = False
        for sentence in sentences:
            if not copypastaing:
                break
            pause_event.wait()  # Wait here if paused
            controller.tap(Key.enter)
            interruptible_sleep(0.1)
            sentence_no_emoji = replace_emojis(sentence)
            controller.type(sentence_no_emoji)
            interruptible_sleep(0.1)
            controller.tap(Key.enter)
            pos += len(sentence_no_emoji)
            current_chars = pos
            current_percent = (current_chars / leng) * 100 if leng > 0 else 0
            interruptible_sleep(3.3)  # replaces time.sleep(3.3)
            endf = True
        # After loop ends, print/type summary
        chars_typed = pos if pos < leng else leng
        percent_typed = (chars_typed / leng) * 100 if leng > 0 else 0
        if not endf:  # Force stop by Escape
            print(f"Forced stop at > [{chars_typed}] characters [{percent_typed:.2f}%]")
            controller.tap(Key.enter)
            interruptible_sleep(0.1)
            controller.type(f"Forced stop at > [{chars_typed}] characters [{percent_typed:.2f}%]")
            interruptible_sleep(0.1)
        else:
            if not disable_finish_text:
                print(f"Copypasta of > [{leng}] characters < finished")
                controller.tap(Key.enter)
                interruptible_sleep(0.1)
                controller.type(f"Copypasta of > [{leng}] characters < finished")
                interruptible_sleep(0.1)
            else:
                print(f"Copypasta of > [{leng}] characters < finished (without finish text)")
        if not disable_finish_text:
            controller.tap(Key.enter)
            interruptible_sleep(0.1)
            time.sleep(3.5)
            controller.tap(Key.enter)
            interruptible_sleep(0.1)
            print(f"Time taken: > [{round(1000*(time.time()-start), 3)}ms] <")
            controller.type(f"Time taken: > [{round(1000*(time.time()-start), 3)}ms] <")
            interruptible_sleep(0.1)
            controller.tap(Key.enter)
            interruptible_sleep(0.1)
        # Do not exit here; let the thread finish
    copypastaing = False

def on_press(key):
    global copypastaing, pause_event, current_chars, current_percent, controller
    try:
        if key == keyboard.Key.esc:
            copypastaing = False
        elif hasattr(key, 'char') and key.char == 'p' and copypastaing:
            if pause_event.is_set():
                pause_event.clear()
                time.sleep(3.3)
                print(f"Paused at > [{current_chars}] < chars | > [{current_percent:.2f}%] <")
                controller.tap(Key.enter)
                interruptible_sleep(0.1)
                controller.type(f"Paused at > [{current_chars}] < chars | > [{current_percent:.2f}%] <")
                interruptible_sleep(0.1)
                controller.tap(Key.enter)
                interruptible_sleep(0.1)
            else:
                pause_event.set()
                time.sleep(3.3)
                print(f"Resumed at > [{current_chars}] < chars | > [{current_percent:.2f}%] <")
                controller.tap(Key.enter)
                interruptible_sleep(0.1)
                controller.type(f"Resumed at > [{current_chars}] < chars | > [{current_percent:.2f}%] <")
                interruptible_sleep(0.1)
                controller.tap(Key.enter)
                interruptible_sleep(0.1)
    except UnicodeDecodeError:
        print("UnicodeDecodeError: Non-standard key (emoji?) pressed. Ignored.")

listener = keyboard.Listener(on_press=on_press)
listener.daemon = True
listener.start()

while True:
    id_input = input("Enter copypasta id > ").strip()
    prepare_input = input("Prepare mode? (true/false) > ").strip().lower()
    disable_space_breaking_input = input("Disable space breaking? (true/false) > ").strip().lower()
    disable_line_breaks_input = input("Disable line breaks? (true/false) > ").strip().lower()
    disable_finish_text_input = input("Disable finish text? (true/false) > ").strip().lower()

    prepare = prepare_input == 'true'
    disable_space_breaking = disable_space_breaking_input == 'true'
    disable_line_breaks = disable_line_breaks_input == 'true'
    disable_finish_text = disable_finish_text_input == 'true'

    if id_input in ids:
        if copypastaing:
            print("Already copypastaing, wait until finished or press Escape to stop")
        else:
            thread = threading.Thread(target=copypasta, args=(id_input, prepare, disable_space_breaking, disable_finish_text, disable_line_breaks))
            thread.start()
    else:
        print("Invalid id, available ids are:")
        print(ids)
        print("Using 'char' as default id for testing purposes")
        if copypastaing:
            print("Already copypastaing, wait until finished or press Escape to stop")
        else:
            thread = threading.Thread(target=copypasta, args=('char', prepare, disable_space_breaking, disable_finish_text, disable_line_breaks))
            thread.start()
    done = False
    while not done:
        if thread is not None and not thread.is_alive():
            done = True
        time.sleep(0.1)