# filepath: [screensender.py](http://_vscodecontentref_/0)
import sys
print("Python executable:", sys.executable)
import asyncio
import io
import json
import os
import urllib.parse
from pathlib import Path

import mss
from PIL import Image
import websockets
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button

# Configuration
HOST = "0.0.0.0"
PORT = 8765
FPS = 30  # approximate frames per second
AUTH_TOKEN = os.environ.get("SCREEN_SENDER_TOKEN", "changeme")  # set SCREEN_SENDER_TOKEN in env

sct = mss.mss()
monitor = sct.monitors[1]  # primary monitor
kb = KeyboardController()
mouse = MouseController()

# primitive mapping for a few special keys
SPECIAL_KEYS = {
    "enter": Key.enter,
    "esc": Key.esc,
    "tab": Key.tab,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "alt": Key.alt,
    "space": Key.space,
    "backspace": Key.backspace,
}

async def send_frames(ws):
    try:
        interval = 1.0 / FPS
        while True:
            img = sct.grab(monitor)
            pil = Image.frombytes("RGB", img.size, img.rgb)
            buf = io.BytesIO()
            # WebP with quality 65 typically gives better results than JPEG quality 60
            pil.save(buf, format="WebP", quality=65, method=4)
            data = buf.getvalue()
            await ws.send(data)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        return

async def handle_input_message(msg):
    # msg is dict
    t = msg.get("type")
    if t == "mouse":
        action = msg.get("action")
        # coordinates are normalized (0..1)
        nx = msg.get("nx")
        ny = msg.get("ny")
        if nx is not None and ny is not None:
            x = int(nx * monitor["width"]) + monitor["left"]
            y = int(ny * monitor["height"]) + monitor["top"]
        else:
            x = None; y = None

        if action == "move" and x is not None:
            mouse.position = (x, y)
        elif action == "click":
            btn = msg.get("button", "left")
            count = int(msg.get("count", 1))
            if x is not None:
                mouse.position = (x, y)
            b = Button.left if btn == "left" else Button.right
            for _ in range(count):
                mouse.click(b, 1)
        elif action == "scroll":
            dx = int(msg.get("dx", 0)); dy = int(msg.get("dy", 0))
            mouse.scroll(dx, dy)

    elif t == "keyboard":
        action = msg.get("action")
        if action == "type":
            text = msg.get("text", "")
            kb.type(text)
        elif action == "press":
            k = msg.get("key", "")
            keyobj = SPECIAL_KEYS.get(k.lower()) if isinstance(k, str) else None
            if keyobj is None and isinstance(k, str) and len(k) == 1:
                kb.press(k); kb.release(k)
            elif keyobj is not None:
                kb.press(keyobj); kb.release(keyobj)

async def recv_inputs(ws):
    try:
        async for raw in ws:
            # incoming messages may be text
            try:
                if isinstance(raw, (bytes, bytearray)):
                    text = raw.decode("utf-8")
                else:
                    text = raw
                msg = json.loads(text)
            except Exception:
                continue
            await handle_input_message(msg)
    except asyncio.CancelledError:
        return

async def handler(ws, path):
    # path is passed as an argument
    qs = urllib.parse.urlparse(path).query
    params = urllib.parse.parse_qs(qs)
    token = params.get("token", [None])[0]
    if token != AUTH_TOKEN:
        await ws.close(code=4003, reason="auth_failed")
        return

    send_task = asyncio.create_task(send_frames(ws))
    recv_task = asyncio.create_task(recv_inputs(ws))
    done, pending = await asyncio.wait([send_task, recv_task], return_when=asyncio.FIRST_COMPLETED)
    for p in pending:
        p.cancel()

async def main():
    addr = f"{HOST}:{PORT}"
    print(f"Starting screen sender on ws://{addr}  (set SCREEN_SENDER_TOKEN to change token)")
    async with websockets.serve(handler, HOST, PORT, max_size=None, max_queue=None):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())