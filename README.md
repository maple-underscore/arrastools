[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

# arrastools

Desktop automation tools and a PPO-based AI for Arras.io gameplay. Cross-platform support for macOS, Linux, and Windows.

> [!TIP]
> **Python 3.14 is recommended** for optimal performance and compatibility.
> ```bash
> # Create a Python 3.14 virtual environment
> python3.14 -m venv .venv314
> 
> # Activate it
> source .venv314/bin/activate  # Linux/macOS
> .venv314\Scripts\activate     # Windows
> ```

> [!WARNING]
> This tool automates keyboard and mouse input. Use responsibly and ensure compliance with game terms of service.

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

> [!IMPORTANT]
> Ensure you have Python 3.10+ installed (3.14 recommended). Check with: `python3 --version`

### 1. Clone the repository
```bash
git clone https://github.com/maple-underscore/arrastools.git
cd arrastools
```

### 2. Create a virtual environment (recommended)
```bash
# Python 3.14 (recommended)
python3.14 -m venv .venv314
source .venv314/bin/activate  # Linux/macOS
# OR
.venv314\Scripts\activate     # Windows

# Or use default Python 3
python3 -m venv .venv
source .venv/bin/activate     # Linux/macOS
# OR
.venv\Scripts\activate        # Windows
```

> [!NOTE]
> Virtual environments isolate project dependencies from your system Python, preventing version conflicts.

### 3. Install Python dependencies
```bash
pip install pynput mss numpy ping3 pillow torch shapely pytesseract
```

> [!TIP]
> Use `pip install -r requirements.txt` if available for easier dependency management.

### 4. Install system dependencies

> [!CAUTION]
> **Tesseract OCR is required** for text scanning features (`scan_screen_for_text`). The script will work without it but text detection will be disabled.

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

## Configuration

> [!IMPORTANT]
> **First-time setup**: Coordinates are configured for a specific screen resolution. You'll likely need to adjust these for your display.

### Display Scaling
Adjust `SCALE` in `arrasbot.py` based on your display:
- **Retina/HiDPI displays (macOS)**: `SCALE = 2`
- **Standard displays (Windows/Linux)**: `SCALE = 1`

> [!NOTE]
> Use `arrasbot.py` command `dbgmon` to check your monitor properties and determine the correct scale.

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

> [!TIP]
> Run `python arrasbot.py` and use the `probe` command, then hover your mouse over UI elements to get their exact coordinates.

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

> [!NOTE]
> Most issues stem from permissions or coordinate mismatches. Follow the steps below for your platform.

### Permission Issues

**macOS:**
- Go to System Settings > Privacy & Security
- Enable Accessibility for your Terminal/IDE
- Enable Screen Recording for your Terminal/IDE

> [!WARNING]
> macOS will prompt for permissions on first run. You must grant both Accessibility and Screen Recording access.

**Linux:**
- Check if running on X11 (pynput works better than Wayland)
- Accessibility permissions vary by desktop environment

**Windows:**
- Run Terminal as Administrator if automation fails
- Ensure Tesseract is in your system PATH

### Coordinate/Scaling Issues

> [!TIP]
> Follow these steps to fix coordinate-related issues:
> 1. Use `arrasbot.py` command `dbgmon` to list monitor properties
> 2. Use `probe` command to check pixel colors at cursor position
> 3. Adjust `SCALE` variable (2 for HiDPI, 1 for standard)
> 4. Re-map coordinates for your resolution

### Dependency Issues
- Ensure Tesseract OCR is installed system-wide
- Use virtual environment to isolate Python packages
- Check pynput documentation for platform-specific issues

> [!CAUTION]
> If you encounter `ModuleNotFoundError`, ensure your virtual environment is activated and dependencies are installed.

## Development

> [!NOTE]
> See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed development guidelines, conventions, and architecture notes.

> [!TIP]
> **For contributors**: All functions now have type annotations for better IDE support and type checking with Mypy.

## License

CC BY-NC-SA 4.0 License - See LICENSE and NOTICE files for details. Non-commercial use only.

## Contributing

> [!IMPORTANT]
> Contributions welcome! Please follow these guidelines:

1. **Test on your target platform** (macOS/Linux/Windows)
2. **Use `pathlib`** for file paths (cross-platform compatibility)
3. **Follow existing patterns** (see copilot-instructions.md)
4. **Add platform detection** for new scripts
5. **Include type annotations** for all new functions

> [!TIP]
> Run `mypy --check-untyped-defs` to verify type annotations before submitting.

## Disclaimer

> [!WARNING]
> This tool is for **educational purposes only**. Use responsibly and in accordance with game terms of service. The authors are not responsible for any consequences of misuse.