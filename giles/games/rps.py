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

MAX_SESSION_NAME_LENGTH = 16

class RockPaperScissors(object):
    """A Rock-Paper-Scissors game session implementation.
    """

    def __init__(self, server, session_name):

        self.server = server
        self.channel = server.channel_manager.add_channel(session_name, persistent = True)
        self.game_display_name = "Rock-Paper-Scissors"
        self.game_name = "rps"
        self.session_display_name = session_name
        self.session_name = session_name.lower()
        self.players = []
        self.state = State("need_players")
        self.plays = [None, None]
        self.prefix = "(^RRPS^~): "

    def handle(self, player, command_str):

        state = self.state.get()

        # Bail if the game is over.
        if self.state.get() == "finished":
            player.tell_cc(self.prefix + "Game already finished.\n")
            return

        # So, presumably we need commands, since the game isn't over.
        command_bits = command_str.split()
        primary = command_bits[0].lower()
        print(primary)

        # You can always add yourself as a kibitzer...
        if primary in ('kibitz', 'watch'):
            self.channel.connect(player)
            return

        # Okay, now, let's actually go through the states.

        # LFG.
        if state == "need_players":
            if primary in ('add', 'join'):
                if len(command_bits) == 1:

                    # Adding themselves.
                    self.add_player(player, player.name)
                elif len(command_bits) == 2:
                    self.add_player(player, command_bits[1])
                else:
                    player.tell_cc(self.prefix + "Invalid add.\n")
                    return

                if len(self.players) == 2:
                    self.state.set("need_moves")
                    self.channel.broadcast_cc(self.prefix + "Player One: ^Y%s^~; Player Two: ^Y%s^~\n" %
                       (self.players[0].display_name, self.players[1].display_name))
                    self.channel.broadcast_cc(self.prefix + "Players, make your moves!\n")
            else:
                player.tell_cc(self.prefix + "Invalid command; I need players!\n")

        elif state == "need_moves":

            if primary in ('r', 'p', 's', 'rock', 'paper', 'scissors'):
                self.move(player, primary)

                if self.plays[0] and self.plays[1]:

                    # Got the moves!
                    self.resolve()
                    self.state.set("finished")

            else:
                player.tell_cc(self.prefix + "Invalid command.\n")

    def add_player(self, player, player_name):

        lower_name = player_name.lower()
        for other in self.server.players:
            if lower_name == other.name:
                if other in self.players:
                    player.tell_cc(self.prefix + "%s is already playing!\n" % other.display_name)
                else:
                    self.players.append(other)
                    player.tell_cc(self.prefix + "Added %s to the game.\n" % other.display_name)
                    self.channel.broadcast_cc(self.prefix + "%s is now playing.\n" % other.display_name)
                    self.channel.connect(other)

    def move(self, player, play):

        if player not in self.players:
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

        if player == self.players[0]:
            self.plays[0] = this_move
        else:
            self.plays[1] = this_move

    def resolve(self):

        one = self.plays[0]
        two = self.plays[1]
        one_name = self.players[0].display_name
        two_name = self.players[1].display_name
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
        self.channel.broadcast_cc (msg)
