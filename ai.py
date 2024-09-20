from pieces import Kind, Piece
from board import Board
from util import *
from random import choice as random_pick

MEMORY_FILE_NAME = "ai_memory.board"
DEPTH = 3  # THIS SHOULD BE AN ODD NUMBER

SPACE_VALUE = 1/128
PROMOTION_VALUE = 5

class Reversal():
	def __init__(self, board, squares):
		
		self.en_passant = board.en_passant
		
		self.changes = dict()
		for sq in squares:
			self.memorize(board, sq)
				
	def memorize(self, board, sq):
		piece = board.squares[sq]
		if piece is None:
			self.changes[sq] = None
		else:
			self.changes[sq] = (piece.side, piece.kind)


class AiMemoryBoard(Board):
	
	def __init__(self, turn):
		Board.__init__(self, turn)
		self.stack_of_reversals = []
		
		self.side_1_pieces = set()
		self.side_2_pieces = set()
	
	def clear(self):
		Board.clear(self)
		self.stack_of_reversals = []
		
		self.side_1_pieces = set()
		self.side_2_pieces = set()
	
	def get_setup_from_board(self, board):
		
		for sq in range(self.size ** 2):
			piece = board.squares[sq]
			
			if piece is not None:
				new_piece = Piece(piece.side, piece.kind, sq)
				self.squares[sq] = new_piece
				
				if new_piece.side == 1:
					self.side_1_pieces.add(sq)
				else:
					self.side_2_pieces.add(sq)
		
		self.turn = board.turn
		self.en_passant = board.en_passant
		
		self.side_1_worth = board.side_1_worth
		self.side_2_worth = board.side_2_worth
		
	def remove_piece(self, sq):
		piece = self.squares[sq]
		if piece is not None:
			if piece.side == 1:
				self.side_1_worth -= WORTHS[piece.kind.value]
				self.side_1_pieces.remove(sq)
			else:
				self.side_2_worth -= WORTHS[piece.kind.value]
				self.side_2_pieces.remove(sq)
			
			self.squares[sq] = None
		
	def create_piece(self, side, kind, square=0, xy=None):
		sq = square if xy is None else to_square(xy)
		self.remove_piece(sq)
		
		self.squares[sq] = Piece(side, kind, sq)
		
		if side == 1:
			self.side_1_worth += WORTHS[kind.value]
			self.side_1_pieces.add(sq)
		else:
			self.side_2_worth += WORTHS[kind.value]
			self.side_2_pieces.add(sq)
			
	def place_piece(self, piece, square=0, xy=None):
		sq = square if xy is None else to_square(xy)
		self.remove_piece(sq)
		
		self.squares[sq] = piece
		
		if piece.side == 1:
			self.side_1_worth += WORTHS[piece.kind.value]
			self.side_1_pieces.add(sq)
		else:
			self.side_2_worth += WORTHS[piece.kind.value]
			self.side_2_pieces.add(sq)
		
	def reset(self):
		while self.stack_of_reversals:
			self.revert()
		
	def move(self, from_sq, to_sq, promote_idx=0):
		reversal = Reversal(self, {from_sq, to_sq})
		piece = self.squares[from_sq]
		
		# REMOVE PIECE THAT IS TAKEN EN PASSANT
		if self.en_passant[0] >= 0:
			if to_sq == self.en_passant[0] and piece.kind in [Kind.PAWN, Kind.CENTURION]:
				reversal.memorize(self, self.en_passant[1])
				self.remove_piece(self.en_passant[1])
				
		piece.move(to_sq)
		self.place_piece(piece, to_sq)
		self.remove_piece(from_sq)  
		
		passant = (from_sq + to_sq) // 2
		if piece.kind in [Kind.PAWN, Kind.CENTURION] and abs(from_sq - to_sq) == BOARD_SIZE * 2:
			self.en_passant = (passant, to_sq)
		else:
			self.en_passant = (-1, -1)

		if to_sq in piece.promotion_squares():
			options = piece.promotion_pieces()
			self.change_piece_kind(piece.square, options[promote_idx])

		self.turn = 3 - self.turn
		self.stack_of_reversals.append(reversal)
		
	def revert(self):
		reversal = self.stack_of_reversals.pop()
		self.en_passant = reversal.en_passant
		
		for sq in reversal.changes:
			entry = reversal.changes[sq]
			if entry is None:
				self.remove_piece(sq)
			else:
				side, kind = entry
				self.create_piece(side, kind, sq)
				
		self.turn = 3 - self.turn
				
	def evaluate(self):
		"""
		Outputs a tuple of numbers (a, b, c).
		a = Checkmate.
		b = Value of pieces.
		c = Attacks on enemy pieces.
		d = Negative value of undefended pieces.
		e = Nearness of promoting pieces to their promotion squares.
		f = Scope.
		"""
		
		# CHECKMATE ECLIPSES ALL
		if self.check_mate():
			if self.turn == 1:
				return (-1, 0, 0, 0, 0, 0)
			else:
				return (1, 0, 0, 0, 0, 0)
				
		turn_player_pieces = self.side_1_pieces if self.turn == 1 else self.side_2_pieces
		other_player_pieces = self.side_2_pieces if self.turn == 1 else self.side_1_pieces
		
		# CREATE DATA ABOUT MOVES, CAPTURES AND DEFENDED SQUARES
		possible_moves = dict()
		possible_captures = dict()
		cheapest_attackers = dict()
		defended_pieces = set()
		
		for sq in self.side_1_pieces | self.side_2_pieces:
			piece = self.squares[sq]
			moves, captures = piece.move_and_capture_squares(self, check_check=False)
			defenses = piece.defended_pieces(self)
			
			possible_moves[sq] = moves
			for to_sq in captures:
				if to_sq not in cheapest_attackers:
					cheapest_attackers[to_sq] = WORTHS[piece.kind.value]
				else:
					cheapest_attackers[to_sq] = min(cheapest_attackers[to_sq], WORTHS[piece.kind.value])
			defended_pieces = defended_pieces | defenses
		
		# INITIALIZE SCORE
		score_b = self.side_1_worth - self.side_2_worth
		score_c = 0
		score_d = 0
		score_e = 0
		score_f = 0
		
		# HANDLE TURN PLAYER UNDEFENDED PIECES
		turn_player_weaknesses = []
		
		for sq in turn_player_pieces:
			piece = self.squares[sq]
			worth = WORTHS[piece.kind.value]
			defended = sq in defended_pieces
			attacked = sq in cheapest_attackers
			
			if attacked and defended:
				if worth > cheapest_attackers[sq]:
					turn_player_weaknesses.append(worth - cheapest_attackers[sq])
			
			elif attacked and not defended:
				turn_player_weaknesses.append(worth)
		
		if turn_player_weaknesses:
			turn_player_weaknesses.remove(max(turn_player_weaknesses))
		
		# HANDLE NON_TURN PLAYER UNDEFENDED PIECES
		other_player_weaknesses = []
		other_player_undefended = []
		
		for sq in other_player_pieces:
			piece = self.squares[sq]
			worth = WORTHS[piece.kind.value]
			defended = sq in defended_pieces
			attacked = sq in cheapest_attackers
			
			if attacked and defended:
				if worth > cheapest_attackers[sq]:
					other_player_weaknesses.append(worth - cheapest_attackers[sq])
			
			elif attacked and not defended:
				other_player_weaknesses.append(worth)
			
			elif piece.side == 1 and sq >= 2 * BOARD_SIZE: 	
				if not attacked and not defended:
					other_player_undefended.append(worth)
					
			elif piece.side == 2 and sq < BOARD_SIZE * (BOARD_SIZE - 2): 	
				if not attacked and not defended:
					other_player_undefended.append(worth)
		
		# UPDATE_SCORE
		if self.turn == 1:
			score_b += sum(other_player_weaknesses)
			score_c -= sum(turn_player_weaknesses)
			score_d += sum(other_player_undefended)
		else:
			score_b -= sum(other_player_weaknesses)
			score_c += sum(turn_player_weaknesses)
			score_d -= sum(other_player_undefended)
		
		# ADD NEARNESS OF PIECES TO THEIR PROMOTION SQUARES
		for sq in self.side_1_pieces | self.side_2_pieces:
			piece = self.squares[sq]
			
			if piece.kind in [Kind.PAWN, Kind.CENTURION]:
				if piece.side == 1:
					score_e += 2**-(BOARD_SIZE - 1 - piece.y)
				else:
					score_e -= 2**-piece.y

			elif piece.kind == Kind.BUFFOON:
				if piece.side == 1:
					score_e += 2**-abs((BOARD_SIZE // 2) - piece.y)
				else:
					score_e -= 2**-abs(piece.y - (BOARD_SIZE // 2 - 1))

			elif piece.kind == Kind.SHIP:
				if piece.side == 1:
					score_e += 2**-min(abs(piece.x - 1), abs(piece.x - (BOARD_SIZE - 2)))
				else:
					score_e -= 2**-min(abs(piece.x - 1), abs(piece.x - (BOARD_SIZE - 2)))
		
		# ADD SCORE FOR SPACE
		for sq in self.side_1_pieces:
			if self.squares[sq].kind not in (Kind.BOW, Kind.CANNON, Kind.STAR, Kind.KING):
				score_f += len(possible_moves[sq])
			
		for sq in self.side_2_pieces:
			if self.squares[sq].kind not in (Kind.BOW, Kind.CANNON, Kind.STAR, Kind.KING):
				score_f -= len(possible_moves[sq])
			
		return (0, score_b, score_c, score_d, score_e, score_f)
		
	def find_best_move(self):
		all_moves = set()
		all_captures = set()
		
		scores = dict()
		
		# MAKE SETS WITH MOVES AND CAPTURES
		turn_player_pieces = self.side_1_pieces if self.turn == 1 else self.side_2_pieces
		
		for sq in turn_player_pieces:
			moves, captures = self.possible_moves(sq)
			for to_sq in moves:
				all_moves.add((sq, to_sq))
			for to_sq in captures:
				all_captures.add((sq, to_sq))
		
		# EVALUATE MOVES
		for sq, to_sq in all_moves | all_captures:
			self.move(sq, to_sq)
			score = self.evaluate()
			scores[(sq, to_sq)] = score
			print(to_coords(sq), "->", to_coords(to_sq) ,":", score)
			self.revert()

		# CHOOSE A RANDOM HIGHEST SCORING MOVE
		if self.turn == 1:
			best_score = max(scores.values(), key=score_sort_key)
		else:
			best_score = min(scores.values(), key=score_sort_key)
		best_move = random_pick(tuple(key for key in scores if scores[key] == best_score))
		
		print("--- Decided on", to_coords(best_move[0]), "->", to_coords(best_move[1]) ,":", best_score, "---")
		return best_move

def score_sort_key(score):
	a, b, c, d, e, f = score
	return (a, b, c, d + PROMOTION_VALUE * e + SPACE_VALUE * f)

def get_ai_move(board):
	turn = board.turn
	
	memory_board = AiMemoryBoard(turn)
	memory_board.get_setup_from_board(board)
	
	return memory_board.find_best_move()
	
def get_ai_promotion(board, sq, kinds):
	side = board.squares[sq].side
	
	best_score = None
	best_kind = Kind.QUEEN
	
	for kind in kinds:
		turn = board.turn
		
		memory_board = AiMemoryBoard(turn)
		memory_board.get_setup_from_board(board)
		memory_board.change_piece_kind(sq, kind)
		score = memory_board.evaluate()
		
		if best_score is None:
			best_score = score
			best_kind = kind
			
		elif side == 1 and score_sort_key(score) > score_sort_key(best_score):
			best_score = score
			best_kind = kind
			
		elif side == 2 and score_sort_key(score) < score_sort_key(best_score):
			best_score = score
			best_kind = kind

	return best_kind
		
		
