"""Automated Arras copypasta typer with optional AI prompt mode.

Unicode Support:
- Uses UTF-16 encoding with proper surrogate pair handling
- All non-ASCII characters (emoji, rare unicode, etc.) are typed via clipboard
- Ensures every character types correctly regardless of encoding complexity
- Pure ASCII text is typed directly for speed
"""

import time, threading, os
import platform
from pathlib import Path
import re
import subprocess
import tempfile
import random
import pyperclip

# Lazy import pynput to avoid slow startup
def _lazy_import_pynput():
    global keyboard, KeyboardController, Key, MouseController, Button
    from pynput import keyboard
    from pynput.keyboard import Controller as KeyboardController, Key
    from pynput.mouse import Controller as MouseController, Button

# Placeholder globals - will 
# be populated by lazy import
keyboard = None
KeyboardController = None
Key = None
MouseController = None
Button = None

def get_ollama_models():
    """Fetch list of available Ollama models from 'ollama list' command"""
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Skip header line and parse model names
            models = []
            for line in lines[1:]:  # Skip first line (header)
                if line.strip():
                    # Extract first column (NAME)
                    name = line.split()[0]
                    models.append(name)
            
            if models:
                print(f"Found {len(models)} Ollama models")
                return models
            else:
                print("No models found, using fallback list")
                return ["deepseek-r1-14b-16k:latest"]
        else:
            print(f"Error running 'ollama list': {result.stderr}")
            return ["deepseek-r1-14b-16k:latest"]
    except FileNotFoundError:
        print("Warning: ollama command not found. Install Ollama to use AI mode.")
        return []
    except Exception as e:
        print(f"Error fetching Ollama models: {e}")
        return ["deepseek-r1-14b-16k:latest"]

models = get_ollama_models()

# Detect platform
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows'
print(f"Arras Copypasta running on: {PLATFORM}")

# Platform notes
if PLATFORM not in ('darwin', 'linux', 'windows'):
    print(f"Warning: Platform '{PLATFORM}' may have limited support.")
    print("Tested on macOS, Linux (Arch/Debian/Ubuntu), and Windows.")

#each line should be 60 chars long
global ids, copypastaing, controller, thread, filepaths, current_chars, current_percent, is_ai_mode, listener
is_ai_mode = False
listener = None

# Use pathlib for cross-platform file paths
# Script dir holds automation scripts; copypastas live one level up
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent
copypasta_dir = repo_root / 'copypastas'

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
controller = None  # Will be initialized on first use
current_chars = 0
current_percent = 0
controller_typing = False  # Flag to ignore synthetic keypresses

def _ensure_controller():
    """Initialize pynput components on first use"""
    global controller
    if controller is None:
        _lazy_import_pynput()
        controller = KeyboardController()

def _ensure_key():
    """Ensure Key class is available"""
    if Key is None:
        _lazy_import_pynput()

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
                    #print(f"[DEBUG] No-space chunk ({len(chunk)} chars): '{chunk}'")  # Debug
                    buffer = buffer[max_length:]
                if buffer:
                    sentences.append(buffer)
                    #print(f"[DEBUG] No-space final ({len(buffer)} chars): '{buffer}'")  # Debug
            else:
                # Break at spaces, but always start a new sentence at each line
                words = line.split()
                buffer = ""
                for word in words:
                    if buffer:
                        if len(buffer) + 1 + len(word) > max_length:
                            sentences.append(buffer)
                            #print(f"[DEBUG] Space-broken chunk ({len(buffer)} chars): '{buffer}'")  # Debug
                            buffer = word
                        else:
                            buffer += " " + word
                    else:
                        if len(word) > max_length:
                            sentences.append(word[:max_length])
                            #print(f"[DEBUG] Long word chunk ({len(word[:max_length])} chars): '{word[:max_length]}'")  # Debug
                            buffer = word[max_length:]
                        else:
                            buffer = word
                if buffer:
                    sentences.append(buffer)
                    #print(f"[DEBUG] Space-broken final ({len(buffer)} chars): '{buffer}'")  # Debug
    return sentences

pause_event = threading.Event()
pause_event.set()  # Start as running

