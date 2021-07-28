BOARD_SIZE = 16
TIME = 3600


def to_coords(square):
    return square % BOARD_SIZE, square // BOARD_SIZE


def to_square(xy):
    x, y = xy
    return y * BOARD_SIZE + x


def format_time(secs):
    hrs = secs // 3600
    mins = (secs % 3600) // 60
    mins = "0" + str(mins) if mins < 10 else str(mins)
    secs = secs % 60
    secs = "0" + str(secs) if secs < 10 else str(secs)
    return f"{hrs}:{mins}:{secs}" if hrs > 0 else f"{mins}:{secs}"

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
