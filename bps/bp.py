from pynput import keyboard, mouse
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import time, threading

s = 9 # wall width
controller = KeyboardController()
mouse = MouseController()
POSITIONPATH = "bps/wall.txt"
MODIFIERPATH = "bps/type.txt"
COLORRGBPATH = "bps/color.txt"
colorheld = "b"
modifierheld = "n"

time.sleep(4)

colors = ["n", "b", "g", "r", "p", "y", "G", "e", "s", "t", "P", "h", "c", "S", "l", "w", "o", "W", "C", "f", "B"]
colorinstructions = [
    "pass",
    "mouse.position = (mouse.position[0] + 1.5, mouse.position[1] - 22.8)",
    "mouse.position = (mouse.position[0] + 11.9, mouse.position[1] - 21.5)",
    "mouse.position = (mouse.position[0] + 19.4, mouse.position[1] - 16.8)",
    "mouse.position = (mouse.position[0] + 21.1, mouse.position[1] - 8.8)",
    "mouse.position = (mouse.position[0] + 23.2, mouse.position[1] - 3.5)",
    "mouse.position = (mouse.position[0] + 23.2, mouse.position[1] + 1.8)",
    "mouse.position = (mouse.position[0] + 23.2, mouse.position[1] + 11.8)",
    "mouse.position = (mouse.position[0] + 20.5, mouse.position[1] + 18.4)",
    "mouse.position = (mouse.position[0] + 8.5, mouse.position[1] + 21.7)",
    "mouse.position = (mouse.position[0] + 2.8, mouse.position[1] + 23.3)",
    "mouse.position = (mouse.position[0] + -3.6, mouse.position[1] + 23.3)",
    "mouse.position = (mouse.position[0] + -12.9, mouse.position[1] + 22.5)",
    "mouse.position = (mouse.position[0] + -19.7, mouse.position[1] + 20.3)",
    "mouse.position = (mouse.position[0] + -24.3, mouse.position[1] + 14.8)",
    "mouse.position = (mouse.position[0] + -24.3, mouse.position[1] + 7.6)",
    "mouse.position = (mouse.position[0] + -24.9, mouse.position[1] + -0.8)",
    "mouse.position = (mouse.position[0] + -24.9, mouse.position[1] + -11.0)",
    "mouse.position = (mouse.position[0] + -22.1, mouse.position[1] + -18.7)",
    "mouse.position = (mouse.position[0] + -14.3, mouse.position[1] + -23.3)",
    "mouse.position = (mouse.position[0] + -5.3, mouse.position[1] + -25.4)",
]

modifiers = ["n", "k", "h", "b", "B", "s", "e", "^", "v", ">", "<", "S", "f", "p", "F", "t", "T", "P", "r"]
modifierinstructions = [
    "mouse.position = (mouse.position[0] + 3.4, mouse.position[1] - 23.7)",
    "mouse.position = (mouse.position[0] + 14.6, mouse.position[1] - 22.0)",
    "mouse.position = (mouse.position[0] + 20.3, mouse.position[1] - 16.5)",
    "mouse.position = (mouse.position[0] + 22.2, mouse.position[1] - 9.7)",
    "mouse.position = (mouse.position[0] + 23.9, mouse.position[1] - 1.8)",
    "mouse.position = (mouse.position[0] + 23.9, mouse.position[1] + 8.0)",
    "mouse.position = (mouse.position[0] + 22.5, mouse.position[1] + 15.4)",
    "mouse.position = (mouse.position[0] + 15.6, mouse.position[1] + 17.0)",
    "mouse.position = (mouse.position[0] + 5.8, mouse.position[1] + 20.4)",
    "mouse.position = (mouse.position[0] + -2.2, mouse.position[1] + 21.2)",
    "mouse.position = (mouse.position[0] + -10.2, mouse.position[1] + 20.7)",
    "mouse.position = (mouse.position[0] + -16.5, mouse.position[1] + 18.1)",
    "mouse.position = (mouse.position[0] + -19.2, mouse.position[1] + 12.5)",
    "mouse.position = (mouse.position[0] + -22.6, mouse.position[1] + 5.4)",
    "mouse.position = (mouse.position[0] + -22.6, mouse.position[1] + -1.9)",
    "mouse.position = (mouse.position[0] + -22.6, mouse.position[1] + -10.0)",
    "mouse.position = (mouse.position[0] + -17.6, mouse.position[1] + -18.3)",
    "mouse.position = (mouse.position[0] + -11.0, mouse.position[1] + -20.5)",
    "mouse.position = (mouse.position[0] + -4.2, mouse.position[1] + -20.7)",
]

# map every corresponding pair of characters
# from each text file to a 2-character string in a list (including spaces)
# assign every pair an x and y coordinate
# format: [{type}, {modifier}, {color}, {x}, {y}]
buildqueue = []
with open(POSITIONPATH, "r") as p:
    with open(MODIFIERPATH, "r") as m:
        with open(COLORRGBPATH, "r") as c:
            ypos = 0
            for mline, cline in zip(m.readlines(), c.readlines()):
                xpos = 0
                for mchar, cchar in zip(mline.strip(), cline.strip()):
                    buildqueue.append([mchar, cchar, xpos, ypos])
                    xpos += s
                ypos += s

def place(queue):
    # Group datapoints by modifier first, then by color within each modifier group
    modifier_groups = {}
    for datapoint in queue:
        modifier = datapoint[0]
        if modifier not in modifier_groups:
            modifier_groups[modifier] = {}
        color = datapoint[1]
        if color not in modifier_groups[modifier]:
            modifier_groups[modifier][color] = []
        modifier_groups[modifier][color].append(datapoint)
    
    # Process each modifier group
    for modifier in modifier_groups:
        # Set modifier once for this group
        controller.press("`")
        time.sleep(0.01)
        controller.tap("x")
        time.sleep(0.01)
        controller.press("z")
        time.sleep(0.01)
        exec(modifierinstructions[modifiers.index(modifier)])
        time.sleep(0.01)
        controller.release("z")
        time.sleep(0.01)
        
        # Process each color group within this modifier
        for color in modifier_groups[modifier]:
            # Set color once for this group
            controller.press("c")
            time.sleep(0.01)
            exec(colorinstructions[colors.index(color)])
            time.sleep(0.01)
            controller.release("c")
            time.sleep(0.01)
            
            # Place all walls with this modifier+color combination
            for datapoint in modifier_groups[modifier][color]:
                x = datapoint[2]
                y = datapoint[3]
                mouse.position = (int(x) + 404, int(y) + 179)
                time.sleep(0.01)
                controller.tap("x")
        
        controller.release("`")
        time.sleep(0.01)

place(buildqueue)