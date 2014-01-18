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
from giles.games.seated_game import SeatedGame
from giles.games.seat import Seat

class RockPaperScissors(SeatedGame):
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
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # RPS requires both seats, so may as well mark them active.
        self.seats[0].active = True
        self.seats[1].active = True

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        state = self.state.get()

        if state == "need_moves":

            command_bits = command_str.split()
            primary = command_bits[0].lower()

            # If this player is used to prefacing plays with 'move'/'play',
            # let's be polite and just chomp that away.  Also allow 'throw'
            # and 'th', even though they're undocumented, because they seem
            # like an obvious sort of command to try.  (Read that as: I kept
            # typing it.)
            if primary in ('move', 'play', 'throw', 'mv', 'pl', 'th') and len(command_bits) > 1:
                primary = command_bits[1].lower()
            if primary in ('r', 'p', 's', 'rock', 'paper', 'scissors'):
                self.move(player, primary)
                handled = True

            if self.plays[0] and self.plays[1] and self.active:

                # Got the moves!
                self.resolve()
                self.finish()

        if not handled:
            player.tell_cc(self.prefix + "Invalid command.\n")

    def tick(self):

        # If we were looking for players, check to see if both
        # seats are full and the game is active.  If so, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player and
           self.seats[1].player and self.active):
            self.state.set("need_moves")
            self.channel.broadcast_cc(self.prefix + "Left: ^Y%s^~; Right: ^Y%s^~\n" %
               (self.seats[0].player, self.seats[1].player))
            self.channel.broadcast_cc(self.prefix + "Players, make your moves!\n")

    def show(self, player):

        state = self.state.get()
        if state == "need_players":
            player.tell_cc(self.prefix + "Everyone is hovering around the table, waiting for players.\n")
        elif state == "need_moves":
            for loc, color in ((0, "^Y"), (1, "^M")):
                if self.seats[loc].player:
                    name = repr(self.seats[loc].player)
                    if self.plays[loc]:
                        player.tell_cc(self.prefix + color + name + "^~'s hand is trembling with anticipation.\n")
                    else:
                        player.tell_cc(self.prefix + color + name + "^~ seems to be deep in thought.\n")
                else:
                    player.tell_cc(self.prefix + "^C%s^~ is strangely empty.\n" % self.seats[loc])
        else:
            player.tell_cc(self.prefix + "Nothing to see here.  Move along.\n")

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

        self.channel.broadcast_cc(self.prefix + "%s's hand twitches.\n" % player)

        if seat == self.seats[0]:
            self.plays[0] = this_move
        else:
            self.plays[1] = this_move

    def resolve(self):

        one = self.plays[0]
        two = self.plays[1]
        one_name = "^Y" + repr(self.seats[0].player) + "^~"
        two_name = "^M" + repr(self.seats[1].player) + "^~"
        self.channel.broadcast_cc(self.prefix + "Jan... ken... pon... Throwdown time!\n")
        self.channel.broadcast_cc(self.prefix + "%s throws ^!%s^.; %s throws ^!%s^.!\n" % (one_name, one, two_name, two))
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
