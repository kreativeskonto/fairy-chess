from pieces import *
from util import *

class Board:
    def __init__(self, turn=1):
        self.size = BOARD_SIZE
        self.squares = [None] * (self.size ** 2)
        self.turn = turn
        
        self.finished = False
        self.en_passant = (-1, -1)  # This is a pair (sq1, sq2).
                                    # The piece at sq2 can be taken en passant as though it only moved to sq1.
        self.side_1_worth = 0
        self.side_2_worth = 0

    def clear(self):
        self.squares = [None] * (self.size ** 2)
        self.turn = 1
        
        self.en_passant = (-1, -1)
        self.finished = False
        
        self.side_1_worth = 0
        self.side_2_worth = 0
    
    def remove_piece(self, sq):
        piece = self.squares[sq]
        if piece is not None:
            if piece.side == 1:
                self.side_1_worth -= WORTHS[piece.kind.value]
            else:
                self.side_2_worth -= WORTHS[piece.kind.value]
            self.squares[sq] = None
        
    
    def create_piece(self, side, kind, square=0, xy=None):
        sq = square if xy is None else to_square(xy)
        self.remove_piece(sq)
        
        self.squares[sq] = Piece(side, kind, sq)
        
        if side == 1:
            self.side_1_worth += WORTHS[kind.value]
        else:
            self.side_2_worth += WORTHS[kind.value]
            
    def place_piece(self, piece, square=0, xy=None):
        sq = square if xy is None else to_square(xy)
        self.remove_piece(sq)
        
        self.squares[sq] = piece
        
        if piece.side == 1:
            self.side_1_worth += WORTHS[piece.kind.value]
        else:
            self.side_2_worth += WORTHS[piece.kind.value]
            
    def change_piece_kind(self, sq, new_kind):
        piece = self.squares[sq]
        if piece is None:
            return
        
        if piece.side == 1:
            self.side_1_worth += (WORTHS[new_kind.value] - WORTHS[piece.kind.value])
        else:
            self.side_2_worth += (WORTHS[new_kind.value] - WORTHS[piece.kind.value])
            
        piece.kind = new_kind
        

    def setup_file(self, filename):
        with open(filename) as file:
            content = file.readlines()

        self.clear()
        side = 1
        for line in content:
            if line == "\n":
                side = 2
                continue
            kind_name, square = line.strip().split()
            self.create_piece(side, Kind[kind_name], int(square))

    def write_file(self, filename):
        side1 = []
        side2 = []

        for i, piece in enumerate(self.squares):
            if piece is not None:
                line = f"{piece.kind.value.upper()} {i}\n"
                [side1, side2][piece.side - 1].append(line)

        with open(filename, "w") as file:
            file.writelines(side1)
            file.write("\n")
            file.writelines(side2)
            
    def make_copy(self):
        new_board = Board()
        
        new_board.turn = self.turn
        new_board.en_passant = self.en_passant
        new_board.side_1_worth = self.side_1_worth
        new_board.side_2_worth = self.side_2_worth
        
        for sq in range(self.size ** 2):
            if self.squares[sq] is not None:
                piece = self.squares[sq]
                new_board.squares[sq] = Piece(piece.side, piece.kind, sq)
        return new_board

    def printout(self):
        lines = []
        digits = len(str(self.size ** 2 - 1))
        for y in range(self.size):
            line = ""
            for x in range(self.size):
                sq = to_square((x, y))
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
    
    def move_raw(self, from_sq, to_sq, set_en_passant=True, promote_idx=0, switch_turn=True):
        piece = self.squares[from_sq]
        
        # REMOVE PIECE THAT IS TAKEN EN PASSANT
        if self.en_passant[0] >= 0:
            if to_sq == self.en_passant[0] and piece.kind in [Kind.PAWN, Kind.CENTURION]:
                self.remove_piece(self.en_passant[1])

        piece.move(to_sq)
        self.place_piece(piece, to_sq)
        self.remove_piece(from_sq)  
            
        if set_en_passant:
            passant = (from_sq + to_sq) // 2
            if piece.kind in [Kind.PAWN, Kind.CENTURION] and abs(from_sq - to_sq) == BOARD_SIZE * 2:
                self.en_passant = (passant, to_sq)
            else:
                self.en_passant = (-1, -1)

        if to_sq in piece.promotion_squares():
            options = piece.promotion_pieces()
            self.change_piece_kind(piece.square, options[promote_idx])

        if switch_turn:
            self.turn = 3 - self.turn
        
    
    def possible_moves(self, square=0, xy=None, check_side=False, no_en_passant=False):
        if xy is not None:
            square = to_square(xy)
        piece = self.squares[square]
        if piece is None:
            return None
        return piece.move_and_capture_squares(self, check_side=check_side, no_en_passant=no_en_passant)

    def in_check(self, side=0):
        if side == 0:
            side = self.turn
        for piece in self.squares:
            if piece is not None:
                if piece.side != side:
                    _, captures = piece.move_and_capture_squares(self, check_check=False)
                    for cap in captures:
                        if cap != self.en_passant[0]:
                            if self.squares[cap].kind == Kind.KING:
                                return True
        return False

    def check_move_for_check(self, from_sq, to_sq):  # returns False if the move results in its side being in check.
        piece = self.squares[from_sq]
        if piece is None:
            return False
        
        test_board = self.make_copy()
        test_board.move_raw(from_sq, to_sq)
        
        return not test_board.in_check(piece.side)

    def check_mate(self, side=0):  # output: 0 = no mate, 1 = stalemate, 2 = checkmate
        if side == 0:
            side = self.turn
        for piece in self.squares:
            if piece is not None:
                if piece.side == side:
                    if piece.move_and_capture_squares(self) != (set(), set()):
                        return 0
        self.finished = True
        if self.in_check(side):
            return 2
        return 1
        
    def get_worths(self):
        return self.side_1_worth, self.side_2_worth
        
