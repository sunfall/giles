# Giles: square_oust.py
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

TAGS = ["abstract", "capture", "square", "2p"]

class SquareOust(SeatedGame):
    """A Square Oust game table implementation.  Invented in 2007 by Mark Steere.
    """

    def __init__(self, server, table_name):

        super(SquareOust, self).__init__(server, table_name)

        self.game_display_name = "Square Oust"
        self.game_name = "square_oust"
        self.seats = [
            Seat("Black"),
            Seat("White"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RSquare Oust^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Square Oust-specific stuff.
        self.height = 11
        self.width = 11
        self.turn = None
        self.black = self.seats[0]
        self.black.data.seat_str = "^KBlack^~"
        self.black.data.groups = []
        self.black.data.made_move = False
        self.white = self.seats[1]
        self.white.data.seat_str = "^WWhite^~"
        self.white.data.groups = []
        self.white.data.made_move = False
        self.resigner = None
        self.layout = None
        self.move_was_capture = False

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

    def get_new_piece(self, seat):

        if seat == self.black:
            p = Piece("^K", "x", "X")
        else:
            p = Piece("^W", "o", "O")
        p.data.owner = seat
        p.data.adjacencies = []
        p.data.size = 1
        p.data.num = id(p)

        return p

    def replace(self, old, new):

        # First step: Replace the actual pieces on the board.
        for r in range(self.height):
            for c in range(self.width):
                if self.layout.grid[r][c] == old:
                    self.layout.place(new, r, c, update=False)
        self.layout.update()

        # Second step: Get rid of it from the group list of its owner.
        owner = new.data.owner
        owner.data.groups.remove(old)

        # Third step: Replace instances of it in the other player's group
        # adjacencies.
        for group in self.next_seat(owner).data.groups:
            if old in group.data.adjacencies:
                group.data.adjacencies.remove(old)
                if new not in group.data.adjacencies:
                    group.data.adjacencies.append(new)

    def remove(self, dead_group):

        # Like above, except removing this time.
        for r in range(self.height):
            for c in range(self.width):
                if self.layout.grid[r][c] == dead_group:
                    self.layout.remove(r, c, update=False)
        self.layout.update()

        owner = dead_group.data.owner
        owner.data.groups.remove(dead_group)

        for group in self.next_seat(owner).data.groups:
            if dead_group in group.data.adjacencies:
                group.data.adjacencies.remove(dead_group)

    def update_board(self, row, col):

        # We just put a fresh piece at this location; it will have to be
        # incorporated into everything else that's on the board.
        this_piece = self.layout.grid[row][col]

        # Look at all of the adjacencies and collapse the same-color groups
        # into one.  Collate the unique enemy groups as well, as we may be
        # capturing them.
        other_adjacencies = []
        potential_capture = False
        for r_delta, c_delta in CONNECTION_DELTAS:
            new_r = row + r_delta
            new_c = col + c_delta
            if self.layout.is_valid(new_r, new_c):
                loc = self.layout.grid[new_r][new_c]
                if loc and loc.data.owner == this_piece.data.owner:
                    potential_capture = True
                    if loc != this_piece:

                        # New same-color group to collapse.
                        other_adjacencies.extend([x for x in loc.data.adjacencies
                           if x not in other_adjacencies])
                        new_size = this_piece.data.size + loc.data.size
                        if this_piece.data.num < loc.data.num:
                            self.replace(loc, this_piece)
                        else:
                            self.replace(this_piece, loc)
                            this_piece = loc

                        # Whichever "won," set the new size.
                        this_piece.data.size = new_size
                elif loc:

                    # A group of the other player.  Add to other adjacencies if
                    # it's not already there.
                    if loc not in other_adjacencies:
                        other_adjacencies.append(loc)

        # After having collapsed all of the same-colored groups, we look to see
        # if this is a potential capture.  If not, we can't affect the opponent's
        # groups, other than to become adjacent to them.  If so, all groups in the
        # list of other adjacencies must be removed from the board.
        if potential_capture:
            for group in other_adjacencies:
                self.remove(group)

            # By definition, a capturing group has no enemy adjacencies.
            this_piece.data.adjacencies = []

            # Return the number of groups we captured.
            return len(other_adjacencies)

        else:

            # Set the adjacency list.
            this_piece.data.adjacencies = other_adjacencies

            # Add ourselves to those pieces' adjacency lists.
            for group in other_adjacencies:
                if this_piece not in group.data.adjacencies:
                    group.data.adjacencies.append(this_piece)

            # No captures.
            return 0

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

        # Is this move a valid play?
        if not self.is_valid_play(seat, row, col):
            self.tell_pre(player, "That move is not valid.\n")
            return False

        # Valid.  Put a piece there.
        move_str = "%s%s" % (COLS[col], row + 1)
        piece = self.get_new_piece(seat)
        seat.data.groups.append(piece)
        self.layout.place(piece, row, col, True)

        # Update the board, making any captures.
        capture_str = ""
        self.move_was_capture = False
        capture_count = self.update_board(row, col)
        if capture_count:
            capture_str = ", ^Ycapturing %s^~" % (get_plural_str(capture_count, "group"))
            self.move_was_capture = True
        self.bc_pre("%s places a piece at ^C%s^~%s.\n" % (self.get_sp_str(seat), move_str, capture_str))

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

                        # No.  If the move was not a capturing move, see if the
                        # next player has a move; if so, change turns.  If not,
                        # print a message and stay here.
                        other = self.next_seat(self.turn)
                        if not self.move_was_capture:
                            if not self.has_move(other):
                                self.bc_pre("%s has no valid move; ^Rskipping their turn^~.\n" % self.get_sp_str(other))
                            else:
                                self.turn = other

                        elif not self.has_move(self.turn):
                            self.bc_pre("%s has no further valid moves.\n" % self.get_sp_str(self.turn))
                            self.turn = other

                        else:
                            self.bc_pre("%s continues their turn.\n" % self.get_sp_str(self.turn))

                        # No matter what, send the board again.
                        self.send_board()

        if not handled:
            self.tell_pre(player, "Invalid command.\n")

    def is_valid_play(self, seat, row, col):

        # Obviously we can't place a piece if there's already one here or we're
        # out of bounds.
        if not self.layout.is_valid(row, col) or self.layout.grid[row][col]:
            return False

        # Okay; can we place a piece here?  Check the adjacent spaces; if there
        # are any pieces owned by this seat, the sum total of their sizes must
        # be equal to the largest enemy group adjacent either to them or this
        # new piece.  If there are no pieces owned by this seat, it's valid.
        same_list = []
        same_total = 0
        largest_other = 0

        for r_delta, c_delta in CONNECTION_DELTAS:
            new_r = row + r_delta
            new_c = col + c_delta
            if self.layout.is_valid(new_r, new_c):
                loc = self.layout.grid[new_r][new_c]
                if loc and loc.data.owner == seat:
                    if loc not in same_list:
                        same_list.append(loc)
                        same_total += loc.data.size
                        for other in loc.data.adjacencies:
                            if other.data.size > largest_other:
                                largest_other = other.data.size
                elif loc:
                    if loc.data.size > largest_other:
                        largest_other = loc.data.size

        # If we didn't find an adjacent same-colored piece, it is immediately
        # valid.
        if not same_total:
            return True

        # If we found same-colored pieces but no other groups, this is not a
        # valid play.
        if not largest_other:
            return False

        # Otherwise, check the sum from the same_list and see if that equals
        # or is greater than the largest other group.
        if same_total >= largest_other:
            return True

        # Not a valid play.
        return False

    def has_move(self, seat):

        for r in range(self.height):
            for c in range(self.width):
                if self.is_valid_play(seat, r, c):
                    return True

        # We checked every location and found no legitimate location.  No move.
        return False

    def find_winner(self):

        # Did someone resign?
        if self.resigner == self.white:
            return self.black
        elif self.resigner == self.black:
            return self.white

        # If one player has no pieces left, the other player won.
        if not len(self.white.data.groups) and self.white.data.made_move:
            return self.black
        elif not len(self.black.data.groups) and self.black.data.made_move:
            return self.white

        # No winner.
        return None

    def resolve(self, winner):

        self.send_board()
        self.bc_pre("%s wins!\n" % self.get_sp_str(winner))

    def show_help(self, player):

        super(SquareOust, self).show_help(player)
        player.tell_cc("\nSQUARE OUST SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("             ^!size^. <size>,  ^!sz^.     Set board to <size>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nSQUARE OUST PLAY:\n\n")
        player.tell_cc("      ^!move^. <ln>, ^!play^., ^!mv^., ^!pl^.     Make move <ln> (letter number).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
