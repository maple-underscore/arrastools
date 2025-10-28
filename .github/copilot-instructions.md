# Copilot instructions for arrastools

Purpose: Help AI coding agents work productively in this repo of desktop automation tools and a PPO-based Arras AI. Scripts control keyboard/mouse, read pixels, and automate gameplay/UI flows on macOS.

## Architecture and key files
- This is a collection of standalone Python scripts (no package/pytest). Common patterns repeat across files.
- Screen + input automation:
  - `arrastools.py` — hotkey-driven macros using pynput. Listeners run at module end and spawn daemon threads via `start_*` helpers.
  - `arrasbot.py` — a watchdog that samples screen pixels with `mss`, reacts to state (disconnected/died/banned), and logs/screenshots.
- PPO AI prototype:
  - `arrasai.py` — defines PPO agent (PolicyNetwork, PPOMemory, ArrasAI) and training/exec loops over screen observations sampled in a polygon (`GAME_REGION`). Models saved to `arras_models/` (e.g., `arras_model.pt_best`).
- Assets/data: `arras_models/`, `logs/`, `copypastas/`.

## Runtime assumptions and permissions (macOS)
- Requires Accessibility (keyboard/mouse control) and Screen Recording permissions for Terminal/VS Code (pynput + mss).
- Coordinates are absolute screen pixels for a specific UI layout. Retina scaling handled manually:
  - `arrasbot.py`: `MONITOR_INDEX` (default 1) and `SCALE` (2 on Retina, 1 on non-Retina). Convert global to local with these.
  - If your resolution/layout differs, update `GAME_REGION` and bounds used by `arrastools.py` and `arrasai.py` (e.g., mouse x in [2,1693], y in [128,1094]).

## Dependencies used across scripts
- Core: `pynput`, `mss`, `numpy`.
- Bot: `ping3`, `Pillow`, `mss.tools`.
- AI: `torch`, `shapely`, `pytesseract` (requires system Tesseract), `Pillow`.
- Example install (Python 3.10+): pynput, mss, numpy, ping3, pillow, torch, shapely, pytesseract.

## How to run and control
- `arrastools.py` hotkeys (hold Ctrl):
  - `Ctrl+1` one/two/three presses within 2s: `$arena size` automation type 1/2/3 (`start_arena_automation`).
  - `Ctrl+y` begin “Controlled Nuke”: click 2 points in 10s to spray `k` within rectangle (uses global mouse listener).
  - Safety: `Esc` stops activities; `Ctrl+Esc` immediate exit.
  - Other examples: `Ctrl+6` double-press within 5s triggers `ballcrash()`; `Ctrl+9` runs `nuke()`; `Ctrl+m` benchmarks ball spam.
- `arrasbot.py` CLI commands (typed in terminal while running): `stop`, `setscale <1|2>`, `setmon <index>`, `dbgmon`, `screenshot`, `status`, `ping`, `probe`, `forcedisconnect`, `forcedeath`, `forcereconnect`.
  - Logs: `logs/abss_*.log`; screenshots: `~/Desktop/abss/<session>/`. Uses `color_close()` for tolerant RGB checks.
- `arrasai.py` training:
  - Hotkeys while running: `Esc` force-stop (hard exit), `p` pause/resume, `r` simulate death.
  - Samples RGB at `OBSERVATION_POINTS = sample_points_in_polygon(GAME_REGION, step=10)` using `mss`; outputs: action (W/A/S/D/Space), mouse target, Sum42 head, and upgrade path.
  - Models saved in `arras_models/` with suffixes `_best`, `_final`, `_interrupted` based on training flow.

## Conventions and patterns to follow
- Threading: Use `threading.Thread(..., daemon=True)` for background actions; toggle with global flags (e.g., `slowballs`, `randomwalld`). Provide `start_*` helpers to avoid duplicate threads.
- Input synthesis: Use a single `KeyboardController`/`MouseController` per module; batch keystrokes within backtick-quoted console in-game by `controller.press("`")` … `controller.release("`")`.
- Color detection: Prefer `color_close(tupleRGB, tupleRGB, tol=6)` rather than strict equality to account for antialiasing/transparency.
- File outputs: Prefer timestamped paths from `timestamp()`; keep bot logs under `logs/` and images under `~/Desktop/abss/<session>/`.

## When extending
- For new macros, mirror `arrastools.py` style: add a function, a `start_*` wrapper if it loops, and wire a Ctrl+<key> branch in `on_press()` with debouncing if needed.
- For new detectors, add small, monitor-relative probes (`probe` in `arrasbot.py`) and gate user-visible actions with tolerant checks + cooldowns.
- If changing layout/resolution, update `GAME_REGION`, bounds and any hard-coded click points in `arrastools.py` (e.g., `conq_quickstart()` positions).

References: `arrastools.py`, `arrasbot.py`, `arrasai.py`, `arras_models/`, `logs/`, `copypastas/`. Keep changes minimal and aligned with existing patterns.