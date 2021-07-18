import sys
import os
import pygame
from pygame import Color, Rect

from board import Board
from pieces import Kind
from util import BOARD_SIZE, to_square


BLACK = Color(0, 0, 0)
WHITE = Color(255, 255, 255)
SMOOTH = False
THEMES = {
    'Chess.com': {
        'background': Color('#333333'),
        'white': Color('#eeeed2'),
        'black': Color('#769656'),
        'move': Color('#baca2b'),
        'capture': Color('#ec7e6a'),
    }
}


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption('Fairy chess')

        self.size = BOARD_SIZE
        self.theme = THEMES['Chess.com']
        self.padding = 20

        self.surface = pygame.display.set_mode((800, 670), flags=pygame.RESIZABLE)

        self.textures = {}
        for path, _, files in os.walk('pieces'):
            for file in files:
                filepath = os.path.join(path, file)
                kind = Kind[os.path.splitext(file)[0].upper()]
                side = 1 if 'white' in path else 2
                self.textures[(side, kind)] = pygame.image.load(filepath).convert_alpha()

        self.board_rect: Rect = None
        self.square_rect: Rect = None
        self.scaled = {}
        self.resize()

        self.board = Board()
        self.board.setup_file("default_moab.pos")

        self.dragged = None
        self.moves = []
        self.captures = []

    def run(self):
        while True:
            event = pygame.event.wait()
            self.update(event)

            for event in pygame.event.get():
                self.update(event)

            self.draw()

    def update(self, event):
        if event.type == pygame.QUIT:
            sys.exit()

        elif event.type == pygame.VIDEORESIZE:
            self.resize()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sq = self.hit_test()
            if sq is not None:
                piece = self.board.squares[sq]
                if piece:
                    self.dragged = piece
                    self.moves, self.captures = piece.move_and_capture_squares(self.board, check_side=True)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged:
                target = self.hit_test()
                if target is not None:
                    feedback = self.board.move(self.dragged.square, target)
                    if feedback == "Stalemate":
                        pass
                    if feedback == "Checkmate":
                        pass

                self.dragged = None

    def draw(self):
        self.surface.fill(self.theme['background'])

        for x in range(self.size):
            for y in range(self.size):
                sq = to_square((x, y))
                if self.dragged and sq in self.moves:
                    key = 'move'
                elif self.dragged and sq in self.captures:
                    key = 'capture'
                elif (x + y) % 2:
                    key = 'white'
                else:
                    key = 'black'

                square = self.square_rect.move(x * self.square_rect.width, -y * self.square_rect.height)
                pygame.draw.rect(self.surface, self.theme[key], square)

                piece = self.board.squares[sq]
                if piece and piece != self.dragged:
                    self.draw_piece(piece, square)

        if self.dragged:
            x, y = pygame.mouse.get_pos()
            x -= self.square_rect.width // 2
            y -= self.square_rect.height // 2
            self.draw_piece(self.dragged, (x, y))

        pygame.display.update()

    def draw_piece(self, piece, where):
        try:
            bitmap = self.scaled[piece.side, piece.kind]
            self.surface.blit(bitmap, where)
        except KeyError:
            pass

    def resize(self):
        # Determine the size of a screen-filling, slightly padded board with
        # pixel-aligned squares.
        w, h = pygame.display.get_window_size()
        b = min(w, h) - self.padding
        b -= b % self.size
        s = b // self.size

        # Rectangle for the whole board.
        self.board_rect = Rect(0, 0, b, b)
        self.board_rect.center = w / 2, h / 2

        # Rectangle for the first square.
        self.square_rect = Rect(0, 0, s, s)
        self.square_rect.bottomleft = self.board_rect.bottomleft

        # Scaled piece textures.
        f = pygame.transform.smoothscale if SMOOTH else pygame.transform.scale
        self.scaled = {k: f(v, (s, s)) for k, v in self.textures.items()}

    def hit_test(self):
        mx, my = pygame.mouse.get_pos()
        if self.board_rect.collidepoint(mx, my):
            x = int((mx - self.board_rect.left) / self.square_rect.width)
            y = int((self.board_rect.bottom - my) / self.square_rect.height)
            return to_square((x, y))


if __name__ == '__main__':
    Game().run()
