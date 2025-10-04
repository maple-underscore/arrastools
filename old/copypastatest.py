import time, threading, os
#each line should be 60 chars long

global ids, copypastaing, controller, thread
ids = ['longest', 'long'] #etc
filepaths = ["/workspaces/arrastools/copypastas/longest.txt", "/workspaces/copypastas/long.txt"]
copypastaing = False
thread = None

def copypasta(id):
    global ids, copypastaing, filepaths, controller
    if id in ids:
        index = ids.index(id)
        filepath = filepaths[index]
        pos = 0
        copypastaing = True
        start = time.time()
        with open(filepath, "r") as file:
            file.seek(0)
            text = file.read()
            lent = len(text)
            file_size_bytes = os.path.getsize(filepath)
            file_size_kb = file_size_bytes / (1024)
            end = time.time()
            time.sleep(0.1)
            print(f"Loaded file from filepath ==> [{filepath[23:len(filepath)]}]")
            time.sleep(0.1)
            print(f"> Loaded {lent} characters < [{file_size_kb:.2f}KB]")
            time.sleep(0.1)
            print(f"Time taken > [{round((end-start)*1000, 3)}ms] < Waiting for chat delay...")
            time.sleep(0.1)
            endf = False
            while copypastaing and not endf:
                for _ in range(3):
                    if not endf:
                        if pos+61 < lent-1:
                            if pos+61 < lent-1:
                                text2=""
                                for char in text[pos:pos+61]:
                                    if char == " ":
                                        text2+="x"
                                    else:
                                        text2+=" "
                                print(text2)
                            else:
                                print(text[pos:(lent-1)])
                            pos+=60
                        else:
                            pos = 0
                        time.sleep(0.01)
            print(f"Copypasta of > {lent} characters < finished")
copypasta('longest')