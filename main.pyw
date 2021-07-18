import sys
import os
import socket

from queue import Empty, Queue
from threading import Thread
from urllib import request

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
from pygame import Color, Rect

from board import Board
from pieces import Kind
from util import BOARD_SIZE, to_square

PORT = 5398
BLACK = Color(0, 0, 0)
WHITE = Color(255, 255, 255)
SMOOTH = False
THEMES = {
    "Chess.com": {
        "background": Color("#333333"),
        "white": Color("#eeeed2"),
        "black": Color("#769656"),
        "move": Color("#baca2b"),
        "capture": Color("#ec7e6a"),
    }
}


class Game:
    def __init__(self, host):
        pygame.init()
        pygame.display.set_caption("Fairy chess")

        self.size = BOARD_SIZE
        self.theme = THEMES["Chess.com"]
        self.padding = 20

        self.surface = pygame.display.set_mode((800, 670), flags=pygame.RESIZABLE)

        self.textures = {}
        for path, _, files in os.walk("pieces"):
            for file in files:
                filepath = os.path.join(path, file)
                kind = Kind[os.path.splitext(file)[0].upper()]
                side = 1 if "white" in path else 2
                self.textures[(side, kind)] = pygame.image.load(filepath).convert_alpha()

        self.board_rect: Rect = None
        self.square_rect: Rect = None
        self.scaled = {}
        self.resize()

        self.board = Board()
        self.board.setup_file("default_moab.pos")
        self.side = 1 if host else 2

        self.dragged = None
        self.moves = []
        self.captures = []

        self.incoming = Queue()
        self.outgoing = Queue()

        self.network = NetworkThread(host, self.incoming, self.outgoing)
        self.network.daemon = True
        self.network.start()

    def run(self):
        while True:
            try:
                item = self.incoming.get(block=False)
                from_sq, to_sq = item
                feedback = self.board.move(from_sq, to_sq)
                if feedback in ("Stalemate", "Checkmate"):
                    print(feedback)
            except Empty:
                pass

            event = pygame.event.wait(50)
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
                if piece and piece.side == self.side:
                    self.dragged = piece
                    self.moves, self.captures = piece.move_and_capture_squares(self.board, check_side=True)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragged:
            target = self.hit_test()
            if target is not None:
                item = (self.dragged.square, target)
                feedback = self.board.move(*item)
                self.outgoing.put(item)
                if feedback in ("Stalemate", "Checkmate"):
                    print(feedback)

            self.dragged = None

    def draw(self):
        self.surface.fill(self.theme["background"])

        for x in range(self.size):
            for y in range(self.size):
                sq = to_square((x, y))
                if self.dragged and sq in self.moves:
                    key = "move"
                elif self.dragged and sq in self.captures:
                    key = "capture"
                elif (x + y) % 2:
                    key = "white"
                else:
                    key = "black"

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


class NetworkThread(Thread):
    def __init__(self, host, incoming, outgoing):
        Thread.__init__(self)
        self.host = host
        self.incoming = incoming
        self.outgoing = outgoing

    def run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if self.host:
            # Find out own local and public IP
            local_ip = socket.gethostbyname(socket.gethostname())
            public_ip = request.urlopen("https://api.ipify.org").read().decode()

            print(f"If you want to play over the internet, you need to forward port {PORT}.")
            print(f"Your IP address is:")
            print(f"  {local_ip} in the local network.")
            print(f"  {public_ip} in the internet.")

            self.socket.bind(("localhost", PORT))
            self.socket.listen(1)

            self.socket, (peer_ip, _) = self.socket.accept()

        else:
            peer_ip = input("Please enter the IP you want to connect to: ")
            print(f"Connecting to {peer_ip}:{PORT}")
            self.socket.connect((peer_ip, PORT))

        print(f"Connected with {peer_ip}")

        self.socket.settimeout(0.1)

        while True:
            try:
                data = self.socket.recv(2)
                assert len(data) == 2
                item = tuple(data)
                self.incoming.put(item)
            except socket.timeout:
                pass

            try:
                item = self.outgoing.get(block=False)
                assert len(item) == 2
                self.socket.send(bytes(item))
            except Empty:
                pass


if __name__ == "__main__":
    mode = input("Do you want to host (H) or connect (C) ").upper()
    host = mode == "H"
    Game(host).run()
