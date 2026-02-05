# -*- coding: utf-8 -*-

"""Hotkey-driven Arras macros and drawing helpers.

The script mirrors historical behavior; readability tweaks (docstrings,
comments) clarify intent without altering any macro logic.
"""

# Set to True to use C++ implementations when available
USE_CPP_MACROS = True

tailamount = 40

style = None

import random
import time
import threading
import multiprocessing
from multiprocessing import Process
import platform
import sys
import math
import string
from typing import Any, TYPE_CHECKING

# Detect platform early (needed for overlay decision)
PLATFORM = platform.system().lower()  # 'darwin' (macOS), 'linux', 'windows', 'android'

# Optional GUI overlay (tkinter). If unavailable, overlay auto-disables.
# On macOS, tkinter windows MUST be created on the main thread, so we disable
# the overlay by default on macOS to avoid NSInternalInconsistencyException crashes.
DISABLE_OVERLAY_ON_MACOS = PLATFORM == 'darwin'

try:
    import tkinter as tk
    overlay_import_error = None
    # If overlay would be disabled on macOS, set it to disabled now
    if DISABLE_OVERLAY_ON_MACOS:
        tk = None
        overlay_import_error = "Overlay disabled on macOS (tkinter threading issue)"
except Exception as exc:  # ModuleNotFoundError or Tcl/Tk missing
    tk = None
    overlay_import_error = exc

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event as MpEvent
else:
    MpEvent = Any

try:
    from pynput.keyboard import Controller as KeyboardController, Key, KeyCode, Listener as KeyboardListener
    from pynput.mouse import Controller as MouseController, Button, Listener as MouseListener
except ImportError:
    print("Missing dependency: pynput is required to run this script.")
    print("Install with: python3 -m pip install -r requirements.txt")
    sys.exit(1)

# macOS Quartz support for better Unicode typing
HAS_QUARTZ = False
if PLATFORM == 'darwin':
    try:
        from Quartz import (
            CGEventCreateKeyboardEvent,
            CGEventKeyboardSetUnicodeString,
            CGEventPost,
            kCGHIDEventTap
        )
        HAS_QUARTZ = True
    except ImportError:
        print("Warning: Quartz not available. Unicode typing may not work properly.")
        print("Install with: pip install pyobjc-framework-Quartz")

try:
    import mss
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("Warning: OCR dependencies (mss, pytesseract, Pillow) not available.")
    print("Text scanning features will be disabled.")
    print("Install with: pip install mss pytesseract pillow")


listener_event_injected = False


class RobustKeyboardListener(KeyboardListener):
    """Wrapper around pynput's KeyboardListener that handles Unicode decode errors.
    
    On macOS, certain keyboard events can trigger UnicodeDecodeError in pynput's
    internal event handler. This wrapper catches those errors gracefully.
    """
    
    def _handle_message(self, proxy: Any, event_type: Any, event: Any, refcon: Any, is_injected: Any) -> None:
        """Override pynput's message handler to catch Unicode decode errors.
        
        This is called from the C callback handler and processes keyboard events.
        On macOS, some special keys can cause UnicodeDecodeError in _event_to_key().
        """
        global listener_event_injected
        listener_event_injected = bool(is_injected)
        try:
            super()._handle_message(proxy, event_type, event, refcon, is_injected)
        except UnicodeDecodeError:
            # Silently ignore Unicode decode errors from special keys on macOS
            # These don't indicate a problem and shouldn't crash the listener
            pass
        except Exception as e:
            # Log but don't crash on other unexpected errors
            print(f"Keyboard listener error (suppressed): {type(e).__name__}: {e}")
        finally:
            listener_event_injected = False


# Platform notes:
# - macOS: Ctrl hotkeys work; Option+Arrow for 1px nudges
# - Linux: Ctrl hotkeys work; Alt+Arrow for 1px nudges
# - Windows: Ctrl hotkeys work; Alt+Arrow for 1px nudges
# - Android: Limited support (pynput may not work on all devices)

# C++ macro integration
try:
    from cpp_wrapper import (
        is_cpp_available,
        circles_cpp,
        walls_cpp,
        circlecrash_cpp,
        minicirclecrash_cpp,
        arena_automation_cpp,
        benchmark_cpp,
    )
    HAS_CPP = is_cpp_available()
except ImportError:
    HAS_CPP = False
    print("C++ wrapper not available, using pure Python implementations")


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL VARIABLES
# ═══════════════════════════════════════════════════════════════════════════

# -------- Controllers and Basic State --------
controller = KeyboardController()
mouse = MouseController()
pressed_keys = set()
length = 4
step = 20
s = 25  # circle spacing in px

# -------- Feature Flags --------
ctrlswap = False  # When True, use Cmd (macOS) instead of Ctrl for macros
berserk = False  # When True, every typed character becomes random from a random fancy style
emoji_replacement_enabled = False  # Toggle emoji :{text}: replacement on/off (Ctrl+H)

# -------- Arena Automation Settings --------
arena_auto_terminate = True  # If True, stop after arena_auto_max_commands
arena_auto_max_commands = 576  # Number of commands before auto-termination
arena_auto_rate_limit = 150  # Maximum commands per second (0 = unlimited)
arena_size_step = 8  # Step size for arena size changes (must be even, default: 2)
arena_current_type = 1

# -------- Circle Mouse Settings --------
circle_mouse_active = False
circle_mouse_speed = 0.02  # Time delay between updates (lower = faster)
circle_mouse_radius = 100  # Radius in pixels
circle_mouse_direction = 1  # 1 for clockwise, -1 for counterclockwise

# -------- Macro State Flags --------
automation_working = False
engineer_spam_working = False
mcrash_working = False
custom_reload_spam_working = False
circle_art_working = False
circlecrash_working = False
braindamage_working = False

# -------- Legacy Thread References (deprecated) --------
mcrash_thread = None
engineer_spam_thread = None
circlecrash_thread = None


# ═══════════════════════════════════════════════════════════════════════════
# INPUT HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════
def press_with_delay(key: str | Key, wait: float = 0.1, count: int = 2) -> None:
    """Press a key multiple times with delay between presses.
    
    Args:
        key: The key to press
        wait: Delay in seconds between presses (default: 0.1)
        count: Number of times to press (default: 2)
    """
    for i in range(count):
        controller.tap(key)
        if i < count - 1:  # Don't sleep after last tap
            time.sleep(wait)


def type_unicode(text: str) -> None:
    """Type Unicode text using the best available method for the platform.
    
    On macOS with Quartz, uses CGEvent for proper Unicode support.
    Falls back to pynput on other platforms or if Quartz is unavailable.
    
    Args:
        text: The Unicode text to type
    """
    if PLATFORM == 'darwin' and HAS_QUARTZ:
        # Create a dummy keyboard event
        event = CGEventCreateKeyboardEvent(None, 0, True)
        
        # IMPORTANT: Quartz expects UTF-16 code units, not Python length
        utf16 = text.encode("utf-16-le")
        length = len(utf16) // 2
        
        CGEventKeyboardSetUnicodeString(event, length, text)
        CGEventPost(kCGHIDEventTap, event)
    else:
        # Fallback to pynput for non-macOS or if Quartz unavailable
        controller.type(text)


def type_with_enter(text: str, wait: float = 0) -> None:
    """Type text wrapped with Enter key presses.
    
    Args:
        text: The text to type
        wait: Optional delay after first enter and before final enter (default: 0)
    """
    processed_text = process_fancy_patterns(text)
    processed_text = process_emoji_patterns(processed_text)
    controller.tap(Key.enter)
    if wait > 0:
        time.sleep(wait)
    type_unicode(processed_text)
    if wait > 0:
        time.sleep(wait)
    controller.tap(Key.enter)


def type_in_console(text: str, hold_backtick: bool = True) -> None:
    """Type text in the game console (backtick-wrapped).
    
    Args:
        text: The text to type
        hold_backtick: If True, hold backtick during typing for speed (default: True)
    """
    processed_text = process_fancy_patterns(text)
    processed_text = process_emoji_patterns(processed_text)
    if hold_backtick:
        controller.press("`")
        controller.type(processed_text)
        controller.release("`")
    else:
        controller.tap("`")
        controller.type(processed_text)
        controller.tap("`")


def safe_chr(codepoint):
    try:
        return chr(codepoint)
    except ValueError:
        return None


STYLES = {
    # ───────────── Mathematical ─────────────
    "bold_serif": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
        "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
        "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
    )),

    "italic_sans": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
    )),

    "bold_sans": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
        "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
        "𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵𝟬"
    )),

    "bold_italic_serif": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛"
        "𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁"
    )),

    "bold_italic_sans": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯"
        "𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕"
    )),

    "double_struck": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫"
        "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ"
        "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"
    )),

    "monospace": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣"
        "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"
        "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"
    )),

    # ───────────── Decorative ─────────────
    "circled": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"
        "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ"
        "⓪①②③④⑤⑥⑦⑧⑨"
    )),

    "squared": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉"
    )),

    "fullwidth": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
        "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
        "０１２３４５６７８９"
    )),

    # ───────────── Script / Gothic ─────────────
    "script": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝒶𝒷𝒸𝒹ℯ𝒻ℊ𝒽𝒾𝒿𝓀𝓁𝓂𝓃ℴ𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏"
        "𝒜ℬ𝒞𝒟ℰℱ𝒢ℋℐ𝒥𝒦ℒℳ𝒩𝒪𝒫𝒬ℛ𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵"
    )),

    "bold_script": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃"
        "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"
    )),

    "fraktur": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷"
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ"
    )),

    "cursed2": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ค๒ς๔єŦﻮђเןкɭ๓ภ๏קợгรՇยשฬאץչค๒ς๔єŦﻮђเןкɭ๓ภ๏קợгรՇยשฬאץչ"
    )),

    "cursed3": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ąɓƈđɛƒɠɦįʝƙŀɱŋơƥɋřşŧųʋŵҳyʐĄƁƇĐƐƑƓĦĮʝƘĿƜŊƠƤɊŘŞŦŲƲŴҲYʐ"
    )),

    "cursed4": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "αႦƈԃҽϝɠԋιʝƙʅɱɳσρϙɾʂƚυʋɯxყȥΑႦƇԂƐϜƓԊΙʝƘʟƜƝΣΡϘɌƧƬΥƲɰXყȤ"
    )),

    "cursed5": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ǟɮƈɖɛʄɢɦɨʝӄʟʍռօքզʀֆȶʊʋաӼʏʐǟɮƈɖɛʄɢɦɨʝӄʟʍռօքզʀֆȶʊʋաӼʏʐ"
    )),

    "cursed6": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᏗᏰፈᎴᏋᎦᎶᏂᎥᏠᏦᏝᎷᏁᎧᎮᎤᏒᏕᏖᏬᏉᏇጀᎩፚᏗᏰፈᎴᏋᎦᎶᏂᎥᏠᏦᏝᎷᏁᎧᎮᎤᏒᏕᏖᏬᏉᏇጀᎩፚ"
    )),

    "cursed7": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ąცƈɖɛʄɠɧıʝƙƖɱŋơ℘զཞʂɬų۷ῳҳყʑąცƈɖɛʄɠɧıʝƙƖɱŋơ℘զཞʂɬų۷ῳҳყʑ"
    )),

    "cursed8": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ค๖¢໓ēfງhiวkl๓ຖ໐p๑rŞtนงຟxฯຊค๖¢໓ēfງhiวkl๓ຖ໐p๑rŞtนงຟxฯຊ"
    )),

    "cursed9": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "åß¢Ðê£ghïjklmñðþqr§†µvwx¥zÄßÇÐÈ£GHÌJKLMñÖþQR§†ÚVW×¥Z"
    )),

    "cursed10": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "₳฿₵ĐɆ₣₲ⱧłJ₭Ⱡ₥₦Ø₱QⱤ₴₮ɄV₩ӾɎⱫ₳฿₵ĐɆ₣₲ⱧłJ₭Ⱡ₥₦Ø₱QⱤ₴₮ɄV₩ӾɎⱫ"
    )),

    "bold_fraktur": dict(zip(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅"
    ))
}

