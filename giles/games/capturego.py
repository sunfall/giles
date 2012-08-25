# Giles: capturego.py
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
from giles.utils import demangle_move

import giles.games.goban

# Some useful default values.
MIN_SIZE = giles.games.goban.MIN_SIZE
MAX_SIZE = giles.games.goban.MAX_SIZE

BLACK = giles.games.goban.BLACK
WHITE = giles.games.goban.WHITE

LETTERS = giles.games.goban.LETTERS

class CaptureGo(Game):
    """A Capture Go game table implementation.  One-Capture Go was invented by
    Yasuda Yashutoshi.
    """

    def __init__(self, server, table_name):

        super(CaptureGo, self).__init__(server, table_name)

        self.game_display_name = "Capture Go"
        self.game_name = "capturego"
        self.seats = [
            Seat("Black"),
            Seat("White")
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RCapture Go^~): "
        self.log_prefix = "%s/%s" % (self.table_display_name, self.game_display_name)

        # Capture Go-specific stuff.
        self.turn = None
        self.seats[0].data.side = BLACK
        self.seats[1].data.side = WHITE
        self.seats[0].data.capture_list = []
        self.seats[1].data.capture_list = []
        self.capture_goal = 1
        self.resigner = None
        self.turn_number = 0
        self.goban = giles.games.goban.Goban()

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

        if self.turn == BLACK:
            player = self.seats[0].player
            color_msg = "^KBlack^~"
        else:
            player = self.seats[1].player
            color_msg = "^WWhite^~"

        to_return = "It is ^Y%s^~'s turn (%s).\n" % (player, color_msg)
        to_return += "^KBlack^~ has captured %s. ^WWhite^~ has captured %s.\n" % (self.get_stone_str(len(self.seats[0].data.capture_list)), self.get_stone_str(len(self.seats[1].data.capture_list)))
        to_return += ("The goal is to capture %s.\n" % self.get_stone_str(self.capture_goal))
        return(to_return)

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player
           and self.seats[1].player and self.active):
            self.state.set("playing")
            self.channel.broadcast_cc(self.prefix + "^KBlack^~: ^R%s^~; ^WWhite^~: ^Y%s^~\n" %
               (self.seats[0].player, self.seats[1].player))
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

        # Valid!
        self.goban.resize(w, h)
        self.channel.broadcast_cc(self.prefix + "^R%s^~ has set the board size to ^C%d^Gx^C%d^~.\n" % (player, w, h))

    def set_capture_goal(self, player, count_bits):

        # Bail on garbage.
        if len(count_bits) != 1 or not count_bits[0].isdigit():
            player.tell_cc(self.prefix + "Invalid capture count command.\n")
            return

        count = int(count_bits[0])
        if count < 1:
            player.tell_cc(self.prefix + "Count must be at least 1.\n")
            return

        # Valid.  Yes, you can set this astronomically high; since Capture Go does not
        # allow passing, I guess you could keep filling the board up over and over to
        # reach a capture goal.
        self.capture_goal = count
        self.channel.broadcast_cc(self.prefix + "^R%s^~ has set the capture goal to ^C%s^~.\n" % (player, self.get_stone_str(count)))

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

        # Okay, this looks like a legitimate move.
        move_return = self.goban.go_play(seat.data.side, row, col)

        if not move_return:
            player.tell_cc(self.prefix + "That move was unsuccessful.  Weird.\n")
            return False

        else:
            coords, capture_color, capture_list = move_return
            move_str = "%s%s" % (LETTERS[col], row + 1)
            capture_str = ""
            capturer = None
            if capture_color == seat.data.side:

                # Suicide.  The opponent is the "capturer" in this case.
                capture_str += ", ^Rsuiciding %s^~" % (self.get_stone_str(len(capture_list)))
                if seat == self.seats[0]:
                    capturer = self.seats[1]
                else:
                    capturer = self.seats[0]

            elif capture_color:

                # Captured opponent pieces!
                capture_str += ", ^!capturing %s^." % (self.get_stone_str(len(capture_list)))
                capturer = seat

            # If there was a capturer, update their capture list.
            if capturer:
                capturer.data.capture_list.extend(capture_list)

            # And no matter what, print information about the move.
            self.channel.broadcast_cc("^Y%s^~ places a stone at ^C%s^~%s.\n" % (player, move_str, capture_str))

            self.turn_number += 1

            return True

    def swap(self, player):

        self.goban.invert()
        self.channel.broadcast_cc("^Y%s^~ has swapped ^KBlack^~'s first move.\n" % (player))

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.strip().split()
            primary = command_bits[0]

            if state == "setup":

                if primary in ("size", "sz",):

                    self.set_size(player, command_bits[1:])
                    handled = True

                if primary in ("count", "goal", "ct",):
                    self.set_capture_goal(player, command_bits[1:])
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
            return self.seats[0].player
        elif self.resigner == BLACK:
            return self.seats[1].player

        # If someone's capture count has reached the goal, they win.
        if len(self.seats[0].data.capture_list) >= self.capture_goal:
            return self.seats[0].player
        if len(self.seats[1].data.capture_list) >= self.capture_goal:
            return self.seats[1].player

        # No winner yet.
        return None

    def resolve(self, winner):
        self.send_board()
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % winner)

    def show_help(self, player):

        super(Breakthrough, self).show_help(player)
        player.tell_cc("\nCAPTURE GO SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("    ^!size^. <size> | <w> <h>, ^!sz^.     Set board to <size>x<size>/<w>x<h>.\n")
        player.tell_cc("            ^!count^. <num>, ^!goal^.     Set capture goal to <num> stones.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nCAPTURE GO PLAY:\n\n")
        player.tell_cc("                ^!move^. <ln>, ^!mv^.     Place stone at <ln> (letter number).\n")
        player.tell_cc("                         ^!swap^.     Swap first move (White only, first only).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
