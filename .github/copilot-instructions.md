# Copilot Instructions for arrastools

**Purpose**: Desktop automation toolkit for Arras.io game automation, including screen capture, input synthesis, pixel detection, AI agents (PPO/DQN), and cross-platform macro scripts.

---

## Project Overview

**Type**: Collection of standalone Python automation scripts (no package structure)  
**Platforms**: Linux, macOS, Windows (primary: Linux)  
**Python**: 3.10+ required  
**Testing**: No pytest; manual testing only

---

## Directory Structure

### `««««« CORE »»»»»/` — Core automation scripts
- **arrastools.py** — Main hotkey-driven macro system with pynput listeners
- **arrasbot.py** — Pixel-based game state watchdog (disconnect/death/ban detection)
- **arrascopypasta.py** — Auto-types text from `copypastas/*.txt` files
- **arrastext_detector.py** — OCR-based text detection using pytesseract
- **arrasbp.py** — Blueprint and character pair processing
- **keylogger.py** — Keypress logger with timestamped output to `logsk/`
- **rollbot.py** — Automated game mechanics bot
- **rg.py** — Utility script
- **renderer/** — OpenGL and Tkinter rendering modules with shader support

### `random/` — Experimental and utility scripts
- **asnake.py** — DQN Snake AI with configurable training (see `snake_config.json`)
- **arrasantiafk.py** — Anti-AFK mouse wiggler
- **drawacircle.py** — Interactive circle drawing tool
- **minesweeper.py** — Terminal Minesweeper game
- **nodebuster.py** — Node automation
- **ping.py** — Network ping utility

### `tools/` — Standalone utilities
- **arraspixel.py** — Click-to-inspect pixel color tool (mss + pynput)
- **unicode_chunker.py** — Unicode text processing utility

### `copypastas/` — Text files for auto-typing
20+ `.txt` files with pre-written messages

### `bps/` — Blueprint data
- `color.txt`, `type.txt`, `wall.txt`

---

## Key Technologies

### Core Dependencies (see requirements.txt)
- **pynput** (>=1.7.6) — Keyboard/mouse input synthesis and monitoring
- **mss** (>=9.0.1) — Fast cross-platform screen capture
- **numpy** (>=1.26.0) — Numerical operations for AI models
- **ping3** (>=4.0.4) — Network connectivity checks
- **pillow** (>=10.0.0) — Image processing
- **torch** (>=2.0.0) — PyTorch for AI training
- **shapely** (>=2.0.0) — Polygon geometry for screen regions
- **pytesseract** (>=0.3.10) — OCR text extraction
- **pygame** (>=2.5.0) — Optional visualization for Snake AI

### System Dependencies
- **Tesseract OCR** (system package):
  - Linux: `sudo apt install tesseract-ocr python3-tk`
  - macOS: `brew install tesseract`
  - Windows: Download from GitHub releases, add to PATH

---

## Architecture Patterns

### Threading Model
- Use `threading.Thread(..., daemon=True)` for all background tasks
- Control loops with global boolean flags (e.g., `slowballs`, `randomwalld`)
- Provide `start_*()` wrapper functions to prevent duplicate threads
- Example:
  ```python
  running = False
  def start_task():
      global running
      if not running:
          running = True
          threading.Thread(target=task_loop, daemon=True).start()
  ```

### Input Synthesis
- **Single controller per module**: One `KeyboardController()` and `MouseController()` instance
- **Batch in-game chat commands**: Wrap in backtick quotes
  ```python
  controller.press('`')
  controller.type("arena size 4")
  controller.release('`')
  ```

### Color Detection
- Always use tolerance-based comparison: `color_close(rgb1, rgb2, tol=6)`
- Accounts for antialiasing/compression artifacts
- Never use strict `==` for pixel RGB values

### File Paths
- **Always use `pathlib.Path`** for cross-platform compatibility
- Never hardcode `/` or `\` separators
- Example: `Path.home() / "Desktop" / "abss" / session_id`

### Coordinate Systems
- **Display scaling critical**:
  - Retina/HiDPI (macOS): `SCALE=2`
  - Standard displays (Linux/Windows): `SCALE=1`
- Coordinates are absolute screen pixels
- Use `arrasbot.py` commands to probe:
  - `dbgmon` — List all monitors and properties
  - `probe` — Sample pixel color at cursor position

---

## Platform-Specific Behavior

### Linux (Primary Platform)
- X11 recommended (Wayland has pynput limitations)
- Install: `sudo apt install python3-tk tesseract-ocr`
- Modifier for 1px nudges: `Alt+Arrow`
- Screenshot paths: `~/Desktop/abss/<session>/`

### macOS
- Requires Accessibility + Screen Recording permissions (System Settings > Privacy & Security)
- Retina displays: Set `SCALE=2` in arrasbot.py
- Modifier for 1px nudges: `Option+Arrow`
- Install: `brew install tesseract`

### Windows
- May require Administrator privileges for input automation
- Install Tesseract manually, add to PATH
- Modifier for 1px nudges: `Alt+Arrow`
- Screenshot paths: `C:\Users\<user>\Desktop\abss\<session>\`

### Platform Detection
All main scripts should detect platform at startup:
```python
import platform
PLATFORM = platform.system().lower()  # 'linux', 'darwin', 'windows'
```

---

## Script Usage Reference

### arrastools.py — Hotkey Macros
**Hotkeys** (hold Ctrl unless noted):
- `Ctrl+1` (1/2/3 presses in 2s) → Arena size automation type 1/2/3
- `Ctrl+y` → "Controlled Nuke" (click 2 points, spray 'k' in rectangle)
- `Alt+Arrow` / `Option+Arrow` → 1px mouse movement
- `Ctrl+6` (double-press in 5s) → `ballcrash()`
- `Ctrl+9` → `nuke()`
- `Ctrl+m` → Ball spam benchmark
- `Esc` → Stop activities
- `Ctrl+Esc` → Immediate exit

**Threading**: Listeners run as daemon threads spawned by `start_*()` helpers at module end

### arrasbot.py — State Watchdog
**CLI Commands** (type in terminal while running):
- `stop` — Stop monitoring
- `setscale <1|2>` — Adjust display scaling
- `setmon <index>` — Change monitor
- `dbgmon` — List all monitors
- `screenshot` — Capture screen
- `status` — Show current state
- `ping` — Network check
- `probe` — Sample pixel at cursor
- `forcedisconnect`, `forcedeath`, `forcereconnect` — Simulate states

**Logs**: `logs/abss_*.log`  
**Screenshots**: `~/Desktop/abss/<session>/` (Linux/macOS)

**Color Detection**: Uses `color_close(rgb1, rgb2, tol=6)` for antialiasing tolerance

### arrascopypasta.py
- Reads `.txt` files from `copypastas/` directory
- Uses pathlib for cross-platform file handling
- Auto-types content into game chat

### keylogger.py
- Logs all keypresses to `logsk/keylog_<timestamp>.txt`
- Press `Esc` to stop logging

### asnake.py — DQN Snake AI
- Config: `random/snake_config.json` (grid size, episodes, rewards, display)
- Models saved to `snake_models/` with suffixes `_best`, `_ep<N>`, `_interrupted`
- Hotkeys: `Esc` to quit
- Optional pygame visualization (headless if unavailable)

### arraspixel.py
- Click anywhere to display RGB color value
- Uses mss for capture, pynput for mouse listener
- Helpful for calibrating color detection thresholds

---

## Development Guidelines

### Adding New Macros
1. Create function in `arrastools.py`
2. Add `start_*()` wrapper if it loops
3. Wire hotkey in `on_press()` with debouncing
4. Use global flags for state control

### Adding Pixel Detectors
1. Add small monitor-relative probe in `arrasbot.py`
2. Use `color_close()` for RGB comparison (tolerance ≥ 6)
3. Gate actions with cooldowns to prevent spam
4. Test with `probe` command before hardcoding

### Changing Display Coordinates
**Critical**: Coordinates are hardcoded for specific resolutions. When changing:
1. Update `GAME_REGION` in arrasai.py (if applicable)
2. Update mouse bounds in `arrastools.py` `on_press()`
3. Update click positions in automation functions (e.g., `conq_quickstart()`)
4. Use `arrasbot.py probe` command to sample new coordinates
5. Verify `SCALE` setting matches your display

### Modifier Key Handling
Use helper functions to handle cross-platform variants:
```python
def is_ctrl(key):
    return key in {Key.ctrl, Key.ctrl_l, Key.ctrl_r}

def is_alt(key):
    return key in {Key.alt, Key.alt_l, Key.alt_r}
```

### File Output Conventions
- Timestamped paths: Use `timestamp()` function
- Bot logs: `logs/` directory
- Screenshots: `~/Desktop/abss/<session>/` (use pathlib)
- Models: `arras_models/`, `snake_models/`

---

## Installation

### Quick Setup
```bash
# Clone repository
git clone https://github.com/maple-underscore/arrastools
cd arrastools

# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (Linux example)
sudo apt install tesseract-ocr python3-tk

# macOS
brew install tesseract

# Windows
# Download Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
# Add to system PATH
```

---

## Troubleshooting

### Permission Issues
- **Linux**: Check X11 vs Wayland; pynput requires X11 for best results
- **macOS**: Grant Accessibility + Screen Recording in System Settings > Privacy & Security
- **Windows**: Run Terminal/IDE as Administrator if input automation fails

### Coordinate/Scaling Issues
1. Run `arrasbot.py` and use `dbgmon` command to list monitors
2. Use `probe` command to check pixel colors at cursor
3. Adjust `SCALE` variable (2 for Retina/HiDPI, 1 for standard)
4. Re-map `GAME_REGION` coordinates for your resolution

### Dependency Issues
- Ensure Tesseract OCR is installed system-wide and in PATH
- Use virtual environment to isolate Python packages
- Check pynput documentation for platform-specific requirements

### pynput on Wayland
- If using Wayland on Linux, consider switching to X11 session
- Alternatively, use xwayland-run or similar compatibility layer
- Some features may not work reliably on Wayland

---

## Code Style Conventions

### Consistency Rules
- **No pytest**: Manual testing only
- **Standalone scripts**: No package imports between scripts (except renderer/)
- **Common patterns**: Repeat patterns rather than abstracting (DRY not enforced)
- **Daemon threads**: All background tasks must be daemon threads
- **Global flags**: Use for state control (avoid complex state machines)
- **Pathlib**: Always use for file paths
- **Type hints**: Not required but welcome
- **Comments**: Prefer inline comments explaining "why" not "what"

### When Modifying Code
- Keep changes minimal and aligned with existing patterns
- Test on target platform before committing
- Use virtual machines or containers for cross-platform validation
- Add platform detection if script hasn't been tested cross-platform
- Document any new hotkeys or CLI commands in this file

---

## Important Files and Directories

**Critical Assets**:
- `bitmap.txt` — Bitmap font data for text rendering
- `copypastas/*.txt` — Pre-written messages for auto-typing
- `bps/*.txt` — Blueprint configuration data
- `random/snake_config.json` — Snake AI training configuration
- `logs/` — Runtime logs from arrasbot.py
- `logsk/` — Keylogger output directory

**Generated at Runtime**:
- `arras_models/` — Saved PPO models
- `snake_models/` — Saved DQN models
- `~/Desktop/abss/<session>/` — Screenshots from arrasbot.py
- `progress.json` — Training progress tracking

---

## Additional Notes

### Not Included in This Repo
The old copilot instructions referenced these files that don't exist in the current structure:
- `arrastools2.py`, `arrastools_nomacropanel.py`
- `arrascopypastareload.py`
- `arrasai.py` (PPO agent)
- `arrasmouselocator.py`, `arrasmouse.py`
- `arrashealmacro.py`, `arrastank.py`, `arrasstack.py`
- `arrasdev.py`, `arrasreload.py`, `arrastext.py`, `arrastext2.py`, `arrasshaver.py`
- `screensender.py`, `cobalt.py`, `sumo.py`
- `linuxtest.py`, `arrastest2.py`, `arashealertest.py`

If these scripts are needed, they should be added to the repository and documented here.

### Renderer Module
The `renderer/` directory contains:
- `base_renderer.py` — Abstract renderer interface
- `tkinter_renderer.py` — Tkinter-based rendering
- `opengl_renderer.py` — OpenGL rendering with shader support
- `sprite_pool.py` — Sprite management
- `shaders/` — GLSL vertex/fragment shaders (note.vert/frag, particle.vert/frag)

This is the only modular package in the project; other scripts remain standalone.

---

**Last Updated**: January 2026  
**Maintainer**: maple-underscore  
**License**: See LICENSE and NOTICE files