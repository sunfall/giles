# Giles: gonnect.py
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
from giles.games.seat import Seat
from giles.state import State
from giles.utils import booleanize
from giles.utils import demangle_move

import giles.games.goban

# Some useful default values.
MIN_SIZE = giles.games.goban.MIN_SIZE
MAX_SIZE = giles.games.goban.MAX_SIZE

BLACK = giles.games.goban.BLACK
WHITE = giles.games.goban.WHITE

LETTERS = giles.games.goban.LETTERS

TEST_RIGHT = "->"
TEST_DOWN = "v"

SQUARE_DELTAS = giles.games.goban.SQUARE_DELTAS

class Gonnect(SeatedGame):
    """A Gonnect table implementation.  Gonnect was invented by Joao Pedro
    Neto in 2000.
    """

    def __init__(self, server, table_name):

        super(Gonnect, self).__init__(server, table_name)

        self.game_display_name = "Gonnect"
        self.game_name = "gonnect"
        self.seats = [
            Seat("Black"),
            Seat("White")
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RGonnect^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Gonnect-specific stuff.
        self.turn = None
        self.seats[0].data.side = BLACK
        self.seats[0].data.dir_str = "/Vertical"
        self.seats[1].data.side = WHITE
        self.seats[1].data.dir_str = "/Horizontal"
        self.directional = False
        self.resigner = None
        self.turn_number = 0
        self.goban = giles.games.goban.Goban()

        # A traditional Gonnect board is 13x13.
        self.goban.resize(13, 13)

    def show(self, player):

        if not self.goban.printable_board:
            self.goban.update_printable_board()
        for line in self.goban.printable_board:
            player.tell_cc(line)
        player.tell_cc(self.get_supplemental_str())

    def send_board(self):

        for player in self.channel.listeners:
            self.show(player)

    def get_stone_str(self, count):

        if count == 1:
           return "1 stone"
        return "%d stones" % count

    def get_supplemental_str(self):

        if not self.turn:
            return ("The game has not yet started.\n")

        dir_str = ""
        if self.turn == BLACK:
            player = self.seats[0].player_name
            if self.directional:
                dir_str = self.seats[0].data.dir_str
            color_msg = "^KBlack" + dir_str + "^~"
        else:
            player = self.seats[1].player_name
            if self.directional:
                dir_str = self.seats[1].data.dir_str
            color_msg = "^WWhite" + dir_str + "^~"

        to_return = "It is ^Y%s^~'s turn (%s).\n" % (player, color_msg)
        return(to_return)

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player
           and self.seats[1].player and self.active):
            self.state.set("playing")
            if self.directional:
                black_dir_str = self.seats[0].data.dir_str
                white_dir_str = self.seats[1].data.dir_str
            else:
                black_dir_str = ""
                white_dir_str = ""
            self.channel.broadcast_cc(self.prefix + "^KBlack%s^~: ^R%s^~; ^WWhite%s^~: ^Y%s^~\n" %
               (black_dir_str, self.seats[0].player, white_dir_str, self.seats[1].player))
            self.turn = BLACK
            self.turn_number = 1
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

        if w < MIN_SIZE or w > MAX_SIZE or h < MIN_SIZE or h > MAX_SIZE:
            player.tell_cc(self.prefix + "Width and height must be between %d and %d inclusive.\n" % (MIN_SIZE, MAX_SIZE))
            return

        # We disallow uneven boards if we have directional goals.
        if self.directional and w != h:
            player.tell_cc(self.prefix + "Directional games must have square boards.\n")
            return

        # Valid!
        self.goban.resize(w, h)
        self.channel.broadcast_cc(self.prefix + "^R%s^~ has set the board size to ^C%d^Gx^C%d^~.\n" % (player, w, h))

    def set_directional(self, player, dir_bits):

        dir_bool = booleanize(dir_bits)
        if dir_bool:
            if dir_bool > 0:
                if self.goban.height != self.goban.width:
                    player.tell_cc(self.prefix + "Cannot change to directional with uneven sides.  Resize first.\n")
                    return
                self.directional = True
                display_str = "^Con^~"
            elif dir_bool < 0:
                self.directional = False
                display_str = "^coff^~"
            self.channel.broadcast_cc(self.prefix + "^R%s^~ has turned directional goals %s.\n" % (player, display_str))
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

    def move(self, player, move):

        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "You can't move; you're not playing!\n")
            return False

        if self.turn != seat.data.side:
            player.tell_cc(self.prefix + "You must wait for your turn to move.\n")
            return False

        # Check bounds.
        col, row = move
        if row < 0 or row >= self.goban.height or col < 0 or col >= self.goban.width:
            player.tell_cc(self.prefix + "Your move is out of bounds.\n")
            return False

        # Check that the space is empty.
        if self.goban.board[row][col]:
            player.tell_cc(self.prefix + "That space is already occupied.\n")
            return False

        # Is this move suicidal?  If so, it can't be played.
        if self.goban.move_is_suicidal(seat.data.side, row, col):
            player.tell_cc(self.prefix + "That move is suicidal.\n")
            return False

        # Does this move cause a repeat of a previous board?
        if self.goban.move_causes_repeat(seat.data.side, row, col):
            player.tell_cc(self.prefix + "That move causes a repeat of a previous board.\n")
            return False

        # Okay, this looks like a legitimate move.
        move_return = self.goban.go_play(seat.data.side, row, col, suicide_is_valid = False)

        if not move_return:
            player.tell_cc(self.prefix + "That move was unsuccessful.  Weird.\n")
            return False

        else:
            coords, capture_color, capture_list = move_return
            move_str = "%s%s" % (LETTERS[col], row + 1)
            capture_str = ""
            if capture_color:

                # Captured opponent pieces!
                capture_str += ", ^!capturing %s^." % (self.get_stone_str(len(capture_list)))

            # And no matter what, print information about the move.
            self.channel.broadcast_cc(self.prefix + "^Y%s^~ places a stone at ^C%s^~%s.\n" % (player, move_str, capture_str))

            self.turn_number += 1

            return True

    def swap(self, player):

        self.goban.invert(self.directional)
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ has swapped ^KBlack^~'s first move.\n" % (player))
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

                    self.set_size(player, command_bits[1:])
                    handled = True

                if primary in ("directional", "goals", "dir", "goal",):
                    self.set_directional(player, command_bits[1])
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
                    if self.turn_number == 2 and self.seats[1].player == player:
                        self.swap(player)
                        made_move = True
                    else:
                        player.tell_cc(self.prefix + "Unsuccessful swap.\n")
                    handled = True

                elif primary in ("resign",):

                    if self.resign(player):
                        made_move = True

                    handled = True

                if made_move:

                    if self.turn == BLACK:
                        self.turn = WHITE
                    else:
                        self.turn = BLACK

                    # Did someone win?
                    winner = self.find_winner()
                    if winner:
                        self.resolve(winner)
                        self.finish()
                    else:
                        # Nope.  show everyone the board, and keep on.
                        self.send_board()

        if not handled:
            player.tell_cc(self.prefix + "Invalid command.\n")

    def reset_adjacency(self):

        self.adjacency_map = []
        for r in range(self.goban.height):
            self.adjacency_map.append([None] * self.goban.width)

    def find_winner(self):

        # If someone resigned, this is the easiest thing ever.
        if self.resigner == WHITE:
            return self.seats[0].player_name
        elif self.resigner == BLACK:
            return self.seats[1].player_name

        # Okay, we have to check the board.  First, determine which
        # checks we need to make.  In a directional game, we only
        # need to test the left and top edges for White and Black
        # respectively; otherwise we need to test both edges for
        # both players.

        self.found_winner = False
        self.reset_adjacency()

        for r in range(self.goban.height):
            self.recurse_adjacencies(WHITE, r, 0, TEST_RIGHT)
        if not self.found_winner:
            for c in range(self.goban.width):
                self.recurse_adjacencies(BLACK, 0, c, TEST_DOWN)

        if not self.found_winner and not self.directional:

            # Gotta test both edges with the other colors.  Reset the
            # adjacency graph, as the previous entries will now conflict.
            self.reset_adjacency()

            for r in range(self.goban.height):
                self.recurse_adjacencies(BLACK, r, 0, TEST_RIGHT)
            if not self.found_winner:
                for c in range(self.goban.width):
                    self.recurse_adjacencies(WHITE, 0, c, TEST_DOWN)

        if self.found_winner == BLACK:
            return self.seats[0].player_name
        elif self.found_winner == WHITE:
            return self.seats[1].player_name

        # Blarg, still no winner.  See if the next player (we've already
        # switched turns) has no valid moves.  If so, the current player
        # wins.
        all_moves_invalid = True
        for r in range(self.goban.height):
            for c in range(self.goban.width):
                if (not self.goban.board[r][c] and
                   not self.goban.move_is_suicidal(self.turn, r, c) and
                   not self.goban.move_causes_repeat(self.turn, r, c)):

                    # Player has a non-suicidal move.  No winner.
                    return None

        # Checked all valid moves for the next player, and they're all
        # suicidal.  This player wins.
        if self.turn == WHITE:
            return self.seats[0].player_name
        else:
            return self.seats[1].player_name

    def recurse_adjacencies(self, color, row, col, test_dir):

        # Bail if a winner's been found.
        if self.found_winner:
            return

        # Bail if we're off the board.
        if (row < 0 or row >= self.goban.height or
           col < 0 or col >= self.goban.width):
            return

        # Bail if we've visited this location.
        if self.adjacency_map[row][col]:
            return

        # Bail if it's the wrong color.
        if self.goban.board[row][col] != color:
            return

        # Okay, it's the right color.  Mark it visited...
        self.adjacency_map[row][col] = True

        # Have we reached the proper side?
        if ((test_dir == TEST_RIGHT and col == self.goban.width - 1) or
           (test_dir == TEST_DOWN and row == self.goban.height - 1)):

           # Winner!
           self.found_winner = color
           return

        # Not a win yet... so we need to test the four adjacencies.
        for r_delta, c_delta in SQUARE_DELTAS:
            self.recurse_adjacencies(color, row + r_delta, col + c_delta,
               test_dir)

    def resolve(self, winner):
        self.send_board()
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % winner)

    def show_help(self, player):

        super(Gonnect, self).show_help(player)
        player.tell_cc("\nGONNECT SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("    ^!size^. <size> | <w> <h>, ^!sz^.     Set board to <size>x<size>/<w>x<h>.\n")
        player.tell_cc("      ^!directional^. off|on, ^!dir^.     Turn directional goals off|on.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nGONNECT PLAY:\n\n")
        player.tell_cc("                ^!move^. <ln>, ^!mv^.     Place stone at <ln> (letter number).\n")
        player.tell_cc("                         ^!swap^.     Swap first move (White only, first only).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
