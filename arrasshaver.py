def shave_strings(strings, indexes_to_remove):
    indexes_set = set(indexes_to_remove)
    
    # Process each string in the list
    shaved_list = [
        ''.join(char for i, char in enumerate(s) if i not in indexes_set)
        for s in strings
    ]
    
    return shaved_list

# Example usage
input_strings = [
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
indexes = [0, 4, 5, 9, 10, 14, 15, 19, 20, 24]  # Remove characters at index 0 and 2
result = shave_strings(input_strings, indexes)
print("Original:", input_strings)
print("Shaved:", result)
