import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import tkinter as tk
time.sleep(4)

global controller, mouse
controller = KeyboardController()
mouse = MouseController()
s = 25
letters35 = [
    " XXX  X X  XXX  X X  X X ",# a 0
    " XX   X X  XXX  X X  XX  ",# b 1
    " XXX  X    X    X    XXX ",# c 2
    " XX   X X  X X  X X  XX  ",# d 3
    " XXX  X    XXX  X    XXX ",# e 4
    " XXX  X    XXX  X    X   ",# f 5
    " XXX  X    X X  X X  XXX ",# g 6
    " X X  X X  XXX  X X  X X ",# h 7
    " XXX   X    X    X   XXX ",# i 8
    " XXX   X    X    X   XX  ",# j 9
    " X X  X X  XX   X X  X X ",# k 10
    " X    X    X    X    XXX ",# l 11
    "X   XXX XXX X XX   XX   X",# m 12
    "X   XXX  XX X XX  XXX   X",# n 13
    " XXX  X X  X X  X X  XXX ",# o 14
    " XXX  X X  XXX  X    X   ",# p 15
    " XXX  X X  XXX    X    X ",# q 16
    " XXX  X X  XX   X X  X X ",# r 17
    " XXX  X    XXX    X  XXX ",# s 18
    " XXX   X    X    X    X  ",# t 19
    " X X  X X  X X  X X  XXX ",# u 20
    " X X  X X  X X  X X   X  ",# v 21
    "X X XX X XX X XX X X X X ",# w 22
    " X X  X X   X   X X  X X ",# x 23
    " X X  X X   X    X    X  ",# y 24
    " XXX    X   X   X    XXX " # z 25
]
letters3 = [
    'XXXX XXXXX XX X',
    'XX X XXXXX XXX ',
    'XXXX  X  X  XXX',
    'XX X XX XX XXX ',
    'XXXX  XXXX  XXX',#5 e
    'XXXX  XXXX  X  ',
    'XXXX  X XX XXXX',
    'X XX XXXXX XX X',
    'XXX X  X  X XXX',
    'XXX X  X  X XX ',#10 j
    'X XX XXX X XX X',
    'X  X  X  X  XXX',
    "X   XXX XXX X XX   XX   X",
    "X   XXX  XX X XX  XXX   X",
    'XXXX XX XX XXXX',#15 o
    'XXXX XXXXX  X  ',
    'XXXX XXXX  X  X',
    'XXXX XXX X XX X',
    'XXXX  XXX  XXXX',
    'XXX X  X  X  X ',#20 t
    'X XX XX XX XXXX',
    'X XX XX XX X X ',
    ' X  X  X  X X X',
    'X XX X X X XX X',
    'X XX X X  X  X ',
    'XXX  X X X  XXX']#25 z
letters2 = [
    " XXX  X X  X X  X X  XXX ",# 0 0
    " XX    X    X    X   XXX ",# 1 1
    " XXX    X  XXX  X    XXX ",# 2 2
    " XXX    X  XXX    X  XXX ",# 3 3
    " X X  X X  XXX    X    X ",# 4 4
    " XXX  X    XXX    X  XXX ",# 5 5
    " XXX  X    XXX  X X  XXX ",# 6 6
    " XXX    X    X    X    X ",# 7 7
    " XXX  X X  XXX  X X  XXX ",# 8 8
    " XXX  X X  XXX    X  XXX ",# 9 9
    " X X XXXXX X X XXXXX X X ",# # 10
    "  XX  X    X    X     XX ",# ( 11
    " XXX  X    X    X    XXX ",# [ 12
    " XXX  X   XX    X    XXX ",# { 13
    "  XX    X    X    X   XX ",# ) 14
    " XXX    X    X    X  XXX ",# ] 15
    " XXX    X    XX   X  XXX ",# } 16
    "   X    X   X   X    X   ",# / 17
    " X    X     X     X    X ",# \ 18
    " XXX    X  XXX        X  ",# ? 19
    "   X   X   X     X     X ",# < 20
    " X     X     X   X   X   ",# > 21
    "                    XXXXX",# _ 22
    "           XXX           ",# - 23
    "  X    X  XXXXX  X    X  ",# + 24
    "     XXXXX     XXXXX     ",# = 25
    "     XXX XX XXX          ",# ~ 26
    "  X   X X                " # ^ 27
]
numbers1 = [
    "X XX X         ",# " 0
    " X  X          ",# ' 1
    "             X ",# . 2
    "          X  X ",# , 3
    "    X     X    ",# : 4
    "    X     X  X ",# ; 5
    " X  X  X  X  X ",# | 6
    " X  X  X     X " # ! 7
]
letters5 = [
    "XXXXXX   XXXXXXX   XX   X",# a 0
    "XXXX X   XXXXXXX   XXXXX ",# b 1
    "XXXXXX    X    X    XXXXX",# c 2
    "XXXX X   XX   XX   XXXXX ",# d 3
    "XXXXXX    XXXXXX    XXXXX",# e 4
    "XXXXXX    XXXXXX    X    ",# f 5
    "XXXXXX    X XXXX   XXXXXX",# g 6
    "X   XX   XXXXXXX   XX   X",# h 7
    "XXXXX  X    X    X  XXXXX",# i 8
    "XXXXX  X    X  X X  XXX  ",# j 9
    "X   XX  X XXX  X  X X   X",# k 10
    "X    X    X    X    XXXXX",# l 11
    "X   XXX XXX X XX   XX   X",# m 12
    "X   XXX  XX X XX  XXX   X",# n 13
    "XXXXXX   XX   XX   XXXXXX",# o 14
    "XXXXXX   XXXXXXX    X    ",# p 15
    "XXXXXX   XX   XX  X XXX X",# q 16
    "XXXXXX   XXXXX X   XX   X",# r 17
    "XXXXXX    XXXXX    XXXXXX",# s 18
    "XXXXX  X    X    X    X  ",# t 19
    "X   XX   XX   XX   XXXXXX",# u 20
    "X   XX   X X X  X X   X  ",# v 21
    "X X XX X XX X XX X X X X ",# w 22
    "X   X X X   X   X X X   X",# x 23
    "X   X X X   X    X    X  ",# y 24
    "XXXXX   X   X   X   XXXXX" # z 25
]

def ball(pos=mouse.position):
    mouse.position = (pos)
    controller.press("`")
    for _ in range(4):
        controller.tap("c")
        controller.tap("h")
    controller.release("`")

def placeletter(letterdata, x = 3, y = 5, s = 25):
    # letter height and width are paramaterized
    # default size is 5 x 5
    start = mouse.position
    try:
        if len(letterdata) == (x * y):
            for yp in range(y):
                for xp in range(x):
                    if letterdata[(xp + (yp * y))] == "X":
                        mouse.position = (start[0] + (xp * s), start[1] + (yp * s))
                        time.sleep(0.04)
                        ball(mouse.position)
                        time.sleep(0.1)
            time.sleep(0.04)
        else:
            print(f"String length out of bounds ({len(letterdata)}/{(x * y)})")
    except Exception as ex:
        print(f"Exception as {ex}")
    mouse.position = (start[0] + (x * s), start[1])
    start = mouse.position
    time.sleep(0.1)

placeletter(letters3[22])
placeletter(letters3[15])
placeletter(letters3[22])