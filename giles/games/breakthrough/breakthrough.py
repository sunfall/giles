# Giles: breakthrough.py
# Copyright 2012 Phil Bordelon
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from giles.games.game import Game
from giles.games.piece import Piece
from giles.games.seat import Seat
from giles.games.square_grid_layout import SquareGridLayout, COLS
from giles.state import State
from giles.utils import demangle_move

# Some useful default values.
MIN_HEIGHT = 5
MAX_HEIGHT = 26

MIN_WIDTH = 3
MAX_WIDTH = 26

BLACK = "black"
WHITE = "white"

class Breakthrough(Game):
    """A Breakthrough game table implementation.  Invented in 2000 by Dan Troyka.
    """

    def __init__(self, server, table_name):

        super(Breakthrough, self).__init__(server, table_name)

        self.game_display_name = "Breakthrough"
        self.game_name = "breakthrough"
        self.seats = [
            Seat("Black"),
            Seat("White")
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RBreakthrough^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Breakthrough-specific stuff.
        self.board = None
        self.width = 8
        self.height = 8
        self.turn = None
        self.seats[0].data.side = BLACK
        self.seats[0].data.piece_count = None
        self.seats[1].data.side = WHITE
        self.seats[1].data.piece_count = None
        self.last_r = None
        self.last_c = None
        self.resigner = None
        self.layout = None

        self.init_board()

    def init_board(self):

        self.board = []

        # Top two rows are black.
        self.board.append([BLACK] * self.width)
        self.board.append([BLACK] * self.width)

        # Every row other than the last two is empty.
        for i in range(self.height - 4):
            self.board.append([None] * self.width)

        # The bottom two rows are white.
        self.board.append([WHITE] * self.width)
        self.board.append([WHITE] * self.width)

        # Set the starting piece counts.
        self.seats[0].data.piece_count = 2 * self.width
        self.seats[1].data.piece_count = 2 * self.width

        # Create the layout and the pieces it uses as well.  Note that we
        # can be ultra-lazy with the pieces, as Breakthrough doesn't distinguish
        # between them, so there's no reason to create a bunch of identical
        # bits.
        self.layout = SquareGridLayout()
        self.layout.resize(self.height, self.width)
        bp = Piece("^K", "b", "B")
        wp = Piece("^W", "w", "W")
        last_row = self.height - 1
        next_last_row = last_row - 1

        for i in range(self.width):
            self.layout.place(bp, 0, i)
            self.layout.place(bp, 1, i)
            self.layout.place(wp, next_last_row, i)
            self.layout.place(wp, last_row, i)

    def show(self, player):

        player.tell_cc(self.layout)
        player.tell_cc(self.get_turn_str() + "\n")

    def send_board(self):

        for player in self.channel.listeners:
            self.show(player)

    def get_turn_str(self):

        if not self.turn:
            return ("The game has not yet started.\n")

        if self.turn == BLACK:
            player = self.seats[0].player
            color_msg = "^KBlack^~"
        else:
            player = self.seats[1].player
            color_msg = "^WWhite^~"

        return ("It is ^Y%s^~'s turn (%s)." % (player, color_msg))

    def move(self, player, src, dst):

        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "You can't move; you're not playing!\n")
            return False

        if self.turn != seat.data.side:
            player.tell_cc(self.prefix + "You must wait for your turn to move.\n")
            return False

        src_c, src_r = src
        dst_c, dst_r = dst
        src_str = "%s%s" % (COLS[src_c], src_r + 1)
        dst_str = "%s%s" % (COLS[dst_c], dst_r + 1)

        # Make sure they're all in range.
        if (src_r < 0 or src_r >= self.height or src_c < 0 or
           src_c >= self.width or dst_r < 0 or dst_r >= self.height or
           dst_c < 0 or dst_c >= self.width):
            player.tell_cc(self.prefix + "Your move is out of bounds.\n")
            return False

        # Does the player even have a piece there?
        if self.board[src_r][src_c] != self.turn:
            player.tell_cc(self.prefix + "You don't have a piece at ^C%s^~.\n" % src_str)
            return False

        # Is the destination within range?
        if self.turn == BLACK:
            row_delta = 1
        else:
            row_delta = -1

        if src_r + row_delta != dst_r:
            player.tell_cc(self.prefix + "You can't move from ^C%s^~ to row ^R%d^~.\n" % (src_str, dst_r + 1))
            return False
        if abs(src_c - dst_c) > 1:
            player.tell_cc(self.prefix + "You can't move from ^C%s^~ to column ^R%s^~.\n" % (src_str, COLS[dst_c]))
            return False

        # Okay, this is actually (gasp) a potentially legitimate move.  If
        # it's a move forward, it only works if the forward space is empty.
        if src_c == dst_c and self.board[dst_r][dst_c]:
            player.tell_cc(self.prefix + "A straight-forward move can only be into an empty space.\n")
            return False

        # Otherwise, it must not have one of the player's own pieces in it.
        elif self.board[dst_r][dst_c] == self.turn:
            player.tell_cc(self.prefix + "A diagonal-forward move cannot be onto your own piece.\n")
            return False

        # This is a for-reals legitimate move.  Make it happen!
        self.board[src_r][src_c] = None

        additional_str = ""
        opponent = self.seats[0]
        if seat == self.seats[0]:
            opponent = self.seats[1]
        loc = self.board[dst_r][dst_c]
        if loc:
            # It's a capture.
            additional_str = ", capturing one of ^R%s^~'s pieces" % (opponent.player)
            opponent.data.piece_count -= 1
        self.board[dst_r][dst_c] = self.turn
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ moves a piece from ^C%s^~ to ^G%s^~%s.\n" % (seat.player, src_str, dst_str, additional_str))
        self.last_r = dst_r
        self.last_c = dst_c

        # Also make the move on the layout.
        self.layout.move(src_r, src_c, dst_r, dst_c, True)

        return ((src_r, src_c), (dst_r, dst_c))

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player
           and self.seats[1].player and self.active):
            self.state.set("playing")
            self.channel.broadcast_cc(self.prefix + "^KBlack^~: ^R%s^~; ^WWhite^~: ^Y%s^~\n" %
               (self.seats[0].player, self.seats[1].player))
            self.turn = BLACK
            self.send_board()

    def set_size(self, player, size_bits):

        # Is there an 'x' in the middle of a single argument?
        if len(size_bits) == 1:
            size_bits[0] = size_bits[0].lower()
            if "x" in size_bits[0]:
                size_bits = size_bits[0].split("x")

        width = size_bits[0]
        # If there's a single element, height == width.
        if len(size_bits) == 1:
            height = width
        elif len(size_bits) == 2:
            width = size_bits[0]
            height = size_bits[1]
        else:
            player.tell_cc(self.prefix + "Invalid size command.\n")
            return

        if not width.isdigit() or not height.isdigit():
            player.tell_cc(self.prefix + "Invalid size command.\n")
            return

        w = int(width)
        h = int(height)

        if w < MIN_WIDTH or w > MAX_WIDTH:
            player.tell_cc(self.prefix + "Width must be between %d and %d inclusive.\n" % (MIN_WIDTH, MAX_WIDTH))
            return

        if h < MIN_HEIGHT or h > MAX_HEIGHT:
            player.tell_cc(self.prefix + "Height must be between %d and %d inclusive.\n" % (MIN_HEIGHT, MAX_HEIGHT))
            return

        # Valid!
        self.width = w
        self.height = h
        self.channel.broadcast_cc(self.prefix + "^R%s^~ has set the board size to ^C%d^Gx^C%d^~.\n" % (player, w, h))
        self.init_board()

    def resign(self, player):

        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "You can't resign; you're not playing!\n")
            return False

        if self.turn != seat.data.side:
            player.tell_cc(self.prefix + "You must wait for your turn to resign.\n")
            return False

        self.resigner = seat.data.side
        self.channel.broadcast_cc(self.prefix + "^R%s^~ is resigning from the game.\n" % player)
        return True

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.split()
            primary = command_bits[0]

            if state == "setup":

                if primary in ("size", "sz",):

                    self.set_size(player, command_bits[1:])
                    handled = True

                if primary in ("done", "ready", "d", "r",):
                
                    self.channel.broadcast_cc(self.prefix + "The game is now looking for players.\n")
                    self.state.set("need_players")
                    handled = True

            elif state == "need_players":

                if primary in ("config", "setup", "conf",):

                    self.state.set("setup")
                    self.channel.broadcast_cc(self.prefix + "^R%s^~ has switched the game to setup mode.\n" % player)
                    handled = True

            elif state == "playing":

                made_move = False

                if primary in ("move", "play", "mv", "pl",):

                    invalid = False
                    move_bits = demangle_move(command_bits[1:])
                    if move_bits and len(move_bits) == 2:
                        made_move = self.move(player, move_bits[0], move_bits[1])
                    else:
                        invalid = True

                    if invalid:
                        player.tell_cc(self.prefix + "Invalid move command.\n")
                    handled = True

                elif primary in ("resign",):

                    if self.resign(player):
                        made_move = True

                    handled = True

                if made_move:

                    # Did someone win?
                    winner = self.find_winner()
                    if winner:
                        self.resolve(winner)
                        self.finish()
                    else:

                        # Nope.  Switch turns...
                        if self.turn == BLACK:
                            self.turn = WHITE
                        else:
                            self.turn = BLACK

                        # ...show everyone the board, and keep on.
                        self.send_board()

        if not handled:
            player.tell_cc(self.prefix + "Invalid command.\n")

    def find_winner(self):

        # If someone resigned, this is the easiest thing ever.  Same if
        # they lost all their pieces.
        if self.resigner == WHITE or self.seats[1].data.piece_count == 0:
            return self.seats[0].player_name
        elif self.resigner == BLACK or self.seats[1].data.piece_count == 0:
            return self.seats[1].player_name

        # Aw, we have to do work.  If black has a piece on the last row,
        # they win; if white has a piece on the first row, they win.
        if BLACK in self.board[-1]:
            return self.seats[0].player_name
        if WHITE in self.board[0]:
            return self.seats[1].player_name

        # ...that wasn't really much work, but there's no winner yet.
        return None

    def resolve(self, winner):
        self.send_board()
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % winner)

    def show_help(self, player):

        super(Breakthrough, self).show_help(player)
        player.tell_cc("\nBREAKTHROUGH SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("    ^!size^. <size> | <w> <h>, ^!sz^.     Set board to <size>x<size>/<w>x<h>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nBREAKTHROUGH PLAY:\n\n")
        player.tell_cc("          ^!move^. <ln> <ln2>, ^!mv^.     Move from <ln> to <ln2> (letter number).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
