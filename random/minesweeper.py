import random

def print_grid(grid, opened, marks, win=False, give_up=False, reveal_all=False):
    # ANSI color codes
    COLOR_RESET = '\033[0m'
    COLOR_BOMB = '\033[91m'      # Red
    COLOR_UNOPENED = '\033[94m'  # Blue
    COLOR_WIN = '\033[92m'       # Green
    COLOR_MARK = '\033[93m'      # Yellow
    COLOR_AXIS = '\033[90m'      # Grey
    COLOR_BOMB_WIN = '\033[92m'  # Green for bombs on win
    COLOR_BOMB_GIVEUP = '\033[93m'  # Yellow for bombs on give up
    COLOR_NUMS = [
        '\033[97m',  # 0 - White
        '\033[96m',  # 1 - Cyan
        '\033[92m',  # 2 - Green
        '\033[93m',  # 3 - Yellow
        '\033[95m',  # 4 - Magenta
        '\033[91m',  # 5 - Red
        '\033[90m',  # 6 - Grey
        '\033[35m',  # 7 - Purple
        '\033[31m',  # 8 - Bright Red
    ]
    width = len(grid[0])
    height = len(grid)
    # Print x-axis markers
    axis_row = '   '  # Padding for y-axis
    for x in range(width):
        axis_row += f'{COLOR_AXIS}{x%10} {COLOR_RESET}'
    print(axis_row)
    for y in range(height):
        row = f'{COLOR_AXIS}{y%10}  {COLOR_RESET}'  # y-axis marker
        for x in range(width):
            if give_up or reveal_all:
                if grid[y][x] == '*':
                    row += f'{COLOR_BOMB_GIVEUP}* {COLOR_RESET}'
                elif grid[y][x] == 0:
                    row += f'{COLOR_NUMS[0]}0 {COLOR_RESET}'
                else:
                    color = COLOR_NUMS[grid[y][x]] if grid[y][x] < len(COLOR_NUMS) else COLOR_NUMS[0]
                    row += f'{color}{grid[y][x]} {COLOR_RESET}'
            else:
                if win and grid[y][x] == '*':
                    row += f'{COLOR_BOMB_WIN}* {COLOR_RESET}'
                elif marks[y][x] is not None and not opened[y][x]:
                    row += f'{COLOR_MARK}{marks[y][x]} {COLOR_RESET}'
                elif opened[y][x]:
                    if grid[y][x] == '*':
                        row += f'{COLOR_BOMB}* {COLOR_RESET}'
                    elif grid[y][x] == 0:
                        row += f'{COLOR_NUMS[0]}0 {COLOR_RESET}'
                    else:
                        color = COLOR_NUMS[grid[y][x]] if grid[y][x] < len(COLOR_NUMS) else COLOR_NUMS[0]
                        row += f'{color}{grid[y][x]} {COLOR_RESET}'
                else:
                    row += f'{COLOR_UNOPENED}+ {COLOR_RESET}'
        print(row)

def place_bombs(width, height, num_bombs):
    grid = [[0 for _ in range(width)] for _ in range(height)]
    bombs = set()
    while len(bombs) < num_bombs:
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        if (y, x) not in bombs:
            bombs.add((y, x))
            grid[y][x] = '*'
    # Fill in numbers
    for y in range(height):
        for x in range(width):
            if grid[y][x] == '*':
                continue
            count = 0
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width:
                        if grid[ny][nx] == '*':
                            count += 1
            grid[y][x] = count
    return grid

def open_cell(grid, opened, y, x):
    if opened[y][x]:
        return
    opened[y][x] = True
    if grid[y][x] == 0:
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]):
                    if not opened[ny][nx]:
                        open_cell(grid, opened, ny, nx)

def check_win(grid, opened):
    for y in range(len(grid)):
        for x in range(len(grid[0])):
            if grid[y][x] != '*' and not opened[y][x]:
                return False
    return True


def main():
    width = int(input('Grid width: '))
    height = int(input('Grid height: '))
    num_bombs = int(input('Number of bombs: '))
    grid = place_bombs(width, height, num_bombs)
    opened = [[False for _ in range(width)] for _ in range(height)]
    marks = [[None for _ in range(width)] for _ in range(height)]
    # Reveal a random initial certain square (not a bomb)
    safe_cells = [(y, x) for y in range(height) for x in range(width) if grid[y][x] != '*']
    if safe_cells:
        y, x = random.choice(safe_cells)
        open_cell(grid, opened, y, x)
        print(f"\033[96mInitial safe square revealed at ({y},{x})\033[0m")
    while True:
        print_grid(grid, opened, marks)
        try:
            move = input("Enter cell to open as y,x or mark as 'm y,x n' (e.g. 2,3 or m 2,3 1): ")
            if move.strip().lower() == 'give up':
                print_grid(grid, opened, marks, give_up=True, reveal_all=True)
                print('\033[93mYou gave up! All bombs and numbers revealed.\033[0m')
                break
            if move.startswith('m '):
                _, cell, n = move.split()
                y, x = map(int, cell.strip().split(','))
                if not (0 <= y < height and 0 <= x < width):
                    print('Out of bounds!')
                    continue
                if marks[y][x] == n:
                    marks[y][x] = None
                else:
                    marks[y][x] = n
                continue
            y, x = map(int, move.strip().split(','))
            if not (0 <= y < height and 0 <= x < width):
                print('Out of bounds!')
                continue
            if grid[y][x] == '*':
                opened[y][x] = True
                print_grid(grid, opened, marks)
                print('\033[91mBOOM! You hit a bomb!\033[0m')
                break
            open_cell(grid, opened, y, x)
            if check_win(grid, opened):
                print_grid(grid, opened, marks, win=True)
                print('\033[92mCongratulations, you win!\033[0m')
                break
        except Exception as e:
            print('Invalid input:', e)

if __name__ == '__main__':
    main()