# Emoji mapping system: [text, emoji] pairs
# Usage: type :{text}: to replace with emoji
EMOJIS = [
    ["heart", "❤️"],
    ["love", "❤️"],
    ["smile", "😊"],
    ["happy", "😊"],
    ["sad", "😢"],
    ["sob", "😭"],
    ["laugh", "😂"],
    ["lol", "😂"],
    ["fire", "🔥"],
    ["hot", "🔥"],
    ["cool", "😎"],
    ["wow", "😲"],
    ["shocked", "😲"],
    ["angry", "😠"],
    ["rage", "😡"],
    ["puke", "🤮"],
    ["sick", "🤢"],
    ["thumbs", "👍"],
    ["thumbsup", "👍"],
    ["thumbsdown", "👎"],
    ["clap", "👏"],
    ["wave", "👋"],
    ["pray", "🙏"],
    ["thanks", "🙏"],
    ["point", "👉"],
    ["ok", "👌"],
    ["victory", "✌️"],
    ["peace", "☮️"],
    ["star", "⭐"],
    ["sparkle", "✨"],
    ["boom", "💥"],
    ["explosion", "💥"],
    ["sun", "☀️"],
    ["moon", "🌙"],
    ["star", "⭐"],
    ["zap", "⚡"],
    ["lightning", "⚡"],
    ["flower", "🌸"],
    ["rose", "🌹"],
    ["skull", "💀"],
    ["snake", "🐍"],
    ["turtle", "🐢"],
    ["cat", "🐱"],
    ["dog", "🐶"],
    ["pig", "🐷"],
    ["bird", "🐦"],
    ["fish", "🐠"],
    ["dragon", "🐉"],
    ["unicorn", "🦄"],
    ["pizza", "🍕"],
    ["cake", "🍰"],
    ["candy", "🍬"],
    ["apple", "🍎"],
    ["watermelon", "🍉"],
    ["beer", "🍺"],
    ["wine", "🍷"],
    ["coffee", "☕"],
    ["gift", "🎁"],
    ["bomb", "💣"],
    ["gun", "🔫"],
    ["sword", "⚔️"],
    ["shield", "🛡️"],
    ["medal", "🏅"],
    ["trophy", "🏆"],
    ["rocket", "🚀"],
    ["car", "🚗"],
    ["bike", "🚲"],
    ["money", "💰"],
    ["gem", "💎"],
    ["clock", "🕐"],
    ["watch", "⌚"],
    ["calendar", "📅"],
    ["phone", "📱"],
    ["computer", "💻"],
    ["keyboard", "⌨️"],
    ["mouse", "🖱️"],
    ["printer", "🖨️"],
    ["camera", "📷"],
    ["video", "🎥"],
    ["music", "🎵"],
    ["notes", "🎶"],
    ["art", "🎨"],
    ["game", "🎮"],
    ["dice", "🎲"],
    ["cards", "🃏"],
    ["soccer", "⚽"],
    ["basketball", "🏀"],
    ["football", "🏈"],
    ["baseball", "⚾"],
    ["skull", "💀"],
    ["wilted_rose", "🥀"],
    ["tennis", "🎾"],
    ["volleyball", "🏐"],
    ["ping", "🏓"],
    ["checkmark", "✅"],
    ["check", "✅"],
    ["cross", "❌"],
    ["x", "❌"],
    ["warning", "⚠️"],
    ["error", "❌"],
    ["info", "ℹ️"],
    ["question", "❓"],
    ["idea", "💡"],
    ["bulb", "💡"],
    ["eyes", "👀"],
    ["see", "👀"],
    ["look", "👀"],
]


# ═══════════════════════════════════════════════════════════════════════════
# FANCY TEXT AND STYLING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def fancy(text, style):
    candidate = STYLES.get(style)
    while candidate == style:
        candidate = STYLES.get(style)
    if not candidate:
        raise ValueError(f"Unknown style: {style}")
    print(f"fancy style: {style}")
    return "".join(candidate.get(c, c) for c in text)


def apply_berserk(text: str) -> str:
    """Transform each character with a random fancy style.
    
    Args:
        text: The text to berserkify
        
    Returns:
        Text with each character replaced with its fancy equivalent from a random style
    """
    if not berserk:
        return text
    
    result = []
    for char in text:
        # Pick a random style for each character
        style = random.choice(list(STYLES.keys()))
        table = STYLES.get(style)
        if table:
            # Get the fancy character or keep original if not in style
            result.append(table.get(char, char))
        else:
            result.append(char)
    
    return ''.join(result)


def process_fancy_patterns(text: str) -> str:
    """Replace 'f:{text}:' patterns with randomly styled text.
    
    Supports escaping:
    - \\f:text: -> literal "f:text:" (escaped pattern)
    - f:text\\:more: -> allows escaped colons within the pattern
    
    Args:
        text: Input text that may contain f:{text}: patterns
        
    Returns:
        Text with all fancy patterns replaced with styled versions
    """
    import re
    
    def replace_fancy(match):
        # Check if this match is escaped with backslash
        start_pos = match.start()
        if start_pos > 0 and text[start_pos - 1] == '\\':
            # Remove the escape backslash and return the literal pattern
            return match.group(0)
        
        # Get content and unescape any \: within it
        content = match.group(1).replace('\\:', ':')
        random_style = random.choice(list(STYLES.keys()))
        return fancy(content, random_style)
    
    # First, handle escaped patterns by temporarily replacing them
    text = text.replace('\\f:', '\x00ESCAPED_FANCY\x00')
    
    # Match f:content: where content can include \: but not unescaped :
    # This regex allows \: within the content
    text = re.sub(r'f:((?:[^:\\]|\\:|\\.)+):', replace_fancy, text)
    
    # Restore escaped patterns (remove the escape backslash)
    text = text.replace('\x00ESCAPED_FANCY\x00', 'f:')
    
    return text


def check_and_replace_fancy_pattern() -> None:
    """Check if keyboard buffer ends with f:{text}: and replace it.
    
    Called when ':' is typed to check if we've completed a fancy pattern.
    Supports escaping:
    - \\f:text: -> won't trigger (escaped pattern)
    - f:text\\:more: -> allows escaped colons within the pattern
    """
    global keyboard_buffer
    
    # Get the buffer as a string
    buffer_str = ''.join(keyboard_buffer)
    
    # Look for f:{text}: pattern at the end, allowing \: within content
    import re
    match = re.search(r'f:((?:[^:\\]|\\:|\\.)+):$', buffer_str)
    
    if match:
        # Check if the pattern is escaped (preceded by backslash)
        match_start = len(buffer_str) - len(match.group(0))
        if match_start > 0 and buffer_str[match_start - 1] == '\\':
            # This is an escaped pattern, remove the escape backslash
            controller.tap(Key.backspace)
            time.sleep(0.01)
            # Update buffer to remove the escape backslash
            keyboard_buffer.pop(-len(match.group(0)) - 1)
            return
        
        # Get the captured text from the pattern and unescape \:
        inner_text = match.group(1).replace('\\:', ':')
        
        # Choose a random style
        style = random.choice(list(STYLES.keys()))
        styled_text = fancy(inner_text, style)
        
        # Calculate how many characters to delete (f: + text + :)
        pattern_len = len(match.group(0))
        
        # Delete the pattern by pressing backspace
        time.sleep(0.05)  # Initial delay before starting backspaces
        for _ in range(pattern_len):
            controller.tap(Key.backspace)
            time.sleep(0.02)  # Increased delay between backspaces
        
        # Type the styled text using Unicode-aware function
        time.sleep(0.05)
        type_unicode(styled_text)
        
        # Clear the matching portion from buffer
        keyboard_buffer[:] = keyboard_buffer[:-pattern_len]
        
        # Trim buffer if too long
        if len(keyboard_buffer) > max_buffer_size:
            keyboard_buffer = keyboard_buffer[-max_buffer_size:]


def process_emoji_patterns(text: str) -> str:
    """Replace ':{text}:' patterns with corresponding emojis.
    
    Only processes if emoji_replacement_enabled is True.
    
    Supports escaping:
    - \\:text: -> literal ":text:" (escaped pattern)
    - :text\\:more: -> allows escaped colons within the pattern
    
    Emoji mapping is defined in the EMOJIS list: [[text, emoji], ...]
    
    Args:
        text: Input text that may contain :{text}: patterns
        
    Returns:
        Text with all emoji patterns replaced with their emoji equivalents
    """
    global emoji_replacement_enabled
    
    if not emoji_replacement_enabled:
        return text
    
    import re
    
    def replace_emoji(match):
        # Check if this match is escaped with backslash
        start_pos = match.start()
        if start_pos > 0 and text[start_pos - 1] == '\\':
            # Remove the escape backslash and return the literal pattern
            return match.group(0)
        
        # Get content and unescape any \: within it
        content = match.group(1).replace('\\:', ':').lower()
        
        # Look for matching emoji
        for emoji_text, emoji_char in EMOJIS:
            if emoji_text.lower() == content:
                return emoji_char
        
        # If no match found, return original pattern
        return match.group(0)
    
    # First, handle escaped patterns by temporarily replacing them
    text = text.replace('\\:', '\x00ESCAPED_COLON\x00')
    
    # Match :content: where content can include escaped colons
    # This regex allows \: within the content (before escaping is restored)
    text = re.sub(r':((?:[^:\\]|\\.)+):', replace_emoji, text)
    
    # Restore escaped colons
    text = text.replace('\x00ESCAPED_COLON\x00', ':')
    
    return text


def check_and_replace_emoji_pattern() -> None:
    """Check if keyboard buffer ends with :{text}: and replace it with emoji.
    
    Only processes if emoji_replacement_enabled is True.
    
    Called when ':' is typed to check if we've completed an emoji pattern.
    Supports escaping:
    - \\:text: -> won't trigger (escaped pattern)
    - :text\\:more: -> allows escaped colons within the pattern
    """
    global keyboard_buffer, emoji_replacement_enabled
    
    if not emoji_replacement_enabled:
        return
    
    # Get the buffer as a string
    buffer_str = ''.join(keyboard_buffer)
    
    # Look for :text: pattern at the end
    import re
    match = re.search(r':((?:[^:\\]|\\.)+):$', buffer_str)
    
    if match:
        # Check if the pattern is escaped (preceded by backslash)
        match_start = len(buffer_str) - len(match.group(0))
        if match_start > 0 and buffer_str[match_start - 1] == '\\':
            # This is an escaped pattern, remove the escape backslash
            controller.tap(Key.backspace)
            time.sleep(0.01)
            # Update buffer to remove the escape backslash
            keyboard_buffer.pop(-len(match.group(0)) - 1)
            return
        
        # Get the captured text from the pattern and unescape \:
        inner_text = match.group(1).replace('\\:', ':').lower()
        
        # Find matching emoji
        emoji_char = None
        for emoji_text, emoji_replacement in EMOJIS:
            if emoji_text.lower() == inner_text:
                emoji_char = emoji_replacement
                break
        
        if emoji_char:
            # Calculate how many characters to delete (:text:)
            pattern_len = len(match.group(0))
            
            # Delete the pattern by pressing backspace
            time.sleep(0.05)  # Initial delay before starting backspaces
            for _ in range(pattern_len):
                controller.tap(Key.backspace)
                time.sleep(0.02)
            
            # Type the emoji using Unicode-aware function
            time.sleep(0.05)
            type_unicode(emoji_char)
            
            # Clear the matching portion from buffer
            keyboard_buffer[:] = keyboard_buffer[:-pattern_len]
            
            # Trim buffer if too long
            if len(keyboard_buffer) > max_buffer_size:
                keyboard_buffer = keyboard_buffer[-max_buffer_size:]


# ═══════════════════════════════════════════════════════════════════════════
# CONSOLE INPUT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def tap_in_console(keys: str, hold_backtick: bool = True) -> None:
    """Tap individual keys in the game console (backtick-wrapped).
    
    Args:
        keys: String of keys to tap individually (e.g., "ch" taps 'c' then 'h')
        hold_backtick: If True, hold backtick during tapping for speed (default: True)
    """
    if hold_backtick:
        controller.press("`")
        for k in keys:
            controller.tap(k)
        controller.release("`")
    else:
        for k in keys:
            controller.tap("`")
            controller.tap(k)
            controller.tap("`")


def repeat_tap_in_console(key: str, count: int, hold_backtick: bool = True) -> None:
    """Tap a key multiple times in the game console.
    
    Args:
        key: The key to tap
        count: Number of times to tap
        hold_backtick: If True, hold backtick during tapping for speed (default: True)
    """
    if hold_backtick:
        controller.press("`")
        for _ in range(count):
            controller.tap(key)
        controller.release("`")
    else:
        for _ in range(count):
            controller.tap("`")
            controller.tap(key)
            controller.tap("`")


def repeat_tap_pattern_in_console(pattern: str, count: int, hold_backtick: bool = True) -> None:
    """Repeat a pattern of key taps in the game console.
    
    Args:
        pattern: String of keys to tap as a pattern (e.g., "ch" taps 'c' then 'h')
        count: Number of times to repeat the pattern
        hold_backtick: If True, hold backtick during tapping for speed (default: True)
    """
    if hold_backtick:
        controller.press("`")
        for _ in range(count):
            for k in pattern:
                controller.tap(k)
        controller.release("`")
    else:
        for _ in range(count):
            for k in pattern:
                controller.tap("`")
                controller.tap(k)
                controller.tap("`")

# ═══════════════════════════════════════════════════════════════════════════
# PROCESS AND THREAD REFERENCES
# ═══════════════════════════════════════════════════════════════════════════
automation_process = None
softwallstack_process = None
circle_art_thread: threading.Thread | None = None
braindamage_process = None
tail_process = None
circle_mouse_process = None
custom_reload_spam_process = None
engineer_spam_process = None
circlecrash_process = None
mcrash_process: Process | None = None

