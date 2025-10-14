import random
import time
import threading
from pynput import keyboard
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
from pynput.mouse import Listener as MouseListener
import tkinter as tk

controller = KeyboardController()
mouse = MouseController()

string = ""
pos = 0
pairs = []

# inital processing into pairs of characters
for char in string:
    if pos % 2 == 0:
        temp = char
    else:
        pairs.append((temp, char))