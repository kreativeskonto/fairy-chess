from pieces import *
from util import *


class Board:
    def __init__(self, turn=1):
        self.size = BOARD_SIZE
        self.squares = [None] * (self.size ** 2)
        self.turn = turn

    def clear(self):
        self.squares = [None] * (self.size ** 2)

    def create_piece(self, side, kind, square=0, xy=None):
        piece = Piece(side, kind, square, xy)
        self.squares[piece.square] = piece

    def setup_file(self, filename):
        with open("positions/" + filename) as file:
            content = file.readlines()

        self.clear()
        side = 1
        for line in content:
            if line == "\n":
                side = 2
                continue
            kind_name, square = line.strip().split()
            self.create_piece(side, Kind[kind_name], int(square))

    def printout(self):
        lines = []
        digits = len(str(self.size ** 2 - 1))
        for y in range(self.size):
            line = ""
            for x in range(self.size):
                sq = to_square((x,y))
                piece = self.squares[sq]
                if piece is None:
                    char = "  "
                else:
                    char = piece.kind
                line += f"{' ' * (digits - len(str(sq)))}{sq}:{char} "
            lines.append(line)

        for line in reversed(lines):
            print(line)

    def ray(self, side, origin, directions, max_length=-1):
        move_squares = set()
        capture_squares = set()
        for direction in directions:
            increment, border = direction
            square = origin
            length = 0
            while square % self.size != border and length != max_length:
                square += increment
                length += 1
                if 0 <= square < (self.size ** 2):
                    if self.squares[square] is None:
                        move_squares.add(square)
                        continue
                    elif self.squares[square].side != side:
                        capture_squares.add(square)
                break
        return move_squares, capture_squares

    def knights_move(self, side, origin, ab=(2, 1)):
        move_squares = set()
        capture_squares = set()
        ox, oy = to_coords(origin)
        a, b = ab
        for d1 in {a, -a}:
            for d2 in {b, -b}:
                for x, y in {(ox + d1, oy + d2), (ox + d2, oy + d1)}:
                    if 0 <= x < self.size and 0 <= y < self.size:
                        square = to_square((x, y))
                        if self.squares[square] is None:
                            move_squares.add(square)
                        elif self.squares[square].side != side:
                            capture_squares.add(square)
        return move_squares, capture_squares

    def artillery(self, side, origin, directions):
        move_squares = set()
        capture_squares = set()
        for direction in directions:
            increment, border = direction
            square = origin
            block = 0
            while square % self.size != border and block < 2:
                square += increment
                if 0 <= square < (self.size ** 2):
                    if self.squares[square] is None:
                        if block == 0:
                            move_squares.add(square)
                    elif self.squares[square].side != side:
                        if block == 1:
                            capture_squares.add(square)
                        block += 1
                    else:
                        block += 1
                else:
                    break
        return move_squares, capture_squares

    def possible_moves(self, square=0, xy=None):
        if xy is not None:
            square = to_square(xy)
        piece = self.squares[square]
        if piece is None:
            return None
        return piece.move_and_capture_squares(self)

    def move(self, from_sq, to_sq):
        moves = self.possible_moves(from_sq)
        if moves is None:
            return False
        moves = moves[0] | moves[1]
        piece = self.squares[from_sq]
        if to_sq in moves:
            piece.move(to_sq)
            self.squares[to_sq] = piece
            self.squares[from_sq] = None
            return True
        return False

    def play_game(self):
        self.printout()
        while any(self.squares):
            move_input = input("From where to where? > ")
            from_sq, to_sq = (int(num) for num in move_input.strip().split())
            if self.move(from_sq, to_sq):
                self.turn = 3 - self.turn
                self.printout()
        print("GAME OVER")


if __name__ == "__main__":
    board = Board()
    board.setup_file("default_moab.pos")
    board.play_game()