# -------- Overlay System --------
overlay_thread: threading.Thread | None = None
overlay_stop_event = threading.Event()
overlay_visible = False
overlay_user_disabled = False
overlay_refresh_ms = 250

# -------- Keyboard Buffer for Fancy Text Auto-Expansion --------
keyboard_buffer = []
max_buffer_size = 100  # Keep last 100 characters
fancy_pattern_active = False

# ═══════════════════════════════════════════════════════════════════════════
# MULTIPROCESSING EVENTS AND SHARED VALUES
# ═══════════════════════════════════════════════════════════════════════════
automation_event = multiprocessing.Event()
engineer_spam_event = multiprocessing.Event()
circle_art_event = threading.Event()  # Changed to threading.Event for faster response time
braindamage_event = multiprocessing.Event()
circle_mouse_event = multiprocessing.Event()
mcrash_event = multiprocessing.Event()
custom_reload_spam_event = multiprocessing.Event()
circle_mouse_radius_value = multiprocessing.Value('i', circle_mouse_radius)
circle_mouse_speed_value = multiprocessing.Value('d', circle_mouse_speed)
circle_mouse_direction_value = multiprocessing.Value('i', circle_mouse_direction)

# ═══════════════════════════════════════════════════════════════════════════
# DOUBLE-TAP TIMING VARIABLES
# ═══════════════════════════════════════════════════════════════════════════
ctrl6_last_time = 0.0
ctrl6_armed = False
ctrl7_last_time = 0.0
ctrl7_armed = False
ctrl1_last_time = 0.0
ctrl1_armed = False
ctrlq_last_time = 0.0
ctrlq_armed = False
ctrla_last_time = 0.0
ctrla_armed = False
ctrlz_last_time = 0.0
ctrlz_armed = False
ctrly_last_time = 0.0
ctrly_armed = False
ctrlu_last_time = 0.0
ctrlu_armed = False
ctrli_last_time = 0.0
ctrli_armed = False
ctrlg_last_time = 0.0
ctrlg_armed = False
ctrlr_last_time = 0.0
ctrlr_armed = False

# ═══════════════════════════════════════════════════════════════════════════
# SHIFT-BIND FLAGS
# ═══════════════════════════════════════════════════════════════════════════
circle_art_shift_bind = False
mcrash_shift_bind = False

# ═══════════════════════════════════════════════════════════════════════════
# CIRCLE FINDER MODE STATE
# ═══════════════════════════════════════════════════════════════════════════
circle_finder_active = False
circle_finder_event = multiprocessing.Event()
circle_finder_process = None


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def generate_even(low: int = 2, high: int = 1024) -> int:
    return random.choice([i for i in range(low, high + 1) if i % 2 == 0])


# ═══════════════════════════════════════════════════════════════════════════
# OVERLAY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════
def _overlay_lines() -> list[str]:
    """Build overlay text for long-running macros."""
    dir_text = 'cw' if circle_mouse_direction_value.value >= 0 else 'ccw'
    rate_text = '∞' if arena_auto_rate_limit == 0 else str(arena_auto_rate_limit)
    lines: list[str] = [
        "Arras macro HUD (Ctrl+0 to hide)",
        f"Arena: {'ON' if automation_event.is_set() else 'off'} type={arena_current_type} step={arena_size_step} rate={rate_text}/s",
        f"engineer_spam: {'ON' if engineer_spam_event.is_set() else 'off'}",
        f"circle_art: {'ON' if circle_art_event.is_set() else 'off'} (shift-bind={'ON' if circle_art_shift_bind else 'off'})",
        f"Mcrash: {'ON' if (mcrash_event.is_set() or mcrash_working) else 'off'} (shift-bind={'ON' if mcrash_shift_bind else 'off'})",
        f"custom_reload_spam: {'ON' if custom_reload_spam_event.is_set() else 'off'}",
        f"Brain damage: {'ON' if braindamage_event.is_set() else 'off'}",
        f"Circle mouse: {'ON' if circle_mouse_event.is_set() else 'off'} r={circle_mouse_radius_value.value} v={circle_mouse_speed_value.value:.3f} dir={dir_text}",
        f"Circle finder: {'ON' if circle_finder_event.is_set() else 'off'}",
        f"Tail: {'ON' if (tail_process is not None and tail_process.is_alive()) else 'off'}",
        f"Softwall: {'ON' if (softwallstack_process is not None and softwallstack_process.is_alive()) else 'off'}",
        f"Armed: arena={'YES' if ctrl1_armed else 'no'} circle={'YES' if ctrl6_armed else 'no'} wall={'YES' if ctrl7_armed else 'no'} arenaclose={'YES' if ctrlr_armed else 'no'}",
        f"Ctrl swap: {'Cmd' if ctrlswap and PLATFORM == 'darwin' else 'Ctrl'}",
    ]
    return lines


def _overlay_worker() -> None:
    """Background TK loop that draws the overlay."""
    global overlay_visible, overlay_user_disabled
    if tk is None:
        print(f"Overlay disabled (tk unavailable): {overlay_import_error}")
        overlay_visible = False
        overlay_user_disabled = True
        return
    
    # On macOS, we need to handle Tkinter carefully. Create a new root window in this thread.
    # This thread is separate from the main thread, so we create a new event loop here.
    root = None
    try:
        # On macOS with tkinter from Homebrew, we need to be in a separate thread from the keyboard listener
        root = tk.Tk()
        root.withdraw()
        root.title("Arras HUD")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        try:
            root.attributes("-alpha", 0.85)
        except Exception:
            pass
        root.configure(bg="black")

        label = tk.Label(root, text="", fg="#8cff8c", bg="black", font=("Menlo", 12), justify="left")
        label.pack(anchor="w", padx=6, pady=6)
        root.geometry("360x220+20+20")
        root.deiconify()

        def refresh():
            if overlay_stop_event.is_set():
                try:
                    root.destroy()
                except Exception:
                    pass
                return
            try:
                label.configure(text="\n".join(_overlay_lines()))
            except Exception:
                pass
            try:
                root.after(overlay_refresh_ms, refresh)
            except Exception:
                pass

        refresh()
        overlay_visible = True
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Overlay mainloop error: {e}")
    except Exception as exc:
        print(f"Overlay disabled (tk init failed): {exc}")
        overlay_visible = False
        overlay_user_disabled = True
    finally:
        overlay_visible = False
        try:
            if root is not None:
                root.destroy()
        except Exception:
            pass


def start_overlay() -> None:
    """Show the overlay unless the user explicitly disabled it."""
    global overlay_thread, overlay_visible, overlay_user_disabled
    if overlay_user_disabled:
        return
    if tk is None:
        print(f"Overlay disabled (tk unavailable): {overlay_import_error}")
        overlay_user_disabled = True
        return
    if overlay_thread is not None and overlay_thread.is_alive():
        overlay_visible = True
        return
    overlay_stop_event.clear()
    overlay_thread = threading.Thread(target=_overlay_worker, daemon=True)
    overlay_thread.start()


def stop_overlay(user_request: bool = True) -> None:
    """Hide the overlay. If user-requested, prevent auto-respawn."""
    global overlay_thread, overlay_visible, overlay_user_disabled
    overlay_stop_event.set()
    if user_request:
        overlay_user_disabled = True
    if overlay_thread is not None:
        overlay_thread.join(timeout=1.5)
        overlay_thread = None
    overlay_visible = False


def ensure_overlay_running(reason: str = "") -> None:
    """start overlay when a long-running macro kicks in (unless user hid it)."""
    if overlay_user_disabled:
        return
    if not overlay_visible:
        start_overlay()
        if reason:
            print(f"overlay on ({reason})")


def toggle_overlay() -> None:
    """User-facing toggle used by hotkeys."""
    global overlay_user_disabled
    if overlay_visible:
        stop_overlay(user_request=True)
        print("overlay off")
    else:
        if tk is None:
            print(f"overlay unavailable (tk not installed): {overlay_import_error}")
            overlay_user_disabled = True
            return
        overlay_user_disabled = False
        start_overlay()
        print("overlay on")

def type_unicode_blocks(hex_string: str | None = None, blocks: int = 3) -> None:
    """Type a sequence of Unicode characters encoded as 4-hex-digit code points.

    Format examples:
        "011156F2C11A" -> U+0111 U+56F2 U+C11A

    Behavior:
      - If hex_string is provided its length must be a multiple of 4; each 4-digit
        group is interpreted as a hexadecimal code point.
      - If hex_string is None, a random sequence of `blocks` code points will be
        generated (default 3 groups => 12 hex digits).
      - Surrogate range (D800-DFFF) and code points > 0x10FFFF are skipped and
        regenerated when auto-generating.
      - Null code point (0000) is replaced with a literal space to avoid issues
        with consumers treating NUL as terminator.
      - Any group that parses but produces an unsupported character will be
        replaced with '�'.

    The resulting characters are typed inside backticks to keep existing
    console-open convention consistent with other macros.
    """
    groups: list[str] = []
    if hex_string is not None:
        hex_string = hex_string.strip().upper()
        if len(hex_string) % 4 != 0:
            print("unicode blocks: invalid length (must be multiple of 4)")
            return
        for i in range(0, len(hex_string), 4):
            groups.append(hex_string[i:i+4])
    else:
        while len(groups) < blocks:
            cp = random.randint(0, 0xFFFF)
            # Skip surrogate range and prefer printable BMP subset; allow null rarely
            if 0xD800 <= cp <= 0xDFFF:
                continue
            groups.append(f"{cp:04X}")

    chars: list[str] = []
    for g in groups:
        try:
            cp = int(g, 16)
            if cp == 0:
                # Replace NUL with space to avoid termination semantics
                chars.append(' ')
                continue
            if cp > 0x10FFFF or (0xD800 <= cp <= 0xDFFF):
                chars.append('�')
                continue
            chars.append(chr(cp))
        except Exception:
            chars.append('�')

    out = ''.join(chars)
    print(f"unicode blocks: {' '.join(groups)} -> '{out}'")
    type_unicode(out)


# ═══════════════════════════════════════════════════════════════════════════
# AUTOMATION MACROS
# ═══════════════════════════════════════════════════════════════════════════

def custom_reload_spam(run_event: MpEvent) -> None:
    chars = "kyu"
    controller.press("`")
    while run_event.is_set(): 
        controller.tap("q")
        controller.press("a")
        controller.press("r")
        controller.release("`")
        time.sleep(0.02)
        for char in chars:
            controller.tap(char)
            controller.press("`")
            controller.press("a")
            controller.press("r")
            controller.release("`")
            time.sleep(0.05)
        controller.press("`")
    controller.release("`")

def arena_size_automation(atype: int = 1, run_event: MpEvent | None = None) -> None:
    """Spam $arena commands to resize the arena.
    
    Args:
        atype: Type of automation (1=random, 2=bouncing, 3=inverse bouncing)
        run_event: Multiprocessing event to control when to stop
    """
    global arena_auto_terminate, arena_auto_max_commands, arena_auto_rate_limit, arena_size_step
    
    # Ensure step is even
    step = arena_size_step if arena_size_step % 2 == 0 else 2
    if step != arena_size_step:
        print(f"Warning: arena_size_step must be even, using {step} instead of {arena_size_step}")
    
    # Calculate delay between commands based on rate limit
    cmd_delay = (1.0 / arena_auto_rate_limit) if arena_auto_rate_limit > 0 else 0
    
    print(f"Arena automation type {atype} (step={step})")
    if arena_auto_terminate:
        print(f"Will terminate after {arena_auto_max_commands} commands")
    if arena_auto_rate_limit > 0:
        print(f"Rate limit: {arena_auto_rate_limit} commands/sec (delay: {cmd_delay:.3f}s)")
    
    if run_event is None:
        run_event = multiprocessing.Event()
        run_event.set()

    cmd_count = 0
    
    # C++ fast path: generate all commands at once if terminate is enabled
    if USE_CPP_MACROS and HAS_CPP and arena_auto_terminate:
        import random
        seed = random.randint(0, 2**32 - 1)
        commands = arena_automation_cpp(atype, arena_auto_max_commands, step, seed)
        print(f"Generated {len(commands)} commands using C++ (fast path)")
        for cmd in commands:
            if not run_event.is_set():
                break
            type_with_enter(cmd)
            if cmd_delay > 0:
                time.sleep(cmd_delay)
        return
    
    # Python fallback or continuous mode
    if atype == 1:
        while run_event.is_set():
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
            x = generate_even(2, 1024)
            y = generate_even(2, 1024)
            type_with_enter(f"$arena size {x} {y}")
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
    elif atype == 2:
        # x and y go from 2 to 1024 in steps of arena_size_step
        x = 2
        y = 2
        direction_x = step
        direction_y = step
        while run_event.is_set():
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
            type_with_enter(f"$arena size {x} {y}")
            x += direction_x
            y += direction_y
            # Clamp and reverse direction if out of bounds
            if x > 1024:
                x = 1024
                direction_x = -step
            elif x < 2:
                x = 2
                direction_x = step
            if y > 1024:
                y = 1024
                direction_y = -step
            elif y < 2:
                y = 2
                direction_y = step
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
    elif atype == 3:
        # x goes from 2 to 1024, y goes from 1024 to 2
        x = 2
        y = 1024
        direction_x = step
        direction_y = -step
        while run_event.is_set():
            if arena_auto_terminate and cmd_count >= arena_auto_max_commands:
                print(f"Reached {arena_auto_max_commands} commands, stopping")
                break
            type_with_enter(f"$arena size {x} {y}")
            x += direction_x
            y += direction_y
            # Clamp and reverse direction if out of bounds
            if x > 1024:
                x = 1024
                direction_x = -step
            elif x < 2:
                x = 2
                direction_x = step
            if y > 1024:
                y = 1024
                direction_y = -step
            elif y < 2:
                y = 2
                direction_y = step
            cmd_count += 1
            if cmd_delay > 0:
                time.sleep(cmd_delay)
        
