[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

# arrastools

Desktop automation tools and a PPO-based AI for Arras.io gameplay. Cross-platform support for macOS, Linux, and Windows.

## Features

- **Hotkey-driven automation** (`arrastools.py`, `arrastools2.py`): Control gameplay with keyboard shortcuts
- **Game state monitoring** (`arrasbot.py`): Automatic detection of disconnection, death, and bans with logging
- **PPO Reinforcement Learning AI** (`arrasai.py`): Train an AI agent to play Arras.io
- **Copypasta automation** (`arrascopypasta.py`): Send text automatically with timing control
- **Cross-platform**: Works on macOS, Linux (Arch/Debian/Ubuntu), and Windows

## Platform Support

### macOS
✅ **Primary development platform** - Fully tested

**Requirements:**
- macOS 10.14 or later
- Accessibility + Screen Recording permissions (System Settings > Privacy & Security)
- Homebrew (recommended): `brew install tesseract`

### Linux
✅ **Tested on Arch, Debian, Ubuntu**

**Requirements:**
```bash
# Debian/Ubuntu
sudo apt install python3-tk tesseract-ocr

# Arch
sudo pacman -S tk tesseract
```

**Notes:**
- Works best on X11; Wayland may have limitations with pynput
- Accessibility permissions may vary by desktop environment
- Use `SCALE=1` for standard displays

### Windows
✅ **Tested on Windows 10/11**

**Requirements:**
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (install separately, add to PATH)
- May require running Terminal as Administrator for input automation
- Use `SCALE=1` for standard displays

### Android
⚠️ **Experimental** - Limited support
- pynput may not work on all devices
- Consider using Termux with X11 server

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/maple-underscore/arrastools.git
cd arrastools
```

### 2. Create a virtual environment (recommended)
```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Python dependencies
```bash
pip install pynput mss numpy ping3 pillow torch shapely pytesseract
```

### 4. Install system dependencies

**macOS:**
```bash
brew install tesseract
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install python3-tk tesseract-ocr
```

**Windows:**
- Download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- Add Tesseract to your system PATH

## Quick Start

### Automation Tools
```bash
python arrastools.py
```

**Key shortcuts (hold Ctrl):**
- `Ctrl+1` (press 1-3 times): Arena size automation
- `Ctrl+y`: Controlled nuke (click two points)
- `Alt+Arrow` (`Option+Arrow` on macOS): 1-pixel mouse movement
- `Ctrl+9`: Nuke
- `Ctrl+m`: Benchmark balls
- `Esc`: Stop current activity
- `Ctrl+Esc`: Emergency exit

### Bot Monitor
```bash
python arrasbot.py
```

**CLI commands:**
- `status`: Check bot state
- `screenshot`: Take manual screenshot
- `probe`: Sample pixel color at mouse position
- `dbgmon`: List all monitors
- `setscale <1|2>`: Set display scaling
- `ping`: Check connection to arras.io

### AI Training
```bash
python arrasai.py
```

**Hotkeys while training:**
- `Esc`: Force stop
- `p`: Pause/resume
- `r`: Simulate death

## Configuration

### Display Scaling
Adjust `SCALE` in `arrasbot.py` based on your display:
- **Retina/HiDPI displays (macOS)**: `SCALE = 2`
- **Standard displays (Windows/Linux)**: `SCALE = 1`

### Game Region
Update `GAME_REGION` coordinates in `arrasai.py` to match your screen resolution:
```python
GAME_REGION = Polygon([
    (x1, y1), (x2, y2), ...  # Your screen coordinates
])
```

Use `arrasbot.py` with the `probe` command to find your coordinates.

### Click Positions
Hard-coded positions in `arrastools.py` (e.g., `conq_quickstart()`) may need adjustment for different resolutions.

## Project Structure

```
arrastools/
├── arrastools.py          # Main automation script
├── arrastools2.py         # Alternative automation script
├── arrasbot.py            # Game state monitor
├── arrasai.py             # PPO AI trainer
├── arrascopypasta.py      # Text automation
├── copypastas/            # Text files for copypasta
├── arras_models/          # Saved AI models
├── logs/                  # Bot logs
└── .github/
    └── copilot-instructions.md  # AI coding agent guidance
```

## Troubleshooting

### Permission Issues

**macOS:**
- Go to System Settings > Privacy & Security
- Enable Accessibility for your Terminal/IDE
- Enable Screen Recording for your Terminal/IDE

**Linux:**
- Check if running on X11 (pynput works better than Wayland)
- Accessibility permissions vary by desktop environment

**Windows:**
- Run Terminal as Administrator if automation fails
- Ensure Tesseract is in your system PATH

### Coordinate/Scaling Issues
1. Use `arrasbot.py` command `dbgmon` to list monitor properties
2. Use `probe` command to check pixel colors at cursor position
3. Adjust `SCALE` variable (2 for HiDPI, 1 for standard)
4. Re-map coordinates for your resolution

### Dependency Issues
- Ensure Tesseract OCR is installed system-wide
- Use virtual environment to isolate Python packages
- Check pynput documentation for platform-specific issues

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed development guidelines, conventions, and architecture notes.

## License

CC BY-NC-SA 4.0 License - See LICENSE and NOTICE files for details. Non-commercial use only.

## Contributing

Contributions welcome! Please:
1. Test on your target platform (macOS/Linux/Windows)
2. Use `pathlib` for file paths (cross-platform)
3. Follow existing patterns (see copilot-instructions.md)
4. Add platform detection for new scripts

## Disclaimer

This tool is for educational purposes. Use responsibly and in accordance with game terms of service.