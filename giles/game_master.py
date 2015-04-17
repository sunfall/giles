# Giles: game_master.py
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

from giles.game_handle import GameHandle
from giles.utils import name_is_valid

import ConfigParser
import traceback

class GameMaster(object):
    """The GameMaster is the arbiter of games.  It starts up new games
    for players, manages connecting players to running games (whether
    for kibitzing or to replace a player who dropped out), and so on.
    It is not a game implementation itself; just the framework around
    all game implementations.
    """

    def __init__(self, server):

        self.server = server
        self.games = {}
        self.tables = []
        self.load_games_from_conf()

    def log(self, message):
        self.server.log.log("[GM] %s" % message)

    def load_game(self, game_key, class_path, admin_only=False):

        # Loads a game given a key ("rps") and a full class path
        # ("games.rock_paper_scissors.rock_paper_scissors.RockPaperScissors").
        try:
            module_bits = class_path.split(".")
            module_path = ".".join(module_bits[:-1])
            module_class_name = module_bits[-1]

            # Get a GameHandle for this game.
            game_handle = GameHandle(module_path, module_class_name, admin_only)

            # Store it in the game tracker.
            self.games[game_key] = game_handle
            self.log("Successfully loaded game %s (%s, admin=%s)." % (game_key, class_path, admin_only))
            return True
        except Exception as e:
            self.log("Failed to load game %s (%s).\nException: %s\n%s" % (game_key, class_path, e, traceback.format_exc()))
            return False

    def load_games_from_conf(self):

        cp = ConfigParser.SafeConfigParser()
        cp.read(self.server.config_filename)

        game_sections = [x for x in cp.sections() if x.startswith("game.")]
        if len(game_sections) == 0:
            self.log("No games defined in %s." % self.server.config_filename)
            return

        for sec in game_sections:
            # Trim "game." from the name.
            game_name = sec[5:]
            if not cp.has_option(sec, "class"):
                self.log("Cannot load game %s, as it has no class definition." % game_name)
            else:
                # Assume it's not admin-only, but pull the option if it's set.
                admin_only = False
                if cp.has_option(sec, "admin"):
                    admin_only = cp.getboolean(sec, "admin")

                # Actually load the game.
                self.load_game(game_name, cp.get(sec, "class"), admin_only)

        del cp

    def is_game(self, game_key):
        return game_key in self.games

    def reload_game(self, game_key):

        if self.is_game(game_key):
            try:
                name = self.games[game_key].name
                self.games[game_key].reload_game()
                self.log("Successfully reloaded game %s (%s)." % (game_key, name))
                return True
            except Exception as e:
                self.log("Failed to reload game %s (%s).\nException: %s\n%s" % (game_key, name, e, traceback.format_exc()))
                return False
        return False

    def reload_all_games(self):
        for game_key in self.games:
            self.reload_game(game_key)

    def unload_game(self, game_key):

        if self.is_game(game_key):
            game_handle = self.games[game_key]
            del self.games[game_key]
            self.log("Successfully unloaded game %s." % game_key)
            return True
        return False

    def unload_all_games(self):
        for game_key in self.games.keys():
            self.unload_game(game_key)

    def get_table(self, table_name):

        # Check our list of tables to see if this game ID is in it.
        lower_name = table_name.lower()
        for table in self.tables:
            if table.table_name == lower_name:
                return table

        return None

    def handle(self, player, table_name, command_str):

        if table_name and command_str and type(command_str) == str:

            # Check our list of tables to see if this game ID is in it.
            table = self.get_table(table_name)
            if table:
                try:
                    table.handle(player, command_str)
                except Exception as e:
                    table.channel.broadcast_cc("This table just crashed on a command! ^RAlert the admin^~.\n")
                    self.log("%scrashed on command |%s|.\n%s" % (table.log_prefix, command_str, traceback.format_exc()))
                    self.remove_table(table)

            else:
                player.tell_cc("Game table ^M%s^~ does not exist.\n" % table_name)

        else:
            player.send("Invalid table command.\n")

    def new_table(self, player, game_name, table_name, scope="local",
                  private=False):

        if not name_is_valid(table_name):
            player.tell_cc("Invalid table name.\n")
            return False

        # Make sure this isn't a duplicate table name.  It also can't
        # match a non-gameable channel.
        chan = self.server.channel_manager.has_channel(table_name)
        if chan and not chan.gameable:
            player.tell_cc("A channel named ^R%s^~ already exists.\n" % table_name)
            return False

        lower_table_name = table_name.lower()
        for table in self.tables:
            if table.table_name == lower_table_name:
                player.tell_cc("A table named ^R%s^~ already exists.\n" % table_name)
                return False

        # Check our list of games and see if we have this.
        lower_game_name = game_name.lower()
        if lower_game_name in self.games:

            # If this game is admin-only, verify that the player is an admin.
            if self.games[lower_game_name].admin_only:
                if not self.server.admin_manager.is_admin(player):
                    player.tell_cc("You cannot create a table; this game is admin-only.\n")
                    self.log("Non-admin %s failed to create table of admin-only game %s." % (player, lower_game_name))
                    return False

            # Okay.  Create the new table.
            try:
                table = self.games[lower_game_name].game_class(self.server, table_name)
            except Exception as e:
                player.tell_cc("Creating the table failed!  ^RAlert the admin^~.\n")
                self.log("Creating table %s of game %s failed.\n%s" % (table_name, lower_game_name, traceback.format_exc()))
                return False
            table.private = private

            # Connect the player to its channel, because presumably they
            # want to actually hear what's going on.
            if not table.channel.is_connected(player):
                table.channel.connect(player)

            # Send a message to the channel...
            table.channel.broadcast_cc("%s created a new table of ^M%s^~.\n" % (player, table.game_display_name))

            # ...and notify the proper scope.
            if scope == "personal":
                player.tell_cc("A new table of ^M%s^~ called ^R%s^~ has been created.\n" % (table.game_display_name, table.table_display_name))
                self.log("%s created new personal table %s of %s (%s)." % (player, table.table_display_name, table.game_name, table.game_display_name))
            elif scope == "global":
                self.server.wall.broadcast_cc("%s created a new table of ^M%s^~ called ^R%s^~.\n" % (player, table.game_display_name, table.table_display_name))
                self.log("%s created new global table %s of %s (%s)." % (player, table.table_display_name, table.game_name, table.game_display_name))
            else:
                player.location.notify_cc("%s created a new table of ^M%s^~ called ^R%s^~.\n" % (player, table.game_display_name, table.table_display_name))
                self.log("%s created new local table %s of %s (%s)." % (player, table.table_display_name, table.game_name, table.game_display_name))
            self.tables.append(table)
            return True

        player.tell_cc("No such game ^R%s^~.\n" % game_name)
        return False

    def list_games(self, player):

        player.tell_cc("\nGames available:\n\n")
        game_names = sorted(self.games.keys())
        state = "magenta"
        msg = "   "

        # Filter the game list, removing admin-only games if the player is not
        # an admin.
        if not self.server.admin_manager.is_admin(player):
            game_names = [x for x in game_names if not self.games[x].admin_only]

        for game in game_names:
            if state == "magenta":
                msg += "^M%s^~ [" % game
                state = "red"
            elif state == "red":
                msg += "^R%s^~ [" % game
                state = "magenta"
            if self.games[game].tags:
                msg += " ".join(self.games[game].tags)
            else:
                msg += "(no tags)"
            msg += "]\n   "

        player.tell_cc(msg + "\n\n")
        self.log("%s requested the list of available games." % player)

    def list_tables(self, player, show_private=False):

        player.tell_cc("\n^RACTIVE GAMES^~:\n")
        found_a_table = False
        state = "magenta"
        for table in self.tables:

            # We print tables if they're public, if this call is privileged
            # via show_private, or if the player is listening to the table.
            if ((table.private and table.channel.is_connected(player)) or
               show_private or not table.private):

                # All right, we can print this table.
                found_a_table = True
                private_str = ""
                if table.private:
                    private_str = "(^Rprivate^~)"
                if state == "magenta":
                    table_color_code = "^M"
                    game_color_code = "^G"
                    state = "yellow"
                else:
                    table_color_code = "^Y"
                    game_color_code = "^C"
                    state = "magenta"
                player.tell_cc("   %s%s^~ (%s%s^~) %s\n" % (table_color_code, table.table_display_name, game_color_code, table.game_display_name, private_str))

        # If there were no visible tables, say so.
        if not found_a_table:
            player.tell_cc("   ^!None found!  You should start a game.^.\n")

        player.tell("\n")
        self.log("%s requested a list of active tables." % player)

    def remove_player(self, player):

        # Remove the player from every table they might be at.
        for table in self.tables:
            table.remove_player(player)

    def tick(self):

        # Send ticks to all tables under our control.
        for table in self.tables:
            try:
                table.tick()
            except Exception as e:
                table.channel.broadcast_cc("This table just crashed on tick()! ^RAlert the admin^~.\n")
                self.log("%scrashed on tick().\n%s" % (table.log_prefix, traceback.format_exc()))
                self.remove_table(table)

    def remove_table(self, table):

        # If any players are focused on this table, unfocus them,
        # as it no longer exists.
        for player in self.server.players:
            if player.config["focus_table"] == table.table_name:
                player.tell_cc("Table ^Y%s^~ is defunct; unfocusing.\n" % table.table_name)
                player.config["focus_table"] = None
                if player.state.get() == "chat":
                    player.prompt()
        self.tables.remove(table)
        del table


    def cleanup(self):

        # Remove tables whose state is "finished".

        for table in self.tables:
            if table.state.get() == "finished":

                self.log("Deleting stale game table %s (%s)." % (table.table_display_name, table.game_display_name))
                self.remove_table(table)
