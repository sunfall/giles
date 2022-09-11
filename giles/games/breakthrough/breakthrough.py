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

from giles.games.seated_game import SeatedGame
from giles.games.piece import Piece
from giles.games.seat import Seat
from giles.games.square_grid_layout import SquareGridLayout, COLS
from giles.state import State
from giles.utils import demangle_move

# Some useful default values.
MAX_HEIGHT = 26

MIN_WIDTH = 2
MAX_WIDTH = 26

TAGS = ["abstract", "capture", "square", "2p"]

CONFIG_PARAMS = (
    ("height", "Board height"),
    ("width", "Board width"),
    ("rows", "Number of rows with pieces"),
)

class Breakthrough(SeatedGame):
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
        self.config_params = CONFIG_PARAMS

        # Breakthrough-specific stuff.
        self.width = 8
        self.height = 8
        self.rows = 2
        self.turn = None
        self.black = self.seats[0]
        self.white = self.seats[1]
        self.resigner = None
        self.layout = None

        # We cheat and create a black and white piece here.  Breakthrough
        # doesn't differentiate between pieces, so this allows us to do
        # comparisons later.
        self.bp = Piece("^K", "b", "B")
        self.bp.data.owner = self.black
        self.wp = Piece("^W", "w", "W")
        self.wp.data.owner = self.white

        self.init_board()

    def init_board(self):

        # Create the layout and the pieces it uses as well.  Note that we
        # can be ultra-lazy with the pieces, as Breakthrough doesn't distinguish
        # between them, so there's no reason to create a bunch of identical
        # bits.
        self.layout = SquareGridLayout()
        self.layout.resize(self.width, self.height)

        for i in range(self.rows):
            # Some stupid math to get proper row numbers for White.
            white_row = self.height - (1 + i)
            for j in range(self.width):
                self.layout.place(self.bp, i, j, update=False)
                self.layout.place(self.wp, white_row, j, update=False)

        # Set the piece counts.
        self.white.data.piece_count = self.width * self.rows
        self.black.data.piece_count = self.width * self.rows
        self.layout.update()

    def show(self, player):

        player.tell_cc(self.layout)
        player.tell_cc(self.get_turn_str() + "\n")

    def send_board(self):

        for player in self.channel.listeners:
            self.show(player)

    def get_turn_str(self):

        if not self.turn:
            return ("The game has not yet started.\n")

        if self.turn == self.black:
            player = self.seats[0].player
            color_msg = "^KBlack^~"
        else:
            player = self.seats[1].player
            color_msg = "^WWhite^~"

        return ("It is ^Y%s^~'s turn (%s)." % (player, color_msg))

    def move(self, player, src, dst):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You can't move; you're not playing!\n")
            return False

        if self.turn != seat:
            self.tell_pre(player, "You must wait for your turn to move.\n")
            return False

        src_c, src_r = src
        dst_c, dst_r = dst
        src_str = "%s%s" % (COLS[src_c], src_r + 1)
        dst_str = "%s%s" % (COLS[dst_c], dst_r + 1)

        # Make sure they're all in range.
        if (not self.layout.is_valid(src_r, src_c) or
         not self.layout.is_valid(dst_r, dst_c)):
            self.tell_pre(player, "Your move is out of bounds.\n")
            return False

        # Does the player even have a piece there?
        src_loc = self.layout.grid[src_r][src_c]
        if not src_loc or src_loc.data.owner != self.turn:
            self.tell_pre(player, "You don't have a piece at ^C%s^~.\n" % src_str)
            return False

        # Is the destination within range?
        if self.turn == self.black:
            row_delta = 1
        else:
            row_delta = -1

        if src_r + row_delta != dst_r:
            self.tell_pre(player, "You can't move from ^C%s^~ to row ^R%d^~.\n" % (src_str, dst_r + 1))
            return False
        if abs(src_c - dst_c) > 1:
            self.tell_pre(player, "You can't move from ^C%s^~ to column ^R%s^~.\n" % (src_str, COLS[dst_c]))
            return False

        # Okay, this is actually (gasp) a potentially legitimate move.  If
        # it's a move forward, it only works if the forward space is empty.
        if src_c == dst_c and self.layout.grid[dst_r][dst_c]:
            self.tell_pre(player, "A straight-forward move can only be into an empty space.\n")
            return False

        # Otherwise, it must not have one of the player's own pieces in it.
        dst_loc = self.layout.grid[dst_r][dst_c]
        if src_loc == dst_loc:
            self.tell_pre(player, "A diagonal-forward move cannot be onto your own piece.\n")
            return False

        additional_str = ""
        opponent = self.seats[0]
        if seat == self.seats[0]:
            opponent = self.seats[1]
        if dst_loc:
            # It's a capture.
            additional_str = ", capturing one of ^R%s^~'s pieces" % (opponent.player)
            opponent.data.piece_count -= 1
        self.bc_pre("^Y%s^~ moves a piece from ^C%s^~ to ^G%s^~%s.\n" % (seat.player, src_str, dst_str, additional_str))

        # Make the move on the layout.
        self.layout.move(src_r, src_c, dst_r, dst_c, True)

        return ((src_r, src_c), (dst_r, dst_c))

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player
           and self.seats[1].player and self.active):
            self.state.set("playing")
            self.bc_pre("^KBlack^~: ^R%s^~; ^WWhite^~: ^Y%s^~\n" %
               (self.seats[0].player, self.seats[1].player))
            self.turn = self.black
            self.send_board()

    def set_rows(self, player, row_bits):

        if len(row_bits) != 1:
            self.tell_pre(player, "Invalid rows command.\n")
            return

        if not row_bits[0].isdigit():
            self.tell_pre(player, "Invalid rows command.\n")
            return

        r = int(row_bits[0])
        max_rows = self.height / 2
        if r < 1 or r > max_rows:
            self.tell_pre(player, "Rows must be between 1 and %d inclusive.\n" % (max_rows))
            return

        # Valid!
        self.rows = r
        self.bc_pre("^R%s^~ has set the piece row count to ^C%d^~.\n" % (player, r))
        self.init_board()

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
            self.tell_pre(player, "Invalid size command.\n")
            return

        if not width.isdigit() or not height.isdigit():
            self.tell_pre(player, "Invalid size command.\n")
            return

        w = int(width)
        h = int(height)

        if w < MIN_WIDTH or w > MAX_WIDTH:
            self.tell_pre(player, "Width must be between %d and %d inclusive.\n" % (MIN_WIDTH, MAX_WIDTH))
            return

        # Determine a minimum height based on the current row count.
        curr_min_height = self.rows * 2
        if h < curr_min_height or h > MAX_HEIGHT:
            self.tell_pre(player, "Height must be between %d and %d inclusive.\n" % (curr_min_height, MAX_HEIGHT))
            return

        # Valid!
        self.width = w
        self.height = h
        self.bc_pre("^R%s^~ has set the board size to ^C%d^Gx^C%d^~.\n" % (player, w, h))
        self.init_board()

    def resign(self, player):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You can't resign; you're not playing!\n")
            return False

        if self.turn != seat:
            self.tell_pre(player, "You must wait for your turn to resign.\n")
            return False

        self.resigner = seat
        self.bc_pre("^R%s^~ is resigning from the game.\n" % player)
        return True

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.split()
            primary = command_bits[0]

            if state == "setup":

                if primary in ("rows", "ro",):
                    self.set_rows(player, command_bits[1:])
                    handled = True

                if primary in ("size", "sz",):

                    self.set_size(player, command_bits[1:])
                    handled = True

                if primary in ("done", "ready", "d", "r",):

                    self.bc_pre("The game is now looking for players.\n")
                    self.state.set("need_players")
                    handled = True

            elif state == "need_players":

                if primary in ("config", "setup", "conf",):

                    self.state.set("setup")
                    self.bc_pre("^R%s^~ has switched the game to setup mode.\n" % player)
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
                        self.tell_pre(player, "Invalid move command.\n")
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
                        self.turn = self.next_seat(self.turn)

                        # ...show everyone the board, and keep on.
                        self.send_board()

        if not handled:
            self.tell_pre(player, "Invalid command.\n")

    def find_winner(self):

        # If someone resigned, this is the easiest thing ever.  Same if
        # they lost all their pieces.
        if self.resigner == self.white or self.seats[1].data.piece_count == 0:
            return self.seats[0].player_name
        elif self.resigner == self.black or self.seats[1].data.piece_count == 0:
            return self.seats[1].player_name

        # Aw, we have to do work.  If black has a piece on the last row,
        # they win; if white has a piece on the first row, they win.
        if self.bp in self.layout.grid[-1]:
            return self.seats[0].player_name
        if self.wp in self.layout.grid[0]:
            return self.seats[1].player_name

        # ...that wasn't really much work, but there's no winner yet.
        return None

    def resolve(self, winner):
        self.send_board()
        self.bc_pre("^C%s^~ wins!\n" % winner)

    def show_help(self, player):

        super(Breakthrough, self).show_help(player)
        player.tell_cc("\nBREAKTHROUGH SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("    ^!rows^. <count>, ^!ro^.     Set piece row count to <count>.\n")
        player.tell_cc("    ^!size^. <size> | <w> <h>, ^!sz^.     Set board to <size>x<size>/<w>x<h>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nBREAKTHROUGH PLAY:\n\n")
        player.tell_cc("          ^!move^. <ln> <ln2>, ^!mv^.     Move from <ln> to <ln2> (letter number).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
