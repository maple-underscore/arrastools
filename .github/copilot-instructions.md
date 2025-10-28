# Copilot instructions for arrastools

Purpose: Help AI coding agents work productively in this repo of desktop automation tools and a PPO-based Arras AI. Scripts control keyboard/mouse, read pixels, and automate gameplay/UI flows across macOS, Linux, and Windows.

## Architecture and key files
- This is a collection of standalone Python scripts (no package/pytest). Common patterns repeat across files.
- Screen + input automation:
  - `arrastools.py` — hotkey-driven macros using pynput. Listeners run at module end and spawn daemon threads via `start_*` helpers.
  - `arrastools2.py` — alternative version with similar functionality and cross-platform support.
  - `arrasbot.py` — a watchdog that samples screen pixels with `mss`, reacts to state (disconnected/died/banned), and logs/screenshots.
  - `arrascopypasta.py` — copypasta automation with platform-agnostic file path handling using pathlib.
- PPO AI prototype:
  - `arrasai.py` — defines PPO agent (PolicyNetwork, PPOMemory, ArrasAI) and training/exec loops over screen observations sampled in a polygon (`GAME_REGION`). Models saved to `arras_models/` (e.g., `arras_model.pt_best`).
- Assets/data: `arras_models/`, `logs/`, `copypastas/`.

## Cross-platform support and runtime assumptions

### Platform detection
All main scripts now include platform detection using `platform.system().lower()`:
- Returns: `'darwin'` (macOS), `'linux'`, `'windows'`
- Scripts print platform on startup and warn if unsupported

### Platform-specific behaviors
- **macOS (primary development platform)**:
  - Requires Accessibility + Screen Recording permissions (System Settings > Privacy & Security)
  - Retina displays: Set `SCALE=2` in `arrasbot.py`
  - Modifier keys: `Option+Arrow` for 1px mouse nudges
  - Coordinate system: May differ from Linux/Windows due to Retina scaling
  
- **Linux (Arch, Debian, Ubuntu)**:
  - Install dependencies via package manager: `sudo apt install python3-tk tesseract-ocr` (Debian/Ubuntu) or `sudo pacman -S tk tesseract` (Arch)
  - Accessibility permissions may vary by DE/WM (check pynput documentation)
  - Standard displays: Set `SCALE=1` in `arrasbot.py`
  - Modifier keys: `Alt+Arrow` for 1px mouse nudges
  - Wayland vs X11: pynput works best on X11; Wayland may have limitations
  
- **Windows**:
  - Install Tesseract OCR separately: Download from https://github.com/UB-Mannheim/tesseract/wiki
  - May require running as Administrator for input automation
  - Standard displays: Set `SCALE=1` in `arrasbot.py`
  - Modifier keys: `Alt+Arrow` for 1px mouse nudges
  - Path separators: Now handled automatically via pathlib
  
- **Android**:
  - Limited/experimental support
  - pynput may not work on all devices
  - Consider using Termux with X11 server for best compatibility

### Display scaling and coordinates
- Coordinates are absolute screen pixels for a specific UI layout
- **Critical**: Adjust based on YOUR display resolution:
  - `arrasbot.py`: `MONITOR_INDEX` (default 1) and `SCALE` (2 on Retina, 1 on standard displays)
  - `arrasai.py`: Update `GAME_REGION` polygon coordinates to match your game window
  - `arrastools.py`: Update mouse bounds in `on_press()` and click positions in `conq_quickstart()`
- Use `arrasbot.py` CLI command `probe` to sample pixel colors and positions on your setup
- Retina/HiDPI displays require coordinate conversion: multiply or divide by `SCALE` as needed

## Dependencies and installation

### Python requirements
- **Python version**: 3.10+ recommended
- **Core libraries**: `pynput`, `mss`, `numpy`, `pathlib` (built-in)
- **Bot utilities**: `ping3`, `Pillow`, `mss.tools`
- **AI/ML**: `torch`, `shapely`, `pytesseract`, `Pillow`

### System dependencies (platform-specific)
- **macOS**: Tesseract via Homebrew: `brew install tesseract`
- **Linux**: `sudo apt install python3-tk tesseract-ocr` (Debian/Ubuntu) or equivalent
- **Windows**: Download Tesseract installer from GitHub, add to PATH
- **All platforms**: Ensure Python tkinter is installed (usually bundled)

### Quick setup
```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate  # Windows

# Install dependencies
pip install pynput mss numpy ping3 pillow torch shapely pytesseract

# Platform-specific system packages
# macOS: brew install tesseract
# Linux: sudo apt install tesseract-ocr python3-tk
# Windows: Install Tesseract from GitHub releases
```

