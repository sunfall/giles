# Giles: redstone.py
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
from giles.utils import demangle_move, get_plural_str

# Useful defaults.
MIN_SIZE = 4
MAX_SIZE = 26

# Deltas are useful.
CONNECTION_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))

class Redstone(SeatedGame):
    """A Redstone game table implementation.  Invented in 2012 by Mark Steere.
    """

    def __init__(self, server, table_name):

        super(Redstone, self).__init__(server, table_name)

        self.game_display_name = "Redstone"
        self.game_name = "redstone"
        self.seats = [
            Seat("Black"),
            Seat("White"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RRedstone^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Redstone-specific stuff.
        self.height = 19
        self.width = 19
        self.turn = None
        self.black = self.seats[0]
        self.black.data.seat_str = "^KBlack^~"
        self.black.data.made_move = False
        self.white = self.seats[1]
        self.white.data.seat_str = "^WWhite^~"
        self.white.data.made_move = False
        self.resigner = None
        self.layout = None

        # Like most abstracts, Redstone doesn't need to differentiate between
        # the pieces on the board.
        self.bp = Piece("^K", "x", "X")
        self.bp.data.owner = self.black
        self.black.data.piece = self.bp
        self.wp = Piece("^W", "o", "O")
        self.wp.data.owner = self.white
        self.white.data.piece = self.wp
        self.rp = Piece("^R", "r", "R")
        self.rp.data.owner = None

        # Initialize the starting layout.
        self.init_layout()

    def init_layout(self):

        # Create the layout.  Empty, so easy.
        self.layout = SquareGridLayout(highlight_color="^I")
        self.layout.resize(self.width, self.height)

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
            self.tell_pre(player, "You didn't even send numbers!\n")
            return

        w = int(width)
        h = int(height)

        if w < MIN_SIZE or w > MAX_SIZE or h < MIN_SIZE or h > MAX_SIZE:
            self.tell_pre(player, "Width and height must be between %d and %d inclusive.\n" % (MIN_SIZE, MAX_SIZE))
            return

        # Valid!
        self.width = w
        self.height = h
        self.bc_pre("^R%s^~ has set the board size to ^C%d^Gx^C%d^~.\n" % (player, w, h))
        self.init_layout()

    def recurse_capture(self, seat, row, col, visited):

        # If it's a dud coordinate, bail.
        if not self.layout.is_valid(row, col):
            return None

        # If we've been here, bail.
        if visited[row][col]:
            return None

        # If it's an empty space, then it's a liberty.
        pos = self.layout.grid[row][col]
        if not pos:
            return []

        # If it's a piece of the other player, bail.
        if pos.data.owner != seat:
            return None

        # Okay.  New piece, right color.  Mark it visited.
        visited[row][col] = True

        # Recurse on adjacencies.  If any return an empty list, this group has
        # a liberty and we return an empty list as well; otherwise we return a
        # concatenation of pieces found further on, for easy removal.
        return_list = [(row, col)]
        for r_delta, c_delta in CONNECTION_DELTAS:
            result = self.recurse_capture(seat, row + r_delta, col + c_delta, visited)
            if result == []:

                # Liberty!  Bail.
                return []
            elif result:

                # Found a subgroup with no liberties.  Extend.
                return_list.extend(result)

        # We never found a liberty.  Return the list of pieces.
        return return_list

    def move_is_capture(self, piece, row, col):

        # Tentatively place the piece here.
        self.layout.place(piece, row, col, update=False)

        # Build the visitation list.
        visited = []
        for r in range(self.height):
            visited.append([None] * self.width)

        # If this piece is not a redstone, we check its own liberties.  We
        # can quickly bail if this succeeds.
        if piece != self.rp:
            if self.recurse_capture(piece.data.owner, row, col, visited):
                self.layout.remove(row, col, update=False)
                return True

        # Now we check the liberties of all four adjacent locations, assuming
        # there's a piece there and it's not a redstone.
        for r_delta, c_delta in CONNECTION_DELTAS:
            new_r = row + r_delta
            new_c = col + c_delta
            if self.layout.is_valid(new_r, new_c):
                pos = self.layout.grid[new_r][new_c]
                if pos and pos != self.rp:

                    # We have to rebuild the visited list for each piece we
                    # check, because of the recursive "bail fast" method we use
                    # for detecting liberties.  This should be improved.
                    visited = []
                    for r in range(self.height):
                        visited.append([None] * self.width)

                    if self.recurse_capture(pos.data.owner, new_r, new_c, visited):

                        # Bail.
                        self.layout.remove(row, col, update=False)
                        return True

        # We never found a capture.  Remove and return.
        self.layout.remove(row, col, update=False)
        return False

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

        # Is there a piece already there?
        if self.layout.grid[row][col]:
            self.tell_pre(player, "There is already a piece there.\n")
            return False

        # Is it a capturing move?
        piece = seat.data.piece
        if self.move_is_capture(piece, row, col):
            self.tell_pre(player, "That would cause a capture.\n")
            return False

        # Valid.  Put a piece there.
        move_str = "%s%s" % (COLS[col], row + 1)
        self.layout.place(piece, row, col, True)

        # Update the board.
        self.bc_pre("%s places a piece at ^C%s^~.\n" % (self.get_sp_str(seat), move_str))

        seat.data.made_move = True
        return True

    def capture(self, row, col):

        # If for some reason this is called and there's not a redstone at this
        # location, bail.
        if self.layout.grid[row][col] != self.rp:
            return -1

        # All right.  Check all four adjacencies; if they no longer have a
        # liberty, capture them.  Note that we come up with the list first,
        # and /then/ execute the captures, as doing them as we find them may
        # give groups liberties during the removal process.

        visited = []
        for r in range(self.height):
            visited.append([None] * self.width)

        capture_list = []
        for r_delta, c_delta in CONNECTION_DELTAS:
            new_r = row + r_delta
            new_c = col + c_delta
            if self.layout.is_valid(new_r, new_c):
                loc = self.layout.grid[new_r][new_c]
                if loc and loc != self.rp:
                    captures = self.recurse_capture(loc.data.owner, new_r, new_c, visited)
                    if captures:
                        capture_list.extend([x for x in captures if x not in capture_list])

        # Remove all pieces in the capture list.
        for capture_r, capture_c in capture_list:
            self.layout.remove(capture_r, capture_c, update=False)

        self.layout.update()

        # Return the number of pieces captured.
        return len(capture_list)

    def red(self, player, move_bits):

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

        # Is there a piece already there?
        if self.layout.grid[row][col]:
            self.tell_pre(player, "There is already a piece there.\n")
            return False

        # Is it not a capturing move?
        piece = self.rp
        if not self.move_is_capture(piece, row, col):
            self.tell_pre(player, "That would not cause a capture.\n")
            return False

        # Valid.  Put the piece there.
        move_str = "%s%s" % (COLS[col], row + 1)
        self.layout.place(piece, row, col, True)

        # Redstones by definition make captures.
        capture_count = self.capture(row, col)

        self.bc_pre("%s places a ^Rredstone^~ at ^C%s^~, ^Ycapturing %s^~.\n" % (self.get_sp_str(seat), move_str, get_plural_str(capture_count, "stone")))

        seat.data.made_move = True
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

                    self.set_size(player, command_bits[1:])
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

                if primary in ("redstone", "red", "r",):

                    move_bits = demangle_move(command_bits[1:])
                    if move_bits and len(move_bits) == 1:
                        made_move = self.red(player, move_bits[0])
                    else:
                        self.tell_pre(player, "Invalid red command.\n")
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

                        # No.  Switch turns.
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

        # If one player has no pieces left, the other player won.  If neither
        # player has a piece, mover wins.
        found_white = False
        found_black = False
        for r in range(self.height):
            for c in range(self.width):
                loc = self.layout.grid[r][c]
                if loc:
                    if loc.data.owner == self.black:
                        found_black = True
                    elif loc.data.owner == self.white:
                        found_white = True

        if not found_black and self.black.data.made_move:
            if not found_white and self.white.data.made_move:

                # Mover wins.
                return self.turn
            else:
                return self.white
        elif not found_white and self.white.data.made_move:
            return self.black

        # No winner yet.
        return None

    def resolve(self, winner):

        self.send_board()
        self.bc_pre("%s wins!\n" % self.get_sp_str(winner))

    def show_help(self, player):

        super(Redstone, self).show_help(player)
        player.tell_cc("\nREDSTONE SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("             ^!size^. <size>,  ^!sz^.     Set board to <size>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nREDSTONE PLAY:\n\n")
        player.tell_cc("      ^!move^. <ln>, ^!play^., ^!mv^., ^!pl^.     Make move <ln> (letter number).\n")
        player.tell_cc("                  ^!red^. <ln>, ^!r^.     Place redstone at <ln> (letter number).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
