#!/usr/bin/env python3
"""
Macro Recorder - Record and playback keyboard and mouse actions.

Usage:
    - Press Ctrl + any key to START recording (e.g., Ctrl+Q)
    - Press the same hotkey again to STOP recording
    - Double-press the hotkey (within 2s) to PLAYBACK the recording
    - Press Esc to exit the script

Recordings are stored in memory and can be saved/loaded from files.
"""

import platform
import sys
import time
import threading
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

# Platform detection
PLATFORM = platform.system().lower()
print(f"Running on platform: {PLATFORM}")

try:
    from pynput.keyboard import Controller as KeyboardController, Key, KeyCode, Listener as KeyboardListener
    from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener
except ImportError:
    print("Missing dependency: pynput is required to run this script.")
    print("Install with: python3 -m pip install pynput")
    sys.exit(1)

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
MACROS_DIR = REPO_ROOT / "macros"
MACROS_DIR.mkdir(parents=True, exist_ok=True)

# Controllers
keyboard_controller = KeyboardController()
mouse_controller = MouseController()

# Double-press detection threshold (seconds)
DOUBLE_PRESS_THRESHOLD = 2

# Playback speed multiplier (1.0 = original speed, 0.5 = 2x faster, 2.0 = 2x slower)
PLAYBACK_SPEED = 0.1


class ActionType(Enum):
    """Types of recordable actions."""
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_RELEASE = "mouse_release"
    MOUSE_SCROLL = "mouse_scroll"


@dataclass
class RecordedAction:
    """A single recorded action with timestamp."""
    action_type: ActionType
    timestamp: float  # Time since recording started (seconds)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "action_type": self.action_type.value,
            "timestamp": self.timestamp,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RecordedAction":
        """Create from dictionary."""
        return cls(
            action_type=ActionType(d["action_type"]),
            timestamp=d["timestamp"],
            data=d["data"]
        )


@dataclass
class MacroRecording:
    """A complete macro recording."""
    name: str
    hotkey: str  # The key used to trigger this macro (e.g., "q", "1")
    actions: List[RecordedAction] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "hotkey": self.hotkey,
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MacroRecording":
        """Create from dictionary."""
        return cls(
            name=d["name"],
            hotkey=d["hotkey"],
            actions=[RecordedAction.from_dict(a) for a in d["actions"]],
            created_at=d.get("created_at", datetime.now().isoformat())
        )
    
    def save(self, filepath: Optional[Path] = None) -> Path:
        """Save recording to a JSON file."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = MACROS_DIR / f"macro_{self.hotkey}_{timestamp}.json"
        
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        
        print(f"Macro saved to: {filepath}")
        return filepath
    
    @classmethod
    def load(cls, filepath: Path) -> "MacroRecording":
        """Load recording from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


