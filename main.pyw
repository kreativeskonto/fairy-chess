import sys
import os
import socket
import time

from enum import Enum
from threading import Thread, Lock
from urllib import request

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
from pygame import Color, Rect

from board import Board
from pieces import Kind, Piece
from util import BOARD_SIZE, TIME, to_coords, format_time

PORT = 5398
BLACK = Color(0, 0, 0)
WHITE = Color(255, 255, 255)
SMOOTH = False
THEMES = {
    "Chess.com": {
        "background": Color("#333333"),
        "text": Color("#eeeeee"),
        "white": Color("#eeeed2"),
        "black": Color("#769656"),
        "move": Color("#baca2b"),
        "capture": Color("#ec7e6a"),
        "promotion": Color("#00d5ff"),
        "last_squares": Color("#fadf11"),
        "popup": Color("#c29f76"),
    }
}


class State(Enum):
    MAINMENU = 0
    HOSTMENU = 1
    JOINMENU = 2
    CONNECTING = 3
    INGAME = 4

class Mode(Enum):
    LOCAL = "Play locally"
    HOST = "Host network game"
    JOIN = "Join network game"


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.mixer.init()
        pygame.key.set_repeat(500, 40)

        # Configuration.
        self.mode = None
        self.size = BOARD_SIZE
        self.theme = THEMES["Chess.com"]
        self.padding = 20
        self.board = Board()
        self.board.setup_file("resources/default_moab.pos")
        self.side = None
        self.turn = 1
        self.paused = False

        # Window, event and drag state.
        pygame.display.set_caption("Fairy chess")
        self.surface = pygame.display.set_mode((850, 670), flags=pygame.RESIZABLE)
        self.state = State.MAINMENU
        self.event = None
        self.dirty = False
        self.pressed = False
        self.cursor = [0, 0]
        self.dragged = None
        self.promoting = None
        self.moves = []
        self.captures = []
        self.promotions = []

        # Clock.
        self.white_time = TIME
        self.black_time = TIME
        self.last_second = time.time()

        # Piece textures.
        self.textures = {}
        self.load_textures("resources/black")
        self.load_textures("resources/white")

        # Scale-dependent things.
        self.screen_rect: Rect = None
        self.square_rect: Rect = None
        self.title_font = None
        self.body_font = None
        self.scaled = {}
        self.resize()

        # Sounds.
        self.move_sound = pygame.mixer.Sound("resources/move.ogg")
        self.capture_sound = pygame.mixer.Sound("resources/capture.ogg")

        # Network communication.
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.public_ip = None
        self.peer_ip = ""
        self.socket = None
        self.mutex = Lock()

    def load_textures(self, dir):
        for path, _, files in os.walk(dir):
            for file in files:
                filepath = os.path.join(path, file)
                kind = Kind[os.path.splitext(file)[0].upper()]
                side = 1 if "white" in path else 2
                self.textures[(side, kind)] = pygame.image.load(filepath).convert_alpha()

    def resize(self):
        # Determine the size of a screen-filling, slightly padded board with
        # pixel-aligned squares.
        w, h = pygame.display.get_window_size()

        # Rectangle for the whole screen.
        self.screen_rect = Rect(0, 0, w, h)

        # Scaled font.
        self.title_font = pygame.font.Font(None, min(w, h) // 12)
        self.body_font = pygame.font.Font(None, min(w, h) // 20)

        # Determine size of board while leaving space for the clock.
        clock_rect1 = self.text(format_time(self.white_time), pos=(20, 20), center=False, draw=False)
        clock_rect2 = self.text(format_time(self.black_time), pos=(20, self.screen_rect.height - (20 + clock_rect1.height)), center=False, draw=False)

        b = max(min(w - max(clock_rect1.right, clock_rect2.right) - self.padding, h) - self.padding,
                min(h - 2 * (clock_rect1.height + self.padding), w) - self.padding)
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

    def mainloop(self):
        while True:
            self.event = pygame.event.wait(50)
            if self.event.type == pygame.NOEVENT and not self.dirty and self.last_second == int(time.time()):
                continue

            self.dirty = False
            self.refresh()

            for event in pygame.event.get():
                self.event = event
                self.refresh()

            self.event = pygame.event.Event(pygame.NOEVENT)
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
        elif self.event.type == pygame.KEYDOWN and self.event.key == pygame.K_p and self.side in (None, self.turn):
            self.pause()

        self.surface.fill(self.theme["background"])
        self.cursor = [self.screen_rect.centerx, self.screen_rect.height // 3]

        if self.state == State.MAINMENU:
            self.mainmenu()

        elif self.state == State.HOSTMENU:
            self.hostmenu()

        elif self.state == State.JOINMENU:
            self.joinmenu()

        elif self.state == State.CONNECTING:
            self.connecting()

        elif self.state == State.INGAME:
            self.ingame()

        pygame.display.update()

    def mainmenu(self):
        self.text("Fairy chess", title=True)
        for mode in Mode:
            if self.button(mode.value):
                self.mode = mode

                if mode == Mode.LOCAL:
                    self.state = State.INGAME
                    self.last_second = int(time.time())

                elif mode == Mode.HOST:
                    self.state = State.HOSTMENU
                    self.side = 1
                    Thread(target=self.lookup_public_ip, daemon=True).start()
                    Thread(target=self.netloop, daemon=True).start()

                elif mode == Mode.JOIN:
                    self.state = State.JOINMENU

    def hostmenu(self):
        self.text("Hosting game", title=True)
        self.text(f"Your local IP is {self.local_ip}")
        self.text(f"Your public IP is {self.public_ip}" if self.public_ip else "")
        self.text("")

        color = "white" if self.side == 1 else "black"
        if self.button(f"Playing as {color}."):
            self.side = 3 - self.side

        self.text("")
        self.text(f"Waiting for opponent " + self.dots())

    def joinmenu(self):
        if self.event.type == pygame.KEYDOWN:
            if self.event.key == pygame.K_BACKSPACE:
                self.peer_ip = self.peer_ip[:-1]
            else:
                value = self.event.unicode.upper()
                if value in "0123456789ABCDEF.:":
                    self.peer_ip += value

        self.text("Joining game", title=True)
        self.text("Please enter the IP you want to connect with:")
        self.text(self.peer_ip)
        self.text("")

        if self.button("Connect") or self.enter():
            self.state = State.CONNECTING
            if not self.peer_ip:
                self.peer_ip = self.local_ip
            Thread(target=self.netloop, daemon=True).start()

    def connecting(self):
        self.text(f"Connecting with {self.peer_ip} " + self.dots(), pos=self.screen_rect.center)

    def ingame(self):
        if not self.board.finished and not self.paused:
            if self.turn == 1:
                self.white_time -= (int(time.time() - self.last_second))
            else:
                self.black_time -= (int(time.time() - self.last_second))

        if self.last_second != int(time.time()):
            self.last_second = int(time.time())
            self.dirty = True

        clock_rect1 = self.text(format_time(self.black_time if self.side != 2 else self.white_time), pos=(20, 20), center=False)
        clock_rect2 = self.text(format_time(self.white_time if self.side != 2 else self.black_time), pos=(20, self.screen_rect.height - (20 + clock_rect1.height)), center=False)
        offset_x = 0

        if self.board_rect.top < clock_rect1.bottom and self.board_rect.left < max(clock_rect1.right, clock_rect2.right) + self.padding:
            offset_x = max(clock_rect1.right, clock_rect2.right) - self.board_rect.left + self.padding

        if not self.paused:
            self.mutex.acquire()
            for sq in range(len(self.board.squares)):
                self.square(sq, offset_x)
            self.mutex.release()

        if self.promoting is not None:
            self.promotion_popup()

        if self.dragged:
            x, y = pygame.mouse.get_pos()
            x -= self.square_rect.width // 2
            y -= self.square_rect.height // 2
            self.piece(self.dragged, (x, y))

            if self.mouseup() and not self.board_rect.collidepoint(*pygame.mouse.get_pos()):
                self.dragged = None

    def square(self, sq, offset_x=0, offset_y=0):
        x, y = to_coords(255 - sq if self.side == 2 else sq)

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

        square = self.square_rect.move(x * self.square_rect.width + offset_x, -y * self.square_rect.height + offset_y)
        pygame.draw.rect(self.surface, self.theme[key], square)

        if self.promoting is None and square.collidepoint(*pygame.mouse.get_pos()):
            if self.mousedown():
                piece = self.board.squares[sq]
                if piece and (self.side is None or piece.side == self.side):
                    self.dragged = piece
                    self.moves, self.captures = piece.move_and_capture_squares(self.board, check_side=True)
                    self.promotions = piece.promotion_squares()

            elif self.dragged and self.mouseup():
                from_sq = self.dragged.square
                feedback = self.board.move(from_sq, sq)
                self.handle_feedback(feedback, from_sq, sq)
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

    def promotion_popup(self):
        from_sq, to_sq, choices = self.promoting

        square = self.square_rect.copy()
        square.center = self.screen_rect.center
        square.x -= ((len(choices) - 1) * self.square_rect.width) // 2

        popup = Rect(0, 0, len(choices) * self.square_rect.width, self.square_rect.height)
        padding = square.width // 4
        popup.inflate_ip(padding, padding)
        popup.center = self.screen_rect.center

        pygame.draw.rect(self.surface, self.theme["popup"], popup)

        for choice in choices:
            alpha = 255
            if square.collidepoint(*pygame.mouse.get_pos()):
                alpha = 150 if self.pressed else 200
                if self.mouseup():
                    feedback = self.board.promote(to_sq, choice), None
                    self.handle_feedback(feedback, from_sq, to_sq, promotion=choice)

            self.piece(Piece(self.turn, choice), square, alpha)
            square.x += self.square_rect.width

    def piece(self, piece, pos, alpha=255):
        try:
            bitmap = self.scaled[piece.side, piece.kind]
            bitmap.set_alpha(alpha)
            self.surface.blit(bitmap, pos)
        except KeyError:
            pass

    def button(self, text, pos=None):
        flow = pos is None
        if flow:
            pos = self.cursor

        bitmap = self.body_font.render(text, True, self.theme["text"])
        rect = bitmap.get_rect()
        rect.center = pos

        if flow:
            self.cursor[1] += 1.5 * rect.height

        clicked = False
        if rect.collidepoint(*pygame.mouse.get_pos()):
            bitmap.set_alpha(150 if self.pressed else 200)
            clicked = self.mouseup()

        self.surface.blit(bitmap, rect)
        return clicked

    def text(self, text, pos=None, center=True, title=False, draw=True):
        flow = pos is None
        if flow:
            pos = self.cursor

        font = self.title_font if title else self.body_font
        font.underline = title
        bitmap = font.render(text, True, self.theme["text"])

        rect = bitmap.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos

        if flow:
            self.cursor[1] += (2.0 if title else 1.5) * rect.height

        if draw:
            self.surface.blit(bitmap, rect)
        return rect

    def mouseup(self):
        return self.event.type == pygame.MOUSEBUTTONUP and self.event.button == 1

    def mousedown(self):
        return self.event.type == pygame.MOUSEBUTTONDOWN and self.event.button == 1

    def enter(self):
        return self.event.type == pygame.KEYDOWN and self.event.key == pygame.K_RETURN

    def netloop(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if self.peer_ip:
            print(f"Connecting to {self.peer_ip}")
            self.socket.connect((self.peer_ip, PORT))
            self.side, = self.socket.recv(1)
        else:
            print(f"Listening for incoming connections")
            self.socket.bind((self.local_ip, PORT))
            self.socket.listen(1)
            self.socket, (self.peer_ip, _) = self.socket.accept()
            self.socket.send(bytes([3 - self.side]))

        print(f"Connected to {self.peer_ip}")
        self.state = State.INGAME
        self.last_second = time.time()
        self.dirty = True

        while True:
            pause, from_sq, to_sq, promotion = self.socket.recv(4)
            if pause == 0:
                self.mutex.acquire()
                feedback = self.board.move(from_sq, to_sq)
                if promotion < len(Kind):
                    feedback = self.board.promote(to_sq, list(Kind)[promotion]), feedback[1]
                self.handle_feedback(feedback, from_sq, to_sq, own=False)
                self.mutex.release()
            else:
                self.pause(send=False)
            self.dirty = True

    def handle_feedback(self, feedback, from_sq, to_sq, promotion=None, own=True):
        result, mocap = feedback
        if result == "Invalid":
            return

        if result in ("Stalemate", "Checkmate"):
            print(result)

        if mocap == "Move":
            self.move_sound.play()
        elif mocap == "Capture":
            self.capture_sound.play()

        if own and type(result) == list:
            self.promoting = from_sq, to_sq, result
            return

        self.turn = 3 - self.turn
        self.promoting = None

        if own and self.socket is not None:
            promotion = len(Kind) if promotion is None else list(Kind).index(promotion)
            self.socket.send(bytes([0, from_sq, to_sq, promotion]))

    def lookup_public_ip(self):
        self.public_ip = request.urlopen("https://api.ipify.org").read().decode()

    def dots(self):
        return (1 + int(time.time()) % 3) * "."

    def pause(self, send=True):
        self.dragged = None
        self.paused = not self.paused
        if self.socket is not None and send:
            self.socket.send(bytes([1, 0, 0, 0]))


if __name__ == "__main__":
    Game().mainloop()
