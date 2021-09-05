BOARD_SIZE = 16
TIME = 3600


def to_coords(square):
    return square % BOARD_SIZE, square // BOARD_SIZE


def to_square(xy):
    x, y = xy
    return y * BOARD_SIZE + x


def format_time(secs):
    prefix = '-' if secs < 0 else ''
    mins = abs(secs) // 60
    secs = abs(secs) % 60
    return f"{prefix}{mins:02d}:{secs:02d}"

DIR_NORTH = (BOARD_SIZE, None)
DIR_NORTHWEST = (BOARD_SIZE - 1, 0)
DIR_NORTHEAST = (BOARD_SIZE + 1, BOARD_SIZE - 1)
DIR_WEST = (-1, 0)
DIR_EAST = (1, BOARD_SIZE - 1)
DIR_SOUTH = (-BOARD_SIZE, None)
DIR_SOUTHWEST = (-BOARD_SIZE - 1, 0)
DIR_SOUTHEAST = (-BOARD_SIZE + 1, BOARD_SIZE - 1)

DIRS_ROOK = [DIR_NORTH, DIR_SOUTH, DIR_EAST, DIR_WEST]
DIRS_BISHOP = [DIR_NORTHWEST, DIR_SOUTHWEST, DIR_NORTHEAST, DIR_SOUTHEAST]
DIRS_QUEEN = DIRS_ROOK + DIRS_BISHOP
