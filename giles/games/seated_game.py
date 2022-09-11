# Giles: seated_game.py
# Copyright 2012, 2014 Phil Bordelon
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

class SeatedGame(Game):
    """The base SeatedGame class.  Extends game to handle stuff for a
    typical board game: adding and removing players to seats, allowing
    players to switch seats, and so on.
    """

    def __init__(self, server, table_name):

        super(SeatedGame, self).__init__(server, table_name)

        self.seats = [
            Seat("One"),
            Seat("Two"),
            Seat("Three"),
            Seat("Four"),
        ]

        self.min_players = 1
        self.max_players = 4
        self.num_players = 0
        self.activate_on_sitting = True

    def next_seat(self, seat):

        # This utility function returns the next seat, in order, from the
        # one given.  Lots of games have turns that simply rotate between
        # all the players.  Note that this function doesn't handle inactive
        # seats or anything fancy; override it if you need to.

        seat_index = self.seats.index(seat)
        return self.seats[(seat_index + 1) % len(self.seats)]

    def prev_seat(self, seat):

        # Like next_seat(), above, except in the other direction.

        seat_index = self.seats.index(seat)
        return self.seats[(seat_index - 1) % len(self.seats)]

    def update_active(self):

        # If there are any seats that are marked as active but do not
        # have a player, mark the game as inactive.  This can happen
        # if a player disconnects during the course of the game.  Most
        # games will want to handle this by not taking commands until
        # that seat has been filled.

        self.active = True
        for seat in self.seats:
            if seat.active and not seat.player:
                self.active = False

    def get_seat_of_player(self, player):

        # If a player is seated, snag the seat they're at.
        for seat in self.seats:
            if seat.player == player:
                return seat

        return None

    def get_seat(self, seat_name):

        lower_name = seat_name.lower()
        for seat in self.seats:
            if seat.name == lower_name:
                return seat

        return None

    def show_help(self, player):
        self.log_pre("%s asked for help with the game." % player)
        player.tell_cc("\nVIEWING:\n\n")
        player.tell_cc("                ^!kibitz^., ^!watch^.     Watch the game as it happens.\n")
        player.tell_cc("                 ^!list^., ^!who^., ^!w^.     List players and kibitzers.\n")
        player.tell_cc("                ^!show^., ^!look^., ^!l^.     Look at the game itself.\n")
        player.tell_cc("        ^!show_config^., ^!showconf^.     Show the game's configuration.\n")
        player.tell_cc("\nPARTICIPATING:\n\n")
        player.tell_cc("   ^!join^. [<seat>], ^!add^., ^!sit^., ^!j^.     Join the game [in seat <seat>].\n")
        player.tell_cc("                 ^!leave^., ^!stand^.     Leave the game.\n")
        player.tell_cc("      ^!replace^. <seat> <player>     Replace <seat> with <player>.\n")
        player.tell_cc("            ^!terminate^., ^!finish^.     Terminate game.\n")
        if self.debug:
            player.tell_cc("\nDEBUG:\n\n")
            player.tell_cc("         ^!change_state^. <state>     Change game state to <state>.\n")


    def add_player(self, player, seat_name=None):

        # Is the game already full?
        if self.num_players >= self.max_players:
            self.tell_pre(player, "Game already full.\n")
            return False

        # Is the player already in the game?
        if self.get_seat_of_player(player):
            self.tell_pre(player, "You're already playing.\n")
            return False

        # Okay, we should have at least one empty seat and we have a
        # willing player.  If they asked for a specific seat, check
        # to see if it's available, and bail if not.  Otherwise, stick
        # 'em in the first available seat.
        if seat_name:
            seat = self.get_seat(seat_name)
            if seat:
                if not seat.player:
                    seat.sit(player, self.activate_on_sitting)
                    self.tell_pre(player, "You successfully snagged seat %s.\n" % seat)
                    if not self.channel.is_connected(player):
                        self.channel.connect(player)
                    self.bc_pre("^Y%s^~ is now playing in seat ^C%s^~ by choice.\n" % (player, seat))
                    self.num_players += 1
                    return True
                else:
                    self.tell_pre(player, "Seat %s is unavailable.\n" % seat_name)
                    return False

            else:
                self.tell_pre(player, "Seat %s does not exist.\n" % seat_name)
                return False

        # Just snag the first available seat.
        for seat in self.seats:
            if not seat.player:
                seat.sit(player, self.activate_on_sitting)
                self.tell_pre(player, "You are now sitting in seat %s.\n" % seat)
                if not self.channel.is_connected(player):
                    self.channel.connect(player)
                self.bc_pre("^Y%s^~ is now playing in seat ^C%s^~.\n" % (player, seat))
                self.num_players += 1
                return True

        # Uh oh.  Something went wrong; we shouldn't have had a problem
        # finding a seat.
        self.tell_pre(player, "Something went wrong when adding you.  Notify the admin.\n")
        self.log_pre("Failed to seat %s." % player)
        return False

    def replace(self, player, seat_name, player_name):

        # First, easiest bit: make sure the player is valid...
        other = self.server.get_player(player_name)
        if not other:
            self.tell_pre(player, "Player ^Y%s^~ does not exist.\n" % player_name)
            return False

        # ...the player isn't /already/ at the table...
        if self.get_seat_of_player(other):
            self.tell_pre(player, "Player ^Y%s^~ is already playing.\n" % player_name)
            return False

        # ...and that the seat exists.
        seat = self.get_seat(seat_name)
        if not seat:
            self.tell_pre(player, "Seat ^G%s^~ does not exist.\n" % seat_name)
            return False

        # Okay.  We've got a new player and a seat they can sit in.  Make it happen.
        prev_player = seat.player
        if not self.channel.is_connected(other):
            self.channel.connect(other)
        if prev_player:
            self.remove_player(prev_player)
            self.tell_pre(player, "You replaced ^R%s^~ with ^Y%s^~ in seat ^G%s^~.\n" % (prev_player, other, seat))
            self.bc_pre("^C%s^~ replaced ^R%s^~ with ^Y%s^~ in seat ^G%s^~.\n" % (player, prev_player, other, seat))
            self.log_pre("%s replaced %s with %s in seat %s." % (player, prev_player, other, seat))
        else:
            self.tell_pre(player, "You placed ^R%s^~ in seat ^G%s^~.\n" % (other, seat))
            self.bc_pre("^C%s^~ placed ^R%s^~ in seat ^G%s^~.\n" % (player, other, seat))
            self.log_pre("%s placed %s in seat %s." % (player, other, seat))
            self.num_players += 1
        seat.sit(other)

    def remove_player(self, player):

        for seat in self.seats:
            if seat.player == player:
                self.bc_pre("^R%s^~ has left the table.\n" % player)
                self.num_players -= 1
                seat.stand()

        self.update_active()

    def leave(self, player):

        # Is this player even at the table?
        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "Can't leave a table you're not at.\n")
            return

        # Okay, the player is actually at the table.
        self.remove_player(player)

    def list_players(self, player):

        player.tell_cc("\nPlayers at table ^R%s^~ of ^G%s^~:\n\n" % (self.table_display_name, self.game_display_name))

        msg = "   "
        state = "yellow"
        for seat in self.seats:
            if seat.active:
                player_name = seat.player_name
                if state == "yellow":
                    msg += "^Y%s^~: %s " % (seat, player_name)
                    state = "magenta"
                elif state == "magenta":
                    msg += "^M%s^~: ^!%s^. " % (seat, player_name)
                    state = "yellow"

        if msg == "   ":
            msg = "   ^!None yet!^."

        player.tell_cc(msg + "\n")
        player.tell_cc("\nKibitzers:\n\n")

        msg = "   "
        state = "bold"
        for listener in self.channel.listeners:
            if not self.get_seat_of_player(listener):
                if state == "bold":
                    msg += "^!%s^. " % listener
                    state = "normal"
                elif state == "normal":
                    msg += "%s " % listener
                    state = "bold"

        if msg == "   ":
            msg = "   ^!None yet!^."

        player.tell_cc(msg + "\n")

    def join(self, player, join_bits):

        # If your game needs to do custom join handling (such as if it
        # supports a potentially-infinite number of players), you should
        # override this function with your own custom implementation.  Its
        # return value should be whether it handled the join or not (and
        # so it should therefore potentially be handled by your handle()
        # implementation.
        if self.state.get() == 'need_players':
            if len(join_bits) == 0:

                # Willing to take any seat.
                self.add_player(player)
            elif len(join_bits) == 1:

                # Looking for a specific seat.
                self.add_player(player, join_bits[0])
            else:
                self.tell_pre(player, "Invalid add.\n")
        else:
            self.tell_pre(player, "Not looking for players.\n")

        return True

    def handle_common_commands(self, player, command_str):

        # This handles certain command bits common to all seated games.
        # It passes the buck to the standard game class first, then:
        # - If the game is in the "need_players" state, accept new
        #   players unless we're already at max_players.
        # - At any point, take these generic commands:
        #   * replace (replace a player at the table)
        #   * leave (leave the table)
        #   * list (show players at the table)
        #
        # We also return whether or not we handled the command, which may
        # be useful to games that call us.

        # First, let's see if the superclass can handle it.
        if super(SeatedGame, self).handle_common_commands(player, command_str):

            # Yup, it did; we're done.  Return True because it was handled.
            return True

        state = self.state.get()

        # Bail if the game is over.
        if state == "finished":
            self.tell_pre(player, "Game already finished.\n")
            return True

        handled = False
        # Pull out the command bits.
        command_bits = command_str.split()
        primary = command_bits[0].lower()

        if primary in ('replace', 'switch'):
            if len(command_bits) == 3:
                self.replace(player, command_bits[1], command_bits[2])
            else:
                self.tell_pre(player, "Invalid replacement.\n")
            handled = True

        elif primary in ('leave', 'stand'):
            self.leave(player)
            handled = True

        elif primary in ('list', 'who', 'w'):
            self.list_players(player)
            handled = True

        elif primary in ('add', 'join', 'sit', 'j'):
            handled = self.join(player, command_bits[1:])

        # If we've done something, update the active state.
        if handled:
            self.update_active()

        return handled
