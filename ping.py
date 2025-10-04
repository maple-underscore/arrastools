from ping3 import ping
import time
from threading import *

pings=[]
# Replace with your target URL or IP
def ping200():
    target = "arras.io"
    # Send ping and get delay in seconds
    for _ in range(200):
        delay = ping(target)

        if delay is None:
            print(f"Ping to {target} failed.")
        else:
            pings.append(float(f"{delay * 1000:.2f}"))

time.sleep(3)

#run 16 threads at the same time
threads = []
for i in range(16):
    thread = Thread(target=ping200)
    threads.append(thread)
    thread.start()

#print average of pings
for thread in threads:
    thread.join()  
print(f"Average ping: {sum(pings)/len(pings)} ms")