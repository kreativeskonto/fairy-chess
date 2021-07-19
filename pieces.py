from enum import Enum
from util import *


class Kind(Enum):
    PAWN = "Pawn"
    CENTURION = "Centurion"
    KNIGHT = "Knight"
    BISHOP = "Bishop"
    ROOK = "Rook"
    QUEEN = "Queen"
    KING = "King"
    ELEPHANT = "Elephant"
    CAMEL = "Camel"
    DRAGONWOMAN = "Dragonwoman"
    MACHINE = "Machine"
    UNICORN = "Unicorn"
    DIABLO = "Diablo"
    ANTILOPE = "Antilope"
    BULL = "Bull"
    BUFFALO = "Buffalo"
    LION = "Lion"
    BUFFOON = "Buffoon"
    SHIP = "Ship"
    RHINOCEROS = "Rhinoceros"
    GRYPHON = "Gryphon"
    CANNON = "Cannon"
    BOW = "Bow"
    STAR = "Star"


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
        if self.kind != Kind.PAWN:
            return []
        elif self.side == 1:
            return set(range(BOARD_SIZE ** 2 - BOARD_SIZE, BOARD_SIZE ** 2))
        else:
            return set(range(BOARD_SIZE))

    def move(self, square):
        self.square = square
        self.x, self.y = to_coords(square)

    def move_and_capture_squares(self, board, check_check=True, check_side=False):
        if check_side and self.side != board.turn:
            return set(), set()

        if self.kind == Kind.ROOK:
            moves, captures = board.ray(self.side, self.square, DIRS_ROOK)

        elif self.kind == Kind.BISHOP:
            moves, captures = board.ray(self.side, self.square, DIRS_BISHOP)

        elif self.kind == Kind.QUEEN:
            moves, captures = board.ray(self.side, self.square, DIRS_QUEEN)

        elif self.kind == Kind.KING:
            moves, captures = board.ray(self.side, self.square, DIRS_QUEEN, max_length=1)

        elif self.kind == Kind.BUFFOON:
            moves, captures = board.ray(self.side, self.square, DIRS_QUEEN, max_length=1)

        elif self.kind == Kind.KNIGHT:
            moves, captures = board.knights_move(self.side, self.square)

        elif self.kind == Kind.ELEPHANT:
            move1, cap1 = board.ray(self.side, self.square, DIRS_BISHOP, max_length=1)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(2, 2))
            moves, captures = move1 | move2, cap1 | cap2

        elif self.kind == Kind.MACHINE:
            move1, cap1 = board.ray(self.side, self.square, DIRS_ROOK, max_length=1)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(2, 0))
            moves, captures = move1 | move2, cap1 | cap2

        elif self.kind == Kind.CAMEL:
            moves, captures = board.knights_move(self.side, self.square, ab=(3, 1))

        elif self.kind == Kind.DRAGONWOMAN:
            move1, cap1 = board.ray(self.side, self.square, DIRS_ROOK)
            move2, cap2 = board.knights_move(self.side, self.square)
            moves, captures = move1 | move2, cap1 | cap2

        elif self.kind == Kind.DIABLO:
            move1, cap1 = board.ray(self.side, self.square, DIRS_BISHOP)
            move2, cap2 = board.knights_move(self.side, self.square)
            moves, captures = move1 | move2, cap1 | cap2

        elif self.kind == Kind.UNICORN:
            move1, cap1 = board.ray(self.side, self.square, DIRS_QUEEN)
            move2, cap2 = board.knights_move(self.side, self.square)
            moves, captures = move1 | move2, cap1 | cap2

        elif self.kind == Kind.BULL:
            moves, captures = board.knights_move(self.side, self.square, ab=(3, 2))

        elif self.kind == Kind.ANTILOPE:
            move1, cap1 = board.knights_move(self.side, self.square, ab=(2, 2))
            move2, cap2 = board.knights_move(self.side, self.square, ab=(3, 3))
            move3, cap3 = board.knights_move(self.side, self.square, ab=(2, 0))
            move4, cap4 = board.knights_move(self.side, self.square, ab=(3, 0))
            moves, captures = move1 | move2 | move3 | move4, cap1 | cap2 | cap3 | cap4

        elif self.kind == Kind.BUFFALO:
            move1, cap1 = board.knights_move(self.side, self.square)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(3, 1))
            move3, cap3 = board.knights_move(self.side, self.square, ab=(3, 2))
            moves, captures = move1 | move2 | move3, cap1 | cap2 | cap3

        elif self.kind == Kind.LION:
            move1, cap1 = board.ray(self.side, self.square, DIRS_QUEEN, max_length=1)
            move2, cap2 = board.knights_move(self.side, self.square, ab=(2, 0))
            move3, cap3 = board.knights_move(self.side, self.square)
            move4, cap4 = board.knights_move(self.side, self.square, ab=(2, 2))
            moves, captures = move1 | move2 | move3 | move4, cap1 | cap2 | cap3 | cap4

        elif self.kind == Kind.PAWN:
            if self.side == 1:
                move, _ = board.ray(self.side, self.square, [DIR_NORTH], max_length=2)
                _, cap = board.ray(self.side, self.square, [DIR_NORTHEAST, DIR_NORTHWEST], max_length=1)
            else:
                move, _ = board.ray(self.side, self.square, [DIR_SOUTH], max_length=2)
                _, cap = board.ray(self.side, self.square, [DIR_SOUTHEAST, DIR_SOUTHWEST], max_length=1)
            moves, captures = move, cap

        elif self.kind == Kind.CENTURION:
            if self.side == 1:
                move1, _ = board.ray(self.side, self.square, [DIR_NORTH], max_length=2)
                move2, cap = board.ray(self.side, self.square, [DIR_NORTHEAST, DIR_NORTHWEST], max_length=1)
            else:
                move1, _ = board.ray(self.side, self.square, [DIR_SOUTH], max_length=2)
                move2, cap = board.ray(self.side, self.square, [DIR_SOUTHEAST, DIR_SOUTHWEST], max_length=1)
            moves, captures = move1 | move2, cap

        elif self.kind == Kind.SHIP:
            move1, cap1 = board.ray(self.side, to_square((self.x - 1, self.y)), [DIR_NORTH, DIR_SOUTH]) if self.x > 0 else (set(), set())
            move2, cap2 = board.ray(self.side, to_square((self.x + 1, self.y)), [DIR_NORTH, DIR_SOUTH]) if self.x < board.size else (set(), set())
            moves, captures = move1 | move2, cap1 | cap2

        elif self.kind == Kind.RHINOCEROS:
            move1, cap1 = board.ray(self.side, to_square((self.x - 1, self.y)), [DIR_NORTHWEST, DIR_SOUTHWEST]) if self.x > 0 else (set(), set())
            move2, cap2 = board.ray(self.side, to_square((self.x + 1, self.y)), [DIR_NORTHEAST, DIR_SOUTHEAST]) if self.x < board.size else (set(), set())
            move3, cap3 = board.ray(self.side, to_square((self.x, self.y - 1)), [DIR_SOUTHWEST, DIR_SOUTHEAST]) if self.y > 0 else (set(), set())
            move4, cap4 = board.ray(self.side, to_square((self.x, self.y + 1)), [DIR_NORTHWEST, DIR_NORTHEAST]) if self.y < board.size else (set(), set())
            moves, captures = move1 | move2 | move3 | move4, cap1 | cap2 | cap3 | cap4

        elif self.kind == Kind.GRYPHON:
            move1, cap1 = board.ray(self.side, to_square((self.x - 1, self.y)), [DIR_NORTH, DIR_SOUTH]) if self.x > 0 else (set(), set())
            move2, cap2 = board.ray(self.side, to_square((self.x + 1, self.y)), [DIR_NORTH, DIR_SOUTH]) if self.x < board.size else (set(), set())
            move3, cap3 = board.ray(self.side, to_square((self.x, self.y - 1)), [DIR_WEST, DIR_EAST]) if self.y > 0 else (set(), set())
            move4, cap4 = board.ray(self.side, to_square((self.x, self.y + 1)), [DIR_WEST, DIR_EAST]) if self.y < board.size else (set(), set())
            moves, captures = move1 | move2 | move3 | move4, cap1 | cap2 | cap3 | cap4

        elif self.kind == Kind.CANNON:
            moves, captures = board.artillery(self.side, self.square, DIRS_ROOK)

        elif self.kind == Kind.BOW:
            moves, captures = board.artillery(self.side, self.square, DIRS_BISHOP)

        else:  # self.kind == PIECE_STAR
            moves, captures = board.artillery(self.side, self.square, DIRS_QUEEN)

        if not check_check:
            return moves, captures

        valid_moves, valid_captures = set(), set()
        for to_sq in moves:
            if board.check_move_for_check(self.square, to_sq):
                valid_moves.add(to_sq)

        for to_sq in captures:
            if board.check_move_for_check(self.square, to_sq):
                valid_captures.add(to_sq)

        return valid_moves, valid_captures
