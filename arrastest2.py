import os

filepath = "vsc/copypastas/longest.txt"

print("Current working directory:", os.getcwd())
print("File exists:", os.path.exists(filepath))

if os.path.exists(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
        print("File length:", len(content))
        print("Preview:", repr(content[:100]))
else:
    print("File not found.")