## How to run and control
- `arrastools.py` / `arrastools2.py` hotkeys (hold Ctrl):
  - `Ctrl+1` one/two/three presses within 2s: `$arena size` automation type 1/2/3 (`start_arena_automation`).
  - `Ctrl+y` begin "Controlled Nuke": click 2 points in 10s to spray `k` within rectangle (uses global mouse listener).
  - `Alt+Arrow` (Option+Arrow on macOS): Move mouse 1 pixel in arrow direction (for precise positioning).
  - Safety: `Esc` stops activities; `Ctrl+Esc` immediate exit.
  - Other examples: `Ctrl+6` double-press within 5s triggers `ballcrash()`; `Ctrl+9` runs `nuke()`; `Ctrl+m` benchmarks ball spam.
- `arrasbot.py` CLI commands (typed in terminal while running): `stop`, `setscale <1|2>`, `setmon <index>`, `dbgmon`, `screenshot`, `status`, `ping`, `probe`, `forcedisconnect`, `forcedeath`, `forcereconnect`.
  - Logs: `logs/abss_*.log`; screenshots: `~/Desktop/abss/<session>/` (Linux/macOS) or `C:\Users\<user>\Desktop\abss\<session>\` (Windows).
  - Uses `color_close()` for tolerant RGB checks (accounts for antialiasing).
- `arrasai.py` training:
  - Hotkeys while running: `Esc` force-stop (hard exit), `p` pause/resume, `r` simulate death.
  - Samples RGB at `OBSERVATION_POINTS = sample_points_in_polygon(GAME_REGION, step=10)` using `mss`; outputs: action (W/A/S/D/Space), mouse target, Sum42 head, and upgrade path.
  - Models saved in `arras_models/` with suffixes `_best`, `_final`, `_interrupted` based on training flow.
- `arrascopypasta.py`: Reads `.txt` files from `copypastas/` directory (uses pathlib for cross-platform compatibility).

## Conventions and patterns to follow
- **Threading**: Use `threading.Thread(..., daemon=True)` for background actions; toggle with global flags (e.g., `slowballs`, `randomwalld`). Provide `start_*` helpers to avoid duplicate threads.
- **Input synthesis**: Use a single `KeyboardController`/`MouseController` per module; batch keystrokes within backtick-quoted console in-game by `controller.press("`")` … `controller.release("`")`.
- **Color detection**: Prefer `color_close(tupleRGB, tupleRGB, tol=6)` rather than strict equality to account for antialiasing/transparency.
- **File paths**: Use `pathlib.Path` for cross-platform compatibility (see `arrascopypasta.py` for example). Avoid hardcoded `/` or `\`.
- **File outputs**: Prefer timestamped paths from `timestamp()`; keep bot logs under `logs/` and images under `~/Desktop/abss/<session>/`.
- **Modifier key detection**: Use helper functions `is_ctrl()`, `is_alt()`, `is_modifier_for_arrow_nudge()` to handle cross-platform modifier key variants (Key.ctrl vs Key.ctrl_l vs Key.ctrl_r).

## When extending
- For new macros, mirror `arrastools.py` style: add a function, a `start_*` wrapper if it loops, and wire a Ctrl+<key> branch in `on_press()` with debouncing if needed.
- For new detectors, add small, monitor-relative probes (`probe` in `arrasbot.py`) and gate user-visible actions with tolerant checks + cooldowns.
- If changing layout/resolution, update `GAME_REGION`, bounds and any hard-coded click points in `arrastools.py` (e.g., `conq_quickstart()` positions).
- **Platform testing**: Test on target platforms before committing. Use virtual machines or containers for cross-platform validation.
- Add platform detection at script start: `PLATFORM = platform.system().lower()` with appropriate warnings.

## Troubleshooting

### Permission issues
- **macOS**: Grant Accessibility + Screen Recording in System Settings > Privacy & Security
- **Linux**: Check X11 vs Wayland; pynput may need additional configuration for Wayland
- **Windows**: Run Terminal/IDE as Administrator if input automation fails

### Coordinate/scaling issues
- Use `arrasbot.py` command `dbgmon` to list all monitors and their properties
- Use `probe` command to check pixel colors at cursor position
- Adjust `SCALE` variable to match your display (2 for Retina/HiDPI, 1 for standard)
- Re-map `GAME_REGION` coordinates for your screen resolution

### Dependency issues
- Ensure Tesseract OCR is installed system-wide and in PATH
- Virtual environment recommended to isolate Python packages
- Check pynput documentation for platform-specific requirements

References: `arrastools.py`, `arrastools2.py`, `arrasbot.py`, `arrasai.py`, `arrascopypasta.py`, `arras_models/`, `logs/`, `copypastas/`. Keep changes minimal and aligned with existing patterns.