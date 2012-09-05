# Giles: metamorphosis.py
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
from giles.games.seat import Seat
from giles.state import State
from giles.utils import booleanize
from giles.utils import demangle_move

# Some useful default values.
MIN_SIZE = 4
MAX_SIZE = 26

BLACK = "black"
WHITE = "white"

COLS = "abcdefghijklmnopqrstuvwxyz"

# Adjacency in Metamorphosis is strictly orthogonal.
CONNECTION_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))

class Metamorphosis(Game):
    """A Metamorphosis game table implementation.  Invented in 2009 by Gregory
    Keith Van Patten.  Play seems to show that ko fight mode is definitely
    superior to the alternative, so we set it as default.
    """

    def __init__(self, server, table_name):

        super(Metamorphosis, self).__init__(server, table_name)

        self.game_display_name = "Metamorphosis"
        self.game_name = "metamorphosis"
        self.seats = [
            Seat("Black"),
            Seat("White")
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RMetamorphosis^~): "
        self.log_prefix = "%s/%s " % (self.table_display_name, self.game_display_name)

        # Metamorphosis-specific stuff.
        self.board = None
        self.printable_board = None
        self.size = 12
        self.ko_fight = True
        self.group_count = None
        self.turn = None
        self.turn_number = 0
        self.seats[0].data.side = BLACK
        self.seats[0].data.last_was_ko = False
        self.seats[1].data.side = WHITE
        self.seats[1].data.last_was_ko = False
        self.last_r = None
        self.last_c = None
        self.resigner = None

        self.init_board()

    def init_board(self):

        self.board = []

        # Generate a new empty board.  Boards alternate the starting checkered
        # layout, which we can pregen.
        white_first_row = []
        black_first_row = []
        for c in range(self.size):
            if c % 2:
                white_first_row.append(BLACK)
                black_first_row.append(WHITE)
            else:
                white_first_row.append(WHITE)
                black_first_row.append(BLACK)

        # Then we just add the appropriate rows, two at a time.
        for r in range(self.size / 2):
            self.board.append(white_first_row[:])
            self.board.append(black_first_row[:])

        # Count the number of groups on the board.  Should be size^2.
        self.group_count = self.get_group_count()

    def update_printable_board(self):

        self.printable_board = []
        col_str = "    " + "".join([" " + COLS[i] for i in range(self.size)])
        self.printable_board.append(col_str + "\n")
        self.printable_board.append("   ^m.=" + "".join(["=="] * self.size) + ".^~\n")
        for r in range(self.size):
            this_str = "%2d ^m|^~ " % (r + 1)
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
            this_str += "^m|^~ %d" % (r + 1)
            self.printable_board.append(this_str + "\n")
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
            color_msg = "^KBlack/Vertical^~"
        else:
            player = self.seats[1].player_name
            color_msg = "^WWhite/Horizontal^~"

        return ("It is ^Y%s^~'s turn (%s)." % (player, color_msg))

    def is_valid(self, row, col):

        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            return False
        return True

    def get_group_count(self):

        # Counting groups can be done in a single pass, even if the groups
        # are complicated.  It is done as follows:
        # - Check the color in a location and the locations above and to the
        #   left.
        # - If it's the same color as only one of them, assign ourselves the
        #   group ID of that piece;
        # - If it's the same color as /both/, and they have distinct group IDs,
        #   reassign the higher-numbered group ID to the lower group ID, as this
        #   piece joins those two groups;
        # - If it's the same color as neither, add a new group ID.
        # At the end, we simply count the number of distinct group IDs.

        # Build a temporary board tracking the IDs of each spot.
        id_board = []
        for r in range(self.size):
            id_board.append([None] * self.size)

        id_dict = {}
        curr_id = 0
        for r in range(self.size):
            for c in range(self.size):
                self_color = self.board[r][c]
                above_color = None
                left_color = None
                if r - 1 >= 0:
                    above_color = self.board[r - 1][c]
                if c - 1 >= 0:
                    left_color = self.board[r][c - 1]

                if self_color == above_color:

                    # Definitely a group above.  Check to see if it's the same
                    # to the left too.
                    group_id = id_dict[id_board[r - 1][c]]
                    if self_color == left_color:

                        # Same color.  Are they the same group ID?
                        left_id = id_dict[id_board[r][c - 1]]
                        if left_id == group_id:

                            # Yup.  Use it.
                            id_board[r][c] = group_id

                        else:

                            # This piece joins two previously-distinct groups.
                            # Update the ID dict to collapse those two groups
                            # into one and use the lower-valued one for this
                            # space.
                            if left_id < group_id:
                                id_dict[group_id] = left_id
                                id_board[r][c] = left_id
                            else:
                                id_dict[left_id] = group_id
                                id_board[r][c] = group_id

                    else:

                        # Different color left, same color above.  Use the
                        # above ID.
                        id_board[r][c] = group_id

                elif self_color == left_color:

                    # Group to the left, but not above.  Use the left ID.
                    id_board[r][c] = id_dict[id_board[r][c - 1]]

                else:

                    # No group in either direction.  New group.
                    id_board[r][c] = curr_id
                    id_dict[curr_id] = curr_id
                    curr_id += 1

        # Now that we're done with those shenanigans, count the number of unique
        # groups on the board.
        unique_set = set()
        for group_id in id_dict:
            if id_dict[group_id] not in unique_set:
                unique_set.add(id_dict[group_id])

        return len(unique_set)

    def flip(self, row, col):

        curr = self.board[row][col]
        if curr == BLACK:
            self.board[row][col] = WHITE
        else:
            self.board[row][col] = BLACK

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

        # Does this move increase the number of groups on the board?
        self.flip(row, col)
        new_group_count = self.get_group_count()
        if new_group_count > self.group_count:

            # Yup.  Flip it back and inform the player.
            self.flip(row, col)
            player.tell_cc(self.prefix + "That move increases the group count.\n")
            return False

        move_is_ko = False
        ko_str = ""
        # If we're in ko fight mode, check to see if a ko move is valid.
        if new_group_count == self.group_count:
            move_is_ko = True
            ko_str = ", a ko move"

            if not self.ko_fight:

                # Flip it back; we're not in ko fight mode.
                self.flip(row, col)
                player.tell_cc(self.prefix + "That is a ko move and does not decrease the group count.\n")
                return False

            elif seat.data.last_was_ko:

                # Flip it back; two kos in a row is not allowed.
                self.flip(row, col)
                player.tell_cc(self.prefix + "That is a ko move and you made a ko move last turn.\n")
                return False

            elif row == self.last_r and col == self.last_c:

                # Flip it back; this is the same move their opponent just made.
                self.flip(row, col)
                player.tell_cc(self.prefix + "You cannot repeat your opponent's last move.\n")
                return False

        # This is a valid move.  Apply, announce.
        play_str = "%s%s" % (COLS[col], row + 1)
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ flips the piece at ^C%s^~%s.\n" % (seat.player, play_str, ko_str))
        self.last_r = row
        self.last_c = col
        self.turn_number += 1
        self.group_count = new_group_count

        # If it was a ko move, mark the player as having made one, so they
        # can't make another the next turn.  Otherwise clear that bit.
        if move_is_ko:
            seat.data.last_was_ko = True
        else:
            seat.data.last_was_ko = False

        return True

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player
           and self.seats[1].player and self.active):
            self.state.set("playing")
            self.channel.broadcast_cc(self.prefix + "^KBlack/Vertical^~: ^R%s^~; ^WWhite/Horizontal^~: ^Y%s^~\n" %
               (self.seats[0].player, self.seats[1].player))
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

        if size % 2:
            player.tell_cc(self.prefix + "Size must be even.\n")
            return

        # Valid!
        self.size = size
        self.channel.broadcast_cc(self.prefix + "^R%s^~ has set the board size to ^C%d^~.\n" % (player, size))
        self.init_board()
        self.update_printable_board()

    def set_ko_fight(self, player, ko_str):

        ko_bool = booleanize(ko_str)
        if ko_bool:
            if ko_bool > 0:
                self.ko_fight = True
                display_str = "^Con^~"
            else:
                self.ko_fight = False
                display_str = "^coff^~"
            self.channel.broadcast_cc(self.prefix + "^R%s^~ has turned ^Gko fight^~ mode %s.\n" % (player, display_str))

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

        # Like Hex, a swap in Metamorphosis requires a translation to make it the
        # equivalent move for the other player.

        self.flip(self.last_r, self.last_c)
        self.flip(self.last_c, self.last_r)
        self.last_c, self.last_r = self.last_r, self.last_c

        self.channel.broadcast_cc("^Y%s^~ has swapped ^KBlack^~'s first move.\n" % (player))
        self.turn_number += 1

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.split()
            primary = command_bits[0]

            if state == "setup":

                if primary in ("size", "sz",):

                    if len(command_bits) == 2:
                        self.set_size(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid size command.\n")
                    handled = True

                elif primary in ("ko",):

                    if len(command_bits) == 2:
                        self.set_ko_fight(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid ko command.\n")
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
        # top and left edges to see whether a player has won.
        self.found_winner = False
        self.adjacency_map = []
        for i in range(self.size):
            self.adjacency_map.append([None] * self.size)

        for i in range(self.size):
            if self.board[i][0] == WHITE:
                self.recurse_adjacency(WHITE, i, 0)
            if self.board[0][i] == BLACK:
                self.recurse_adjacency(BLACK, 0, i)

        # ...except that it has to be at the end of the OTHER player's turn!
        if self.found_winner == BLACK and self.turn == WHITE:
            return self.seats[0].player_name
        elif self.found_winner == WHITE and self.turn == BLACK:
            return self.seats[1].player_name

        # No winner yet.
        return None

    def recurse_adjacency (self, color, row, col):

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
        if ((color == WHITE and col == self.size - 1) or
           (color == BLACK and row == self.size - 1)):

            # Success!
            self.found_winner = color
            return

        # Not a win yet.  Recurse over adjacencies.
        for r_delta, c_delta in CONNECTION_DELTAS:
            self.recurse_adjacency(color, row + r_delta, col + c_delta)

    def resolve(self, winner):
        self.send_board()
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % winner)

    def show_help(self, player):

        super(Metamorphosis, self).show_help(player)
        player.tell_cc("\nMETAMORPHOSIS SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("                    ^!ko^. on|off     Enable/disable ko fight mode.\n")
        player.tell_cc("             ^!size^. <size>,  ^!sz^.     Set board to <size>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nMETAMORPHOSIS PLAY:\n\n")
        player.tell_cc("      ^!move^. <ln>, ^!play^., ^!mv^., ^!pl^.     Make move <ln> (letter number).\n")
        player.tell_cc("                         ^!swap^.     Swap the first move (only White, only their first).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
