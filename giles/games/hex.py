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
from giles.state import State
from giles.games.game import Game
from giles.games.seat import Seat

# What are the minimum and maximum sizes for the board?
HEX_MIN_SIZE = 3
HEX_MAX_SIZE = 26

#      . . . . 0
#     . . . . 1
#    . . . . 2
#   . . . . 3
#  0 1 2 3
#
# (1, 2) is adjacent to (1, 1), (2, 2), (0, 2), (1, 3), (2, 3), and (0, 1).
HEX_DELTAS = ((0, -1), (0, 1), (-1, 0), (1, 0), (1, 1), (-1, -1))

WHITE = "white"
BLACK = "black"


COL_CHARACTERS="abcdefghijklmnopqrstuvwxyz"

class Hex(Game):
    """A Hex game table implementation.  Invented independently by Piet
    Hien and John Nash.  Adapted from both my Giles Y implementation and
    my Volity Hex implementation.
    """

    def __init__(self, server, table_name):

        super(Hex, self).__init__(server, table_name)

        self.game_display_name = "Hex"
        self.game_name = "hex"
        self.seats = [
            Seat("White"),
            Seat("Black"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("config")
        self.prefix = "(^RHex^~): "
        self.log_prefix = "%s/%s " % (self.game_display_name, self.game_name)
        self.debug = True

        # Hex-specific guff.
        self.seats[0].color = WHITE
        self.seats[0].color_code = "^W"
        self.seats[1].color = BLACK
        self.seats[1].color_code = "^K"
        self.board = None
        self.size = 14
        self.turn = None
        self.turn_number = 0
        self.move_list = []
        self.resigner = None
        self.last_x = None
        self.last_y = None
        self.is_quickstart = False
        
        self.init_board()

    def init_board(self):

        self.board = []
        for x in range(self.size):
            self.board.append([None] * self.size)

    def set_size(self, player, size_str):

        if not size_str.isdigit():
            player.tell_cc(self.prefix + "You didn't even send a number!\n")
            return False

        new_size = int(size_str)
        if new_size < HEX_MIN_SIZE or new_size > HEX_MAX_SIZE:
            player.tell_cc(self.prefix + "Too small or large.  Must be %s to %s inclusive.\n" % (HEX_MIN_SIZE, HEX_MAX_SIZE))
            return False

        # Got a valid size.
        self.size = new_size
        self.init_board()
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the size of the board to ^C%s^~.\n" % (player.display_name, str(new_size)))
        return True

    def move_to_values(self, move_str):

        # All valid moves are of the form g22, J15, etc.  Ditch blatantly
        # invalid moves.
        if type(move_str) != str or len(move_str) < 2 or len(move_str) > 3:
            return None

        # First character must be in COL_CHARACTERS.
        col_char = move_str[0].lower()
        if col_char not in COL_CHARACTERS:
            return None
        else:
            x = COL_CHARACTERS.index(col_char)

        # Next one or two must be digits.
        row_chars = move_str[1:]
        if not row_chars.isdigit():
            return None
        else:
            y = int(row_chars) - 1

        # Now verify that these are even in range for this board.
        if (x < 0 or x >= self.size or y < 0 or y >= self.size):
            return None
        
        # Valid!
        return (x, y)

    def move(self, seat, move_str):

        # Get the actual values of the move.
        values = self.move_to_values(move_str)
        if not values:
            seat.player.tell_cc(self.prefix + "Invalid move.\n")
            return None

        x, y = values
        if self.board[x][y]:
            seat.player.tell_cc(self.prefix + "That space is already occupied.\n")
            return None

        # Okay, it's an unoccupied space!  Let's make the move.
        self.board[x][y] = seat.color
        self.channel.broadcast_cc(self.prefix + seat.color_code + "%s^~ has moved to ^C%s^~.\n" % (seat.player.display_name, move_str))
        self.last_x = x
        self.last_y = y
        return (x, y)

    def swap(self):

        # In Hex, to get the equivalent piece for the other player, it
        # must be swapped along the x = y axis.  That is, x <-> y for
        # the piece.  Easy enough!

        self.board[self.move_list[0][0]][self.move_list[0][1]] = None
        self.board[self.move_list[0][1]][self.move_list[0][0]] = BLACK
        self.last_x, self.last_y = self.last_y, self.last_x
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ has swapped ^WWhite^~'s first move.\n" % self.seats[1].player.display_name)

    def print_board(self, player):

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
            for y in range(self.size):
                piece = self.board[y][x]
                if y == self.last_x and x == self.last_y:
                    msg += "^I"
                if piece == BLACK:
                    msg += "^Kx^~ "
                elif piece == WHITE:
                    msg += "^Wo^~ "
                elif y % 2 == 0:
                    msg += "^m,^~ "
                else:
                    msg += "^M.^~ "
            msg += "- " + str(x + 1) + "\n"
            player.tell_cc(msg)
        player.tell_cc(slash_line + "\n")
        player.tell_cc(char_line + "\n")

    def get_turn_str(self):
        if self.state.get() == "playing":
            if self.seats[0].color == self.turn:
                color_word = "^WWhite/Horizontal^~"
                name_word = "^R%s^~" % self.seats[0].player.display_name
            else:
                color_word = "^KBlack/Vertical^~"
                name_word = "^Y%s^~" % self.seats[1].player.display_name
            return "It is %s's turn (%s).\n" % (name_word, color_word)
        else:
            return "The game is not currently active.\n"

    def send_board(self):

        for player in self.channel.listeners:
            self.print_board(player)

    def resign(self, seat):

        # Okay, this person can resign; it's their turn, after all.
        self.channel.broadcast_cc(self.prefix + "^R%s^~ is resigning from the game.\n" % seat.player.display_name)
        self.resigner = seat.color
        return True

    def show(self, player):
        self.print_board(player)
        player.tell_cc(self.get_turn_str())

    def show_help(self, player):

        super(Hex, self).show_help(player)
        player.tell_cc("\nHEX SETUP PHASE:\n\n")
        player.tell_cc("              ^!size^. <size>, ^!sz^.     Set board to size <size>.\n")
        player.tell_cc("        ^!quickstart^. on|off, ^!qs^.     Enable quickstart mode.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nHEX PLAY:\n\n")
        player.tell_cc("      ^!move^. <ln>, ^!play^., ^!mv^., ^!pl^.     Make move <ln> (letter number).\n")
        player.tell_cc("                         ^!swap^.     Swap the first move (only Black, only their first).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")

    def quickstart(self, player, qs_str):

        qs_bool = booleanize(qs_str)
        if qs_bool:
            if qs_bool > 0:
                self.is_quickstart = True
                display_str = "^Con^~"
            else:
                self.is_quickstart = False
                display_str = "^coff^~"
            self.channel.broadcast_cc(self.prefix + "^R%s^~ has turned quickstart mode %s.\n" % (player.display_name, display_str))
        else:
            player.tell_cc(self.prefix + "Not a valid boolean!\n")

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        state = self.state.get()

        command_bits = command_str.strip().split()
        primary = command_str.split()[0].lower()
        if state == "config":

            if primary in ('size', 'sz'):
                if len(command_bits) == 2:
                    self.set_size(player, command_bits[1])
                else:
                    player.tell_cc(self.prefix + "Invalid size command.\n")
                handled = True

            elif primary in ('quickstart', 'headstart', 'qs', 'hs'):

                if len(command_bits) == 2:
                    self.quickstart(player, command_bits[1])
                else:
                    player.tell_cc(self.prefix + "Invalid quickstart command.\n")
                handled = True

            elif primary in ('done', 'ready', 'd', 'r'):

                self.channel.broadcast_cc(self.prefix + "The game is now ready for players.\n")
                self.state.set("need_players")
                handled = True

        elif state == "need_players":

            # If both seats are full and the game is active, time to
            # play!

            if self.seats[0].player and self.seats[1].player and self.active:
                self.state.set("playing")
                self.channel.broadcast_cc(self.prefix + "^WWhite/Horizontal^~: ^R%s^~; ^KBlack/Vertical^~: ^Y%s^~\n" %
                   (self.seats[0].player.display_name, self.seats[1].player.display_name))
                self.turn = WHITE
                self.turn_number = 1

                # If quickstart mode is on, make the quickstart moves.
                if self.is_quickstart:
                    middle = self.size / 2
                    self.board[0][middle] = BLACK
                    self.board[self.size - 1][middle] = BLACK
                    self.board[middle][0] = WHITE
                    self.board[middle][self.size - 1] = WHITE
                self.send_board()
                self.channel.broadcast_cc(self.prefix + self.get_turn_str())

        elif state == "playing":

            made_move = False

            # For all move types, don't bother if it's not this player's turn.
            if primary in ('move', 'mv', 'play', 'pl', 'swap', 'resign'):

                seat = self.get_seat_of_player(player)
                if not seat:
                    player.tell_cc(self.prefix + "You can't move; you're not playing!\n")
                    return

                elif seat.color != self.turn:
                    player.tell_cc(self.prefix + "You must wait for your turn to move.\n")
                    return

            if primary in ('move', 'mv', 'play', 'pl'):
                if len(command_bits) == 2:
                    success = self.move(seat, command_bits[1])
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
                return self.seats[1].player
            elif self.resigner == BLACK:
                return self.seats[0].player
            else:
                self.server.log.log(self.log_prefix + "Weirdness; a resign that's not a player.")
                return None

        # Well, darn, we have to do actual work.  Time for recursion!
        # To calculate a winner:
        # - Start on one edge.
        # - Recursively mark pieces of the same colour adjacent to that one.
        # - If you're about to mark a piece on the opposite edge, there's a
        #   winner!
        #
        # You only have to run this algorithm on two edges, one for each
        # player.  Which is precisely what we're going to do.

        self.found_winner = None
        self.adjacency = []

        # Set up our adjacency checker.
        for i in range(self.size):
            self.adjacency.append([None] * self.size)

        # Check both edges.
        for i in range(self.size):
            if self.board[0][i]:
                self.update_adjacency(0, i, WHITE)
            if self.board[i][0]:
                self.update_adjacency(i, 0, BLACK)

        if self.found_winner == WHITE:
            return self.seats[0].player
        elif self.found_winner == BLACK:
            return self.seats[1].player

        # No winner yet.
        return None

    def update_adjacency(self, x, y, color):

        # Skip work if a winner's already found.
        if self.found_winner:
            return

        # Skip work if we're off the board.
        if (x < 0 or x >= self.size or y < 0 or y >= self.size):
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

        # If we're on the winning edge for this player, success!
        # They have won.
        if ((color == WHITE and x == self.size - 1) or
           (color == BLACK and y == self.size - 1)):
            self.found_winner = color
            return

        # Okay, no winner yet.  Recurse on the six adjacent cells.
        for x_delta, y_delta in HEX_DELTAS:
            self.update_adjacency(x + x_delta, y + y_delta, color)
        
    def resolve(self, winner):
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % (winner.display_name))