def click_positions(pos_list: list[tuple[float, float]], delay: float = 0.5) -> None:
    mouse = MouseController()
    for x, y in pos_list:
        mouse.position = (int(x), int(y))
        time.sleep(0.02)
        mouse.click(Button.left, 1)
        print(f"Clicked at {x}, {y}")
        time.sleep(delay)


# ═══════════════════════════════════════════════════════════════════════════
# DRAWING MACROS (CIRCLES, WALLS, SHAPES)
# ═══════════════════════════════════════════════════════════════════════════

def conq_quickstart() -> None:
    for _ in range(50):
        controller.tap("n")
    controller.type("kyyv")
    mouse = MouseController()
    pos = mouse.position
    click_positions([
        (53.58203125, 948.08984375),
        (167.4765625, 965.703125),
        (166.66796875, 983.11328125),
        (90.53515625, 998.28125),
        (166.09765625, 1014.546875),
        (166.71875, 1031.28125),
        (92.51953125, 1049.71875)
    ], 0)
    mouse.position=pos

def wallcrash() -> None:
    type_in_console("x"*1800)

def nuke() -> None:
    type_in_console("wk"*100)

def shape() -> None:
    type_in_console("f"*5000)

def circlecrash() -> None:
    if USE_CPP_MACROS and HAS_CPP:
        pattern = circlecrash_cpp()
        type_in_console(pattern)
    else:
        repeat_tap_pattern_in_console("ccccccccccccccccccccccccch", 1600) # 40,000 = 25 * 1600

def minicirclecrash() -> None:
    if USE_CPP_MACROS and HAS_CPP:
        pattern = minicirclecrash_cpp()
        type_in_console(pattern)
    else:
        repeat_tap_pattern_in_console("ccccccccccccccccccccccccch", 240) # 6,000 = 25 * 240

def circles(amt: int = 22) -> None:
    if USE_CPP_MACROS and HAS_CPP:
        pattern = circles_cpp(amt)
        type_in_console(pattern)
    else:
        repeat_tap_pattern_in_console("cccccccccch", amt) # 220 = 22 * 20

def walls() -> None:
    if USE_CPP_MACROS and HAS_CPP:
        pattern = walls_cpp()
        type_in_console(pattern)
    else:
        type_in_console("x"*210)

def circle_art(run_event: threading.Event) -> None:
    """Circle art with threading.Event for fast response time."""
    controller.press("`")
    while run_event.is_set():
        controller.tap("c")
        controller.tap("h")
        time.sleep(0.02)
    controller.release("`")

def mcrash(run_event: MpEvent) -> None:
    controller.press("`")
    while run_event.is_set():
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def tail() -> None:
    controller.press("`")
    mouse = MouseController()
    init = mouse.position
    controller.type("ch"*int(length*33))
    time.sleep(3)
    starting_position = (init[0], init[1]+2*s)
    i2=0
    while i2 < length:
        i=0
        while i < length:
            controller.release("w")
            time.sleep(0.04)
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            time.sleep(0.04)
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            controller.press("w")
            time.sleep(0.04)
            mouse.position = (starting_position[0]+i*s, starting_position[1]+i2*s)
            time.sleep(0.04)
            controller.release("w")
            time.sleep(0.04)
            mouse.position = (init[0]+s, init[1])
            time.sleep(0.04)
            i+=1
        i2+=1
    mouse.position = (init[0], init[1]+2*s)
    i2=0
    time.sleep(0.1)
    mouse.position = (mouse.position[0]-s, mouse.position[1])
    time.sleep(2)
    mouse.position = (mouse.position[0]+s, mouse.position[1])
    time.sleep(0.1)
    down = True
    while i2 < length:
        i=0
        while i < length:
            controller.press("j")
            time.sleep(0.04)
            if down:
                mouse.position = (mouse.position[0], mouse.position[1]+s)
                time.sleep(0.04)
                controller.release("j")
                if i == length-1:
                    mouse.position = (mouse.position[0], mouse.position[1]-s)
                    time.sleep(0.04)
                    controller.press("j")
            else:
                mouse.position = (mouse.position[0], mouse.position[1]-s)
                time.sleep(0.04)
                controller.release("j")
                if i == length-1:
                    mouse.position = (mouse.position[0], mouse.position[1]+s)
                    time.sleep(0.04)
                    controller.press("j")
            i+=1
        i2+=1
        time.sleep(0.04)
        if down:
            mouse.position = (mouse.position[0]+s, mouse.position[1])
        else:
            mouse.position = (mouse.position[0]+s, mouse.position[1])
        time.sleep(0.04)
        controller.release("j")
        down = not down
    controller.release("`")

def brain_damage(run_event: MpEvent) -> None:
    mouse = MouseController()
    while run_event.is_set():
        mouse.position = (random.randint(0, 1710), random.randint(168, 1112))
        time.sleep(0.02)  # Add a small delay to prevent locking up your system

def circle_mouse(
    run_event: MpEvent,
    radius_value: Any,
    speed_value: Any,
    direction_value: Any,
) -> None:
    """Move mouse in circles around a center point. Press '\\' to reverse direction."""

    print("Click anywhere to set the center point for circular motion...")
    temp_points: list[tuple[int, int]] = []

    def temp_click_handler(x: int, y: int, button: Button, pressed: bool) -> None:
        if pressed and button == Button.left and run_event.is_set():
            temp_points.append((x, y))

    temp_listener = MouseListener(on_click=temp_click_handler)
    temp_listener.start()

    start_time = time.time()
    while len(temp_points) == 0 and run_event.is_set() and time.time() - start_time < 10:
        time.sleep(0.01)

    temp_listener.stop()

    if len(temp_points) == 0 or not run_event.is_set():
        print("Circle mouse: No point selected or cancelled")
        return

    center_x, center_y = temp_points[0]
    
    # Calculate rotations per second
    # angle_step_base = 5.0 / max(radius, 10) per iteration
    # Each full rotation = 2π radians
    # Rotations per second = (angle_step_base / (2π)) / sleep_time
    radius_for_calc = max(radius_value.value, 5)
    speed_for_calc = max(speed_value.value, 0.001)
    angle_step_base = 5.0 / max(radius_for_calc, 10)
    rotations_per_second = (angle_step_base / (2 * math.pi)) / speed_for_calc
    
    print(
        "Circle mouse: center (%s, %s), radius %s, speed %.4f, %.2f rotations/sec"
        % (center_x, center_y, radius_value.value, speed_value.value, rotations_per_second)
    )

    angle = 0.0
    while run_event.is_set():
        radius = max(radius_value.value, 5)
        speed = max(speed_value.value, 0.001)
        direction = 1 if direction_value.value >= 0 else -1

        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle))
        mouse.position = (x, y)

        angle_step_base = 5.0 / max(radius, 10)
        angle += direction * angle_step_base
        if angle >= 2 * math.pi:
            angle = 0.0

        time.sleep(speed)

def score() -> None:
    type_in_console("n"*20000)

def benchmark(amt: int = 500, mult = 200) -> None: # 500 * 220 = around 100,000 with loss
    shift_pressed = threading.Event()

    def on_press(key: Key | KeyCode | None) -> None:
        if key == Key.shift or key == Key.shift_r:
            shift_pressed.set()
            print("Benchmark stopped by Shift key press.")

    # start the benchmark
    start = time.time()
    if USE_CPP_MACROS and HAS_CPP:
        pattern = benchmark_cpp(amt)
        controller.tap("`")
        controller.type(pattern)
        controller.tap("`")
    else:
        circles(amt)
    print("Press any Shift key to stop the benchmark timer...")
    # start keyboard listener
    with KeyboardListener(on_press=on_press) as listener:
        shift_pressed.wait()  # Wait until Shift is pressed
        listener.stop()
    elapsed = time.time() - start
    print(f"{amt * mult} circles in {round(elapsed*1000, 3)} ms")
    type_with_enter(f"> [{round(elapsed * 1000, 3)}ms] < for {amt * mult} circles", 0.1)
    time.sleep(0.1)
    press_with_delay(Key.enter, 0.1, 2)
    bps = round(amt * mult * (1 / elapsed), 3) if elapsed > 0 else 0
    type_with_enter(f"> [{bps*2}] < inputs/s, > [bps] < circles/s", 0.1)

def score50m() -> None:
    type_in_console("f"*20)

def engineer_spam(run_event: MpEvent) -> None:
    while run_event.is_set():
        controller.tap(",")
        controller.tap("y")
        controller.tap("i")
        controller.press("`")
        controller.press("a")
        controller.press("c")
        controller.release("`")
        controller.press(Key.space)
        time.sleep(0.25)
        controller.release(Key.space)
        controller.press("`")
        controller.press("q")
        controller.release("`")

def circle() -> None:
    tap_in_console("ch")

def softwallstack() -> None:
    walls()
    start = mouse.position
    stackpos = (start[0] - s, start[1] + 4 * s)
    controller.press("`")
    for _ in range(200):
        mouse.position = (start[0] + 2 * s, start[1])
        controller.tap("w")
        time.sleep(0.03)
        controller.press("c")
        time.sleep(0.03)
        controller.release("c")
        time.sleep(0.03)
        controller.tap("y")
        time.sleep(0.03)
        controller.press("w")
        mouse.position = stackpos
        time.sleep(0.03)
        controller.release("w")
    controller.release("`")


def simpletail(amt: int = 20) -> None:
    controller.press("`")
    delay = 0.04
    s2 = 25
    time.sleep(delay)
    for _ in range(amt):
        for _ in range(3):
            circle()
        controller.press("`")
        time.sleep(delay)
        controller.press("c")
        time.sleep(delay*3)
        controller.release("c")
        mouse.position = (mouse.position[0] + s2, mouse.position[1])
        time.sleep(delay * 2.5)
    mouse.position = (mouse.position[0] + 2 * s2, mouse.position[1])
    pos = mouse.position
    mouse.position = (pos[0] + 30, pos[1])
    controller.press("`")
    time.sleep(2)
    mouse.position = (pos[0] - s2, pos[1])
    for _ in range(amt - 1):
        controller.press("j")
        time.sleep(delay)
        mouse.position = (mouse.position[0] - s2, mouse.position[1])
        time.sleep(delay)
        controller.release("j")


# ═══════════════════════════════════════════════════════════════════════════
# PROCESS MANAGEMENT (START/STOP HELPERS)
# ═══════════════════════════════════════════════════════════════════════════

def start_arena_automation(atype: int = 1) -> None:
    global automation_process, automation_working
    global arena_current_type
    arena_current_type = int(atype)
    automation_working = True
    automation_event.set()
    ensure_overlay_running("arena")
    if automation_process is None or not automation_process.is_alive():
        automation_process = multiprocessing.Process(
            target=arena_size_automation,
            args=(atype, automation_event),
        )
        automation_process.daemon = True
        automation_process.start()

def start_engineer_spam() -> None:
    global engineer_spam_process
    engineer_spam_event.set()
    ensure_overlay_running("engineer_spam")
    if engineer_spam_process is None or not engineer_spam_process.is_alive():
        engineer_spam_process = multiprocessing.Process(target=engineer_spam, args=(engineer_spam_event,))
        engineer_spam_process.daemon = True
        engineer_spam_process.start()

def start_brain_damage() -> None:
    global braindamage_process
    braindamage_event.set()
    ensure_overlay_running("brain damage")
    if braindamage_process is None or not braindamage_process.is_alive():
        braindamage_process = multiprocessing.Process(target=brain_damage, args=(braindamage_event,))
        braindamage_process.daemon = True
        braindamage_process.start()

def start_tail() -> None:
    global tail_process
    if tail_process is None or not tail_process.is_alive():
        tail_process = multiprocessing.Process(target=tail)
        tail_process.daemon = True
        tail_process.start()
        ensure_overlay_running("tail")

