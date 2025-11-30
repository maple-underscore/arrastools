import asyncio
import io
import os
import urllib.parse
from datetime import datetime

import mss
import numpy as np
from PIL import Image
import websockets

# Configuration
HOST = "0.0.0.0"
PORT = 8766
FPS = 10                          # frames per second (tune down to save bandwidth)
TARGET_WIDTH = 1280               # resize width (maintains aspect ratio)
AUTH_TOKEN = "tokenhere"          # verification token required by the client
MAX_SEND_BYTES = 200 * 1024       # target max payload per frame (will reduce quality if needed)
DIFF_SIZE = (64, 64)              # downscale size for quick frame-diffing
DIFF_THRESHOLD = 3.0              # mean absolute diff threshold (0..255) to consider as changed
FORCE_KEYFRAME_SECONDS = 2        # force sending a full frame this often

sct = mss.mss()
monitor = sct.monitors[1]  # primary monitor


def pil_from_sct(img):
    return Image.frombytes("RGB", img.size, img.rgb)


def resize_keep_aspect(pil, target_w):
    w, h = pil.size
    if w <= target_w:
        return pil
    new_h = int(h * (target_w / w))
    return pil.resize((target_w, new_h), Image.Resampling.LANCZOS)


def encode_webp(pil, quality=50):
    buf = io.BytesIO()
    pil.save(buf, format="WEBP", quality=quality, method=4)
    return buf.getvalue()


def small_gray(pil):
    return pil.convert("L").resize(DIFF_SIZE, Image.Resampling.BILINEAR)


async def send_loop(ws):
    interval = 1.0 / FPS
    prev_small = None
    last_keyframe = 0.0

    try:
        while True:
            start = asyncio.get_event_loop().time()
            img = sct.grab(monitor)
            pil = pil_from_sct(img)
            pil = resize_keep_aspect(pil, TARGET_WIDTH)

            now = datetime.utcnow().timestamp()
            force_keyframe = (now - last_keyframe) >= FORCE_KEYFRAME_SECONDS

            # compute cheap diff on downscaled grayscale image
            small = small_gray(pil)
            send_frame = True
            if prev_small is not None and not force_keyframe:
                a = np.asarray(prev_small, dtype=np.int16)
                b = np.asarray(small, dtype=np.int16)
                mad = np.mean(np.abs(a - b))
                send_frame = (mad >= DIFF_THRESHOLD)

            if send_frame:
                # adaptive quality to try to keep under MAX_SEND_BYTES
                quality = 50
                data = encode_webp(pil, quality=quality)
                # if too big, progressively lower quality
                while len(data) > MAX_SEND_BYTES and quality > 20:
                    quality -= 8
                    data = encode_webp(pil, quality=quality)
                await ws.send(data)
                prev_small = small
                last_keyframe = now

            # sleep accounting for work time
            elapsed = asyncio.get_event_loop().time() - start
            to_sleep = max(0, interval - elapsed)
            await asyncio.sleep(to_sleep)
    except asyncio.CancelledError:
        return
    except Exception:
        return


async def handler(ws, path):
    # simple token check in query string e.g. ws://host:8766/?token=tokenhere
    qs = urllib.parse.urlparse(path).query
    params = urllib.parse.parse_qs(qs)
    token = params.get("token", [None])[0]
    if token != AUTH_TOKEN:
        # close with special code for auth failed
        await ws.close(code=4003, reason="auth_failed")
        return

    send_task = asyncio.create_task(send_loop(ws))
    try:
        # keep connection open while send_loop runs; we don't expect inbound messages
        await send_task
    finally:
        if not send_task.done():
            send_task.cancel()


def main():
    print(f"Starting screenlink sender on ws://{HOST}:{PORT}  (token='{AUTH_TOKEN}')")
    start_server = websockets.serve(handler, HOST, PORT, max_size=None)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()