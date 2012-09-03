# Giles: y.py
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

from giles.utils import booleanize
from giles.utils import demangle_move
from giles.state import State
from giles.games.game import Game
from giles.games.seat import Seat

# What are the minimum and maximum sizes for the board?
Y_MIN_SIZE = 2
Y_MAX_SIZE = 26

#      . 0
#     . . 1
#    . . . 2
#   . . . . 3
#  0 1 2 3
#
# (1, 2) is adjacent to (1, 1), (2, 2), (0, 2), (1, 3), (2, 3), and (0, 1).
Y_DELTAS = ((0, -1), (0, 1), (-1, 0), (1, 0), (1, 1), (-1, -1))

# Because we're lazy and use a square board despite the shape of the Y, we
# fill the rest of the square with invalid characters that match neither
# side.  Define white and black here too.
INVALID = "invalid"
WHITE = "white"
BLACK = "black"


COL_CHARACTERS="abcdefghijklmnopqrstuvwxyz"

class Y(Game):
    """A Y game table implementation.  Invented by Claude Shannon.
    Adapted from my Volity implementation.
    """

    def __init__(self, server, table_name):

        super(Y, self).__init__(server, table_name)

        self.game_display_name = "Y"
        self.game_name = "y"
        self.seats = [
            Seat("White"),
            Seat("Black"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RY^~): "
        self.log_prefix = "%s/%s " % (self.table_display_name, self.game_display_name)

        # Y-specific guff.
        self.seats[0].data.color = WHITE
        self.seats[0].data.color_code = "^W"
        self.seats[1].data.color = BLACK
        self.seats[1].data.color_code = "^K"
        self.board = None
        self.printable_board = None
        self.size = 19
        self.empty_space_count = None
        self.master = False
        self.turn = None
        self.turn_number = 0
        self.move_list = []
        self.last_moves = []
        self.resigner = None

        # Y requires both seats, so may as well mark them active.
        self.seats[0].active = True
        self.seats[1].active = True

        self.init_board()

    def init_board(self):

        self.board = []
        self.empty_space_count = 0

        # We're going to be lazy and build a square board, then fill the
        # half that doesn't make the proper shape with invalid marks.
        # The number of empty spaces on a Y board is equal to the sizeth
        # triangular number; we abuse that to get the right empty space
        # count while we're at it.
        for x in range(self.size):
            self.board.append([None] * self.size)
            self.empty_space_count += x + 1

            # Looking at the grid above, you can see that for a given column,
            # all row values less than that value are invalid.
            for y in range(x):
                self.board[x][y] = INVALID

        # That's it!

    def set_size(self, player, size_str):

        if not size_str.isdigit():
            player.tell_cc(self.prefix + "You didn't even send a number!\n")
            return False

        new_size = int(size_str)
        if new_size < Y_MIN_SIZE or new_size > Y_MAX_SIZE:
            player.tell_cc(self.prefix + "Too small or large.  Must be %s to %s inclusive.\n" % (Y_MIN_SIZE, Y_MAX_SIZE))
            return False

        # Got a valid size.
        self.size = new_size
        self.init_board()
        self.update_printable_board()
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the size of the board to ^C%s^~.\n" % (player, str(new_size)))
        return True

    def set_master(self, player, master_str):

        master_bool = booleanize(master_str)
        if master_bool:
            if master_bool > 0:
                self.master = True
                display_str = "^Con^~"
            else:
                self.master = False
                display_str = "^coff^~"
            self.channel.broadcast_cc(self.prefix + "^R%s^~ has turned ^GMaster Y^~ mode %s.\n" % (player, display_str))
        else:
            player.tell_cc(self.prefix + "Not a valid boolean!\n")

    def move(self, seat, move_list):

        move_count = len(move_list)

        # If we're in normal Y mode and there's more than one move, bail.
        if (not self.master) and move_count != 1:
            seat.player.tell_cc(self.prefix + "You can only make one move per turn.\n")
            return None

        # If you're in master mode and it's the first turn, only one move.
        if self.master and self.turn_number == 1 and move_count != 1:
            seat.player.tell_cc(self.prefix + "You can only make one move on the first turn.\n")
            return None

        # You make two moves per turn in master mode (unless there's only
        # one space left on the board).
        if self.master and self.turn_number > 1 and move_count != 2:
            if not (self.empty_space_count == 1 and move_count == 1):
                seat.player.tell_cc(self.prefix + "You must make two moves per turn.\n")
                return None

        valid_moves = []
        move_strs = []
        for x, y in move_list:
            move_str = "%s%s" % (COL_CHARACTERS[x], y + 1)

            # Check bounds.
            if (x < 0 or x > y or y >= self.size):
                seat.player.tell_cc(self.prefix + "^R%s^~ is out of bounds.\n" % move_str)
                return None

            if self.board[x][y]:
                seat.player.tell_cc(self.prefix + "^R%s^~ is already occupied.\n" % move_str)
                return None

            # Is it a move we've already made this turn?
            for other_move in valid_moves:
                if other_move == (x, y):
                    seat.player.tell_cc(self.prefix + "You can't move to the same place twice!\n")
                    return None

            # It's a valid move.  Add it to the list.
            valid_moves.append((x, y))
            move_strs.append(move_str)

        # All the moves were valid.  Make them.
        self.last_moves = []
        for x, y in valid_moves:
            self.board[x][y] = seat.data.color
            self.last_moves.append((x, y))
        move_str = ", ".join(move_strs)
        self.channel.broadcast_cc(self.prefix + seat.data.color_code + "%s^~ has moved to ^C%s^~.\n" % (seat.player_name, move_str))
        self.empty_space_count -= move_count
        return (valid_moves)

    def swap(self):

        # This is an easy one.  Take the first move and change the piece
        # on the board from white to black.
        self.board[self.move_list[0][0][0]][self.move_list[0][0][1]] = BLACK
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ has swapped ^WWhite^~'s first move.\n" % self.seats[1].player_name)
        self.turn_number += 1

    def update_printable_board(self):

        self.printable_board = []
        slash_line = " "
        char_line = ""
        for x in range(self.size):
            msg = " "
            color_char = "^W"
            if x % 2 == 0:
                color_char = "^K"
            slash_line += color_char + "/^~ "
            char_line += "%s " % COL_CHARACTERS[x]
            for spc in range(self.size - x):
                msg += " "
            for y in range(x + 1):
                piece = self.board[y][x]
                if (y, x) in self.last_moves:
                    msg += "^5"
                if piece == BLACK:
                    msg += "^Kx^~ "
                elif piece == WHITE:
                    msg += "^Wo^~ "
                elif y % 2 == 0:
                    msg += "^m,^~ "
                else:
                    msg += "^M.^~ "
            msg += "- " + str(x + 1) + "\n"
            self.printable_board.append(msg)
        self.printable_board.append(slash_line + "\n")
        self.printable_board.append(char_line + "\n")

    def print_board(self, player):

        if not self.printable_board:
            self.update_printable_board()
        for line in self.printable_board:
            player.tell_cc(line)

    def get_turn_str(self):
        if self.state.get() == "playing":
            if self.seats[0].data.color == self.turn:
                color_word = "^WWhite^~"
                name_word = "^R%s^~" % self.seats[0].player_name
            else:
                color_word = "^KBlack^~"
                name_word = "^Y%s^~" % self.seats[1].player_name
            return "It is %s's turn (%s).\n" % (name_word, color_word)
        else:
            return "The game is not currently active.\n"

    def send_board(self):

        for player in self.channel.listeners:
            self.print_board(player)

    def resign(self, seat):

        # Okay, this person can resign; it's their turn, after all.
        self.channel.broadcast_cc(self.prefix + "^R%s^~ is resigning from the game.\n" % seat.player_name)
        self.resigner = seat.data.color
        return True

    def show(self, player):
        self.print_board(player)
        player.tell_cc(self.get_turn_str())

    def show_help(self, player):

        super(Y, self).show_help(player)
        player.tell_cc("\nY SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("              ^!size^. <size>, ^!sz^.     Set board to size <size>.\n")
        player.tell_cc("             ^!master^. on|off, ^!m^.     Enable/disable Master Y mode.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nY PLAY:\n\n")
        player.tell_cc("      ^!move^. <ln>, ^!play^., ^!mv^., ^!pl^.     Make move <ln> (letter number).\n")
        player.tell_cc("                         ^!swap^.     Swap the first move (only Black, only their first).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player and
           self.seats[1].player and self.active):
            self.state.set("playing")
            self.channel.broadcast_cc(self.prefix + "^WWhite^~: ^R%s^~; ^KBlack^~: ^Y%s^~\n" %
               (self.seats[0].player_name, self.seats[1].player_name))
            self.turn = WHITE
            self.turn_number = 1
            self.send_board()
            self.channel.broadcast_cc(self.prefix + self.get_turn_str())

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        state = self.state.get()

        command_bits = command_str.split()
        primary = command_bits[0].lower()
        if state == "setup":

            if primary in ('size', 'sz'):
                if len(command_bits) == 2:
                    self.set_size(player, command_bits[1])
                else:
                    player.tell_cc(self.prefix + "Invalid size command.\n")
                handled = True

            elif primary in ('master', 'm'):
                if len(command_bits) == 2:
                    self.set_master(player, command_bits[1])
                else:
                    player.tell_cc(self.prefix + "Invalid master command.\n")
                handled = True

            elif primary in ('done', 'ready', 'd', 'r'):

                self.channel.broadcast_cc(self.prefix + "The game is now looking for players.\n")
                self.state.set("need_players")
                handled = True

        elif state == "need_players":

            if primary in ('config', 'setup', 'conf'):
                self.state.set("setup")
                self.channel.broadcast_cc(self.prefix + "^R%s^~ has switched the game to setup mode.\n" %
                   (player))
                handled = True

        elif state == "playing":

            made_move = False

            # For all move types, don't bother if it's not this player's turn.
            if primary in ('move', 'mv', 'play', 'pl', 'swap', 'resign'):

                seat = self.get_seat_of_player(player)
                if not seat:
                    player.tell_cc(self.prefix + "You can't move; you're not playing!\n")
                    return

                elif seat.data.color != self.turn:
                    player.tell_cc(self.prefix + "You must wait for your turn to move.\n")
                    return

            if primary in ('move', 'mv', 'play', 'pl'):
                move_bits = demangle_move(command_bits[1:])
                if move_bits:
                    success = self.move(seat, move_bits)
                    if success:
                        move = success
                        made_move = True
                    else:
                        player.tell_cc(self.prefix + "Unsuccessful move.\n")
                else:
                    player.tell_cc(self.prefix + "Unsuccessful move.\n")

                handled = True

            elif primary in ('swap',):

                if self.turn_number == 2 and seat.player == player:
                    self.swap()
                    move = "swap"
                    made_move = True

                else:
                    player.tell_cc(self.prefix + "Unsuccessful swap.\n")

                handled = True

            elif primary in ('resign',):

                if self.resign(seat):
                    move = "resign"
                    made_move = True

                handled = True

            if made_move:

                self.update_printable_board()
                self.send_board()
                self.move_list.append(move)
                self.turn_number += 1

                winner = self.find_winner()
                if winner:
                    self.resolve(winner)
                    self.finish()
                else:
                    if self.turn == WHITE:
                        self.turn = BLACK
                    else:
                        self.turn = WHITE
                    self.channel.broadcast_cc(self.prefix + self.get_turn_str())

        if not handled:
            player.tell_cc(self.prefix + "Invalid command.\n")

    def find_winner(self):


        # First, check resignations; that's a fast bail.
        if self.resigner:
            if self.resigner == WHITE:
                return self.seats[1].player_name
            elif self.resigner == BLACK:
                return self.seats[0].player_name
            else:
                self.server.log.log(self.log_prefix + "Weirdness; a resign that's not a player.")
                return None

        # Well, darn, we have to do actual work.  Time for recursion!
        # To calculate a winner:
        #    - Pick a side.
        #    - For each piece on that side, see if it's connected to
        #      both other sides.  If so, that player is a winner.
        #    - If not, there is no winner (as winners must connect all
        #      three sides).

        self.found_winner = None
        self.adjacency = []

        # Set up our adjacency checker.
        for i in range(self.size):
            self.adjacency.append([None] * self.size)

        # For each piece on the left side of the board...
        for i in range(self.size):
            if self.board[0][i]:

                # We're not touching the other two sides yet.
                self.touch_bottom = False
                self.touch_right = False
                self.update_adjacency(0, i, self.board[0][i])

                if self.found_winner == WHITE:
                    return self.seats[0].player_name
                elif self.found_winner == BLACK:
                    return self.seats[1].player_name

        # No winner yet.
        return None

    def update_adjacency(self, x, y, color):

        # Skip work if a winner's already found.
        if self.found_winner:
            return

        # Skip work if we're off the board.
        if (x < 0 or x > y or y >= self.size):
            return

        # Skip work if we've been here already.
        if self.adjacency[x][y]:
            return

        # Skip work if it's empty or for the other player.
        this_cell = self.board[x][y]
        if this_cell != color:
            return

        # All right, it's this player's cell.  Mark it visited.
        self.adjacency[x][y] = color

        # If we're on either the bottom or right edges, mark that.
        if (y == self.size - 1):
            self.touch_bottom = True

        if (x == y):
            self.touch_right = True

        # Bail if we've met both win conditions.
        if self.touch_bottom and self.touch_right:
            self.found_winner = color

        # Okay, no winner yet.  Recurse on the six adjacent cells.
        for x_delta, y_delta in Y_DELTAS:
            self.update_adjacency(x + x_delta, y + y_delta, color)

    def resolve(self, winner):
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % (winner))