def start_circle_mouse() -> None:
    global circle_mouse_process
    circle_mouse_event.set()
    circle_mouse_radius_value.value = circle_mouse_radius
    circle_mouse_speed_value.value = circle_mouse_speed
    circle_mouse_direction_value.value = circle_mouse_direction
    ensure_overlay_running("circle mouse")
    if circle_mouse_process is None or not circle_mouse_process.is_alive():
        circle_mouse_process = multiprocessing.Process(
            target=circle_mouse,
            args=(
                circle_mouse_event,
                circle_mouse_radius_value,
                circle_mouse_speed_value,
                circle_mouse_direction_value,
            ),
        )
        circle_mouse_process.daemon = True
        circle_mouse_process.start()
        monitor = threading.Thread(target=_monitor_circle_mouse, args=(circle_mouse_process,))
        monitor.daemon = True
        monitor.start()

def stop_circle_mouse() -> None:
    """Gracefully stop the circle mouse process."""
    global circle_mouse_process
    circle_mouse_event.clear()
    if circle_mouse_process is not None:
        try:
            circle_mouse_process.join(timeout=1)
            if circle_mouse_process is not None and circle_mouse_process.is_alive():
                circle_mouse_process.terminate()
        except Exception:
            pass
        circle_mouse_process = None

def _monitor_circle_mouse(proc: Process) -> None:
    """Reset circle-mouse state when its process exits."""
    global circle_mouse_process, circle_mouse_active
    if proc is None:
        return
    proc.join()
    if circle_mouse_process is proc:
        circle_mouse_event.clear()
        circle_mouse_active = False
        circle_mouse_process = None

def start_circle_art() -> None:
    global circle_art_thread, circle_art_working
    circle_art_event.set()
    circle_art_working = True
    ensure_overlay_running("circle_art")
    if circle_art_thread is None or not circle_art_thread.is_alive():
        circle_art_thread = threading.Thread(target=circle_art, args=(circle_art_event,))
        circle_art_thread.daemon = True
        circle_art_thread.start()

def start_softwallstack() -> None:
    global softwallstack_process
    if softwallstack_process is None or not softwallstack_process.is_alive():
        softwallstack_process = multiprocessing.Process(target=softwallstack)
        softwallstack_process.daemon = True
        softwallstack_process.start()
        ensure_overlay_running("softwall")

def start_mcrash() -> None:
    global mcrash_process, mcrash_working
    mcrash_event.set()
    mcrash_working = True
    ensure_overlay_running("mcrash")
    if mcrash_process is None or not mcrash_process.is_alive():
        mcrash_process = multiprocessing.Process(target=mcrash, args=(mcrash_event,))
        mcrash_process.daemon = True
        mcrash_process.start()

def start_custom_reload_spam() -> None:
    global custom_reload_spam_process
    custom_reload_spam_event.set()
    ensure_overlay_running("custom_reload_spam")
    if custom_reload_spam_process is None or not custom_reload_spam_process.is_alive():
        custom_reload_spam_process = multiprocessing.Process(target=custom_reload_spam, args=(custom_reload_spam_event,))
        custom_reload_spam_process.daemon = True
        custom_reload_spam_process.start()

# Normalize modifier detection across platforms
def is_ctrl(k: Key | KeyCode) -> bool:
    """Check if key is Ctrl (or Cmd if ctrlswap=True on macOS)"""
    global ctrlswap
    if not isinstance(k, Key):
        return False
    if ctrlswap and PLATFORM == 'darwin':
        # Use Cmd key on macOS when ctrlswap is enabled
        return k in (Key.cmd, Key.cmd_l, Key.cmd_r)
    else:
        # Use Ctrl key normally
        return k in (Key.ctrl, Key.ctrl_l, Key.ctrl_r)


# ═══════════════════════════════════════════════════════════════════════════
# KEY/MODIFIER UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def is_alt(k: Key | KeyCode) -> bool:
    # On macOS, Option is alt; on other platforms, Alt is alt
    if not isinstance(k, Key):
        return False
    return k in (Key.alt, Key.alt_l, Key.alt_r)

def get_char(key: Key | KeyCode | None) -> str | None:
    """Safely get the char attribute from a key, returns None if not available."""
    if isinstance(key, KeyCode):
        return key.char
    return None


