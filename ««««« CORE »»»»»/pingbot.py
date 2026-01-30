from pynput.keyboard import Key, Controller
#import ping for https://arras.io
import ping3
import time
time.sleep(3)
keyboard = Controller()
while True:
    ping = ping3.ping('arras.io')
    ping_ms = ping * 1000  # Convert to milliseconds
    keyboard.tap(Key.enter)
    time.sleep(0.1)
    keyboard.type(f'Ping: {int(ping_ms)} ms')
    time.sleep(0.1)
    keyboard.tap(Key.enter)
    time.sleep(5)