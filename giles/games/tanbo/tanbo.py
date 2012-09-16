# Giles: tanbo.py
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
from giles.utils import demangle_move, get_plural_str

# Deltas are useful.
CONNECTION_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))

class Tanbo(Game):
    """A Tanbo game table implementation.  Invented in 1993 by Mark Steere.
    This only implements the 2p version, although it does have the 9x9, 13x13,
    and 19x19 sizes.  There's also an undocumented 5x5 grid strictly for
    testing.
    """

    def __init__(self, server, table_name):

        super(Tanbo, self).__init__(server, table_name)

        self.game_display_name = "Tanbo"
        self.game_name = "tanbo"
        self.seats = [
            Seat("Black"),
            Seat("White"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RTanbo^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Tanbo-specific stuff.
        self.size = 19
        self.turn = None
        self.black = self.seats[0]
        self.black.data.seat_str = "^KBlack^~"
        self.black.data.root_list = []
        self.white = self.seats[1]
        self.white.data.seat_str = "^WWhite^~"
        self.white.data.root_list = []
        self.resigner = None
        self.layout = None

        # Initialize the starting layout.
        self.init_layout()

    def get_root_piece(self, seat, num):
        if seat == self.black:
            p = Piece("^K", "x", "X")
            p.data.owner = self.black
        else:
            p = Piece("^W", "o", "O")
            p.data.owner = self.white
        p.data.num = num
        return p

    def init_layout(self):

        # Create the layout and fill it with pieces.
        self.layout = SquareGridLayout(highlight_color = "^I")
        self.layout.resize(self.size)

        black_count = 0
        white_count = 0
        self.black.data.root_list = []
        self.white.data.root_list = []

        # There are three different layouts depending on the size.  All of them
        # alternate between black and white pieces; the two larger ones have 16
        # roots, whereas the smallest size has 4.  (There's a 5x5 grid for
        # testing as well.)
        if self.size == 5:
            jump_delta = 4
            extent = 2
            offset = 0
        elif self.size == 9:
            jump_delta = 6
            extent = 2
            offset = 1
        elif self.size == 13:
            jump_delta = 4
            extent = 4
            offset = 0
        else: # self.size == 19
            jump_delta = 6
            extent = 4
            offset = 0
        for i in range(extent):
            for j in range(extent):
                if (i + j) % 2:
                    p = self.get_root_piece(self.black, black_count)
                    self.black.data.root_list.append(p)
                    black_count += 1
                else:
                    p = self.get_root_piece(self.white, white_count)
                    self.white.data.root_list.append(p)
                    white_count += 1
                row = offset + i * jump_delta
                col = offset + j * jump_delta
                p.data.start = (row, col)
                self.layout.place(p, row, col)
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

        if size != 5 and size != 9 and size != 13 and size != 19:
            self.tell_pre(player, "Size must be 9, 13, or 19.\n")
            return False

        # Valid!
        self.size = size
        self.bc_pre("^R%s^~ has set the board size to ^C%d^~.\n" % (player, size))
        self.init_layout()

    def can_place_at(self, seat, row, col):

        # You can place a piece in Tanbo iff it is adjacent to exactly one of
        # your own pieces.  If a location is valid, we'll return the piece that
        # is adjacent; otherwise we return nothing.

        if self.layout.grid[row][col]:

            # Occupied; clearly can't place here.
            return None

        adj_count = 0
        for r_delta, c_delta in CONNECTION_DELTAS:
            new_r = row + r_delta
            new_c = col + c_delta
            if self.layout.is_valid(new_r, new_c):
                loc = self.layout.grid[new_r][new_c]
                if loc and loc.data.owner == seat:
                    piece = loc
                    adj_count += 1

        if adj_count == 1:
            return piece
        else:
            return None

    def recurse_is_bound(self, piece, row, col, prev_row, prev_col):

        # Thanks to the way Tanbo placement works, we don't have to worry about
        # loops, so we can get away with not using an adjacenty map and instead
        # just track the direction we came from.
        #
        # Bail if this isn't a valid location.
        if not self.layout.is_valid(row, col):
            return True

        loc = self.layout.grid[row][col]

        # If there's no piece here, see if we can place one.
        if not loc:
            if self.can_place_at(piece.data.owner, row, col):

                # Yup.  This root isn't bound.
                return False

            else:

                # No, this location is binding.
                return True

        elif loc != piece:

            # Some other root.  Definitely binding.
            return True

        else:

            # Okay, it's another part of this root.  Recurse, but don't double
            # back.
            for r_delta, c_delta in CONNECTION_DELTAS:
                new_r = row + r_delta
                new_c = col + c_delta
                if new_r != prev_row or new_c != prev_col:
                    if not self.recurse_is_bound(piece, new_r, new_c, row, col):

                        # A recursive call found a liberty.  Awesome!
                        return False

            # All of the recursive calls returned that they were bound.  This
            # (sub)root is bound.
            return True

    def root_is_bound(self, piece):

        # We'll just start recursing at the root's starting location and find
        # whether it's bound or not.
        row, col = piece.data.start
        return self.recurse_is_bound(piece, row, col, None, None)

    def kill_root(self, piece):

        # We could do this recursively, but we're lazy.
        for r in range(self.size):
            for c in range(self.size):
                loc = self.layout.grid[r][c]
                if loc == piece:
                    self.layout.remove(r, c)

        # Remove this root from the owner's root list.
        piece.data.owner.data.root_list.remove(piece)

    def update_roots(self, row, col):

        # If the piece at row, col is part of a bounded root, that root is killed.
        piece = self.layout.grid[row][col]
        if self.root_is_bound(piece):
            self.kill_root(piece)

            # -1 indicates a suicide.
            return -1

        # Not a suicide; loop through all roots, finding bound ones.
        bound_root_list = []
        all_roots = self.black.data.root_list[:]
        all_roots.extend(self.white.data.root_list)
        for root in all_roots:
            if self.root_is_bound(root):
                bound_root_list.append(root)

        bound_count = 0
        for bound_root in bound_root_list:
            self.kill_root(bound_root)
            bound_count += 1

        # Return the number of roots we killed.
        return bound_count

    def move(self, player, move_bits):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You can't move; you're not playing!\n")
            return False

        if seat != self.turn:
            self.tell_pre(player, "You must wait for your turn to move.\n")
            return False

        col, row = move_bits

        # Is the move on the board?
        if not self.layout.is_valid(row, col):
            self.tell_pre(player, "Your move is out of bounds.\n")
            return False

        # Is it a valid Tanbo play?
        piece = self.can_place_at(seat, row, col)
        if not piece:
            self.tell_pre(player, "That location is not adjacent to exactly one of your pieces.\n")
            return False

        # Valid.  Put the piece there.
        move_str = "%s%s" % (COLS[col], row + 1)
        self.layout.place(piece, row, col, True)

        # Update the root statuses.
        root_kill_str = ""
        root_kill = self.update_roots(row, col)
        if root_kill < 0:
            root_kill_str = ", ^ysuiciding the root^~"
        elif root_kill > 0:
            root_kill_str = ", ^Ykilling %s^~" % (get_plural_str(root_kill, "root"))
        self.bc_pre("%s grows a root to ^C%s^~%s.\n" % (self.get_sp_str(seat), move_str, root_kill_str))

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
        if (self.state.get() == "need_players" and self.black.player and
           self.white.player and self.active):
            self.bc_pre("%s: ^C%s^~; %s: ^C%s^~\n" % (self.black.data.seat_str, self.black.player_name, self.white.data.seat_str, self.white.player_name))
            self.state.set("playing")
            self.turn = self.black
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
                    if move_bits and len(move_bits) == 1:
                        made_move = self.move(player, move_bits[0])
                    else:
                        self.tell_pre(player, "Invalid move command.\n")
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
        if self.resigner == self.white:
            return self.black
        elif self.resigner == self.black:
            return self.white

        # If one player has no pieces left, the other player won.
        if not len(self.white.data.root_list):
            return self.black
        elif not len(self.black.data.root_list):
            return self.white

        # No winner.
        return None

    def resolve(self, winner):

        self.send_board()
        self.bc_pre("%s wins!\n" % self.get_sp_str(winner))

    def show_help(self, player):

        super(Tanbo, self).show_help(player)
        player.tell_cc("\nTANBO SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("            ^!size^. 9|13|19,  ^!sz^.     Set board to <size>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nTANBO PLAY:\n\n")
        player.tell_cc("      ^!move^. <ln>, ^!play^., ^!mv^., ^!pl^.     Make move <ln> (letter number).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