class MacroRecorder:
    """Main macro recorder class that handles recording and playback."""
    
    def __init__(self):
        self.recordings: Dict[str, MacroRecording] = {}  # hotkey -> recording
        self.current_recording: Optional[MacroRecording] = None
        self.recording_start_time: float = 0
        self.is_recording = False
        self.is_playing = False
        self.record_mouse_movement = True  # Toggle for mouse movement recording
        self.mouse_sample_rate = 0.016  # ~60fps for mouse movement sampling
        self.last_mouse_sample_time = 0
        
        # Hotkey state tracking
        self.last_hotkey_press: Dict[str, float] = {}  # hotkey -> last press time
        self.ctrl_pressed = False
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Running state
        self.running = True
        
        # Listeners (will be set up later)
        self.keyboard_listener: Optional[KeyboardListener] = None
        self.mouse_listener: Optional[MouseListener] = None
    
    def get_key_string(self, key: Union[Key, KeyCode]) -> str:
        """Convert a key to a string representation."""
        if isinstance(key, KeyCode):
            if key.char:
                return key.char.lower()
            else:
                return f"vk_{key.vk}"
        else:
            return key.name
    
    def key_to_serializable(self, key: Union[Key, KeyCode]) -> Dict[str, Any]:
        """Convert a key to a serializable dictionary."""
        if isinstance(key, KeyCode):
            return {"type": "keycode", "char": key.char, "vk": key.vk}
        else:
            return {"type": "special", "name": key.name}
    
    def serializable_to_key(self, data: Dict[str, Any]) -> Union[Key, KeyCode]:
        """Convert a serializable dictionary back to a key."""
        if data["type"] == "keycode":
            if data["char"]:
                return KeyCode.from_char(data["char"])
            else:
                return KeyCode.from_vk(data["vk"])
        else:
            return getattr(Key, data["name"])
    
    def is_ctrl_key(self, key: Union[Key, KeyCode]) -> bool:
        """Check if the key is a Ctrl modifier."""
        if isinstance(key, Key):
            return key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r)
        return False
    
    def is_modifier_key(self, key: Union[Key, KeyCode]) -> bool:
        """Check if the key is any modifier key."""
        if isinstance(key, Key):
            return key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r,
                          Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr,
                          Key.shift, Key.shift_l, Key.shift_r,
                          Key.cmd, Key.cmd_l, Key.cmd_r)
        return False
    
    def on_key_press(self, key: Union[Key, KeyCode]) -> Optional[bool]:
        """Handle key press events."""
        # Check for Esc to exit FIRST - highest priority
        if key == Key.esc:
            print("\n⛔ Esc pressed - FORCE STOPPING all operations...")
            # Force stop recording
            if self.is_recording:
                print("   Stopping active recording...")
                self.is_recording = False
            # Force stop playback
            if self.is_playing:
                print("   Stopping active playback...")
                self.is_playing = False
            # Stop the recorder
            self.running = False
            print("   Macro recorder terminated.")
            return False
        
        if not self.running:
            return False
        
        # Track Ctrl state
        if self.is_ctrl_key(key):
            self.ctrl_pressed = True
            return None
        
        # Handle Ctrl+key hotkeys (only when not playing back)
        if self.ctrl_pressed and not self.is_modifier_key(key) and not self.is_playing:
            hotkey = self.get_key_string(key)
            self.handle_hotkey(hotkey)
            return None  # Don't record the hotkey itself
        
        # Record the key press if recording
        if self.is_recording and self.current_recording:
            # Don't record modifier keys by themselves
            if not self.is_modifier_key(key):
                with self.lock:
                    action = RecordedAction(
                        action_type=ActionType.KEY_PRESS,
                        timestamp=time.time() - self.recording_start_time,
                        data={"key": self.key_to_serializable(key)}
                    )
                    self.current_recording.actions.append(action)
        
        return None
    
    def on_key_release(self, key: Union[Key, KeyCode]) -> Optional[bool]:
        """Handle key release events."""
        if not self.running:
            return False
        
        # Track Ctrl state
        if self.is_ctrl_key(key):
            self.ctrl_pressed = False
            return None
        
        # Record the key release if recording
        if self.is_recording and self.current_recording:
            if not self.is_modifier_key(key):
                with self.lock:
                    action = RecordedAction(
                        action_type=ActionType.KEY_RELEASE,
                        timestamp=time.time() - self.recording_start_time,
                        data={"key": self.key_to_serializable(key)}
                    )
                    self.current_recording.actions.append(action)
        
        return None
    
    def on_mouse_move(self, x: int, y: int):
        """Handle mouse move events."""
        if not self.is_recording or not self.record_mouse_movement:
            return
        
        # Rate limit mouse movement recording
        current_time = time.time()
        if current_time - self.last_mouse_sample_time < self.mouse_sample_rate:
            return
        self.last_mouse_sample_time = current_time
        
        if self.current_recording:
            with self.lock:
                action = RecordedAction(
                    action_type=ActionType.MOUSE_MOVE,
                    timestamp=time.time() - self.recording_start_time,
                    data={"x": x, "y": y}
                )
                self.current_recording.actions.append(action)
    
    def on_mouse_click(self, x: int, y: int, button: Button, pressed: bool):
        """Handle mouse click events."""
        if not self.is_recording or not self.current_recording:
            return
        
        with self.lock:
            action = RecordedAction(
                action_type=ActionType.MOUSE_CLICK if pressed else ActionType.MOUSE_RELEASE,
                timestamp=time.time() - self.recording_start_time,
                data={"x": x, "y": y, "button": button.name}
            )
            self.current_recording.actions.append(action)
    
    def on_mouse_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle mouse scroll events."""
        if not self.is_recording or not self.current_recording:
            return
        
        with self.lock:
            action = RecordedAction(
                action_type=ActionType.MOUSE_SCROLL,
                timestamp=time.time() - self.recording_start_time,
                data={"x": x, "y": y, "dx": dx, "dy": dy}
            )
            self.current_recording.actions.append(action)
    
    def handle_hotkey(self, hotkey: str):
        """Handle a Ctrl+key hotkey press."""
        current_time = time.time()
        last_press = self.last_hotkey_press.get(hotkey, 0)
        time_since_last = current_time - last_press
        
        # Check if we're currently recording this hotkey
        if self.is_recording and self.current_recording and self.current_recording.hotkey == hotkey:
            # Stop recording - set timestamp to NOW so next quick press triggers playback
            self.stop_recording()
            # Update timestamp so a quick follow-up press will trigger double-press playback
            self.last_hotkey_press[hotkey] = current_time
            return
        
        # Update last press time (only for non-stop-recording actions)
        self.last_hotkey_press[hotkey] = current_time
        
        # Check for double-press (playback) OR single press if macro exists
        if hotkey in self.recordings:
            # Macro exists - always playback (whether quick or slow press)
            threading.Thread(target=self.playback, args=(hotkey,), daemon=True).start()
            return
        
        # Check if there's an existing saved macro for this hotkey (not yet in memory)
        if hotkey not in self.recordings and not self.is_recording:
            # Try to load from file
            if self.load_macro(hotkey):
                # Macro was loaded, next press will playback
                print(f"   Press Ctrl+{hotkey.upper()} again to playback")
                return
        
        # Start new recording (if not already recording something else)
        if not self.is_recording:
            self.start_recording(hotkey)
    
    def start_recording(self, hotkey: str):
        """Start recording a new macro."""
        with self.lock:
            self.is_recording = True
            self.recording_start_time = time.time()
            self.current_recording = MacroRecording(
                name=f"Macro_{hotkey}",
                hotkey=hotkey
            )
        
        print(f"\n🔴 Recording started for Ctrl+{hotkey.upper()}")
        print("   Press Ctrl+{} again to stop recording".format(hotkey.upper()))
    
    def stop_recording(self):
        """Stop the current recording."""
        with self.lock:
            if self.current_recording:
                hotkey = self.current_recording.hotkey
                action_count = len(self.current_recording.actions)
                
                # Calculate duration
                if self.current_recording.actions:
                    duration = self.current_recording.actions[-1].timestamp
                else:
                    duration = 0
                
                # Store the recording
                self.recordings[hotkey] = self.current_recording
                
                print(f"\n⏹️  Recording stopped for Ctrl+{hotkey.upper()}")
                print(f"   Recorded {action_count} actions over {duration:.2f}s")
                print(f"   Double-press Ctrl+{hotkey.upper()} to playback")
                
                # Auto-save the recording
                self.current_recording.save()
                
                self.current_recording = None
            
            self.is_recording = False
    
    def playback(self, hotkey: str):
        """Play back a recorded macro."""
        recording = self.recordings.get(hotkey)
        if not recording or not recording.actions:
            print(f"No recording found for Ctrl+{hotkey.upper()}")
            return
        
        if self.is_playing:
            print("Already playing a macro!")
            return
        
        self.is_playing = True
        
        # Calculate mouse offset from the first mouse action to current position
        offset_x, offset_y = 0, 0
        current_pos = mouse_controller.position
        
        # Find the first mouse action to determine the original starting position
        for action in recording.actions:
            if action.action_type in (ActionType.MOUSE_MOVE, ActionType.MOUSE_CLICK, 
                                       ActionType.MOUSE_RELEASE, ActionType.MOUSE_SCROLL):
                original_x = action.data["x"]
                original_y = action.data["y"]
                offset_x = current_pos[0] - original_x
                offset_y = current_pos[1] - original_y
                break
        
        print(f"\n▶️  Playing back Ctrl+{hotkey.upper()} ({len(recording.actions)} actions)")
        if offset_x != 0 or offset_y != 0:
            print(f"   Mouse offset: ({int(offset_x):+d}, {int(offset_y):+d})")
        
        try:
            last_timestamp = 0
            
            for action in recording.actions:
                # Check if we should stop (Esc was pressed)
                if not self.running:
                    print("\n⛔ Playback interrupted by Esc")
                    break
                
                # Wait for the appropriate time
                delay = (action.timestamp - last_timestamp) * PLAYBACK_SPEED
                if delay > 0:
                    # Split sleep into smaller chunks to respond faster to Esc
                    sleep_chunk = 0.05  # 50ms chunks
                    remaining = delay
                    while remaining > 0 and self.running:
                        chunk = min(sleep_chunk, remaining)
                        time.sleep(chunk)
                        remaining -= chunk
                    
                    # If Esc was pressed during sleep, stop immediately
                    if not self.running:
                        print("\n⛔ Playback interrupted by Esc")
                        break
                
                last_timestamp = action.timestamp
                
                # Execute the action with mouse offset
                self.execute_action(action, offset_x, offset_y)
            
            if self.running:  # Only print completion if not interrupted
                print(f"✅ Playback complete for Ctrl+{hotkey.upper()}")
        
        except Exception as e:
            print(f"Playback error: {e}")
        
        finally:
            self.is_playing = False
    
    def execute_action(self, action: RecordedAction, offset_x: int = 0, offset_y: int = 0):
        """Execute a single recorded action.
        
        Args:
            action: The action to execute
            offset_x: X offset to apply to mouse positions
            offset_y: Y offset to apply to mouse positions
        """
        try:
            if action.action_type == ActionType.KEY_PRESS:
                key = self.serializable_to_key(action.data["key"])
                keyboard_controller.press(key)
            
            elif action.action_type == ActionType.KEY_RELEASE:
                key = self.serializable_to_key(action.data["key"])
                keyboard_controller.release(key)
            
            elif action.action_type == ActionType.MOUSE_MOVE:
                x = action.data["x"] + offset_x
                y = action.data["y"] + offset_y
                mouse_controller.position = (x, y)
            
            elif action.action_type == ActionType.MOUSE_CLICK:
                button = getattr(Button, action.data["button"])
                x = action.data["x"] + offset_x
                y = action.data["y"] + offset_y
                mouse_controller.position = (x, y)
                mouse_controller.press(button)
            
            elif action.action_type == ActionType.MOUSE_RELEASE:
                button = getattr(Button, action.data["button"])
                x = action.data["x"] + offset_x
                y = action.data["y"] + offset_y
                mouse_controller.position = (x, y)
                mouse_controller.release(button)
            
            elif action.action_type == ActionType.MOUSE_SCROLL:
                x = action.data["x"] + offset_x
                y = action.data["y"] + offset_y
                mouse_controller.position = (x, y)
                mouse_controller.scroll(action.data["dx"], action.data["dy"])
        
        except Exception as e:
            print(f"Action execution error: {e}")
    
    def list_recordings(self):
        """List all available recordings."""
        if not self.recordings:
            print("No recordings available.")
            return
        
        print("\n📋 Available recordings:")
        for hotkey, recording in self.recordings.items():
            duration = recording.actions[-1].timestamp if recording.actions else 0
            print(f"   Ctrl+{hotkey.upper()}: {len(recording.actions)} actions, {duration:.2f}s")
    
    def find_macro_file(self, hotkey: str) -> Optional[Path]:
        """Find the most recent macro file for a given hotkey."""
        # Find all macro files for this hotkey
        pattern = f"macro_{hotkey}_*.json"
        matches = list(MACROS_DIR.glob(pattern))
        
        if not matches:
            return None
        
        # Return the most recent one (sorted by filename timestamp)
        return sorted(matches)[-1]
    
    def load_macro(self, hotkey: str) -> bool:
        """Load a specific macro by hotkey if it exists.
        
        Returns:
            True if macro was loaded, False otherwise
        """
        filepath = self.find_macro_file(hotkey)
        if not filepath:
            return False
        
        try:
            recording = MacroRecording.load(filepath)
            self.recordings[recording.hotkey] = recording
            print(f"📂 Loaded existing macro: {filepath.name}")
            return True
        except Exception as e:
            print(f"Failed to load {filepath.name}: {e}")
            return False
    
    def load_all_recordings(self):
        """Load all saved recordings from the macros directory."""
        for filepath in MACROS_DIR.glob("macro_*.json"):
            try:
                recording = MacroRecording.load(filepath)
                self.recordings[recording.hotkey] = recording
                print(f"Loaded: {filepath.name}")
            except Exception as e:
                print(f"Failed to load {filepath.name}: {e}")
    
    def run(self):
        """Start the macro recorder."""
        print("\n" + "=" * 60)
        print("MACRO RECORDER")
        print("=" * 60)
        print("\nControls:")
        print("  • Ctrl + any key    → Start/stop recording")
        print("  • Double-press      → Playback recording")
        print("  • Esc               → Exit")
        print("\nOptions:")
        print(f"  • Mouse movement recording: {'ON' if self.record_mouse_movement else 'OFF'}")
        print(f"  • Playback speed: {PLAYBACK_SPEED}x")
        print(f"  • Macros directory: {MACROS_DIR}")
        print("=" * 60 + "\n")
        
        # Load existing recordings
        self.load_all_recordings()
        if self.recordings:
            self.list_recordings()
            print()
        
        print("Ready! Press Ctrl + any key to start recording...")
        
        # Set up listeners
        self.keyboard_listener = KeyboardListener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        
        self.mouse_listener = MouseListener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll
        )
        
        # Start listeners
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
        # Wait for exit
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        # Clean up
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        
        # Save any pending recording
        if self.is_recording:
            self.stop_recording()
        
        print("\nMacro recorder stopped.")


def main():
    """Main entry point."""
    recorder = MacroRecorder()
    
    # Command line options
    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-mouse":
            recorder.record_mouse_movement = False
            print("Mouse movement recording disabled.")
        elif sys.argv[1] == "--help":
            print(__doc__)
            print("\nOptions:")
            print("  --no-mouse    Disable mouse movement recording")
            print("  --help        Show this help message")
            return
    
    recorder.run()


if __name__ == "__main__":
    main()
