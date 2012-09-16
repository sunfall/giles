# Giles: talpa.py
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
MIN_SIZE = 4
MAX_SIZE = 26

CONNECTION_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))

class Talpa(Game):
    """A Talpa game table implementation.  Invented in 2010 by Arty Sandler.
    """

    def __init__(self, server, table_name):

        super(Talpa, self).__init__(server, table_name)

        self.game_display_name = "Talpa"
        self.game_name = "talpa"
        self.seats = [
            Seat("Red"),
            Seat("Blue"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RTalpa^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Talpa-specific stuff.
        self.size = 8
        self.turn = None
        self.red = self.seats[0]
        self.red.data.seat_str = "^RRed/Vertical^~"
        self.blue = self.seats[1]
        self.blue.data.seat_str = "^BBlue/Horizontal^~"
        self.resigner = None
        self.layout = None

        # Like in most connection games, there is no difference between pieces
        # of a given color, so we save time and create our singleton pieces
        # here.
        self.rp = Piece("^R", "x", "X")
        self.rp.data.owner = self.red
        self.bp = Piece("^B", "o", "O")
        self.bp.data.owner = self.blue

        # Initialize the starting layout.
        self.init_layout()

    def init_layout(self):

        # Create the layout and fill it with pieces.
        self.layout = SquareGridLayout(highlight_color = "^I")
        self.layout.resize(self.size)

        for i in range(self.size):
            for j in range(self.size):
                if (i + j) % 2:
                    self.layout.place(self.rp, i, j, update = False)
                else:
                    self.layout.place(self.bp, i, j, update = False)

        self.layout.update()

    def get_sp_str(self, seat):

        return "^C%s^~ (%s)" % (seat.player_name, seat.data.seat_str)

    def get_turn_str(self):

        if not self.turn:
            return "The game has not yet started.\n"

        return "It is ^C%s^~'s turn (%s).\n" % (self.turn.player_name, self.turn.data.seat_str)

    def show(self, player):

        player.tell_cc(self.layout)
        player.tell_cc(self.get_turn_str())

    def send_board(self):

        for player in self.channel.listeners:
            self.show(player)

    def set_size(self, player, size_str):

        if not size_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        size = int(size_str)

        if size < MIN_SIZE or size > MAX_SIZE:
            self.tell_pre(player, "Size must be between %d and %d inclusive.\n" % (MIN_SIZE, MAX_SIZE))
            return False

        # Size must be even.
        if size % 2:
            self.tell_pre(player, "Size must be even.\n")
            return False

        # Valid!
        self.size = size
        self.bc_pre("^R%s^~ has set the board size to ^C%d^~.\n" % (player, size))
        self.init_layout()

    def move(self, player, src_bits, dst_bits):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You can't move; you're not playing!\n")
            return False

        if seat != self.turn:
            self.tell_pre(player, "You must wait for your turn to move.\n")
            return False

        src_c, src_r = src_bits
        dst_c, dst_r = dst_bits

        # Are they valid?
        if (not self.layout.is_valid(src_r, src_c) or
           not self.layout.is_valid(dst_r, dst_c)):
            self.tell_pre(player, "Your move is out of bounds.\n")
            return False

        # Is it an orthogonal move?
        c_delta = abs(src_c - dst_c)
        r_delta = abs(src_r - dst_r)
        if c_delta > 1 or r_delta > 1 or (c_delta and r_delta):
            self.tell_pre(player, "You can only make a single-space orthogonal move.\n")
            return False

        # Is there a piece for this player in the source location?
        src_loc = self.layout.grid[src_r][src_c]
        if not src_loc or src_loc.data.owner != seat:
            self.tell_pre(player, "You must have a piece in the source location.\n")
            return False

        # Is there a piece for the other player in the destination location?
        dst_loc = self.layout.grid[dst_r][dst_c]
        if not dst_loc or dst_loc.data.owner == seat:
            self.tell_pre(player, "Your opponent must have a piece in the destination location.\n")
            return False

        # Phew.  Success.  Make the capture.
        src_str = "%s%s" % (COLS[src_c], src_r + 1)
        dst_str = "%s%s" % (COLS[dst_c], dst_r + 1)
        self.bc_pre("%s moves a piece from ^C%s^~ to ^G%s^~.\n" % (self.get_sp_str(seat), src_str, dst_str))
        self.layout.move(src_r, src_c, dst_r, dst_c, True)

        return True

    def has_capture(self, seat):

        # We loop through the board, checking each piece to see if it's for
        # this player.  If so, we check its four adjacencies to see if one
        # of them is for the other player.  If so, there's still a valid
        # capture this player can make.
        for r in range(self.size):
            for c in range(self.size):
                loc = self.layout.grid[r][c]
                if loc and loc.data.owner == seat:
                    for r_delta, c_delta in CONNECTION_DELTAS:
                        new_r = r + r_delta
                        new_c = c + c_delta
                        if self.layout.is_valid(new_r, new_c):
                            dst = self.layout.grid[new_r][new_c]
                            if dst and dst.data.owner != seat:
                                return True

        # We never found a valid capture.
        return False

    def remove(self, player, remove_bits):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You can't remove; you're not playing!\n")
            return False

        if seat != self.turn:
            self.tell_pre(player, "You must wait for your turn to remove.\n")
            return False

        c, r = remove_bits

        # Is it within bounds?
        if not self.layout.is_valid(r, c):
            self.tell_pre(player, "Your remove is out of bounds.\n")
            return False

        # Does this player have a piece there?
        loc = self.layout.grid[r][c]
        if not loc or loc.data.owner != seat:
            self.tell_pre(player, "You must have a piece there to remove.\n")
            return False

        # Do they have a valid capture instead?
        if self.has_capture(seat):
            self.tell_pre(player, "You have a capture left.\n")
            return False

        # All right, remove the piece.
        loc_str = "%s%s" % (COLS[c], r + 1)
        self.bc_pre("%s removes a piece from ^R%s^~.\n" % (self.get_sp_str(seat), loc_str))
        self.layout.remove(r, c, True)

        return True

    def resign(self, player):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You can't resign; you're not playing!\n")
            return False

        if seat != self.turn:
            self.tell_pre(player, "You must wait for your turn to resign.\n")
            return False

        self.resigner = seat
        self.bc_pre("%s is resigning from the game.\n" % self.get_sp_str(seat))
        return True

    def tick(self):

        # If both seats are occupied and the game is active, start.
        if (self.state.get() == "need_players" and self.red.player and
           self.blue.player and self.active):
            self.bc_pre("%s: ^C%s^~; %s: ^C%s^~\n" % (self.red.data.seat_str, self.red.player_name, self.blue.data.seat_str, self.blue.player_name))
            self.state.set("playing")
            self.turn = self.red
            self.send_board()

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.lower().split()
            primary = command_bits[0]

            if state == "setup":

                if primary in ("size", "sz"):

                    if len(command_bits) == 2:
                        self.set_size(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid size command.\n")
                    handled = True

                elif primary in ("done", "ready", "d", "r",):

                    self.bc_pre("The game is now looking for players.\n")
                    self.state.set("need_players")
                    handled = True

            elif state == "need_players":

                if primary in ("config", "setup", "conf",):

                    self.bc_pre("^R%s^~ has switched the game to setup mode.\n" % player)
                    self.state.set("setup")
                    handled = True

            elif state == "playing":

                made_move = False

                if primary in ("move", "play", "mv", "pl",):

                    move_bits = demangle_move(command_bits[1:])
                    if move_bits and len(move_bits) == 2:
                        made_move = self.move(player, move_bits[0], move_bits[1])
                    else:
                        self.tell_pre(player, "Invalid move command.\n")
                    handled = True

                elif primary in ("remove", "re",):

                    move_bits = demangle_move(command_bits[1:])
                    if move_bits and len(move_bits) == 1:
                        made_move = self.remove(player, move_bits[0])
                    else:
                        self.tell_pre(player, "Invalid remove command.\n")
                    handled = True

                elif primary in ("resign",):

                    made_move = self.resign(player)
                    handled = True

                if made_move:

                    # Did someone win?
                    winner = self.find_winner()

                    if winner:

                        # Yup!
                        self.resolve(winner)
                        self.finish()
                    else:

                        # No.  Change turns and send the board to listeners.
                        self.turn = self.next_seat(self.turn)
                        self.send_board()

        if not handled:
            self.tell_pre(player, "Invalid command.\n")

    def find_winner(self):

        # Did someone resign?
        if self.resigner == self.red:
            return self.blue
        elif self.resigner == self.blue:
            return self.red

        # Like most connection games, we will do a recursive check.  Unlike
        # most connection games, we're looking for a lack of pieces, not
        # their existence.  In addition, if both players won at the same
        # time, the mover loses.  We need two distinct adjacency maps since
        # we're looking at blank spaces, not pieces of a given color, and
        # those blank spaces can be used by either side.
        self.blue.data.adjacency_map = []
        self.red.data.adjacency_map = []
        for i in range(self.size):
            self.blue.data.adjacency_map.append([None] * self.size)
            self.red.data.adjacency_map.append([None] * self.size)

        self.red.data.won = False
        self.blue.data.won = False

        for i in range(self.size):
            if not self.red.data.won and not self.layout.grid[0][i]:
                self.recurse(self.red, 0, i)
            if not self.blue.data.won and not self.layout.grid[i][0]:
                self.recurse(self.blue, i, 0)

        # Handle the double-win state (mover loses) first.
        if self.red.data.won and self.blue.data.won:
            if self.turn == self.red:
                return self.blue
            else:
                return self.red

        # Now, normal winning states.
        elif self.red.data.won:
            return self.red
        elif self.blue.data.won:
            return self.blue

        # No winner.
        return None

    def recurse(self, seat, row, col):

        # Bail if this seat's already won.
        if seat.data.won:
            return

        # Bail if we're off the board.
        if not self.layout.is_valid(row, col):
            return

        # Bail if we've been here.
        if seat.data.adjacency_map[row][col]:
            return

        # Bail if there's a piece here.
        if self.layout.grid[row][col]:
            return

        # All right.  Empty and we haven't been here.  Mark.
        seat.data.adjacency_map[row][col] = True

        # Did we hit the winning side for this player?
        if seat == self.blue and col == self.size - 1:
            seat.data.won = True
            return
        elif seat == self.red and row == self.size - 1:
            seat.data.won = True
            return

        # Not a win yet.  Recurse over adjacencies.
        for r_delta, c_delta in CONNECTION_DELTAS:
            self.recurse(seat, row + r_delta, col + c_delta)

    def resolve(self, winner):

        self.send_board()
        self.bc_pre("%s wins!\n" % self.get_sp_str(winner))

    def show_help(self, player):

        super(Talpa, self).show_help(player)
        player.tell_cc("\nTALPA SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("             ^!size^. <size>,  ^!sz^.     Set board to <size>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nTALPA PLAY:\n\n")
        player.tell_cc("          ^!move^. <ln> <ln2>, ^!mv^.     Move from <ln> to <ln2> (letter number).\n")
        player.tell_cc("               ^!remove^. <ln> ^!re^.     Remove piece at <ln> (letter number).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
