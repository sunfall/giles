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

from games.ataxx.ataxx import Ataxx
from games.breakthrough.breakthrough import Breakthrough
from games.crossway.crossway import Crossway
from games.capture_go.capture_go import CaptureGo
from games.gonnect.gonnect import Gonnect
from games.hex.hex import Hex
from games.hokm.hokm import Hokm
from games.metamorphosis.metamorphosis import Metamorphosis
from games.rock_paper_scissors.rock_paper_scissors import RockPaperScissors
from games.set.set import Set
from games.talpa.talpa import Talpa
from games.whist.whist import Whist
from games.y.y import Y

from giles.utils import name_is_valid

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
        self.games = {
           "ataxx": Ataxx,
           "breakthrough": Breakthrough,
           "capturego": CaptureGo,
           "crossway": Crossway,
           "gonnect": Gonnect,
           "hex": Hex,
           "hokm": Hokm,
           "metamorphosis": Metamorphosis,
           "rps": RockPaperScissors,
           "set": Set,
           "talpa": Talpa,
           "whist": Whist,
           "y": Y,
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

    def new_table(self, player, game_name, table_name, scope = "local", private = False):

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

            # Okay.  Create the new table.
            try:
                table = self.games[lower_game_name](self.server, table_name)
            except Exception as e:
                player.tell_cc("Creating the table failed!  ^RAlert the admin^~.\n")
                self.server.log.log("Creating table %s of game %s failed.\n%s" % (table_name, lower_game_name, traceback.format_exc()))
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
                self.server.log.log("%s created new personal table %s of %s (%s)." % (player, table.table_display_name, table.game_name, table.game_display_name))
            elif scope == "global":
                self.server.wall.broadcast_cc("%s created a new table of ^M%s^~ called ^R%s^~.\n" % (player, table.game_display_name, table.table_display_name))
                self.server.log.log("%s created new global table %s of %s (%s)." % (player, table.table_display_name, table.game_name, table.game_display_name))
            else:
                player.location.notify_cc("%s created a new table of ^M%s^~ called ^R%s^~.\n" % (player, table.game_display_name, table.table_display_name))
                self.server.log.log("%s created new local table %s of %s (%s)." % (player, table.table_display_name, table.game_name, table.game_display_name))
            self.tables.append(table)
            return True

        player.tell_cc("No such game ^R%s^~.\n" % game_name)
        return False

    def list_games(self, player):

        player.tell_cc("\nGames available:\n\n")
        game_names = sorted(self.games.keys())
        state = "magenta"
        msg = "   "
        count = 0
        for game in game_names:
            if state == "magenta":
                msg += "^M%s^~ " % game
                state = "red"
            elif state == "red":
                msg += "^R%s^~ " % game
                state = "magenta"
            count += 1
            if count == 7:
                msg += "\n   "
                count = 0

        player.tell_cc(msg + "\n\n")
        self.server.log.log("%s requested the list of available games." % player)

    def list_tables(self, player, show_private = False):

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
        self.server.log.log("%s requested a list of active tables." % player)

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
                self.server.log.log("%scrashed on tick().\n%s" % (table.log_prefix, traceback.format_exc()))
                self.tables.remove(table)
                del table

    def cleanup(self):

        # Remove tables whose state is "finished".

        for table in self.tables:
            if table.state.get() == "finished":

                self.server.log.log("Deleting stale game table %s (%s)." % (table.table_display_name, table.game_display_name))
                self.tables.remove(table)
                del table