# ═══════════════════════════════════════════════════════════════════════════
# OCR AND TEXT SCANNING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def ocr_text_capture() -> None:
    """Capture text from a screen region defined by two mouse clicks.
    
    User clicks two points to define a rectangle. The text within that rectangle
    is read using OCR and typed out using Enter-text-Enter format.
    
    Workflow:
        1. User presses Ctrl+P to start
        2. User clicks first corner of rectangle (within 10 seconds)
        3. User clicks second corner of rectangle (within 10 seconds)
        4. OCR reads text from the defined rectangle
        5. Text is typed out using type_with_enter()
    """
    if not HAS_OCR:
        print("Error: OCR dependencies not installed. Cannot capture text.")
        print("Install with: pip install mss pytesseract pillow")
        return
    
    print("\nOCR Text Capture: Click two corners to define rectangle...")
    print("(You have 10 seconds for each click)")
    
    clicks = []
    click_timeout = 10  # seconds
    
    def on_click(x: int, y: int, button: Button, pressed: bool) -> bool | None:
        """Capture mouse clicks to define rectangle corners."""
        if pressed and button == Button.left:
            clicks.append((x, y))
            print(f"  Click {len(clicks)}: ({x}, {y})")
            if len(clicks) >= 2:
                return False  # Stop listener
        return None
    
    # Start mouse listener to capture clicks
    try:
        with MouseListener(on_click=on_click) as listener:
            listener.join(timeout=click_timeout * 2)
    except Exception as e:
        print(f"Error capturing clicks: {e}")
        return
    
    if len(clicks) < 2:
        print("Error: Timeout - did not receive 2 clicks")
        return
    
    # Calculate rectangle bounds
    x1, y1 = clicks[0]
    x2, y2 = clicks[1]
    
    # Ensure x1,y1 is top-left and x2,y2 is bottom-right
    left = min(x1, x2)
    top = min(y1, y2)
    right = max(x1, x2)
    bottom = max(y1, y2)
    width = right - left
    height = bottom - top
    
    print(f"Rectangle: ({left}, {top}) to ({right}, {bottom}) [{width}x{height}]")
    
    # Capture the screen region using mss
    try:
        with mss.mss() as sct:
            # Define the region to capture
            region = {
                'left': left,
                'top': top,
                'width': width,
                'height': height
            }
            
            # Capture the region
            screenshot = sct.grab(region)
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            
            # Image preprocessing for better OCR
            original_size = img.size
            
            # Upscale image so both dimensions are at least 1024x768
            target_width, target_height = 1024, 768
            current_width, current_height = img.size
            
            # Calculate scale factors needed for each dimension
            scale_x = target_width / current_width if current_width < target_width else 1
            scale_y = target_height / current_height if current_height < target_height else 1
            
            # Use the larger scale factor to ensure both dimensions meet the minimum
            scale_factor = max(scale_x, scale_y)
            
            if scale_factor > 1:
                new_size = (int(current_width * scale_factor), int(current_height * scale_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                print(f"Upscaled image from {original_size} to {img.size} ({scale_factor:.2f}x)")
            
            # Convert to grayscale for better OCR
            img = img.convert('L')
            
            # Enhance contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Optional: Apply sharpening
            from PIL import ImageFilter
            img = img.filter(ImageFilter.SHARPEN)
            
            print("Reading text from captured region...")
            
            # Perform OCR with optimized configuration
            # --oem 1: Use LSTM neural net mode (best for modern text)
            # --psm 6: Assume uniform block of text
            # Other useful PSM modes:
            #   3: Fully automatic page segmentation (default)
            #   6: Assume a single uniform block of text
            #   11: Sparse text. Find as much text as possible in no particular order
            custom_config = r'--oem 1 --psm 6'
            text = pytesseract.image_to_string(img, config=custom_config)
            
            # Clean up the text (strip whitespace, remove empty lines)
            text = text.strip()
            
            if not text:
                print("No text detected in the selected region")
                print("Trying with different PSM mode (sparse text)...")
                # Try again with sparse text mode
                custom_config = r'--oem 1 --psm 11'
                text = pytesseract.image_to_string(img, config=custom_config)
                text = text.strip()
            
            if not text:
                print("Still no text detected - typing 'No text'")
                type_with_enter("No text")
                return
            
            # Replace newlines with literal \n for single-line output
            text = text.replace('\n', '\\n')
            
            print(f"Detected text ({len(text)} chars):")
            print(f"--- START ---")
            print(text)
            print(f"--- END ---")
            
            # Type the text using the existing helper
            print("Typing text...")
            type_with_enter(text)
            print("Done!")
            
    except Exception as e:
        print(f"Error during OCR text capture: {e}")
        import traceback
        traceback.print_exc()


def scan_screen_for_text(search_text: str, monitor_index: int = 1) -> tuple[bool, tuple[int, int] | None]:
    """Scan the screen for the given text using OCR.
    
    Args:
        search_text: The text to search for on screen (case-insensitive)
        monitor_index: Monitor index to capture (1 = primary, 2 = secondary, etc.)
    
    Returns:
        A tuple of (found: bool, center: tuple[int, int] | None)
        - found: True if text was found, False otherwise
        - center: (x, y) coordinates of the center of the text bounding box, or None if not found
    
    Example:
        found, center = scan_screen_for_text("Hello World")
        if found:
            print(f"Text found at center: {center}")
            # Can use mouse.position = center to move mouse to text
    """
    if not HAS_OCR:
        print("Error: OCR dependencies not installed. Cannot scan screen for text.")
        print("Install with: pip install mss pytesseract pillow")
        return (False, None)
    
    try:
        with mss.mss() as sct:
            # Get the monitor (1-indexed for user, 0-indexed for mss)
            if monitor_index < 1 or monitor_index > len(sct.monitors) - 1:
                print(f"Error: Monitor index {monitor_index} out of range (1 to {len(sct.monitors) - 1})")
                return (False, None)
            
            monitor = sct.monitors[monitor_index]
            
            # Capture the screen
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            
            # Perform OCR to get bounding boxes and text
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            # Search for the text (case-insensitive)
            search_lower = search_text.lower().strip()
            
            # Try to find the text in the OCR results
            for i, text in enumerate(ocr_data['text']):
                if text.lower().strip() == search_lower:
                    # Found exact match
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    # Calculate center point
                    # Add monitor offset to get absolute screen coordinates
                    center_x = monitor['left'] + x + w // 2
                    center_y = monitor['top'] + y + h // 2
                    
                    return (True, (center_x, center_y))
            
            # Also try pcircle_artial matching (in case search_text is pcircle_art of a larger word)
            for i, text in enumerate(ocr_data['text']):
                if search_lower in text.lower():
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    center_x = monitor['left'] + x + w // 2
                    center_y = monitor['top'] + y + h // 2
                    
                    return (True, (center_x, center_y))
            
            # Text not found
            return (False, None)
            
    except Exception as e:
        print(f"Error scanning screen for text: {e}")
        return (False, None)


# ═══════════════════════════════════════════════════════════════════════════
# DOUBLE-TAP HELPER
# ═══════════════════════════════════════════════════════════════════════════

def handle_double_tap(armed_flag_name: str, last_time_var_name: str, action_fn, description: str = "", timeout: float = 5.0) -> bool:
    """Handle double-tap pattern for safety-critical macros.
    
    Args:
        armed_flag_name: Name of global flag tracking armed state (e.g., 'ctrl1_armed')
        last_time_var_name: Name of global variable tracking last press time (e.g., 'ctrl1_last_time')
        action_fn: Function to call on second tap
        description: Description for logging
        timeout: Timeout in seconds (default: 5.0)
    
    Returns:
        True if action was executed, False if arming
    """
    now = time.time()
    armed = globals()[armed_flag_name]
    last_time = globals()[last_time_var_name]
    
    if armed and (now - last_time <= timeout):
        # Second tap within timeout - execute action
        if description:
            print(f"{description} - executing")
        action_fn()
        globals()[armed_flag_name] = False
        return True
    else:
        # First tap or timeout expired - arm the trigger
        if description:
            print(f"{description} - armed (press again within {timeout}s to confirm)")
        globals()[armed_flag_name] = True
        globals()[last_time_var_name] = now
        return False


# ═══════════════════════════════════════════════════════════════════════════
# CIRCLE FINDER MODE
# ═══════════════════════════════════════════════════════════════════════════

def circle_finder_mode(run_event: MpEvent) -> None:
    """Circle detection mode that finds and tracks colored circle borders.
    
    Workflow:
    1. Wait for two mouse clicks to define search rectangle
    2. Search within rectangle for circular shapes with colored borders
    3. Move mouse to center of found circle
    4. Continue tracking/centering until Left Shift is released
    
    Uses basic image processing with mss and PIL to detect circles.
    """
    if not HAS_OCR:
        print("Circle finder requires mss and PIL - install with: pip install mss pillow")
        return
    
    print("Circle finder: Click two corners to define search rectangle")
    points: list[tuple[int, int]] = []
    
    def click_handler(x: int, y: int, button: Button, pressed: bool) -> None:
        if pressed and button == Button.left and run_event.is_set() and len(points) < 2:
            points.append((x, y))
            print(f"Circle finder: Point {len(points)}/2 captured at ({x}, {y})")
    
    temp_listener = MouseListener(on_click=click_handler)
    temp_listener.start()
    
    # Wait for two points or timeout
    start_time = time.time()
    while len(points) < 2 and run_event.is_set() and (time.time() - start_time) < 30:
        time.sleep(0.05)
    
    temp_listener.stop()
    
    if len(points) < 2:
        print("Circle finder: Cancelled or timed out")
        return
    
    # Define search rectangle
    x1, y1 = points[0]
    x2, y2 = points[1]
    search_rect = {
        'left': min(x1, x2),
        'top': min(y1, y2),
        'width': abs(x2 - x1),
        'height': abs(y2 - y1)
    }
    
    print(f"Circle finder: Searching in {search_rect['width']}x{search_rect['height']} region")
    
    with mss.mss() as sct:
        while run_event.is_set():
            try:
                # Capture search region
                screenshot = sct.grab(search_rect)
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                
                # Convert to grayscale for edge detection (basic approach)
                gray = img.convert('L')
                width, height = gray.size
                
                # Simple circle detection: find regions with high edge density
                # This is a basic implementation - for production, use cv2.HoughCircles
                center_x = width // 2
                center_y = height // 2
                
                # Scan for brightest/darkest contrasts indicating circle edges
                max_contrast = 0
                best_x, best_y = center_x, center_y
                
                # Sample in a grid pattern
                step = 20
                for y in range(step, height - step, step):
                    for x in range(step, width - step, step):
                        # Calculate local contrast (simple gradient)
                        neighbors = []
                        for dy in [-step, 0, step]:
                            for dx in [-step, 0, step]:
                                ny, nx = y + dy, x + dx
                                if 0 <= ny < height and 0 <= nx < width:
                                    neighbors.append(gray.getpixel((nx, ny)))
                        
                        if len(neighbors) > 0:
                            contrast = max(neighbors) - min(neighbors)
                            if contrast > max_contrast:
                                max_contrast = contrast
                                best_x, best_y = x, y
                
                # Move mouse to detected position (absolute screen coordinates)
                abs_x = search_rect['left'] + best_x
                abs_y = search_rect['top'] + best_y
                mouse.position = (abs_x, abs_y)
                
                time.sleep(0.1)  # Update rate
                
            except Exception as e:
                print(f"Circle finder error: {e}")
                time.sleep(0.5)
    
    print("Circle finder: Stopped")


def start_circle_finder() -> None:
    """Start circle finder mode in separate process."""
    global circle_finder_process, circle_finder_active
    
    if circle_finder_process is not None and circle_finder_process.is_alive():
        print("Circle finder already running")
        return
    
    circle_finder_active = True
    circle_finder_event.set()
    circle_finder_process = Process(target=circle_finder_mode, args=(circle_finder_event,))
    circle_finder_process.start()
    ensure_overlay_running("circle_finder started")
    print("Circle finder started (release Left Shift to stop)")


def stop_circle_finder() -> None:
    """Stop circle finder mode."""
    global circle_finder_process, circle_finder_active
    
    circle_finder_active = False
    circle_finder_event.clear()
    
    if circle_finder_process is not None:
        if circle_finder_process.is_alive():
            circle_finder_process.terminate()
            circle_finder_process.join(timeout=1)
            if circle_finder_process.is_alive():
                circle_finder_process.kill()
        circle_finder_process = None
    
    print("Circle finder stopped")


def cleanup_multiprocessing_resources() -> None:
    """Clean up multiprocessing Events and Values to prevent semaphore leaks."""
    global automation_event, engineer_spam_event, circle_art_event, braindamage_event
    global circle_mouse_event, mcrash_event, custom_reload_spam_event, circle_finder_event
    global circle_mouse_radius_value, circle_mouse_speed_value, circle_mouse_direction_value
    
    # Clear all events first
    for event in [automation_event, engineer_spam_event, circle_art_event, braindamage_event,
                  circle_mouse_event, mcrash_event, custom_reload_spam_event, circle_finder_event]:
        try:
            event.clear()
        except Exception:
            pass
    
    # Note: multiprocessing.Event and Value objects don't have explicit close methods
    # in the public API, but clearing them helps signal child processes to stop.
    # The actual cleanup happens when the main process exits.

def stopallthreads() -> None:
    global automation_process, engineer_spam_process, braindamage_process
    global tail_process, circle_mouse_process, softwallstack_process, circlecrash_process, mcrash_process, custom_reload_spam_process, circle_finder_process
    global circle_art_thread
    global automation_working, engineer_spam_working, circle_art_working, braindamage_working, mcrash_working, custom_reload_spam_working
    global circle_mouse_active, circle_finder_active
    if custom_reload_spam_working:
        controller.tap(Key.space)
    
    # Set all flags to False
    automation_working = False
    engineer_spam_working = False
    circle_art_working = False
    braindamage_working = False
    circle_mouse_active = False
    mcrash_working = False
    custom_reload_spam_working = False
    circle_finder_active = False
    automation_event.clear()
    engineer_spam_event.clear()
    circle_art_event.clear()
    braindamage_event.clear()
    circle_mouse_event.clear()
    mcrash_event.clear()
    custom_reload_spam_event.clear()
    circle_finder_event.clear()
    stop_circle_mouse()
    
    # Terminate all processes and clean up resources
    for proc in [automation_process, engineer_spam_process, braindamage_process,
                 tail_process, softwallstack_process, circlecrash_process, mcrash_process, custom_reload_spam_process, circle_finder_process]:
        if proc is not None:
            try:
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=1)
                    if proc.is_alive():
                        proc.kill()
                        proc.join(timeout=0.5)
                # Close the process to release resources (semaphores, etc.)
                proc.close()
            except Exception:
                pass

    # Reset all process references
    automation_process = None
    engineer_spam_process = None
    circle_art_thread = None
    braindamage_process = None
    tail_process = None
    circle_mouse_process = None
    softwallstack_process = None
    circlecrash_process = None
    mcrash_process = None
    custom_reload_spam_process = None
    circle_finder_process = None
    
    # Clean up multiprocessing resources
    cleanup_multiprocessing_resources()
    
    def is_modifier_for_arrow_nudge(k: Key) -> bool:
        """
        Platform-specific:
        - macOS: Option (alt)
        - Windows/Linux: Alt
        - Android: Alt (if supported)
        """
        return is_alt(k)


# ═══════════════════════════════════════════════════════════════════════════
# KEYBIND SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

# Handler functions for keybinds (simple wrappers for commonly used actions)

def handler_circle():
    """Ctrl+3: Draw a circle."""
    circle()

def handler_circle_square():
    """Ctrl+4: Draw circle square pattern."""
    print("circle square")
    start_tail()

def handler_circles_batch():
    """Ctrl+B: Draw 200 circles."""
    print("200 circles")
    circles()

def handler_walls_batch():
    """Ctrl+W: Draw 200 walls."""
    print("200 walls")
    walls()

def handler_engineer_spam():
    """Ctrl+E: Start engineer spam."""
    global engineer_spam_working
    print("engineer_spam")
    engineer_spam_working = True
    start_engineer_spam()

def handler_nuke():
    """Ctrl+9: Execute nuke."""
    print("NUKE GO BRRRRRRRRRR")
    nuke()

def handler_shape():
    """Ctrl+F: Shape nuke."""
    print("shape nuke")
    shape()

def handler_score():
    """Ctrl+N: Score macro."""
    print("score")
    score()

def handler_benchmark():
    """Ctrl+M: Run benchmark."""
    print("benchmarking...")
    benchmark()

def handler_minicirclecrash():
    """Ctrl+6: Mini circle crash."""
    print("minicirclecrash")
    minicirclecrash()

def handler_simple_tail():
    """Ctrl+8: Simple tail."""
    print("simple tail")
    simpletail(tailamount)

def handler_brain_damage():
    """Ctrl+2: Brain damage mode."""
    global braindamage_working
    braindamage_working = True
    print("bdmg")
    start_brain_damage()

def handler_toggle_emoji():
    """Ctrl+H: Toggle emoji replacement."""
    global emoji_replacement_enabled
    emoji_replacement_enabled = not emoji_replacement_enabled
    status = "enabled" if emoji_replacement_enabled else "disabled"
    print(f"emoji replacement {status}")

def handler_toggle_berserk():
    """Ctrl+P: Toggle berserk mode."""
    global berserk
    berserk = not berserk
    mode_text = "ON" if berserk else "OFF"
    print(f"berserk: {mode_text}")

def handler_custom_reload_spam():
    """Ctrl+T: Custom reload spam."""
    print("custom_reload_spam")
    start_custom_reload_spam()

def handler_ocr_capture():
    """Ctrl+0: OCR text capture."""
    print("OCR Text Capture - Click two corners to define region")
    threading.Thread(target=ocr_text_capture, daemon=True).start()

def handler_toggle_circle_mouse():
    """Ctrl+O: Toggle circle mouse."""
    global circle_mouse_active, circle_mouse_direction
    circle_mouse_active = not circle_mouse_active
    if circle_mouse_active:
        circle_mouse_direction = 1  # reset to default on start
        circle_mouse_direction_value.value = circle_mouse_direction
        print(f"circle mouse on (radius: {circle_mouse_radius}, speed: {circle_mouse_speed})")
        start_circle_mouse()
    else:
        print("circle mouse off")
        stop_circle_mouse()

def handler_toggle_circle_art():
    """Ctrl+C: Toggle circle art shift binding."""
    global circle_art_shift_bind, circle_art_working
    circle_art_shift_bind = True
    circle_art_working = False  # ensure idle until Left Shift is pressed
    circle_art_event.clear()
    print("toggle circle_art")

def handler_toggle_mcrash():
    """Ctrl+V: Toggle mcrash shift binding."""
    global mcrash_shift_bind, mcrash_working
    mcrash_shift_bind = True
    mcrash_working = False
    mcrash_event.clear()
    print("toggle mcrash")

def handler_arena_team_setup():
    """Ctrl+K: Arena team setup."""
    type_with_enter("$arena team 1", 0.05)
    type_with_enter("$arena spawnpoint 0 0", 0.05)

# Keybinds list: (char, modifier, handler_function, description)
# modifier can be 'ctrl', 'alt', or None
# char can be a string character or a Key object
KEYBINDS = [
    ('1', 'ctrl', lambda: handle_double_tap('ctrl1_armed', 'ctrl1_last_time', 
                                            lambda: start_arena_automation(atype=1), 
                                            "arena automation starting (type 1)"), "Arena automation type 1 (double-tap)"),
    ('2', 'ctrl', handler_brain_damage, "Brain damage mode"),
    ('3', 'ctrl', handler_circle, "Draw circle"),
    ('4', 'ctrl', handler_circle_square, "Circle square pattern"),
    ('5', 'ctrl', lambda: handle_double_tap('ctrl6_armed', 'ctrl6_last_time',
                                            circlecrash,
                                            "death by circle"), "Circle crash (double-tap)"),
    ('6', 'ctrl', handler_minicirclecrash, "Mini circle crash"),
    ('7', 'ctrl', lambda: handle_double_tap('ctrl7_armed', 'ctrl7_last_time',
                                            wallcrash,
                                            "death by wall"), "Wall crash (double-tap)"),
    ('8', 'ctrl', handler_simple_tail, "Simple tail"),
    ('9', 'ctrl', handler_nuke, "Nuke"),
    ('0', 'ctrl', handler_ocr_capture, "OCR text capture"),
    
    ('b', 'ctrl', handler_circles_batch, "200 circles"),
    ('c', 'ctrl', handler_toggle_circle_art, "Toggle circle art"),
    ('e', 'ctrl', handler_engineer_spam, "Engineer spam"),
    ('f', 'ctrl', handler_shape, "Shape nuke"),
    ('h', 'ctrl', handler_toggle_emoji, "Toggle emoji replacement"),
    ('k', 'ctrl', handler_arena_team_setup, "Arena team setup"),
    ('m', 'ctrl', handler_benchmark, "Benchmark"),
    ('n', 'ctrl', handler_score, "Score"),
    ('o', 'ctrl', handler_toggle_circle_mouse, "Toggle circle mouse"),
    ('p', 'ctrl', handler_toggle_berserk, "Toggle berserk mode"),
    ('t', 'ctrl', handler_custom_reload_spam, "Custom reload spam"),
    ('v', 'ctrl', handler_toggle_mcrash, "Toggle mcrash"),
    ('w', 'ctrl', handler_walls_batch, "200 walls"),
    
    # Alt keybinds
    ('1', 'alt', start_circle_finder, "Circle finder mode (hold Left Shift)"),
]


def on_press(key: Key | KeyCode | None) -> None:
    # Global variables that track double-press states need to be declared
    global ctrl6_last_time, ctrl6_armed, ctrl7_last_time, ctrl7_armed
    global ctrl1_last_time, ctrl1_armed
    global ctrlq_last_time, ctrlq_armed, ctrla_last_time, ctrla_armed
    global ctrlz_last_time, ctrlz_armed, ctrly_last_time, ctrly_armed
    global ctrlu_last_time, ctrlu_armed, ctrli_last_time, ctrli_armed
    global ctrlg_last_time, ctrlg_armed, ctrlr_last_time, ctrlr_armed
    global circle_art_shift_bind, mcrash_shift_bind, arena_current_type
    global automation_working, braindamage_working, circlecrash_working, circle_art_working, engineer_spam_working, mcrash_working
    global ctrl6_last_time, ctrl6_armed, ctrl7_last_time, ctrl7_armed
    global ctrl1_last_time, ctrl1_armed, ctrlg_armed, ctrlg_last_time
    global ctrlq_last_time, ctrlq_armed, ctrla_last_time, ctrla_armed
    global ctrlz_last_time, ctrlz_armed, ctrly_last_time, ctrly_armed
    global ctrlu_last_time, ctrlu_armed, ctrli_last_time, ctrli_armed
    global ctrlr_last_time, ctrlr_armed
    global circle_art_shift_bind, mcrash_shift_bind, ctrlswap
    global circle_mouse_active, circle_mouse_speed, circle_mouse_radius, circle_mouse_direction
    global keyboard_buffer, berserk
    
    try:
        # Workaround for pynput macOS Unicode decode bug - some special keys trigger this
        if key is None:
            return
        if listener_event_injected:
            return
        
        # Track typed characters for fancy pattern detection
        char = get_char(key)
        if char and len(char) == 1:
            keyboard_buffer.append(char)
            if len(keyboard_buffer) > max_buffer_size:
                keyboard_buffer = keyboard_buffer[-max_buffer_size:]
            
            # Apply berserk effect: delete original character and replace with random fancy version
            if berserk and 'ctrl' not in pressed_keys and is_alt(key) is False:
                # Spawn a background thread to handle the replacement
                # This gives the character time to appear before we delete it
                def berserk_replace():
                    try:
                        # Give the character a moment to appear in the application
                        time.sleep(0.02)
                        
                        # Delete the character that was just typed
                        controller.tap(Key.backspace)
                        
                        # Small delay before typing the replacement
                        time.sleep(0.01)
                        
                        # Pick a random style and transform the character
                        style = random.choice(list(STYLES.keys()))
                        table = STYLES.get(style)
                        if table:
                            fancy_char = table.get(char, char)
                        else:
                            fancy_char = char
                        
                        # Type the fancy character
                        type_unicode(fancy_char)
                    except Exception as e:
                        print(f"Berserk replacement error: {e}")
                
                threading.Thread(target=berserk_replace, daemon=True).start()
            
            # Check for fancy pattern completion when ':' is typed
            if char == ':':
                threading.Thread(target=check_and_replace_fancy_pattern, daemon=True).start()
                threading.Thread(target=check_and_replace_emoji_pattern, daemon=True).start()
        elif key == Key.space:
            # Explicitly track space key
            keyboard_buffer.append(' ')
            if len(keyboard_buffer) > max_buffer_size:
                keyboard_buffer = keyboard_buffer[-max_buffer_size:]
        elif key == Key.backspace:
            # Remove last character from buffer on backspace
            if keyboard_buffer:
                keyboard_buffer.pop()
        elif key == Key.enter:
            # Clear buffer on enter (new line/message)
            keyboard_buffer.clear()
        
        # Use Right Shift to disable shift-bound macros (circle_art/mcrash) and circle_mouse spin
        if key == Key.shift_r:
            if circle_art_shift_bind:
                print("circle_art shift-bind off")
                circle_art_shift_bind = False
                circle_art_working = False
                circle_art_event.clear()
            if mcrash_shift_bind:
                print("mcrash shift-bind off")
                mcrash_shift_bind = False
                mcrash_working = False
                mcrash_event.clear()
                if mcrash_process is not None and mcrash_process.is_alive():
                    mcrash_process.terminate()
                    mcrash_process.join(timeout=1)
            if circle_mouse_active:
                print("circle mouse off")
                circle_mouse_active = False
                stop_circle_mouse()
            return
        # Use Right Option to restart all running macros
        elif key == Key.alt_r:
            print("Restarting macros...")
            # Save state of running macros
            was_automation = automation_event.is_set()
            was_engineer = engineer_spam_event.is_set()
            was_circle_art = circle_art_event.is_set()
            was_brain_damage = braindamage_event.is_set()
            was_circle_mouse = circle_mouse_event.is_set()
            was_mcrash = mcrash_event.is_set()
            was_custom_reload = custom_reload_spam_event.is_set()
            was_tail = tail_process is not None and tail_process.is_alive()
            was_softwall = softwallstack_process is not None and softwallstack_process.is_alive()
            
            # Stop everything
            stopallthreads()
            time.sleep(0.1)  # Brief pause to ensure clean shutdown
            print("Macros restarted")
            return
        elif is_ctrl(key):
            pressed_keys.add('ctrl')
        elif is_alt(key):
            pressed_keys.add('alt')
            # print("alt down")  # uncomment to debug
        # Handle actual Cmd key presses (for toggling ctrlswap on macOS)
        elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
            if ctrlswap:
                pressed_keys.add('ctrl')  # Treat Cmd as Ctrl when ctrlswap is enabled
        elif key in (Key.up, Key.down, Key.left, Key.right):
            if 'alt' in pressed_keys:
                x, y = mouse.position
                if key == Key.up:
                    mouse.position = (x, y - 1)
                elif key == Key.down:
                    mouse.position = (x, y + 1)
                elif key == Key.left:
                    mouse.position = (x - 1, y)
                elif key == Key.right:
                    mouse.position = (x + 1, y)
                return
        # Left Shift: activate circle art OR circle finder OR pause/unpause spam macros (only if already running)
        elif key == Key.shift_l:
            # Priority 0: Circle finder mode
            if circle_finder_active:
                # Left shift is held during circle finder - do nothing special
                pass
            # Priority 1: Circle art shift bind
            elif circle_art_shift_bind:
                if not circle_art_working:
                    print("circle_art on")
                circle_art_working = True
                start_circle_art()
            # Priority 2: Engineer spam pause/unpause (only if already running AND currently paused)
            elif engineer_spam_process and engineer_spam_process.is_alive() and not engineer_spam_event.is_set():
                # Only allow resume if process is alive and currently paused
                engineer_spam_event.set()
                print("Engineer spam RESUMED (left shift)")
            # Priority 3: Custom reload spam pause/unpause (only if already running AND currently paused)
            elif custom_reload_spam_process and custom_reload_spam_process.is_alive() and not custom_reload_spam_event.is_set():
                # Only allow resume if process is alive and currently paused
                custom_reload_spam_event.set()
                print("Custom reload spam RESUMED (left shift)")
        
        # ── Check keybinds list for simple handlers ──
        char = get_char(key)
        if char:
            for keybind_char, modifier, handler, description in KEYBINDS:
                if char == keybind_char:
                    if modifier == 'ctrl' and 'ctrl' in pressed_keys:
                        handler()
                        return
                    elif modifier == 'alt' and 'alt' in pressed_keys:
                        handler()
                        return
                    elif modifier is None:
                        handler()
                        return
        
        # ── Special character handlers (not in keybinds list) ──
        elif get_char(key) == "'":
            if 'ctrl' in pressed_keys:
                print("unicode blocks macro")
                type_unicode_blocks("027103B103C1056C1D07005B000BFFFC007F2400000B005D")
        elif get_char(key) == ",":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.type("«∑∏¯ˇ†∫–⁄∞∆µ•‰ª¬∂Ω◊ﬂı®»")
        elif get_char(key) == ";":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.type("«∑∫–µ¬∂Ωı»")
        elif get_char(key) == ".":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type("«∑⫍ʩ∏₻‖₰¯ˇ†₢ƒ₥∫ø–⁄∞₯※˚")
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type("∆µ•‰৻৲©Íʨ⏔ʧª¬æ∂Ω⋾ↈ◊‘ﬂı®π↹")
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.tap(Key.enter)
                time.sleep(0.1)
                controller.type("⁂⋣௹⁞ß૱ɧ⊯å⁛ɮ⏓⁊⁒Ϡç⁁⌁ϐÂͳϟ֏»")
                time.sleep(0.1)
                controller.tap(Key.enter)
        elif get_char(key) == "/":
            if 'ctrl' in pressed_keys:
                time.sleep(0.5)
                controller.type("₥ἆȵɪꜻƈ [𒈙]")
        elif hasattr(key, 'char') and key.char and key.char=='1':
            if 'ctrl' in pressed_keys:
                now = time.time()
                # double-tap lock: first tap arms, second tap within 5s triggers arena automation
                if ctrl1_armed and (now - ctrl1_last_time <= 5):
                    print("arena automation starting (type 1)")
                    start_arena_automation(atype=1)
                    ctrl1_armed = False
                else:
                    print("arena automation armed - press Ctrl+1 again within 5s to confirm")
                    ctrl1_armed = True
                    ctrl1_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='v':
            if 'ctrl' in pressed_keys:
                mcrash_shift_bind = True
                mcrash_working = False
                mcrash_event.clear()
                print("toggle mcrash")
        elif hasattr(key, 'char') and key.char and key.char=='2':
            if 'ctrl' in pressed_keys:
                braindamage_working = True
                print("bdmg")
                start_brain_damage()
        elif hasattr(key, 'char') and key.char and key.char=='3':
            if 'ctrl' in pressed_keys:
                circle()
        elif hasattr(key, 'char') and key.char and key.char=='4':
            if 'ctrl' in pressed_keys:
                print("circle square")
                start_tail()
        elif hasattr(key, 'char') and key.char and key.char=='5':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrl6_armed and (now - ctrl6_last_time <= 5):
                    print("death by circle")
                    circlecrash()
                    ctrl6_armed = False
                else:
                    print("crasharmed")
                    ctrl6_armed = True
                    ctrl6_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='7':
            if 'ctrl' in pressed_keys:
                now = time.time()
                # double-tap lock: first tap arms, second tap within 5s triggers
                if ctrl7_armed and (now - ctrl7_last_time <= 5):
                    print("death by wall")
                    wallcrash()
                    ctrl7_armed = False
                else:
                    print("wallcrash armed")
                    ctrl7_armed = True
                    ctrl7_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='8':
            if 'ctrl' in pressed_keys:
                print("simple tail")
                simpletail(tailamount)
        elif hasattr(key, 'char') and key.char and key.char=='9':
            if 'ctrl' in pressed_keys:
                print("NUKE GO BRRRRRRRRRR")
                nuke()
        elif hasattr(key, 'char') and key.char and key.char=='f':
            if 'ctrl' in pressed_keys:
                print("shape nuke")
                shape()
        elif hasattr(key, 'char') and key.char and key.char=='n':
            if 'ctrl' in pressed_keys:
                print("score")
                score()
        elif hasattr(key, 'char') and key.char and key.char=='b':
            if 'ctrl' in pressed_keys:
                print("200 circles")
                circles()
        elif hasattr(key, 'char') and key.char and key.char=='w':
            if 'ctrl' in pressed_keys:
                print("200 walls")
                walls()
        elif hasattr(key, 'char') and key.char and key.char=='c':
            if 'ctrl' in pressed_keys:
                # NEW: enable binding to Left Shift instead of starting immediately
                circle_art_shift_bind = True
                circle_art_working = False  # ensure idle until Left Shift is pressed
                circle_art_event.clear()
                print("toggle circle_art")
        elif hasattr(key, 'char') and key.char and key.char=='m':
            if 'ctrl' in pressed_keys:
                print("benchmarking...")
                benchmark()
        elif hasattr(key, 'char') and key.char and key.char=='6':
            if 'ctrl' in pressed_keys:
                print("minicirclecrash")
                minicirclecrash()
        elif hasattr(key, 'char') and key.char and key.char=='e':
            if 'ctrl' in pressed_keys:
                print("engineer_spam")
                engineer_spam_working = True
                start_engineer_spam()
        elif hasattr(key, 'char') and key.char and key.char=='l':
            if 'ctrl' in pressed_keys:
                controller.press("`")
                for _ in range(10):
                    controller.tap("x")
                    time.sleep(0.03)
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='h': 
            if 'ctrl' in pressed_keys:
                global emoji_replacement_enabled
                emoji_replacement_enabled = not emoji_replacement_enabled
                status = "enabled" if emoji_replacement_enabled else "disabled"
                print(f"emoji replacement {status}")
        elif hasattr(key, 'char') and key.char and key.char=='r':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrlr_armed and (now - ctrlr_last_time <= 5):
                    print("Ctrl+R second press - executing arena close spam")
                    for _ in range(500):
                        type_with_enter("$arena close")
                    ctrlr_armed = False
                else:
                    print("Ctrl+R first press - press again within 5s to confirm arena close spam")
                    ctrlr_last_time = now
                    ctrlr_armed = True
        elif hasattr(key, 'char') and key.char and key.char=='g':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrlg_armed and (now - ctrlg_last_time <= 5):
                    print("ctrl+g executing")
                    controller.press("`")
                    for _ in range(500):
                        controller.tap("f")
                        controller.tap("b")
                        controller.tap("b")
                    for _ in range(20):
                        controller.tap("b")
                    controller.release("`")
                    ctrlg_armed = False
                else:
                    print("ctrl+g armed")
                    ctrlg_armed = True
                    ctrlg_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='d':
            if 'ctrl' in pressed_keys:
                for _ in range(50):
                    controller.tap("n")
                controller.tap("k")
                controller.press(Key.space)
                time.sleep(0.1)
                controller.release(Key.space)
                controller.tap("y")
                controller.press(Key.space)
                time.sleep(0.1)
                controller.release(Key.space)
                controller.tap("u")
                controller.press(Key.space)
                time.sleep(0.1)
                controller.release(Key.space)
        elif hasattr(key, 'char') and key.char and key.char=='j':
            if 'ctrl' in pressed_keys:
                start = mouse.position
                controller.press("`")
                for _ in range(200):
                    mouse.position = (start[0] + random.randint(-25, 25), start[1] + random.randint(-25, 25))
                    time.sleep(0.01)
                    controller.press("j")
                    mouse.position = (start[0] + random.randint(-25, 25), start[1] + random.randint(-25, 25))
                    time.sleep(0.01)
                    controller.release("j")
                controller.release("`")
                mouse.position = start
        elif hasattr(key, 'char') and key.char and key.char=='s':
            if 'ctrl' in pressed_keys:
                time.sleep(0.1)
                print("quicksetup")
                controller.press("`")
                time.sleep(0.05)
                for _ in range(50):
                    controller.tap("n")
                controller.tap("i")
                controller.press("s")
                for _ in range(20):
                    controller.tap("h")
                time.sleep(0.05)
                controller.tap("m")
                controller.release("s")
                controller.tap("s")
                time.sleep(0.05)
                controller.press("a")
                time.sleep(0.05)
                controller.tap("c")
                controller.tap("w")
                controller.tap("e")
                controller.tap("t")
                controller.tap("o")
                controller.release("a")
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='q':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrlq_armed and (now - ctrlq_last_time <= 5):
                    print("ctrl+q executing")
                    type_in_console("d" + "fy"*10 + ("f"*50+"h")*2)
                    tap_in_console("dd")
                    controller.press("`")
                    time.sleep(0.1)
                    controller.press("d")
                    controller.release("`")
                    ctrlq_armed = False
                else:
                    print("ctrl+q armed")
                    ctrlq_armed = True
                    ctrlq_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='a':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrla_armed and (now - ctrla_last_time <= 5):
                    print("ctrl+a executing")
                    type_in_console("d" + "fy"*10 + ("f"*50+"h")*6)
                    tap_in_console("dd")
                    controller.press("`")
                    time.sleep(0.1)
                    controller.press("d")
                    controller.release("`")
                    ctrla_armed = False
                else:
                    print("ctrl+a armed")
                    ctrla_armed = True
                    ctrla_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='z':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrlz_armed and (now - ctrlz_last_time <= 5):
                    print("ctrl+z executing")
                    type_in_console("d" + "fy"*10 + ("f"*50+"h")*10)
                    tap_in_console("dd")
                    controller.press("`")
                    time.sleep(0.1)
                    controller.press("d")
                    controller.release("`")
                    ctrlz_armed = False
                else:
                    print("ctrl+z armed")
                    ctrlz_armed = True
                    ctrlz_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='y':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrly_armed and (now - ctrly_last_time <= 5):
                    print("ctrl+y executing")
                    type_in_console("d" + "fy"*10 + ("f"*50+"h")*2)
                    ctrly_armed = False
                else:
                    print("ctrl+y armed")
                    ctrly_armed = True
                    ctrly_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='x':
            if 'ctrl' in pressed_keys:
                time.sleep(1)
                circle()
                circle()
                time.sleep(0.5)
                controller.press("`")
                start = mouse.position
                # make the mouse go a random angle around start with a radius of 20px
                for i in range(4):
                    for _ in range(100):
                        angle = random.uniform(0, 2 * math.pi)
                        radius = 75
                        x_float = start[0] + radius * math.cos(angle)
                        y_float = start[1] + radius * math.sin(angle)
                        mouse.position = (int(x_float), int(y_float))
                        time.sleep(0.003)
                        controller.tap("f")
                        time.sleep(0.006)
                        controller.press("j")
                        time.sleep(0.006)
                        mouse.position = start
                        time.sleep(0.003)
                        controller.release("j")
                        time.sleep(0.003)
                    mouse.position = (start[0] + 100, start[1])
                    controller.tap("h")
                    time.sleep(0.006)
                controller.release("`")
        elif hasattr(key, 'char') and key.char and key.char=='u':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrlu_armed and (now - ctrlu_last_time <= 5):
                    print("ctrl+u executing")
                    type_in_console("d" + "fy"*10 + ("f"*50+"h")*6)
                    ctrlu_armed = False
                else:
                    print("ctrl+u armed")
                    ctrlu_armed = True
                    ctrlu_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='i':
            if 'ctrl' in pressed_keys:
                now = time.time()
                if ctrli_armed and (now - ctrli_last_time <= 5):
                    print("ctrl+i executing")
                    type_in_console("d" + "fy"*10 + ("f"*50+"h")*10)
                    ctrli_armed = False
                else:
                    print("ctrl+i armed")
                    ctrli_armed = True
                    ctrli_last_time = now
        elif hasattr(key, 'char') and key.char and key.char=='[':
            if 'ctrl' in pressed_keys:
                repeat_tap_in_console("f", 100)
            else:
                circle_mouse_radius = max(circle_mouse_radius - 5, 5)
                circle_mouse_radius_value.value = circle_mouse_radius
                # Calculate rotations per second
                angle_step = 5.0 / max(circle_mouse_radius, 10)
                rps = (angle_step / (2 * math.pi)) / max(circle_mouse_speed, 0.001)
                print(f"circle radius: {circle_mouse_radius} | {rps:.2f} rotations/sec")
        elif hasattr(key, 'char') and key.char and key.char==']':
            if 'ctrl' in pressed_keys:
                repeat_tap_in_console("f", 500)
            else:
                circle_mouse_radius = min(circle_mouse_radius + 5, 1000)
                circle_mouse_radius_value.value = circle_mouse_radius
                # Calculate rotations per second
                angle_step = 5.0 / max(circle_mouse_radius, 10)
                rps = (angle_step / (2 * math.pi)) / max(circle_mouse_speed, 0.001)
                print(f"circle radius: {circle_mouse_radius} | {rps:.2f} rotations/sec")
        elif hasattr(key, 'char') and key.char and key.char=='o':
            if 'ctrl' in pressed_keys:
                circle_mouse_active = not circle_mouse_active
                if circle_mouse_active:
                    circle_mouse_direction = 1  # reset to default on start
                    circle_mouse_direction_value.value = circle_mouse_direction
                    print(f"circle mouse on (radius: {circle_mouse_radius}, speed: {circle_mouse_speed})")
                    start_circle_mouse()
                else:
                    print("circle mouse off")
                    stop_circle_mouse()
        elif hasattr(key, 'char') and key.char and key.char=='0':
            if 'ctrl' in pressed_keys:
                print("OCR Text Capture - Click two corners to define region")
                threading.Thread(target=ocr_text_capture, daemon=True).start()
        elif hasattr(key, 'char') and key.char and key.char=='\\':
            # Toggle direction of circle while active
            if circle_mouse_active:
                circle_mouse_direction *= -1
                circle_mouse_direction_value.value = circle_mouse_direction
                dir_text = 'clockwise' if circle_mouse_direction == 1 else 'counterclockwise'
                print(f"circle direction -> {dir_text}")
        elif hasattr(key, 'char') and key.char and key.char=='k':
            if 'ctrl' in pressed_keys:
                type_with_enter("$arena team 1", 0.05)
                type_with_enter("$arena spawnpoint 0 0", 0.05)
        elif hasattr(key, 'char') and key.char and key.char=='t':
            if 'ctrl' in pressed_keys:
                print("custom_reload_spam")
                start_custom_reload_spam()
        elif hasattr(key, 'char') and key.char and key.char.lower()=='p':
            # Ctrl+B toggles berserk mode
            if 'ctrl' in pressed_keys:
                berserk = not berserk
                mode_text = "ON" if berserk else "OFF"
                print(f"berserk: {mode_text}")
        if hasattr(key, 'char') and key.char and key.char=='-':
            circle_mouse_speed = min(circle_mouse_speed + 0.001, 0.5)
            circle_mouse_speed_value.value = circle_mouse_speed
            # Calculate rotations per second
            angle_step = 5.0 / max(circle_mouse_radius, 10)
            rps = (angle_step / (2 * math.pi)) / max(circle_mouse_speed, 0.001)
            print(f"circle speed: {round(circle_mouse_speed, 4)} (slower) | {rps:.2f} rotations/sec")
        if hasattr(key, 'char') and key.char and key.char=='=':
            circle_mouse_speed = max(circle_mouse_speed - 0.001, 0.001)
            circle_mouse_speed_value.value = circle_mouse_speed
            # Calculate rotations per second
            angle_step = 5.0 / max(circle_mouse_radius, 10)
            rps = (angle_step / (2 * math.pi)) / max(circle_mouse_speed, 0.001)
            print(f"circle speed: {round(circle_mouse_speed, 4)} (faster) | {rps:.2f} rotations/sec")
    except UnicodeDecodeError:
        # Silently ignore pynput Unicode decode errors (macOS keyboard event bug)
        pass
    except Exception as e:
        print(f"Error: {e}")
    
def on_release(key: Key | KeyCode | None) -> None:
    global circle_art_working, circle_art_shift_bind, mcrash_working, mcrash_shift_bind, circle_finder_active
    try:
        # Workaround for pynput macOS Unicode decode bug
        if key is None:
            return
        if listener_event_injected:
            return
    except UnicodeDecodeError:
        return
    
    if is_ctrl(key):
        pressed_keys.discard('ctrl')
    elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
        if ctrlswap:
            pressed_keys.discard('ctrl')  # Release Cmd when ctrlswap is enabled
    elif is_alt(key):
        pressed_keys.discard('alt')
        # print("alt up")  # uncomment to debug
    # Releasing Left/Right Shift stops circle_art, mcrash, and circle_finder
    elif key in (Key.shift_l, Key.shift_r, Key.shift):
        if circle_finder_active:
            print("circle_finder stopping (shift released)")
            stop_circle_finder()
        if circle_art_shift_bind and circle_art_working:
            print("circle_art off")
            circle_art_working = False
            circle_art_event.clear()
            # Actually stop the thread (circle_art uses threading, not multiprocessing)
            # Thread will stop when event is cleared
        if mcrash_shift_bind and mcrash_working:
            print("mcrash off")
            mcrash_working = False
            mcrash_event.clear()
            # Actually stop the process
            if mcrash_process is not None and mcrash_process.is_alive():
                mcrash_process.terminate()
                mcrash_process.join(timeout=1)
    # Remove key from pressed_keys (convert to string for set membership)
    if isinstance(key, Key):
        key_str = key.name if hasattr(key, 'name') else str(key)
        if key_str in pressed_keys:
            pressed_keys.discard(key_str)

if __name__ == '__main__':
    # Required for multiprocessing on macOS and Windows
    multiprocessing.set_start_method('spawn', force=True)
    
    print(f"Running on: {PLATFORM}")
    if PLATFORM not in ('darwin', 'linux', 'windows'):
        print(f"Warning: Platform '{PLATFORM}' may have limited support.")
        print("Tested on macOS, Linux (Arch/Debian/Ubuntu), and Windows.")
    
    # Wrapper to suppress pynput Unicode decode errors on macOS
    def safe_on_press(key: Key | KeyCode | None) -> None:
        try:
            on_press(key)
        except UnicodeDecodeError:
            pass  # Ignore Unicode decode errors from special keys
    
    def safe_on_release(key: Key | KeyCode | None) -> None:
        try:
            on_release(key)
        except UnicodeDecodeError:
            pass  # Ignore Unicode decode errors from special keys
    
    listener = RobustKeyboardListener(on_press=safe_on_press, on_release=safe_on_release)
    listener.start()
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Ensure cleanup happens even on unexpected exit
        listener.stop()
        stopallthreads()
        
        # Clean up overlay thread if running
        if overlay_thread is not None and overlay_thread.is_alive():
            overlay_stop_event.set()
            overlay_thread.join(timeout=1.0)
        
        # Give processes time to fully terminate
        time.sleep(0.2)