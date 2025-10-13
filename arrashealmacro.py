import time
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key

controller = KeyboardController()

def heal_macro():
    start = time.time()
    while time.time() - start < 15:
        controller.press("h")
        controller.release("h")
        time.sleep(0.05)  # Add a small delay to avoid spamming too fast

def on_press(key):
    if hasattr(key, 'char') and key.char == 'h':
        heal_macro()

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()