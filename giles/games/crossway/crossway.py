# Giles: crossway.py
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

# TODO: Reimplement the skew for even boards as a shift by one half-cell
# to reduce the racing element.

from giles.games.seated_game import SeatedGame
from giles.games.seat import Seat
from giles.state import State
from giles.utils import booleanize
from giles.utils import demangle_move

# Some useful default values.
MIN_SIZE = 3
MAX_SIZE = 26

BLACK = "black"
WHITE = "white"

COLS = "abcdefghijklmnopqrstuvwxyz"

TAGS = ["abstract", "connection", "square", "2p"]

# 0 1 2
# . . . 0
# . x . 1
# . . . 2
#
# This game allows both orthogonal and diagonal connections.
CONNECTION_DELTAS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))

# A checkerboard play results when one of the diagonal deltas
# is the same color as the play, and the other two corners of
# the defined square are the other player's.  Note that you
# only need to know the diagonals; the other two are the
# diagonal delta with one and then the other set to zero.
CHECKERBOARD_DELTAS = ((-1, -1), (-1, 1), (1, -1), (1, 1))

CONFIG_PARAMS = (
    ("size", "Size of the board"),
    ("is_skewed", "Are the goal edges skewed?"),
)
class Crossway(SeatedGame):
    """A Crossway game table implementation.  Invented in 2007 by Mark Steere.
    """

    def __init__(self, server, table_name):

        super(Crossway, self).__init__(server, table_name)

        self.game_display_name = "Crossway"
        self.game_name = "crossway"
        self.seats = [
            Seat("Black"),
            Seat("White")
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RCrossway^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)
        self.config_params = CONFIG_PARAMS

        # Crossway-specific stuff.
        self.board = None
        self.printable_board = None
        self.size = 19
        self.is_skewed = False
        self.turn = None
        self.turn_number = 0
        self.seats[0].data.side = BLACK
        self.seats[1].data.side = WHITE
        self.last_r = None
        self.last_c = None
        self.resigner = None
        self.adjacency_map = None
        self.found_winner = False

        self.init_board()

    def init_board(self):

        self.board = []

        # Generate a new empty board.
        for r in range(self.size):
            self.board.append([None] * self.size)

    def update_printable_board(self):

        self.printable_board = []
        if self.is_skewed:
            half_edge_str = "".join("==") * (self.size / 2)
        col_str = "    " + "".join([" " + COLS[i] for i in range(self.size)])
        self.printable_board.append(col_str + "\n")
        if self.is_skewed:
            self.printable_board.append("   ^W." + half_edge_str + "=^R=^K" + half_edge_str + ".^~\n")
        else:
            self.printable_board.append("   ^m.=" + "".join(["=="] * self.size) + ".^~\n")
        for r in range(self.size):
            if self.is_skewed:
                if r < (self.size / 2):
                    left_edge_color = "^W"
                    right_edge_color = "^K"
                elif 2 * r == self.size - 1:
                    left_edge_color = right_edge_color = "^R"
                else:
                    left_edge_color = "^K"
                    right_edge_color = "^W"
            else:
                left_edge_color = right_edge_color = "^m"
            this_str = "%2d %s|^~ " % (r + 1, left_edge_color)
            for c in range(self.size):
                if r == self.last_r and c == self.last_c:
                    this_str += "^5"
                loc = self.board[r][c]
                if loc == WHITE:
                    this_str += "^Wo^~ "
                elif loc == BLACK:
                    this_str += "^Kx^~ "
                else:
                    this_str += "^M.^~ "
            this_str += "%s|^~ %d" % (right_edge_color, r + 1)
            self.printable_board.append(this_str + "\n")
        if self.is_skewed:
            self.printable_board.append("   ^K." + half_edge_str + "=^R=^W" + half_edge_str + ".^~\n")
        else:
            self.printable_board.append("   ^m`=" + "".join(["=="] * self.size) + "'^~\n")
        self.printable_board.append(col_str + "\n")

    def show(self, player):

        if not self.printable_board:
            self.update_printable_board()
        for line in self.printable_board:
            player.tell_cc(line)
        player.tell_cc(self.get_turn_str() + "\n")

    def send_board(self):

        for player in self.channel.listeners:
            self.show(player)

    def get_turn_str(self):

        if not self.turn:
            return ("The game has not yet started.\n")

        if self.turn == BLACK:
            player = self.seats[0].player_name
            color_msg = "^KBlack"
            if not self.is_skewed:
                color_msg += "/Vertical"
        else:
            player = self.seats[1].player_name
            color_msg = "^WWhite"
            if not self.is_skewed:
                color_msg += "/Horizontal"
        color_msg += "^~"

        return ("It is ^Y%s^~'s turn (%s)." % (player, color_msg))

    def is_valid(self, row, col):

        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            return False
        return True

    def is_checkerboard(self, color, row, col):

        # Bail immediately if we're given bad input.
        if not self.is_valid(row, col):
            return False

        if self.board[row][col]:
            return False

        # Okay.  Let's check all four checkerboard deltas.
        found = False
        for r_delta, c_delta in CHECKERBOARD_DELTAS:

            # Only bother if this is on the board or we already found it.
            if not found and self.is_valid(row + r_delta, col + c_delta):

                # If the delta space is this color, and the two adjacent spaces
                # in that direction are the other color, it's a checkerboard.
                if self.board[row + r_delta][col + c_delta] == color:
                    corner_one = self.board[row + r_delta][col]
                    corner_two = self.board[row][col + c_delta]
                    if (corner_one and corner_one == corner_two and
                       corner_one != color):

                        # Not empty, is another color.  Checkerboard.
                        found = True

        return found

    def move(self, player, play):

        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "You can't move; you're not playing!\n")
            return False

        if self.turn != seat.data.side:
            player.tell_cc(self.prefix + "You must wait for your turn to move.\n")
            return False

        col, row = play

        # Make sure they're all in range.
        if not self.is_valid(row, col):
            player.tell_cc(self.prefix + "Your move is out of bounds.\n")
            return False

        # Is the space empty?
        if self.board[row][col]:
            player.tell_cc(self.prefix + "That space is already occupied.\n")
            return False

        # Does the move violate the no-checkerboard rule?
        if self.is_checkerboard(self.turn, row, col):
            player.tell_cc(self.prefix + "That move creates a checkerboard.\n")
            return False

        # This is a valid move.  Apply, announce.
        self.board[row][col] = self.turn
        play_str = "%s%s" % (COLS[col], row + 1)
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ places a piece at ^C%s^~.\n" % (seat.player, play_str))
        self.last_r = row
        self.last_c = col
        self.turn_number += 1

        return True

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player
           and self.seats[1].player and self.active):
            self.state.set("playing")
            black_str = "^KBlack"
            if not self.is_skewed:
                black_str += "/Vertical"
            white_str = "^WWhite"
            if not self.is_skewed:
                white_str += "/Horizontal"
            self.channel.broadcast_cc(self.prefix + "%s^~: ^R%s^~; %s^~: ^Y%s^~\n" % (black_str, self.seats[0].player, white_str, self.seats[1].player))
            self.turn = BLACK
            self.turn_number = 1
            self.send_board()

    def set_size(self, player, size_bits):

        if not size_bits.isdigit():
            player.tell_cc(self.prefix + "Invalid size command.\n")
            return

        size = int(size_bits)

        if size < MIN_SIZE or size > MAX_SIZE:
            player.tell_cc(self.prefix + "Size must be between %d and %d inclusive.\n" % (MIN_SIZE, MAX_SIZE))
            return

        if size % 2 == 0 and self.is_skewed:
            player.tell_cc(self.prefix + "Size must be odd to play with skewed goals.\n")
            return

        # Valid!
        self.size = size
        self.channel.broadcast_cc(self.prefix + "^R%s^~ has set the board size to ^C%d^~.\n" % (player, size))
        self.init_board()
        self.update_printable_board()

    def set_skew(self, player, skew_str):

        skew_bool = booleanize(skew_str)
        if skew_bool:
            if skew_bool > 0:

                # We can't be skewed if the board size is even.
                if self.size % 2 == 0:
                    player.tell_cc(self.prefix + "Even-sized boards cannot be skewed.\n")
                    return

                self.is_skewed = True
                display_str = "^Con^~"
            else:
                self.is_skewed = False
                display_str = "^coff^~"
            self.channel.broadcast_cc(self.prefix + "^R%s^~ has turned skew mode %s.\n" % (player, display_str))
            self.update_printable_board()
        else:
            player.tell_cc(self.prefix + "Not a valid boolean!\n")

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

    def swap(self, player):

        # Like Hex, a swap in Crossway requires a translation to make it the
        # equivalent move for the other player.

        self.board[self.last_r][self.last_c] = None
        self.board[self.last_c][self.last_r] = WHITE
        self.last_c, self.last_r = self.last_r, self.last_c

        self.channel.broadcast_cc("^Y%s^~ has swapped ^KBlack^~'s first move.\n" % (player))
        self.turn_number += 1

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.lower().split()
            primary = command_bits[0]

            if state == "setup":

                if primary in ("size", "sz",):

                    if len(command_bits) == 2:
                        self.set_size(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid size command.\n")
                    handled = True

                elif primary in ("skew", "sk",):

                    if len(command_bits) == 2:
                        self.set_skew(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid skew command.\n")
                    handled = True

                elif primary in ("done", "ready", "d", "r",):

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
                    if move_bits and len(move_bits) == 1:
                        made_move = self.move(player, move_bits[0])
                    else:
                        invalid = True

                    if invalid:
                        player.tell_cc(self.prefix + "Invalid move command.\n")
                    handled = True

                elif primary in ("swap",):

                    if self.seats[1].player == player and self.turn_number == 2:
                        self.swap(player)
                        made_move = True
                    else:
                        player.tell_cc(self.prefix + "Invalid swap command.\n")
                    handled = True

                elif primary in ("resign",):

                    if self.resign(player):
                        made_move = True

                    handled = True

                if made_move:

                    # Okay, something happened on the board.  Update.
                    self.update_printable_board()

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

        # If someone resigned, this is the easiest thing ever.
        if self.resigner == WHITE:
            return self.seats[0].player_name
        elif self.resigner == BLACK:
            return self.seats[1].player_name

        # This is like most connection games; we check recursively from the
        # top and left edges to see whether a player has won.  That works
        # for the non-skewed version.  For the skew version, we have to be
        # fancier with the edges.
        self.found_winner = False
        self.adjacency_map = []
        for i in range(self.size):
            self.adjacency_map.append([None] * self.size)

        for i in range(self.size):
            if self.is_skewed:
                # The skew may need diagonal adjacency, so <= rather than <.
                if i <= (self.size / 2):
                    if self.board[i][0] == WHITE:
                        self.recurse_adjacency(WHITE, i, 0)
                    if self.board[0][i] == WHITE:
                        self.recurse_adjacency(WHITE, 0, i)
                    if self.board[self.size - 1][i] == BLACK:
                        self.recurse_adjacency(BLACK, self.size - 1, i)
                if i >= ((self.size - 1) / 2):
                    if self.board[i][0] == BLACK:
                        self.recurse_adjacency(BLACK, i, 0)
            else:
                if self.board[i][0] == WHITE:
                    self.recurse_adjacency(WHITE, i, 0)
                if self.board[0][i] == BLACK:
                    self.recurse_adjacency(BLACK, 0, i)

        if self.found_winner == BLACK:
            return self.seats[0].player_name
        elif self.found_winner == WHITE:
            return self.seats[1].player_name

        # No winner yet.
        return None

    def recurse_adjacency(self, color, row, col):

        # Bail if we found a winner already.
        if self.found_winner:
            return

        # Bail if we're off the board.
        if not self.is_valid(row, col):
            return

        # Bail if we've been here.
        if self.adjacency_map[row][col]:
            return

        # Bail if this is the wrong color.
        if self.board[row][col] != color:
            return

        # Okay.  Occupied and it's this player's.  Mark.
        self.adjacency_map[row][col] = True

        # Have we hit the winning side for this player?
        if not self.is_skewed:
            if ((color == WHITE and col == self.size - 1) or (color == BLACK and row == self.size - 1)):

                # Success!
                self.found_winner = color
                return
        else:
            # Skew far edges are weirder.
            if color == WHITE:
                if (col == self.size - 1 and row >= (self.size - 1) / 2) or (row == self.size - 1 and col >= (self.size - 1) / 2):
                    self.found_winner = WHITE
                    return

            if color == BLACK:
                if (col == self.size - 1 and row <= self.size / 2) or (row == 0 and col >= (self.size - 1) / 2):
                    self.found_winner = BLACK
                    return

        # Not a win yet.  Recurse over adjacencies.
        for r_delta, c_delta in CONNECTION_DELTAS:
            self.recurse_adjacency(color, row + r_delta, col + c_delta)

    def resolve(self, winner):
        self.send_board()
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % winner)

    def show_help(self, player):

        super(Crossway, self).show_help(player)
        player.tell_cc("\nCROSSWAY SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("             ^!size^. <size>,  ^!sz^.     Set board to <size>.\n")
        player.tell_cc("             ^!skew^. on|off,  ^!sk^.     Enable skewed goals.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nCROSSWAY PLAY:\n\n")
        player.tell_cc("      ^!move^. <ln>, ^!play^., ^!mv^., ^!pl^.     Make move <ln> (letter number).\n")
        player.tell_cc("                         ^!swap^.     Swap the first move (only White, only their first).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
