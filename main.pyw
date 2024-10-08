import sys
import os
import socket
import time
import random

from enum import Enum
from threading import Thread, Lock
from urllib import request

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame
from pygame import Color, Rect

from board import DisplayedBoard
from pieces import Kind, Piece
from util import BOARD_SIZE, TIME, to_coords, format_time
from ai import get_ai_move, get_ai_promotion

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
        "advantage": Color("#59d12a"),
        "disadvantage": Color("#ff4d40")
    }
}


class State(Enum):
    MAINMENU = 0
    HOSTMENU = 1
    JOINMENU = 2
    CONNECTING = 3
    INGAME = 4
    CONTROLS = 5

class Mode(Enum):
    LOCAL = "Play locally"
    HOST = "Host network game"
    JOIN = "Join network game"
    CONTROLS = "Show Controls"

class TextStyle(Enum):
    TITLE = "Title"
    BUTTON = "Button"
    TOOLTIP = "Tooltip"


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
        self.board = DisplayedBoard()
        self.board.setup_file("resources/default_moab.pos")
        self.side = None
        self.turn = 1
        self.paused = False
        self.result = None
        self.showing_captured_piece = False
        
        # Ai.
        self.ai_plays_side_2 = False
        self.ai_found_move = None

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

        # Menu tips.
        self.tip = 0
        self.tips = [
            "Long-range pieces are very valuable due to the large board size.",
            "Use the Buffoon to create pressure in the center.",
            "The Centurion can capture Pawns en passant, but the Pawn not Centurions.",
            "Pawns can always move two squares forward. Try to promote them to a Unicorn.",
            "Ships promote to a Gryphon in your opponent's corners.",
            "Sixty minutes seem like a lot of time, but there is much to think about.",
            "The Bow, Cannon and Star can create tricky threats from the backrow.",
            "The Rhinoceros is powerful, so make sure your opponent cannot trap it.",
            "The Buffalo and the Lion are powerful defensive pieces.",
            "The Diablo and the Dragonwoman are best suited for attacking.",
            "There is no castling. Take some moves to see your king to safety.",
            "Use lower valued pieces to gain tempo by attacking higher valued pieces.",
            "Both the Unicorn and the Lion can single-handedly deliver checkmate.",
            "Developing all your pieces can take many moves, but you should still do it.",
            "Seemingly unguarded squares might be guarded by a bull or antelope."
        ]
        random.shuffle(self.tips)
        self.last_tip = time.time()

        # Clock.
        self.white_time = TIME
        self.black_time = TIME
        self.last_second = time.time()

        # Piece textures.
        self.textures = {}
        self.load_textures("resources/black")
        self.load_textures("resources/white")

        # Tooltips.
        self.tooltip_piece = None
        self.tooltips = dict()
        with open("resources/tooltips.txt") as file:
            content = [line[:-1] for line in file.readlines()]
        i = 0
        while i < len(content):
            key = content[i]
            worth = content[i+1]
            tooltip = [f"{key} ({worth})" if worth != "0" else key]
            i += 2
            while i < len(content) and content[i] != "":
                tooltip.append(content[i])
                i += 1
            self.tooltips[key] = tooltip
            i += 1

        # Scale-dependent things.
        self.screen_rect: Rect = None
        self.square_rect: Rect = None
        self.title_font = None
        self.body_font = None
        self.tooltip_font = None
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
        self.title_font = pygame.font.Font("resources/title.ttf", min(w, h) // 12)
        self.body_font = pygame.font.Font("resources/title.ttf", min(w, h) // 20)
        self.tooltip_font = pygame.font.Font("resources/font.ttf", min(w // 40, h // 28))

        # Determine size of board while leaving space for the clock.
        clock_rect1 = self.text(format_time(self.white_time), pos=(20, 20), align=(-1, -1), draw=False)
        clock_rect2 = self.text(format_time(self.black_time), pos=(20, self.screen_rect.height - 20), align=(-1, 1), draw=False)

        b = max(min(w - max(clock_rect1.right, clock_rect2.right) - self.padding, h) - self.padding,
                min(h - 2 * (clock_rect1.height + self.padding), w) - self.padding)
        b -= b % self.size
        s = b // self.size

        # Rectangle for the whole board.
        self.board_rect = Rect(0, 0, b, b)
        self.board_rect.center = w / 2, h / 2

        # Calculating horizontal offset of board due to leaving space for the clock.
        self.offset_x = 0
        if self.board_rect.top < clock_rect1.bottom and self.board_rect.left < max(clock_rect1.right, clock_rect2.right) + self.padding:
            self.offset_x = max(clock_rect1.right, clock_rect2.right) - self.board_rect.left + self.padding
            self.board_rect.center = w / 2 + self.offset_x, h / 2

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

        if self.event.type == pygame.VIDEORESIZE:
            self.resize()

        if self.mousedown():
            self.pressed = True

        if self.mouseup():
            self.pressed = False

        if self.event.type == pygame.KEYDOWN and self.state == State.INGAME:
            # PRESS P TO PAUSE
            if self.event.key == pygame.K_p and self.side in (None, self.turn):
                self.pause()
            
            # HOLD LEFT ARROW TO SEE THE PREVIOUS BOARD STATE
            if self.event.key == pygame.K_LEFT and self.side in (None, self.turn):
                self.showing_captured_piece = True

            # PRESS CTRL+S TO SAVE THE BOARD STATE
            if self.event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.board.write_file("dump.pos")
            
            # PRESS A TO GIVE CONTROL OF THE BLACK PIECES TO THE AI
            if self.event.key == pygame.K_a and self.side == None:
                if self.turn == 1:
                    self.ai_plays_side_2 = not self.ai_plays_side_2
                elif not self.ai_plays_side_2:
                    self.ai_plays_side_2 = True
                    Thread(target=self.find_ai_reply, daemon=True).start()
        
        # STOP HOLDING LEFT ARROW TO NO LONGER SEE THE PREVIOUS BOARD STATE            
        if self.event.type == pygame.KEYUP and self.state == State.INGAME:
            if self.event.key == pygame.K_LEFT:
                self.showing_captured_piece = False

        self.surface.fill(self.theme["background"])
        self.cursor = [self.screen_rect.centerx, self.screen_rect.height // 3]

        # PRESS ESCAPE TO RETURN TO MAIN MENU
        if self.event.type == pygame.KEYDOWN and self.event.key == pygame.K_ESCAPE:
            if self.state in [State.HOSTMENU, State.JOINMENU]:
                os.execv(sys.executable, ["python"] + sys.argv)
            
            elif self.state == State.CONTROLS:
                self.state = State.MAINMENU

        if self.state == State.MAINMENU:
            self.mainmenu()

        elif self.state == State.HOSTMENU:
            self.cursor = [self.screen_rect.centerx, self.screen_rect.height // 4]
            self.hostmenu()

        elif self.state == State.JOINMENU:
            self.joinmenu()

        elif self.state == State.CONNECTING:
            self.connecting()

        elif self.state == State.INGAME:
            self.ingame()
            
        elif self.state == State.CONTROLS:
            self.controls()

        pygame.display.update()

    def mainmenu(self):
        self.text("Fairy chess", style=TextStyle.TITLE)
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
                    
                elif mode == Mode.CONTROLS:
                    self.state = State.CONTROLS

        if self.last_second - self.last_tip > 6:
            self.tip = (self.tip + 1) % len(self.tips)
            self.last_tip = self.last_second

        self.text(f"Tip:   {self.tips[self.tip]}",
            pos=(self.screen_rect.centerx, self.screen_rect.height - 20),
            align=(0, 1),
            style=TextStyle.TOOLTIP)

        self.last_second = int(time.time())

    def hostmenu(self):
        self.text("Hosting game", style=TextStyle.TITLE)
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

        self.text("Joining game", style=TextStyle.TITLE)
        self.text("Please enter the IP you want to connect with or")
        self.text("simply click \"Connect\" to join a game hosted on this computer.")
        self.text(self.peer_ip)
        self.text("")

        if self.button("Connect") or self.enter():
            self.state = State.CONNECTING
            if not self.peer_ip:
                self.peer_ip = self.local_ip
            Thread(target=self.netloop, daemon=True).start()

    def connecting(self):
        self.text(f"Connecting with {self.peer_ip} " + self.dots(), pos=self.screen_rect.center)
    
    def controls(self):
        self.text("Controls", style=TextStyle.TITLE)
        self.text("Move pieces via drag & drop using the left mouse button.")
        self.text("Inspect pieces by holding the right mouse button.")
        self.text("Hold the left arrow key to see the state of the board before the most recent move.")
        self.text("Press P during your turn to pause the timers.")
        self.text("Press A during local play to give control of the black pieces to the computer.")
        self.text("Press CTRL+S to save the current position as a dump file.")
        self.text("Press Esc to return to the main menu.")
    
    def ingame(self):
        now = time.time()
        if not self.board.finished and not self.paused:
            if self.turn == 1:
                self.white_time -= (int(now - self.last_second))
            else:
                self.black_time -= (int(now - self.last_second))

        if self.last_second != int(now):
            self.last_second = int(now)
            self.dirty = True

        self.infos()

        if not self.paused:
            self.mutex.acquire()
            for sq in range(len(self.board.squares)):
                self.square(sq)
            self.mutex.release()
            if self.tooltip_piece or self.result is not None:
                self.draw_tooltip()

        if self.promoting is not None:
            self.promotion_popup()

        if self.dragged:
            x, y = pygame.mouse.get_pos()
            x -= self.square_rect.width // 2
            y -= self.square_rect.height // 2
            self.piece(self.dragged, (x, y))

            if self.mouseup() and not self.board_rect.collidepoint(*pygame.mouse.get_pos()):
                self.dragged = None
                
        if self.ai_plays_side_2 and self.ai_found_move is not None:
            from_sq, to_sq = self.ai_found_move
            self.ai_found_move = None
            feedback = self.board.move(from_sq, to_sq)
            self.handle_feedback(feedback, from_sq, to_sq)
            

    def infos(self):
        is_white = self.side is None or self.side == 1

        clock_rect1 = self.text(format_time(self.black_time if is_white else self.white_time), pos=(20, 20), align=(-1, -1))
        clock_rect2 = self.text(format_time(self.white_time if is_white else self.black_time), pos=(20, self.screen_rect.height - 20), align=(-1, 1))

        side_1_worth, side_2_worth = self.board.get_worths()
        if is_white:
            my_worth, their_worth = side_1_worth, side_2_worth
        else:
            my_worth, their_worth = side_2_worth, side_1_worth

        diff = my_worth - their_worth
        diff_text = f"{'+' if diff > 0 else ''}{'=' if diff == 0 else diff}"
        theme = "advantage" if diff > 0 else "disadvantage" if diff < 0 else "text"
        their_worth_theme = "disadvantage" if self.ai_plays_side_2 else "text"
        
        if self.board_rect.left < clock_rect1.right:
            self.text(f"[{their_worth}]", pos=(self.screen_rect.w - 20, 20), align=(1, -1), theme=their_worth_theme)
            self.text(f"[{my_worth}]", pos=(self.screen_rect.w - 20, clock_rect2.top), align=(1, -1))
            self.text(diff_text, pos=(self.screen_rect.centerx, clock_rect2.top), align=(0, -1), theme=theme)
        else:
            self.text(f"[{their_worth}]", pos=(20, clock_rect1.bottom + 20), align=(-1, -1), theme=their_worth_theme)
            self.text(f"[{my_worth}]", pos=(20, clock_rect2.top - 20), align=(-1, 1))
            diff = my_worth - their_worth
            self.text(diff_text, pos=(20, self.screen_rect.centery), align=(-1, 0), theme=theme)

    def square(self, sq):
        x, y = to_coords(255 - sq if self.side == 2 else sq)

        if self.dragged and sq in self.moves:
            key = "move"
        elif self.dragged and sq in self.captures:
            key = "capture"
        elif sq in self.board.highlighted_squares:
            key = "last_squares"
        elif (x + y) % 2:
            key = "white"
        else:
            key = "black"

        square = self.square_rect.move(x * self.square_rect.width, -y * self.square_rect.height)
        pygame.draw.rect(self.surface, self.theme[key], square)

        if self.promoting is None and square.collidepoint(*pygame.mouse.get_pos()):
            if self.right_mousedown():
                piece = self.board.squares[sq]
                if piece:
                    self.tooltip_piece = piece

            elif self.right_mouseup():
                self.tooltip_piece = None

            if self.mousedown():
                piece = self.board.squares[sq]
                if piece and ((self.side is None and not (piece.side == 2 and self.ai_plays_side_2)) or piece.side == self.side):
                    self.dragged = piece
                    self.moves, self.captures = piece.move_and_capture_squares(self.board, check_side=True)
                    self.promotions = piece.promotion_squares()

            elif self.dragged and self.mouseup():
                from_sq = self.dragged.square
                feedback = self.board.move(from_sq, sq)
                self.handle_feedback(feedback, from_sq, sq)
                self.dragged = None

        if key == "last_squares" and self.showing_captured_piece:
                    
            if sq == self.board.highlighted_squares[0]:
                new_piece = Piece(3 - self.turn, self.board.squares[self.board.highlighted_squares[1]].kind, sq)
                self.piece(new_piece, square.topleft)
                
            elif sq == self.board.highlighted_squares[-1]:
                if self.board.captured_kind is not None:
                    new_piece = Piece(self.turn, self.board.captured_kind, sq)
                    self.piece(new_piece, square.topleft)
        else:
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
        square.center = self.board_rect.center
        square.x -= ((len(choices) - 1) * self.square_rect.width) // 2

        popup = Rect(0, 0, len(choices) * self.square_rect.width, self.square_rect.height)
        padding = square.width // 4
        popup.inflate_ip(padding, padding)
        popup.center = self.board_rect.center

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

    def text(self, text, pos=None, align=(0, 0), style=TextStyle.BUTTON, draw=True, theme="text"):
        flow = pos is None
        if flow:
            pos = self.cursor

        font = {
            TextStyle.TITLE: self.title_font,
            TextStyle.BUTTON: self.body_font,
            TextStyle.TOOLTIP: self.tooltip_font
        }[style]
        bitmap = font.render(text, True, self.theme[theme])

        rect = bitmap.get_rect()

        rect.center = (pos[0] - align[0] * rect.w / 2, pos[1] - align[1] * rect.h / 2)

        if flow:
            self.cursor[1] += (1.6 if style == TextStyle.TITLE else 1.2) * rect.height

        if draw:
            self.surface.blit(bitmap, rect)
        return rect

    def mouseup(self):
        return self.event.type == pygame.MOUSEBUTTONUP and self.event.button == 1

    def mousedown(self):
        return self.event.type == pygame.MOUSEBUTTONDOWN and self.event.button == 1

    def right_mouseup(self):
        return self.event.type == pygame.MOUSEBUTTONUP and self.event.button == 3

    def right_mousedown(self):
        return self.event.type == pygame.MOUSEBUTTONDOWN and self.event.button == 3

    def enter(self):
        return self.event.type == pygame.KEYDOWN and self.event.key == pygame.K_RETURN

    def netloop(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if self.peer_ip:
            print(f"Connecting to {self.peer_ip}")
            self.socket.connect((self.peer_ip, PORT))
            self.side = self.socket.recv(1)[0]
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
        
        if result == "Stalemate":
            self.result = result + "."

        if result == "Checkmate":
            side = "White" if self.turn == 1 else "Black"
            self.result = f"Checkmate. {side} wins."

        if mocap == "Move":
            self.move_sound.play()
        elif mocap == "Capture":
            self.capture_sound.play()

        if own and type(result) == list:
            if self.side == None and self.turn == 2 and self.ai_plays_side_2:
                self.find_ai_promotion(from_sq, to_sq, result)
            else:
                self.promoting = from_sq, to_sq, result
            return

        self.turn = 3 - self.turn
        self.promoting = None
        self.showing_captured_piece = False

        if own and self.socket is not None:
            promotion = len(Kind) if promotion is None else list(Kind).index(promotion)
            self.socket.send(bytes([0, from_sq, to_sq, promotion]))
            
        if self.turn == 2 and self.ai_plays_side_2 and result == "Valid":
            Thread(target=self.find_ai_reply, daemon=True).start()          
            
    def find_ai_reply(self):
        self.ai_found_move = get_ai_move(self.board)
    
    def find_ai_promotion(self, from_sq, to_sq, kinds):
        choice = get_ai_promotion(self.board, to_sq, kinds)
        feedback = self.board.promote(to_sq, choice), None
        self.handle_feedback(feedback, from_sq, to_sq, promotion=choice)

    def lookup_public_ip(self):
        self.public_ip = request.urlopen("https://api.ipify.org").read().decode()

    def dots(self):
        return (1 + int(time.time()) % 3) * "."

    def pause(self, send=True):
        self.dragged = None
        self.paused = not self.paused
        if self.socket is not None and send:
            self.socket.send(bytes([1, 0, 0, 0]))

    def draw_tooltip(self):
        lines = []
        if self.tooltip_piece:
            lines = self.tooltips[self.tooltip_piece.kind.value]
        elif self.result is not None:
            lines = [self.result]

        line_height = self.tooltip_font.get_height()
        w = self.board_rect.width
        h = len(lines) * line_height + line_height

        tooltip = Rect(0, 0, w, h)
        tooltip.center = self.board_rect.center
        pygame.draw.rect(self.surface, self.theme["background"], tooltip)

        for i, line in enumerate(lines):
            x = self.screen_rect.centerx
            y = self.screen_rect.centery - ((len(lines) - 0.7) * line_height // 2) + i * line_height
            self.text(line, pos=(x, y), style=TextStyle.TOOLTIP)


if __name__ == "__main__":
    Game().mainloop()
