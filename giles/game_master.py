# Giles: game_master.py
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

from games.rps import RockPaperScissors

MAX_SESSION_NAME_LENGTH = 16

class GameMaster(object):
    """The GameMaster is the arbiter of games.  It starts up new games
    for players, manages connecting players to running games (whether
    for kibitzing or to replace a player who dropped out), and so on.
    It is not a game implementation itself; just the framework around
    all game implementations.
    """

    def __init__(self, server):

        self.server = server
        self.games = {
           "rps": RockPaperScissors,
        }
        self.tables = []

    def handle(self, player, table_name, command_str):

        if table_name and command_str and type(command_str) == str:

            # Check our list of tables to see if this game ID is in it.
            found = False
            lower_name = table_name.lower()
            for table in self.tables:
                if table.table_name == lower_name:
                    table.handle(player, command_str)
                    found = True

            if not found:
                player.tell_cc("Game table ^M%s^~ does not exist.\n" % table_name)

        else:
            player.send("Invalid table command.\n")

    def new_table(self, player, game_name, table_name, scope = "local"):

        if type(game_name) == str:

            if (type(table_name) != str or not table_name.isalnum()
               or len(table_name) > MAX_SESSION_NAME_LENGTH):
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
                table = self.games[lower_game_name](self.server, table_name)
                if scope == "private":
                    player.tell_cc("A new table of ^M%s^~ called ^R%s^~ has been created.\n" % (table.game_display_name, table.table_display_name))
                    self.server.log.log("%s created new private table %s of %s (%s)." % (player.display_name, table.table_display_name, table.game_name, table.game_display_name))
                elif scope == "global":
                    self.server.wall.broadcast_cc("%s created a new table of ^M%s^~ called ^R%s^~.\n" % (player.display_name, table.game_display_name, table.table_display_name))
                    self.server.log.log("%s created new global table %s of %s (%s)." % (player.display_name, table.table_display_name, table.game_name, table.game_display_name))
                else:
                    player.location.notify_cc("%s created a new table of ^M%s^~ called ^R%s^~.\n" % (player.display_name, table.game_display_name, table.table_display_name))
                    self.server.log.log("%s created new local table %s of %s (%s)." % (player.display_name, table.table_display_name, table.game_name, table.game_display_name))
                self.tables.append(table)
                return True

            player.tell_cc("No such game ^R%s^~.\n" % game_name)
            return False

    def list_games(self, player):

        player.tell_cc("\nGames available:\n\n")
        game_names = sorted(self.games.keys())
        state = "magenta"
        msg = "   "
        for game in game_names:
            if state == "magenta":
                msg += "^M%s^~ " % game
                state = "red"
            elif state == "red":
                msg += "^R%s^~ " % game
                state = "magenta"

        player.tell_cc(msg + "\n\n")

    def cleanup(self):

        # Remove tables whose state is "finished".

        for table in self.tables:
            if table.state.get() == "finished":

                self.server.log.log("Deleting stale game table %s (%s)." % (table.table_display_name, table.game_display_name))
                self.tables.remove(table)
                del table
