[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

# arrastools

Desktop automation toolkit for Arras.io game automation — screen capture, input synthesis, pixel detection, AI agents (PPO/DQN), and cross-platform macro scripts.

> [!WARNING]
> This tool automates keyboard and mouse input. Use responsibly and in accordance with game terms of service.

---

## Features

| Feature | Script | Description |
|---------|--------|-------------|
| 🎮 **Hotkey Macros** | `arrastools.py` | Keyboard-driven game automation with pynput |
| 👁️ **State Watchdog** | `arrasbot.py` | Pixel-based disconnect/death/ban detection with logging |
| 📝 **Copypasta** | `arrascopypasta.py` | Auto-types text from `copypastas/` directory |
| 🔍 **OCR Detection** | `arrastext_detector.py` | Screen text extraction via pytesseract |
| 🐍 **Snake AI** | `asnake.py` | DQN-trained Snake game with configurable training |
| 🎨 **Rendering** | `renderer/` | OpenGL + Tkinter rendering with shader support |

---

## Quick Start

> [!IMPORTANT]
> **Python 3.10+** required. Python 3.14 recommended for best performance.

### 1. Clone & Setup

```bash
git clone https://github.com/maple-underscore/arrastools.git
cd arrastools

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Install System Dependencies

<details>
<summary><strong>Linux (Debian/Ubuntu)</strong></summary>

```bash
sudo apt install tesseract-ocr python3-tk
```
</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install tesseract
```

> [!NOTE]
> Grant **Accessibility** and **Screen Recording** permissions in System Settings → Privacy & Security.
</details>

<details>
<summary><strong>Windows</strong></summary>

1. Download [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add to system PATH
3. Run Terminal as Administrator if input automation fails
</details>

---

## Project Structure

```
arrastools/
├── ««««« CORE »»»»»/           # Main automation scripts
│   ├── arrastools.py           # Hotkey-driven macro system
│   ├── arrasbot.py             # Game state watchdog
│   ├── arrascopypasta.py       # Auto-typing copypastas
│   ├── arrastext_detector.py   # OCR text detection
│   ├── arrasbp.py              # Blueprint processing
│   ├── keylogger.py            # Keypress logger → logsk/
│   ├── rollbot.py              # Automated game mechanics
│   ├── macrorecorder.py        # Macro recording utility
│   ├── window_detector.py      # Window detection utility
│   ├── rg.py                   # Utility script
│   ├── bitmap.txt              # Bitmap font data
│   ├── bps/                    # Blueprint data files
│   └── renderer/               # OpenGL/Tkinter rendering
│       ├── base_renderer.py
│       ├── opengl_renderer.py
│       ├── tkinter_renderer.py
│       ├── sprite_pool.py
│       └── shaders/            # GLSL shaders
│
├── random/                     # Experimental scripts
│   ├── asnake.py               # DQN Snake AI
│   ├── arrasantiafk.py         # Anti-AFK mouse wiggler
│   ├── drawacircle.py          # Circle drawing tool
│   ├── minesweeper.py          # Terminal Minesweeper
│   ├── nodebuster.py           # Node automation
│   ├── ping.py                 # Network ping utility
│   └── snake_config.json       # Snake AI configuration
│
├── tools/                      # Standalone utilities
│   ├── arraspixel.py           # Click-to-inspect pixel color
│   └── unicode_chunker.py      # Unicode text processing
│
├── copypastas/                 # 25+ text files for auto-typing
├── typings/                    # Type stubs for dependencies
├── requirements.txt
└── .github/
    └── copilot-instructions.md
```

---

## Usage

### arrastools.py — Hotkey Macros

> [!TIP]
> Hold **Ctrl** for most hotkeys. Use **Esc** to stop any running macro.

| Hotkey | Action |
|--------|--------|
| `Ctrl+1` (1/2/3×) | Arena size automation |
| `Ctrl+y` | Controlled Nuke (click 2 points) |
| `Ctrl+6` (2× in 5s) | Ball crash |
| `Ctrl+9` | Nuke |
| `Ctrl+m` | Ball spam benchmark |
| `Alt+1` | Circle finder (click 2 corners, hold Left Shift) |
| `Alt+Arrow` | 1px mouse nudge |
| `Esc` | Stop current activity |
| `Ctrl+Esc` | Immediate exit |

#### Circle Finder Mode (Alt+1)

The circle finder automatically detects and tracks circles with colored borders:

1. Press **Alt+1** to activate
2. Click **two corners** to define search rectangle  
3. Hold **Left Shift** — mouse moves to center of detected circles
4. Release **Left Shift** to stop tracking

> [!TIP]
> Best used for tracking moving circular objects. The algorithm uses basic edge detection to find high-contrast regions.

### arrasbot.py — State Watchdog

Run in terminal and use these commands:

| Command | Description |
|---------|-------------|
| `stop` | Stop monitoring |
| `dbgmon` | List all monitors |
| `probe` | Sample pixel at cursor |
| `screenshot` | Capture screen |
| `status` | Show current state |
| `setscale <1\|2>` | Set display scaling |
| `setmon <index>` | Change monitor |

> [!NOTE]
> **Logs** → `logs/abss_*.log`  
> **Screenshots** → `~/Desktop/abss/<session>/`

### asnake.py — DQN Snake AI

```bash
cd random
python asnake.py
```

- Configure via `snake_config.json`
- Models saved to `snake_models/`
- Press `Esc` to quit

---

## Configuration

> [!IMPORTANT]
> Coordinates are hardcoded for specific resolutions. You'll need to calibrate for your display.

### Display Scaling

Set `SCALE` in `arrasbot.py`:
- **Retina/HiDPI** (macOS): `SCALE = 2`
- **Standard displays**: `SCALE = 1`

### Calibrating Coordinates

1. Run `arrasbot.py`
2. Use `dbgmon` to list monitor properties
3. Use `probe` to sample pixel colors at cursor position
4. Update coordinates in scripts as needed

---

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| 🐧 **Linux** | ✅ Primary | X11 recommended; Wayland has pynput limitations |
| 🍎 **macOS** | ✅ Tested | Requires Accessibility + Screen Recording permissions |
| 🪟 **Windows** | ✅ Tested | May need Administrator for input automation |

> [!CAUTION]
> **Wayland users**: pynput works best on X11. Consider switching sessions or using XWayland.

---

## Troubleshooting

<details>
<summary><strong>Permission Issues</strong></summary>

**macOS**: System Settings → Privacy & Security → Enable Accessibility + Screen Recording

**Linux**: Ensure X11 session; check pynput docs for your DE

**Windows**: Run Terminal as Administrator
</details>

<details>
<summary><strong>Coordinate/Scaling Issues</strong></summary>

1. Run `arrasbot.py` → `dbgmon` to check monitors
2. Use `probe` command to verify pixel positions
3. Adjust `SCALE` (2 for HiDPI, 1 for standard)
4. Re-map hardcoded coordinates for your resolution
</details>

<details>
<summary><strong>ModuleNotFoundError</strong></summary>

```bash
# Ensure venv is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```
</details>

<details>
<summary><strong>Tesseract Not Found</strong></summary>

Ensure Tesseract OCR is installed and in PATH:
```bash
tesseract --version
```
</details>

---

## Development

> [!NOTE]
> See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed conventions and architecture patterns.

### Key Patterns

- **Threading**: Daemon threads with global boolean flags
- **Input**: Single `KeyboardController`/`MouseController` per module
- **Color Detection**: Use `color_close(rgb1, rgb2, tol=6)` for tolerance
- **File Paths**: Always use `pathlib.Path`

### Contributing

1. Test on your target platform
2. Use `pathlib` for cross-platform paths
3. Follow existing code patterns
4. Add platform detection for new scripts
5. Include type annotations

---

## License

**CC BY-NC-SA 4.0** — Non-commercial use only. See [LICENSE](LICENSE) and [NOTICE](NOTICE) for details.

---

> [!WARNING]
> **Disclaimer**: This tool is for educational purposes only. The authors are not responsible for any consequences of misuse.