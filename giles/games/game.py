# Giles: game.py
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
from giles.games.seat import Seat

class Game(object):
    """The base Game class.  Does a lot of the boring footwork that all
    games need to handle: adding players, generating the chat channel for
    the game, handling kibitzing and player replacement, and so on.
    """

    def __init__(self, server, table_name):

        self.server = server
        self.channel = server.channel_manager.has_channel(table_name)
        if not self.channel:
            self.channel = self.server.channel_manager.add_channel(table_name, gameable = True, persistent = True)
        else:
            self.channel.persistent = True
        self.game_display_name = "Generic Game"
        self.game_name = "game"
        self.table_display_name = table_name
        self.table_name = table_name.lower()

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

        self.active = False
        self.private = False

        self.state = State("config")
        self.prefix = "(^RGame^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Override this next variable in your subclasses if you're not
        # done debugging them.
        self.debug = False

    def __repr__(self):
        return ("%s (%s)" % (self.table_display_name, self_game_display_name))

    def handle(self, player, command_str):

        # The generic handle does very little work; it passes it all off
        # to the common command handler.  You are not expected to
        # actually /call/ this handle(), but if you do it has the same
        # effect as calling handle_common_commands().

        self.handle_common_commands(player, command_str)

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
        player.tell_cc("\nVIEWING:\n\n")
        player.tell_cc("                ^!kibitz^., ^!watch^.     Watch the game as it happens.\n")
        player.tell_cc("                 ^!list^., ^!who^., ^!w^.     List players and kibitzers.\n")
        player.tell_cc("                ^!show^., ^!look^., ^!l^.     Look at the game itself.\n")
        player.tell_cc("\nPARTICIPATING:\n\n")
        player.tell_cc("   ^!join^. [<seat>], ^!add^., ^!sit^., ^!j^.     Join the game [in seat <seat>].\n")
        player.tell_cc("                 ^!leave^., ^!stand^.     Leave the game.\n")
        player.tell_cc("      ^!replace^. <seat> <player>     Replace <seat> with <player>.\n")
        player.tell_cc("            ^!terminate^., ^!finish^.     Terminate game.\n")
        if self.debug:
            player.tell_cc("\nDEBUG:\n\n")
            player.tell_cc("         ^!change_state^. <state>     Change game state to <state>.\n")


    def add_player(self, player, seat_name = None):

        # Is the game already full?
        if self.num_players >= self.max_players:
            player.tell_cc(self.prefix + "Game already full.\n")
            return False

        # Is the player already in the game?
        if self.get_seat_of_player(player):
            player.tell_cc(self.prefix + "You're already playing.\n")
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
                    player.tell_cc(self.prefix + "You successfully snagged seat %s.\n" % seat.display_name)
                    if not self.channel.is_connected(player):
                        self.channel.connect(player)
                    self.channel.broadcast_cc(self.prefix + "^Y%s^~ is now playing in seat ^C%s^~ by choice.\n" % (player.display_name, seat.display_name))
                    self.num_players += 1
                    return True
                else:
                    player.tell_cc(self.prefix + "Seat %s is unavailable.\n" % seat_name)
                    return False

            else:
                player.tell_cc(self.prefix + "Seat %s does not exist.\n" % seat_name)
                return False

        # Just snag the first available seat.
        for seat in self.seats:
            if not seat.player:
                seat.sit(player, self.activate_on_sitting)
                player.tell_cc(self.prefix + "You are now sitting in seat %s.\n" % seat.display_name)
                if not self.channel.is_connected(player):
                    self.channel.connect(player)
                self.channel.broadcast_cc(self.prefix + "^Y%s^~ is now playing in seat ^C%s^~.\n" % (player.display_name, seat.display_name))
                self.num_players += 1
                return True

        # Uh oh.  Something went wrong; we shouldn't have had a problem
        # finding a seat.
        player.tell_cc(self.prefix + "Something went wrong when adding you.  Notify the admin.\n")
        self.server.log.log(self.log_prefix + "Failed to seat %s." % player.display_name)
        return False

    def replace(self, player, seat_name, player_name):

        # First, easiest bit: make sure the player is valid...
        other = self.server.get_player(player_name)
        if not other:
            player.tell_cc(self.prefix + "Player ^Y%s^~ does not exist.\n" % player_name)
            return False

        # ...the player isn't /already/ at the table...
        if self.get_seat_of_player(other):
            player.tell_cc(self.prefix + "Player ^Y%s^~ is already playing.\n" % player_name)
            return False

        # ...and that the seat exists.
        seat = self.get_seat(seat_name)
        if not seat:
            player.tell_cc(self.prefix + "Seat ^G%s^~ does not exist.\n" % seat_name)
            return False

        # Okay.  We've got a new player and a seat they can sit in.  Make it happen.
        prev_player = seat.player
        if not self.channel.is_connected(other):
            self.channel.connect(other)
        if prev_player:
            self.remove_player(prev_player)
            player.tell_cc(self.prefix + "You replaced ^R%s^~ with ^Y%s^~ in seat ^G%s^~.\n" % (prev_player.display_name, other.display_name, seat.display_name))
            self.channel.broadcast_cc(self.prefix + "^C%s^~ replaced ^R%s^~ with ^Y%s^~ in seat ^G%s^~.\n" % (player.display_name, prev_player.display_name, other.display_name, seat.display_name))
            self.server.log.log(self.log_prefix + "%s replaced %s with %s in seat %s." % (player.display_name, prev_player.display_name, other.display_name, seat.display_name))
        else:
            player.tell_cc(self.prefix + "You placed ^R%s^~ in seat ^G%s^~.\n" % (other.display_name, seat.display_name))
            self.channel.broadcast_cc(self.prefix + "^C%s^~ placed ^R%s^~ in seat ^G%s^~.\n" % (player.display_name, other.display_name, seat.display_name))
            self.server.log.log(self.log_prefix + "%s placed %s in seat %s." % (player.display_name, other.display_name, seat.display_name))
            self.num_players += 1
        seat.sit(other)

    def remove_player(self, player):

        for seat in self.seats:
            if seat.player == player:
                self.channel.broadcast_cc("^R%s^~ has left the table.\n" % player.display_name)
                self.num_players -= 1
                seat.stand()

        self.update_active()

    def leave(self, player):

        # Is this player even at the table?
        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "Can't leave a table you're not at.\n")
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
                    msg += "^Y%s^~: %s " % (seat.display_name, player_name)
                    state = "magenta"
                elif state == "magenta":
                    msg += "^M%s^~: ^!%s^. " % (seat.display_name, player_name)
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
                    msg += "^!%s^. " % listener.display_name
                    state = "normal"
                elif state == "normal":
                    msg += "%s " % listener.display_name
                    state = "bold"

        if msg == "   ":
            msg = "   ^!None yet!^."

        player.tell_cc(msg + "\n")
            

    def show(self, player):

        # This function should /absolutely/ be overridden by any games.
        player.tell_cc(self.prefix + "This is the default game class; nothing to show.\n")

    def finish(self):

        # If you have fancy cleanup that should be done when a game is
        # done, override this function.
        self.channel.persistent = False
        self.state.set("finished")

    def terminate(self, player):

        self.channel.broadcast_cc(self.prefix + "^Y%s^~ has terminated the game.\n" % player.display_name)
        self.server.log.log(self.log_prefix + "%s has terminated the game." % player.display_name)
        self.finish()

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
                player.tell_cc(self.prefix + "Invalid add.\n")
        else:
            player.tell_cc(self.prefix + "Not looking for players.\n")

        return True

    def tick(self):

        # If your game has events that occur potentially without player
        # intervention, override this class.  An obvious example is a
        # game with a timer; a less-obvious one is a game that you want
        # to auto-transition whenever certain conditions are met, such
        # as a game auto-starting when all the players are ready and
        # available.
        pass

    def handle_common_commands(self, player, command_str):

        # This handles certain command bits common to all games.
        # - If the game is finished, reject commands.
        # - If the game is in the "need_players" state, accept new
        #   players unless we're already at max_players.
        # - At any point, take these generic commands:
        #   * help (print help in regards to the game)
        #   * kibitz (watch the game)
        #   * replace (replace a player at the table)
        #   * leave (leave the table)
        #   * list (show players at the table)
        #   * show (show the game itself)
        #   * terminate (end the game immediately)
        #   * private (make private)
        #   * public (make public)
        # - In addition, if we're in debug mode, allow people to
        #   forcibly switch states via change_state.
        #
        # We also return whether or not we handled the command, which may
        # be useful to games that call us.

        state = self.state.get()

        # Bail if the game is over.
        if state == "finished":
            player.tell_cc(self.prefix + "Game already finished.\n")
            return True

        handled = False
        # Pull out the command bits.
        command_bits = command_str.split()
        primary = command_bits[0].lower()

        # You can always ask for help...
        if primary in ('help', 'h', '?'):
            self.show_help(player)
            handled = True

        # You can always add yourself as a kibitzer...
        elif primary in ('kibitz', 'watch'):
            if not self.channel.is_connected(player):
                self.channel.connect(player)
                self.show(player)
            else:
                player.tell_cc(self.prefix + "You're already watching this game!\n")
            handled = True

        # ...or replace players...
        elif primary in ('replace', 'switch'):
            if len(command_bits) == 3:
                self.replace(player, command_bits[1], command_bits[2])
            else:
                player.tell_cc(self.prefix + "Invalid replacement.\n")
            handled = True

        # ...leave...
        elif primary in ('leave', 'stand'):
            self.leave(player)
            handled = True

        elif primary in ('list', 'who', 'w'):
            self.list_players(player)
            handled = True

        elif primary in ('show', 'look', 'l'):
            self.show(player)
            handled = True

        elif primary in ('terminate', 'finish', 'flip'):
            self.terminate(player)
            handled = True

        elif primary in ('private',):
            self.channel.broadcast_cc("^R%s^~ has turned the game ^cprivate^~.\n" % (player.display_name))
            self.private = True
            handled = True

        elif primary in ('public',):
            self.channel.broadcast_cc("^R%s^~ has turned the game ^Cpublic^~.\n" % (player.display_name))
            self.private = False
            handled = True

        elif primary in ('change_state',):
            if not self.debug:
                player.tell_cc(self.prefix + "No switching states in production!\n")
            elif len(command_bits) != 2:
                player.tell_cc(self.prefix + "Invalid state to switch to.\n")
            else:
                self.state.set(command_bits[1].lower())
                self.channel.broadcast_cc("^R%s^~ forced a state change to ^C%s^~.\n" % (player.display_name, self.state.get()))
            handled = True

        elif primary in ('add', 'join', 'sit', 'j'):
            handled = self.join(player, command_bits[1:])

        # If we've done something, update the active state.
        if handled:
            self.update_active()

        return handled
