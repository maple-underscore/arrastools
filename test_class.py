#!/usr/bin/env python3

# Extract just the MacroGUI class to test
import sys

# Read the file
with open('arrastools.py', 'r') as f:
    lines = f.readlines()

# Find class start
for i, line in enumerate(lines, 1):
    if 'class MacroGUI:' in line:
        print(f"Class starts at line {i}")
        # Check next 20 lines for methods
        for j in range(i, min(i+200, len(lines))):
            if lines[j-1].strip().startswith('def '):
                method_name = lines[j-1].split('def ')[1].split('(')[0]
                indent = len(lines[j-1]) - len(lines[j-1].lstrip())
                print(f"  Line {j}: {' '*indent}def {method_name}  (indent={indent})")
        break
