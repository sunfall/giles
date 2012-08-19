# Giles: rps.py
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

from giles.state import State
from giles.games.game import Game
from giles.games.seat import Seat

class RockPaperScissors(Game):
    """A Rock-Paper-Scissors game table implementation.
    """

    def __init__(self, server, table_name):

        super(RockPaperScissors, self).__init__(server, table_name)

        self.game_display_name = "Rock-Paper-Scissors"
        self.game_name = "rps"
        self.seats = [
            Seat("Left"),
            Seat("Right"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.plays = [None, None]
        self.prefix = "(^RRPS^~): "
        self.log_prefix = "%s/%s" % (self.game_display_name, self.game_name)
        self.debug = False

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        state = self.state.get()

        # If we were looking for players, check to see if both
        # seats are full and the game is active.  If so, we're
        # ready to play.
        if state == "need_players":

            if self.seats[0].player and self.seats[1].player and self.active:
                self.state.set("need_moves")
                self.channel.broadcast_cc(self.prefix + "Left: ^Y%s^~; Right: ^Y%s^~\n" %
                   (self.seats[0].player.display_name, self.seats[1].player.display_name))
                self.channel.broadcast_cc(self.prefix + "Players, make your moves!\n")

        elif state == "need_moves":

            primary = command_str.split()[0].lower()
            if primary in ('r', 'p', 's', 'rock', 'paper', 'scissors'):
                self.move(player, primary)
                handled = True

            if self.plays[0] and self.plays[1] and self.active:

                # Got the moves!
                self.resolve()
                self.finish()

        if not handled:
            player.tell_cc(self.prefix + "Invalid command.\n")

    def show_help(self, player):

        super(RockPaperScissors, self).show_help(player)
        player.tell_cc("\nROCK-PAPER-SCISSORS:\n\n")
        player.tell_cc("                      ^!rock^., ^!r^.     Throw rock.\n")
        player.tell_cc("                     ^!paper^., ^!p^.     Throw paper.\n")
        player.tell_cc("                  ^!scissors^., ^!s^.     Throw scissors.\n")

    def move(self, player, play):

        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "You're not playing in this game!\n")
            return

        if play in ('r', 'rock'):
            this_move = "rock"
        elif play in ('p', 'paper'):
            this_move = "paper"
        elif play in ('s', 'scissors'):
            this_move = "scissors"
        else:
            player.tell_cc(self.prefix + "Invalid play.\n")
            return

        self.channel.broadcast_cc(self.prefix + "%s's hand twitches.\n" % player.display_name)

        if seat == self.seats[0]:
            self.plays[0] = this_move
        else:
            self.plays[1] = this_move

    def resolve(self):

        one = self.plays[0]
        two = self.plays[1]
        one_name = self.seats[0].player.display_name
        two_name = self.seats[1].player.display_name
        self.channel.broadcast_cc(self.prefix + "Jan... ken... pon... Throwdown time!\n")
        self.channel.broadcast_cc(self.prefix + "%s throws %s; %s throws %s!\n" % (one_name, one, two_name, two))
        if one == two:
            msg = "It's a tie!\n"
        elif ((one == "rock" and two == "paper") or
           (one == "paper" and two == "scissors") or
           (one == "scissors" and two == "rock")):
            msg = two_name + " wins!\n"
        else:
            msg = one_name + " wins!\n"
        self.channel.broadcast_cc(msg)

    def remove_player(self, player):

        # Not only do we want to do the standard things, but if this person
        # really is a player, we want to invalidate their throw.  That way
        # you're not stuck with another player's throw mid-game.
        if self.seats[0].player == player:
            self.plays[0] = None
        elif self.seats[1].player == player:
            self.plays[1] = None
        super(RockPaperScissors, self).remove_player(player)
