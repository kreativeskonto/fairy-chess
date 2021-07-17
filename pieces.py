from util import *

PIECE_PAWN = "Pw"
PIECE_CENTURION = "Ct"
PIECE_KNIGHT = "Kn"
PIECE_BISHOP = "Bi"
PIECE_ROOK = "Rk"
PIECE_QUEEN = "Qu"
PIECE_KING = "Ki"
PIECE_ELEPHANT = "El"
PIECE_CAMEL = "Cm"
PIECE_DRAGONWOMAN = "Dw"
PIECE_MACHINE = "Ma"
PIECE_UNICORN = "Uc"
PIECE_DIABLO = "Di"
PIECE_ANTILOPE = "At"
PIECE_BULL = "Bl"
PIECE_BUFFALO = "Bf"
PIECE_LION = "Li"
PIECE_BUFFOON = "Bu"
PIECE_SHIP = "Sh"
PIECE_RHINOCEROS = "Rh"
PIECE_GRYPHON = "Gy"
PIECE_CANNON = "Cn"
PIECE_BOW = "Bw"
PIECE_STAR = "St"


class Piece:
    def __init__(self, side, kind, square=0, xy=None):
        self.side = side
        self.kind = kind
        if xy is None:
            self.square = square
            self.x, self.y = to_coords(self.square)
        else:
            self.x, self.y = xy
            self.square = to_square(xy)

    def promotion_squares(self):
        if self.kind != PIECE_PAWN:
            return []
        elif self.side == 1:
            return set(range(BOARD_SIZE ** 2 - BOARD_SIZE, BOARD_SIZE ** 2))
        else:
            return set(range(BOARD_SIZE))

    def move(self, square):
        self.square = square
        self.x, self.y = to_coords(square)

    def move_and_capture_squares(self, board):
        if self.kind == PIECE_ROOK:
            return board.ray(self.side, self.square, DIRS_ROOK)

        elif self.kind == PIECE_BISHOP:
            return board.ray(self.side, self.square, DIRS_BISHOP)

        elif self.kind == PIECE_QUEEN:
            return board.ray(self.side, self.square, DIRS_QUEEN)

        elif self.kind == PIECE_KING:
            return board.ray(self.side, self.square, DIRS_QUEEN, max_length=1)

        elif self.kind == PIECE_BUFFOON:
            return board.ray(self.side, self.square, DIRS_QUEEN, max_length=1)

        elif self.kind == PIECE_KNIGHT:
            return board.knights_move(self.side, self.square)

        elif self.kind == PIECE_ELEPHANT:
            move1, cap1 = board.ray(self.side, self.square, DIRS_BISHOP, max_length=1)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(2, 2))
            return move1.union(move2), cap1.union(cap2)

        elif self.kind == PIECE_MACHINE:
            move1, cap1 = board.ray(self.side, self.square, DIRS_ROOK, max_length=1)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(2, 0))
            return move1.union(move2), cap1.union(cap2)

        elif self.kind == PIECE_CAMEL:
            return board.knights_move(self.side, self.square, ab=(3, 1))

        elif self.kind == PIECE_DRAGONWOMAN:
            move1, cap1 = board.ray(self.side, self.square, DIRS_ROOK)
            move2, cap2 = board.knights_move(self.side, self.square)
            return move1.union(move2), cap1.union(cap2)

        elif self.kind == PIECE_DIABLO:
            move1, cap1 = board.ray(self.side, self.square, DIRS_BISHOP)
            move2, cap2 = board.knights_move(self.side, self.square)
            return move1.union(move2), cap1.union(cap2)

        elif self.kind == PIECE_UNICORN:
            move1, cap1 = board.ray(self.side, self.square, DIRS_QUEEN)
            move2, cap2 = board.knights_move(self.side, self.square)
            return move1.union(move2), cap1.union(cap2)

        elif self.kind == PIECE_BULL:
            return board.knights_move(self.side, self.square, ab=(3, 2))

        elif self.kind == PIECE_ANTILOPE:
            move1, cap1 = board.knights_move(self.side, self.square, ab=(2, 2))
            move2, cap2 = board.knights_move(self.side, self.square, ab=(3, 3))
            move3, cap3 = board.knights_move(self.side, self.square, ab=(2, 0))
            move4, cap4 = board.knights_move(self.side, self.square, ab=(3, 0))
            return move1.union(move2).union(move3).union(move4), cap1.union(cap2).union(cap3).union(cap4)

        elif self.kind == PIECE_BUFFALO:
            move1, cap1 = board.knights_move(self.side, self.square)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(3, 1))
            move3, cap3 = board.knights_move(self.side, self.square, ab=(3, 2))
            return move1.union(move2).union(move3), cap1.union(cap2).union(cap3)

        elif self.kind == PIECE_LION:
            move1, cap1 = board.ray(self.side, self.square, DIRS_QUEEN, max_length=1)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(2, 0))
            move3, cap3 = board.knights_move(self.side, self.square)
            move4, cap4 = board.knights_move(self.side, self.square, ab=(2, 2))
            return move1.union(move2).union(move3).union(move4), cap1.union(cap2).union(cap3).union(cap4)

        elif self.kind == PIECE_PAWN:
            if self.side == 1:
                move, _ = board.ray(self.side, self.square, [DIR_NORTH], max_length=2)
                _, cap = board.ray(self.side, self.square, [DIR_NORTHEAST, DIR_NORTHWEST], max_length=1)
            else:
                move, _ = board.ray(self.side, self.square, [DIR_SOUTH], max_length=2)
                _, cap = board.ray(self.side, self.square, [DIR_SOUTHEAST, DIR_SOUTHWEST], max_length=1)
            return move, cap

        elif self.kind == PIECE_CENTURION:
            if self.side == 1:
                move1, _ = board.ray(self.side, self.square, [DIR_NORTH], max_length=2)
                move2, cap = board.ray(self.side, self.square, [DIR_NORTHEAST, DIR_NORTHWEST], max_length=1)
            else:
                move1, _ = board.ray(self.side, self.square, [DIR_SOUTH], max_length=2)
                move2, cap = board.ray(self.side, self.square, [DIR_SOUTHEAST, DIR_SOUTHWEST], max_length=1)
            return move1.union(move2), cap

        elif self.kind == PIECE_SHIP:
            move1, cap1 = board.ray(self.side, to_square((self.x - 1, self.y)), [DIR_NORTH, DIR_SOUTH]) if self.x > 0 else (set(), set())
            move2, cap2 = board.ray(self.side, to_square((self.x + 1, self.y)), [DIR_NORTH, DIR_SOUTH]) if self.x < board.size else (set(), set())
            return move1.union(move2), cap1.union(cap2)

        elif self.kind == PIECE_RHINOCEROS:
            move1, cap1 = board.ray(self.side, to_square((self.x - 1, self.y)), [DIR_NORTHWEST, DIR_SOUTHWEST]) if self.x > 0 else (set(), set())
            move2, cap2 = board.ray(self.side, to_square((self.x + 1, self.y)), [DIR_NORTHEAST, DIR_SOUTHEAST]) if self.x < board.size else (set(), set())
            move3, cap3 = board.ray(self.side, to_square((self.x, self.y - 1)), [DIR_SOUTHWEST, DIR_SOUTHEAST]) if self.y > 0 else (set(), set())
            move4, cap4 = board.ray(self.side, to_square((self.x, self.y + 1)), [DIR_NORTHWEST, DIR_NORTHEAST]) if self.y < board.size else (set(), set())
            return move1.union(move2).union(move3).union(move4), cap1.union(cap2).union(cap3).union(cap4)

        elif self.kind == PIECE_GRYPHON:
            move1, cap1 = board.ray(self.side, to_square((self.x - 1, self.y)), [DIR_NORTH, DIR_SOUTH]) if self.x > 0 else (set(), set())
            move2, cap2 = board.ray(self.side, to_square((self.x + 1, self.y)), [DIR_NORTH, DIR_EAST]) if self.x < board.size else (set(), set())
            move3, cap3 = board.ray(self.side, to_square((self.x, self.y - 1)), [DIR_WEST, DIR_EAST]) if self.y > 0 else (set(), set())
            move4, cap4 = board.ray(self.side, to_square((self.x, self.y + 1)), [DIR_WEST, DIR_EAST]) if self.y < board.size else (set(), set())
            return move1.union(move2).union(move3).union(move4), cap1.union(cap2).union(cap3).union(cap4)

        elif self.kind == PIECE_CANNON:
            return board.artillery(self.side, self.square, DIRS_ROOK)

        elif self.kind == PIECE_BOW:
            return board.artillery(self.side, self.square, DIRS_BISHOP)

        elif self.kind == PIECE_STAR:
            return board.artillery(self.side, self.square, DIRS_QUEEN)

        return set(), set()
