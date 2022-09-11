# Giles: game.py
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

from giles.state import State
from giles.utils import rgetattr

class Game(object):
    """The base Game class.  Does a lot of the boring footwork that all
    games need to handle: adding players, generating the chat channel for
    the game, handling kibitzing and player replacement, and so on.  In
    general, though, you want one of the subclasses of this class, either
    SeatedGame() or SeatlessGame().
    """

    def __init__(self, server, table_name):

        self.server = server
        self.channel = server.channel_manager.has_channel(table_name)
        if not self.channel:
            self.channel = self.server.channel_manager.add_channel(table_name,
                                                gameable=True, persistent=True)
        else:
            self.channel.persistent = True
        self.game_display_name = "Generic Game"
        self.game_name = "game"
        self.table_display_name = table_name
        self.table_name = table_name.lower()

        self.active = False
        self.private = False

        self.state = State("config")
        self.prefix = "(^RGame^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Override this next variable in your subclasses if you're not
        # done debugging them.
        self.debug = False

    def __repr__(self):
        return ("%s (%s)" % (self.table_display_name, self.game_display_name))

    def log_pre(self, log_str):

        # This utility function logs with the proper prefix.
        self.server.log.log(self.log_prefix + log_str)

    def tell_pre(self, player, tell_str):

        # This utility function tells a player a line with the proper prefix.
        player.tell_cc(self.prefix + tell_str)

    def bc_pre(self, send_str):

        # This utility function sends a message to the game channel with the
        # proper prefix.
        self.channel.broadcast_cc(self.prefix + send_str)

    def handle(self, player, command_str):

        # The generic handle does very little work; it passes it all off
        # to the common command handler.  You are not expected to
        # actually /call/ this handle(), but if you do it has the same
        # effect as calling handle_common_commands().

        self.handle_common_commands(player, command_str)

    def show_help(self, player):
        self.log_pre("%s asked for help with the game." % player)
        player.tell_cc("\nVIEWING:\n\n")
        player.tell_cc("                ^!kibitz^., ^!watch^.     Watch the game as it happens.\n")
        player.tell_cc("                ^!show^., ^!look^., ^!l^.     Look at the game itself.\n")
        player.tell_cc("        ^!show_config^., ^!showconf^.     Show the game's configuration.\n")
        player.tell_cc("\nPARTICIPATING:\n\n")
        player.tell_cc("            ^!terminate^., ^!finish^.     Terminate game.\n")
        if self.debug:
            player.tell_cc("\nDEBUG:\n\n")
            player.tell_cc("         ^!change_state^. <state>     Change game state to <state>.\n")

    def show(self, player):

        # This function should /absolutely/ be overridden by any games.
        self.tell_pre(player, "This is the default game class; nothing to show.\n")

    def show_config(self, player):

        if getattr(self, "config_params", None):
            for name, desc in self.config_params:
                attr = rgetattr(self, name, None)
                if attr != None:
                    player.tell_cc("^G%s^~: ^Y%s^~\n" % (desc, repr(attr)))
                else:
                    player.tell_cc("^G%s^~ is not a valid attribute for this game.  Alert the admin.\n" % name)
        else:
            player.tell_cc("This game does not support showing its configuration.\n")

    def finish(self):

        # If you have fancy cleanup that should be done when a game is
        # done, override this function.
        self.log_pre("This game has been marked as finished.")
        self.channel.persistent = False
        self.state.set("finished")

    def terminate(self, player):

        self.bc_pre("^Y%s^~ has terminated the game.\n" % player)
        self.log_pre("%s has terminated the game." % player)
        self.finish()

    def tick(self):

        # If your game has events that occur potentially without player
        # intervention, override this class.  An obvious example is a
        # game with a timer; a less-obvious one is a game that you want
        # to auto-transition whenever certain conditions are met, such
        # as a game auto-starting when all the players are ready and
        # available.
        pass

    def remove_player(self, player):
        """Signature for removing a player from the game.

        When a player removes themselves from a game or disconnects from
        the server, this method is called on every game currently
        running; implementations are expected to only remove the player
        from a game if they are participating.
        """

        # You will almost certainly want to override this if you're
        # writing a new subclass of Game().  Existing subclasses
        # may or may not have useful implementations extant.
        pass

    def handle_common_commands(self, player, command_str):

        # This handles certain command bits common to all games.
        # - If the game is finished, reject commands.
        # - At any point, take these generic commands:
        #   * help (print help in regards to the game)
        #   * kibitz (watch the game)
        #   * show (show the game itself)
        #   * show_config (show the configuration of the game)
        #   * terminate (end the game immediately)
        #   * private (make private)
        #   * public (make public)
        # - In addition, if we're in debug mode, allow people to
        #   forcibly switch states via change_state.
        #
        # We also return whether or not we handled the command, which may
        # be useful to games that call us.

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
                self.tell_pre(player, "You're already watching this game!\n")
            handled = True

        elif primary in ('show', 'look', 'l'):
            self.show(player)
            handled = True

        elif primary in ('show_config', 'showconf'):
            self.show_config(player)
            handled = True

        elif primary in ('terminate', 'finish', 'flip'):
            self.terminate(player)
            handled = True

        elif primary in ('private',):
            self.bc_pre("^R%s^~ has turned the game ^cprivate^~.\n" % (player))
            self.private = True
            handled = True

        elif primary in ('public',):
            self.bc_pre("^R%s^~ has turned the game ^Cpublic^~.\n" % (player))
            self.private = False
            handled = True

        elif primary in ('change_state',):
            if not self.debug:
                self.tell_pre(player, "No switching states in production!\n")
            elif len(command_bits) != 2:
                self.tell_pre(player, "Invalid state to switch to.\n")
            else:
                self.state.set(command_bits[1].lower())
                self.bc_pre("^R%s^~ forced a state change to ^C%s^~.\n" % (player, self.state.get()))
            handled = True

        return handled