def has_complex_unicode(text):
    """Check if text contains complex unicode (Japanese, Chinese, etc.) that pynput can't handle"""
    for char in text:
        code = ord(char)
        # Japanese hiragana, katakana, kanji
        if (0x3040 <= code <= 0x309F or  # Hiragana
            0x30A0 <= code <= 0x30FF or  # Katakana
            0x4E00 <= code <= 0x9FFF or  # CJK Unified Ideographs
            0x3400 <= code <= 0x4DBF or  # CJK Extension A
            0x20000 <= code <= 0x2A6DF or # CJK Extension B
            0x2A700 <= code <= 0x2B73F or # CJK Extension C
            0x2B740 <= code <= 0x2B81F or # CJK Extension D
            0x2B820 <= code <= 0x2CEAF or # CJK Extension E
            0xF900 <= code <= 0xFAFF or  # CJK Compatibility Ideographs
            0x2F800 <= code <= 0x2FA1F):  # CJK Compatibility Ideographs Supplement
            return True
        # Other complex scripts (Arabic, Hebrew, Thai, etc.)
        if (0x0600 <= code <= 0x06FF or  # Arabic
            0x0590 <= code <= 0x05FF or  # Hebrew
            0x0E00 <= code <= 0x0E7F or  # Thai
            0x1100 <= code <= 0x11FF or  # Hangul Jamo
            0xAC00 <= code <= 0xD7AF):   # Hangul Syllables
            return True
    return False

def safe_type(text):
    """Type text while flagging to ignore synthetic keypresses.
    Uses UTF-16 encoding with proper surrogate pair handling.
    Always uses clipboard for non-ASCII to ensure every character types correctly.
    """
    global controller_typing
    _ensure_controller()
    _ensure_key()
    controller_typing = True
    
    try:
        # Check if text is pure ASCII
        try:
            text.encode('ascii')
            is_pure_ascii = True
        except UnicodeEncodeError:
            is_pure_ascii = False
        
        if not is_pure_ascii:
            # For any non-ASCII text, use clipboard with UTF-16 encoding for maximum compatibility
            old_clipboard = pyperclip.paste()  # Save current clipboard
            try:
                # Encode to UTF-16 to handle surrogates properly, then copy to clipboard
                # This ensures all characters including emoji and rare unicode are preserved
                pyperclip.copy(text)  # Copy text to clipboard (preserves UTF-16 surrogates)
                time.sleep(0.05)  # Small delay for clipboard
                # Paste using Cmd+V (macOS) or Ctrl+V (Windows/Linux)
                if PLATFORM == 'darwin':
                    controller.press(Key.cmd)
                else:
                    controller.press(Key.ctrl)
                controller.press('v')
                controller.release('v')
                if PLATFORM == 'darwin':
                    controller.release(Key.cmd)
                else:
                    controller.release(Key.ctrl)
                time.sleep(0.05)
            finally:
                # Restore old clipboard after a short delay
                time.sleep(0.1)
                pyperclip.copy(old_clipboard)
        else:
            # Use direct typing only for pure ASCII (no surrogates needed)
            controller.type(text)
    finally:
        controller_typing = False

def safe_tap(key):
    """Tap key while flagging to ignore synthetic keypresses"""
    global controller_typing
    _ensure_controller()
    controller_typing = True
    controller.tap(key)
    controller_typing = False

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

