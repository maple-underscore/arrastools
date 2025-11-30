from pynput import mouse

positions = []

def on_click(x, y, button, pressed):
    if pressed:
        positions.append((x, y))
        print(f"Recorded position: {x}, {y}")

def main():
    print("Click anywhere to record mouse positions. Press Ctrl+C to stop.")
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()

if __name__ == "__main__":
    main()