class DisplayedBoard(Board):
    def __init__(self, turn=1):
        Board.__init__(self, turn)
           
        self.highlighted_squares = tuple()
        self.captured_kind = None
        self.promoting = False
        
    def clear(self):
        Board.clear(self)
        
        self.highlighted_squares = tuple()
        self.captured_kind = None
        self.promoting = False
        
    def move(self, from_sq, to_sq):
        mocap = "Move" if self.squares[to_sq] is None else "Capture"
        
        # LIST ALL POSSIBLE MOVES FOR VERIFICATION
        
        moves = self.possible_moves(from_sq, check_side=True)
        if moves is None:
            return "Invalid", mocap
                
        moves = moves[0] | moves[1]
        
        if to_sq in moves:
            
            piece = self.squares[from_sq]
            
            self.highlighted_squares = (from_sq, to_sq)
            self.captured_kind = None if mocap == "Move" else self.squares[to_sq].kind
        
            # REMOVE PIECE THAT IS TAKEN EN PASSANT
            if self.en_passant[0] >= 0:
                
                if to_sq == self.en_passant[0] and piece.kind in [Kind.PAWN, Kind.CENTURION]:
                    
                    self.highlighted_squares = (*self.highlighted_squares, self.en_passant[1])
                    self.captured_kind = self.squares[self.en_passant[1]].kind
                    self.remove_piece(self.en_passant[1])
                    mocap = "Capture"

            piece.move(to_sq)
            self.place_piece(piece, to_sq)
            self.remove_piece(from_sq)  
            
            # SET NEW EN PASSANT SQUARE IF NECESSARY
            passant = (from_sq + to_sq) // 2
            if piece.kind in [Kind.PAWN, Kind.CENTURION] and abs(from_sq - to_sq) == BOARD_SIZE * 2:
                self.en_passant = (passant, to_sq)
            else:
                self.en_passant = (-1, -1)

            # PROMOTE PIECES
            if to_sq in piece.promotion_squares():
                options = piece.promotion_pieces()
                if len(options) == 1:
                    self.change_piece_kind(piece.square, options[0])
                else:
                    self.promoting = True
                    return options, mocap

            self.turn = 3 - self.turn
            mate = self.check_mate()
            
            if mate == 1:
                return "Stalemate", mocap
            if mate == 2:
                return "Checkmate", mocap
                
            return "Valid", mocap
            
        return "Invalid", mocap
        
    def promote(self, sq, kind):
        piece = self.squares[sq]
        if piece == None:
            return "Invalid"
        if sq not in piece.promotion_squares():
            return "Invalid"
        if kind not in piece.promotion_pieces():
            return "Invalid"
        
        self.change_piece_kind(sq, kind)
        
        self.turn = 3 - self.turn
        mate = self.check_mate()
        
        if mate == 1:
            return "Stalemate"
        if mate == 2:
            return "Checkmate"
            
        return "Valid"


if __name__ == "__main__":
    board = Board()
    board.setup_file("default_moab.pos")