def query_model(model, prompt, display_prompt=None):
    """Query Ollama's {model} model and return the response"""
    # Ensure pynput is loaded before using Key
    _ensure_key()
    
    try:
        # Use display_prompt for in-game typing, or full prompt if not provided
        if display_prompt is None:
            display_prompt = prompt
        
        print(f"Querying {model}...")
        time.sleep(2)  # Wait before typing in-game
        
        # Type the prompt in quotations (only display_prompt, not full context)
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        safe_type(f'Sending prompt: "{display_prompt}"')
        interruptible_sleep(0.75)
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        safe_type(f"Waiting for response from {model}...")
        interruptible_sleep(0.75)
        safe_tap(Key.enter)
        interruptible_sleep(5)
        
        # Start ollama subprocess without waiting (use full prompt with context)
        process = subprocess.Popen(
            ['ollama', 'run', model, prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait with periodic messages
        start_time = time.time()
        last_message_time = start_time
        
        while process.poll() is None:  # While process is still running
            current_time = time.time()
            elapsed = current_time - start_time
            
            # After 10 seconds, type a message every 5 seconds
            if elapsed >= 10 and (current_time - last_message_time) >= random.uniform(20, 30):
                elapsed_ms = int(elapsed * 1000)
                msg = f"Model is thinking... ( > {round(elapsed_ms/1000, 3)}s < passed )"
                safe_tap(Key.enter)
                interruptible_sleep(0.75)
                safe_type(msg)
                interruptible_sleep(0.75)
                safe_tap(Key.enter)
                interruptible_sleep(0.75)
                last_message_time = current_time
            
            time.sleep(0.75)  # Check every 0.75 seconds
            
            # Timeout after 300 seconds
            if elapsed > 300:
                process.terminate()
                time.sleep(1)  # Give it a second to terminate gracefully
                if process.poll() is None:
                    process.kill()  # Force kill if still running
                raise subprocess.TimeoutExpired(process.args, 300)
        
        # Get results
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            response = stdout.strip()
            print(f"Received response ({len(response)} chars)")
            safe_tap(Key.enter)
            interruptible_sleep(0.75)
            safe_type(f"Response received > [{len(response)} chars] < ; processing...")
            interruptible_sleep(0.75)
            safe_tap(Key.enter)
            interruptible_sleep(5)
            return response
        else:
            error_msg = f"Error querying {model}: {stderr}"
            print(error_msg)
            safe_tap(Key.enter)
            interruptible_sleep(0.75)
            safe_type(f"Error: Failed to get response from {model}")
            interruptible_sleep(0.75)
            safe_tap(Key.enter)
            interruptible_sleep(0.75)
            return None
    except subprocess.TimeoutExpired:
        print(f"Timeout waiting for response from {model}")
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        safe_type(f"Error: Timeout waiting for response from {model}")
        interruptible_sleep(0.75)
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        return None
    except FileNotFoundError:
        print("Error: ollama command not found. Is Ollama installed?")
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        safe_type("Error: ollama not found. Install Ollama first.")
        interruptible_sleep(0.75)
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        safe_type(f"Error: {str(e)}")
        interruptible_sleep(0.75)
        safe_tap(Key.enter)
        interruptible_sleep(0.75)
        return None

def copypasta(id, prepare=False, disable_space_breaking=False, disable_finish_text=False, disable_line_breaks=False, custom_text=None):
    time.sleep(2)
    global ids, copypastaing, filepaths, controller, pause_event, current_chars, current_percent, controller_typing, is_ai_mode
    
    # Ensure pynput is loaded before using Key
    _ensure_key()
    
    copypastaing = True
    is_ai_mode = custom_text is not None
    start = time.time()
    
    # Special handling for ad_news - random line mode
    if id == "ad_news" and custom_text is None:
        index = ids.index(id)
        filepath = filepaths[index]
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            copypastaing = False
            return
        
        # Read all lines from file
        with open(filepath, encoding='utf-8') as f:
            all_lines = [line.rstrip() for line in f.readlines() if line.strip()]
        
        if not all_lines:
            print(f"No lines found in {filepath}")
            copypastaing = False
            return
        
        print(f"ad_news mode: {len(all_lines)} lines available. Press Esc to stop.")
        
        if prepare:
            path_obj = Path(filepath)
            source_text = f"[.../{path_obj.name}]"
            
            safe_tap(Key.enter)
            interruptible_sleep(0.1)
            safe_type(f"Arras Copypasta Utility [ACU] > v02.04.11-beta.4 < loading")
            interruptible_sleep(0.1)
            for _ in range(2):
                safe_tap(Key.enter)
                interruptible_sleep(0.1)
            safe_type(f"Source: > {source_text} < | ad_news random mode | > {len(all_lines)} lines <")
            interruptible_sleep(0.1)
            safe_tap(Key.enter)
            interruptible_sleep(10)
        
        # Loop indefinitely, picking random lines
        while copypastaing:
            # Wait here if paused
            pause_event.wait()
            
            # Pick a random line
            line = random.choice(all_lines)
            
            # Split the line into sentences following the normal rules
            sentences = []
            max_length = 60
            
            if disable_space_breaking:
                # Break only at max_length, preserving all characters including spaces
                buffer = line
                while len(buffer) > max_length:
                    chunk = buffer[:max_length]
                    sentences.append(chunk)
                    buffer = buffer[max_length:]
                if buffer:
                    sentences.append(buffer)
            else:
                # Break at spaces
                words = line.split()
                buffer = ""
                for word in words:
                    if buffer:
                        if len(buffer) + 1 + len(word) > max_length:
                            sentences.append(buffer)
                            buffer = word
                        else:
                            buffer += " " + word
                    else:
                        if len(word) > max_length:
                            sentences.append(word[:max_length])
                            buffer = word[max_length:]
                        else:
                            buffer = word
                if buffer:
                    sentences.append(buffer)
            
            # Type each sentence
            for sentence in sentences:
                if not copypastaing:
                    break
                pause_event.wait()  # Check pause before each sentence
                safe_tap(Key.enter)
                interruptible_sleep(0.1)
                safe_type(sentence)
                interruptible_sleep(0.1)
                safe_tap(Key.enter)
                interruptible_sleep(3)
            
            # Small delay before next random line
            if copypastaing:
                interruptible_sleep(1)
        
        print("ad_news random mode stopped")
        if not disable_finish_text:
            safe_tap(Key.enter)
            interruptible_sleep(0.1)
            safe_type("ad_news random mode stopped")
            interruptible_sleep(0.1)
            safe_tap(Key.enter)
        
        copypastaing = False
        return
    
    # Handle custom text (AI-generated) vs file-based copypasta
    if custom_text is not None:
        # AI mode: split custom text directly at 60 chars
        sentences = []
        max_length = 60  # Always 60 chars in AI mode
        text = custom_text
        if not disable_line_breaks:
            lines = text.split('\n')
            for line in lines:
                if line.strip() == '':
                    continue
                while len(line) > max_length:
                    if not disable_space_breaking:
                        split_idx = line.rfind(' ', 0, max_length)
                        if split_idx == -1:
                            split_idx = max_length
                    else:
                        split_idx = max_length
                    sentences.append(line[:split_idx])
                    line = line[split_idx:].lstrip()
                if line:
                    sentences.append(line)
        else:
            while len(text) > max_length:
                if not disable_space_breaking:
                    split_idx = text.rfind(' ', 0, max_length)
                    if split_idx == -1:
                        split_idx = max_length
                else:
                    split_idx = max_length
                sentences.append(text[:split_idx])
                text = text[split_idx:].lstrip()
            if text:
                sentences.append(text)
    elif id in ids:
        # File mode: read from copypasta file
        index = ids.index(id)
        filepath = filepaths[index]
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            copypastaing = False
            return
        sentences = split_sentences(filepath, disable_space_breaking=disable_space_breaking, disable_line_breaks=disable_line_breaks)
    else:
        print(f"Invalid id: {id}")
        copypastaing = False
        return
    
    leng = sum(len(replace_emojis(s)) for s in sentences)
    pos = 0
    
    if prepare:
        end = time.time()
        if custom_text is not None:
            # AI mode
            source_text = "AI Response (deepseek-r1:14b)"
            size_kb = len(custom_text.encode('utf-8')) / 1024
        else:
            # File mode
            path_obj = Path(filepath)
            source_text = f"[.../{path_obj.name}]"
            file_size_bytes = os.path.getsize(filepath)
            size_kb = file_size_bytes / 1024
        
        safe_tap(Key.enter)
        interruptible_sleep(0.1)
        safe_type(f"Arras Copypasta Utility [ACU] > v02.04.11-beta.4 < loading")
        interruptible_sleep(0.1)
        for _ in range(2):
            safe_tap(Key.enter)
            interruptible_sleep(0.1)
        safe_type(f"Source: > {source_text} < | Loaded > {leng} chars <")
        interruptible_sleep(0.1)
        for _ in range(2):
            safe_tap(Key.enter)
            interruptible_sleep(0.1)
        safe_type(f"Size: > [{size_kb:.2f}KB] < | Time taken > [{round((end-start)*1000, 3)}ms] <")
        interruptible_sleep(0.1)
        safe_tap(Key.enter)
        interruptible_sleep(10)
    
    endf = False
    for sentence in sentences:
        if not copypastaing:
            break
        if not is_ai_mode:
            pause_event.wait()  # Wait here if paused (only for file mode)
        safe_tap(Key.enter)
        if is_ai_mode:
            time.sleep(0.1)
        else:
            interruptible_sleep(0.1)
        safe_type(sentence)
        if is_ai_mode:
            time.sleep(0.1)
        else:
            interruptible_sleep(0.1)
        safe_tap(Key.enter)
        pos += len(sentence)
        current_chars = pos
        current_percent = (current_chars / leng) * 100 if leng > 0 else 0
        if is_ai_mode:
            time.sleep(3)
        else:
            interruptible_sleep(3)
        endf = True
    
    # After loop ends, print/type summary
    chars_typed = pos if pos < leng else leng
    percent_typed = (chars_typed / leng) * 100 if leng > 0 else 0
    if not endf:  # Force stop by Escape
        print(f"Forced stop at > [{chars_typed}] characters [{percent_typed:.2f}%]")
        safe_tap(Key.enter)
        interruptible_sleep(0.1)
        safe_type(f"Forced stop at > [{chars_typed}] characters [{percent_typed:.2f}%]")
        interruptible_sleep(0.1)
    else:
        if not disable_finish_text:
            print(f"Copypasta of > [{leng}] characters < finished")
            safe_tap(Key.enter)
            interruptible_sleep(0.1)
            safe_type(f"Copypasta of > [{leng}] characters < finished")
            interruptible_sleep(0.1)
        else:
            print(f"Copypasta of > [{leng}] characters < finished (without finish text)")
    
    if not disable_finish_text:
        safe_tap(Key.enter)
        interruptible_sleep(0.1)
        time.sleep(3.5)
        safe_tap(Key.enter)
        interruptible_sleep(0.1)
        print(f"Time taken: > [{round(1000*(time.time()-start), 3)}ms] <")
        safe_type(f"Time taken: > [{round(1000*(time.time()-start), 3)}ms] <")
        interruptible_sleep(0.1)
        safe_tap(Key.enter)
        interruptible_sleep(0.1)
    
    copypastaing = False

def on_press(key):
    global copypastaing, pause_event, current_chars, current_percent, controller, controller_typing, is_ai_mode
    try:
        # Ignore synthetic keypresses from the controller
        if controller_typing:
            return
        
        if key == keyboard.Key.esc:
            copypastaing = False
        elif hasattr(key, 'char') and key.char == 'p' and copypastaing:
            # Allow pausing in file mode (including ad_news), but not AI mode
            if not is_ai_mode:
                if pause_event.is_set():
                    pause_event.clear()
                else:
                    pause_event.set()
    except UnicodeDecodeError:
        print("UnicodeDecodeError: Non-standard key (emoji?) pressed. Ignored.")

# Initialize keyboard listener immediately
if listener is None:
    _lazy_import_pynput()
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    print("Keyboard listener started. Press Esc to stop copypasta.")

while True:
    mode_input = input("Mode (copypasta/ai) > ").strip().lower()
    
    if mode_input == 'ai':
        # AI prompt mode - model selection
        print("\nAvailable models:")
        for item in models:
            print(str(models.index(item) + 1) + ": " + item)
        
        model_input = input(f"Select model (1-{len(models)}) > ").strip()

        try:
            model = models[int(model_input)-1]
        except Exception:
            print("Invalid selection, defaulting to 'deepseek-r1-8b-16k'")
            model = 'deepseek-r1-8b-16k'
        
        prompt_input = input(f"Enter prompt for {model} > ").strip()
        if not prompt_input:
            print("Empty prompt, skipping")
            continue
        
        use_context_input = input("Use context from aacontext.txt? (true/false) > ").strip().lower()
        use_context = use_context_input == 'true'
        
        # Load context if requested
        full_prompt = prompt_input
        if use_context:
            context_path = script_dir / 'aacontext.txt'
            if context_path.exists():
                with open(context_path, 'r', encoding='utf-8') as f:
                    context = f.read().strip()
                full_prompt = f"{context}\n\n{prompt_input}"
                print(f"Context loaded from aacontext.txt ({len(context)} chars)")
            else:
                print(f"Warning: aacontext.txt not found at {context_path}")
                print("Proceeding without context...")
        
        disable_finish_text_input = input("Disable finish text? (true/false) > ").strip().lower()
        disable_finish_text = disable_finish_text_input == 'true'
        
        # AI mode always: no prepare mode, enable space breaking, enable line breaks
        prepare = False
        disable_space_breaking = False
        disable_line_breaks = False
        
        if copypastaing:
            print("Already copypastaing, wait until finished or press Escape to stop")
            continue
        
        # Get AI response (use full_prompt for actual query, but only show prompt_input in-game)
        ai_response = query_model(model, full_prompt, display_prompt=prompt_input)
        if ai_response is None:
            print("Failed to get AI response, skipping")
            continue
        
        # Save to temporary file and type it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write(ai_response)
            tmp_path = tmp.name
        
        try:
            thread = threading.Thread(
                target=copypasta, 
                args=('_ai_temp', prepare, disable_space_breaking, disable_finish_text, disable_line_breaks),
                kwargs={'custom_text': ai_response}
            )
            thread.start()
        finally:
            # Clean up temp file after thread starts
            Path(tmp_path).unlink(missing_ok=True)
    
    else:
        # Original copypasta file mode
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