"""Directional threat detector that nudges the player away from red pixels."""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional, Set

import mss
import numpy as np
from pynput.keyboard import Controller, KeyCode

CENTER_X = 855
CENTER_Y = 615
SCAN_DISTANCE = 140  # pixels sampled outward from the center
SCAN_INTERVAL = 0.008  # faster polling without pegging the CPU
RED_THRESHOLD = 170
RED_DOMINANCE = 70
KEY_REFRESH_DELAY = 0.007
TIE_TOLERANCE = 20  # pixels difference treated as equal pressure
HYSTERESIS_MARGIN = 3  # require extra separation before swapping directions

AXIS_STATE: Dict[str, Optional[KeyCode]] = {"vertical": None, "horizontal": None}

KEY_W = KeyCode.from_char("w")
KEY_A = KeyCode.from_char("a")
KEY_S = KeyCode.from_char("s")
KEY_D = KeyCode.from_char("d")

def capture_window(sct: mss.mss) -> np.ndarray:
	half = SCAN_DISTANCE
	bbox = {
		"left": CENTER_X - half,
		"top": CENTER_Y - half,
		"width": half * 2 + 1,
		"height": half * 2 + 1,
	}
	shot = sct.grab(bbox)
	frame = np.frombuffer(shot.rgb, dtype=np.uint8)
	frame = frame.reshape(shot.height, shot.width, 3)
	return frame


def compute_red_mask(frame: np.ndarray) -> np.ndarray:
	frame16 = frame.astype(np.int16, copy=False)
	red = frame16[:, :, 0]
	green = frame16[:, :, 1]
	blue = frame16[:, :, 2]
	dominance = red - np.maximum(green, blue)
	return (red >= RED_THRESHOLD) & (dominance >= RED_DOMINANCE)


def scan_direction(mask_slice: np.ndarray) -> Optional[int]:
	if not mask_slice.any():
		return None
	return int(mask_slice.argmax() + 1)


def gather_distances(frame: np.ndarray) -> Dict[str, Optional[int]]:
	mask = compute_red_mask(frame)
	center = SCAN_DISTANCE
	up = scan_direction(mask[:center, center][::-1])
	down = scan_direction(mask[center + 1 :, center])
	left = scan_direction(mask[center, :center][::-1])
	right = scan_direction(mask[center, center + 1 :])
	return {"up": up, "down": down, "left": left, "right": right}


def decide_keys(distances: Dict[str, Optional[int]]) -> Set[KeyCode]:
	desired: Set[KeyCode] = set()

	def pick(axis_pos: str, axis_neg: str, move_pos: KeyCode, move_neg: KeyCode, axis_name: str) -> None:
		pos_dist = distances[axis_pos]
		neg_dist = distances[axis_neg]
		if pos_dist is None and neg_dist is None:
			return
		if pos_dist is None:
			desired.add(move_neg)
			return
		if neg_dist is None:
			desired.add(move_pos)
			return
		diff = abs(pos_dist - neg_dist)
		if diff <= TIE_TOLERANCE:
			AXIS_STATE[axis_name] = None
			return
		preferred = move_pos if pos_dist < neg_dist else move_neg
		current = AXIS_STATE.get(axis_name)
		if current is not None and current != preferred and diff < HYSTERESIS_MARGIN:
			desired.add(current)
			return
		AXIS_STATE[axis_name] = preferred
		desired.add(preferred)

	pick("up", "down", KEY_S, KEY_W, "vertical")
	pick("left", "right", KEY_D, KEY_A, "horizontal")
	return desired


class KeyManager:
	def __init__(self, controller: Controller, delay: float = KEY_REFRESH_DELAY) -> None:
		self._controller = controller
		self._delay = delay
		self._desired: Set[KeyCode] = set()
		self._active: Set[KeyCode] = set()
		self._lock = threading.Lock()
		self._poke = threading.Event()
		self._stop = threading.Event()
		self._thread = threading.Thread(target=self._worker, daemon=True)
		self._thread.start()

	def update(self, keys: Set[KeyCode]) -> None:
		with self._lock:
			self._desired = set(keys)
		self._poke.set()

	def stop(self) -> None:
		self._stop.set()
		self._poke.set()
		self._thread.join()
		self._sync(set())

	def _worker(self) -> None:
		while not self._stop.is_set():
			self._poke.wait()
			self._poke.clear()
			with self._lock:
				target = set(self._desired)
			self._sync(target)
			time.sleep(self._delay)

	def _sync(self, target: Set[KeyCode]) -> None:
		to_release = self._active - target
		to_press = target - self._active
		for key in to_release:
			self._controller.release(key)
			self._active.remove(key)
		for key in to_press:
			self._controller.press(key)
			self._active.add(key)


def main() -> None:
	keyboard = Controller()
	key_manager = KeyManager(keyboard)
	sct = mss.mss()
	print("Starting Sumo avoidance. Press Ctrl+C to exit.")
	try:
		while True:
			frame = capture_window(sct)
			distances = gather_distances(frame)
			keys = decide_keys(distances)
			key_manager.update(keys)
			time.sleep(SCAN_INTERVAL)
	except KeyboardInterrupt:
		print("Stopping Sumo avoidance...")
	finally:
		key_manager.stop()


if __name__ == "__main__":
	main()
