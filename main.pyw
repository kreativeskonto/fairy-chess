import sys
import os
import socket

from queue import Empty, Queue
from threading import Thread
from urllib import request

from pygame.constants import MOUSEBUTTONUP

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
from pygame import Color, Rect

from board import Board
from pieces import Kind
from util import BOARD_SIZE, to_coords, to_square

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
        "promotion": Color("#00d5ff"),
        "last_squares": Color("#fadf11")
    }
}


class Game:
    def __init__(self, mode):
        pygame.init()
        pygame.mixer.init()

        # Configuration
        self.mode = mode
        self.size = BOARD_SIZE
        self.theme = THEMES["Chess.com"]
        self.padding = 20
        self.board = Board()
        self.board.setup_file("default_moab.pos")

        # Window, event and drag state.
        pygame.display.set_caption("Fairy chess")
        self.surface = pygame.display.set_mode((800, 670), flags=pygame.RESIZABLE)
        self.event = None
        self.pressed = False
        self.dragged = None
        self.moves = []
        self.captures = []
        self.promotions = []

        # Piece textures.
        self.textures = {}
        for path, _, files in os.walk("pieces"):
            for file in files:
                filepath = os.path.join(path, file)
                kind = Kind[os.path.splitext(file)[0].upper()]
                side = 1 if "white" in path else 2
                self.textures[(side, kind)] = pygame.image.load(filepath).convert_alpha()

        # Scale-dependent things.
        self.board_rect: Rect = None
        self.square_rect: Rect = None
        self.scaled = {}
        self.resize()

        # Sound
        self.move_sound = pygame.mixer.Sound("move.ogg")
        self.capture_sound = pygame.mixer.Sound("capture.ogg")

        # Network communication queues.
        self.incoming = Queue()
        self.outgoing = Queue()

        # Network thread.
        if mode in "HC":
            host = mode == "H"
            self.side = 1 if host else 2
            self.network = NetworkThread(host, self.incoming, self.outgoing)
            self.network.daemon = True
            self.network.start()

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

    def run(self):
        while True:
            try:
                item = self.incoming.get(block=False)
                feedback, mocap = self.board.move(*item)
                if feedback in ("Stalemate", "Checkmate"):
                    print(feedback)
                if feedback != "Invalid":
                    if mocap == "Move":
                        self.move_sound.play()
                    elif mocap == "Capture":
                        self.capture_sound.play()
            except Empty:
                pass

            self.event = pygame.event.wait(50)
            self.refresh()

            for event in pygame.event.get():
                self.event = event
                self.refresh()

    def refresh(self):
        if self.event.type == pygame.QUIT:
            sys.exit()
        elif self.event.type == pygame.VIDEORESIZE:
            self.resize()
        elif self.mousedown():
            self.pressed = True
        elif self.mouseup():
            self.pressed = False

        self.surface.fill(self.theme["background"])

        for sq in range(len(self.board.squares)):
            self.square(sq)

        if self.dragged:
            x, y = pygame.mouse.get_pos()
            x -= self.square_rect.width // 2
            y -= self.square_rect.height // 2
            self.piece(self.dragged, (x, y))

            if self.mouseup() and not self.board_rect.collidepoint(*pygame.mouse.get_pos()):
                self.dragged = None

        pygame.display.update()

    def square(self, sq):
        x, y = to_coords(sq)

        if self.dragged and sq in self.moves:
            key = "move"
        elif self.dragged and sq in self.captures:
            key = "capture"
        elif self.board.move_history and sq in self.board.move_history[-1]:
            key = "last_squares"
        elif (x + y) % 2:
            key = "white"
        else:
            key = "black"

        square = self.square_rect.move(x * self.square_rect.width, -y * self.square_rect.height)
        pygame.draw.rect(self.surface, self.theme[key], square)

        if square.collidepoint(*pygame.mouse.get_pos()):
            if self.mousedown():
                piece = self.board.squares[sq]
                if piece and (self.mode == "L" or piece.side == self.side):
                    self.dragged = piece
                    self.moves, self.captures = piece.move_and_capture_squares(self.board, check_side=True)
                    self.promotions = piece.promotion_squares()

            elif self.dragged and self.mouseup():
                item = (self.dragged.square, sq)
                feedback, mocap = self.board.move(*item)
                if feedback != "Invalid":
                    self.outgoing.put(item)
                    if mocap == "Move":
                        self.move_sound.play()
                    elif mocap == "Capture":
                        self.capture_sound.play()
                if feedback in ("Stalemate", "Checkmate"):
                    print(feedback)
                self.dragged = None

        piece = self.board.squares[sq]
        if piece and piece != self.dragged:
            self.piece(piece, square.topleft)

        if self.dragged and sq in self.promotions:
            temp = pygame.Surface(self.square_rect.size, pygame.SRCALPHA)
            pygame.draw.circle(
                temp,
                self.theme["promotion"],
                (self.square_rect.width // 2, self.square_rect.height // 2),
                self.square_rect.width // 4,
            )
            temp.set_alpha(180)
            self.surface.blit(temp, square)

    def piece(self, piece, pos):
        try:
            bitmap = self.scaled[piece.side, piece.kind]
            self.surface.blit(bitmap, pos)
        except KeyError:
            pass

    def mouseup(self):
        return self.event.type == pygame.MOUSEBUTTONUP and self.event.button == 1

    def mousedown(self):
        return self.event.type == pygame.MOUSEBUTTONDOWN and self.event.button == 1


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

            self.socket.bind((local_ip, PORT))
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
    mode = input("Do you want to host (H), connect (C) or play locally (L)? ").upper()
    assert mode in "HCL"

    Game(mode).run()
