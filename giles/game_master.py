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
        self.sessions = []

    def handle(self, player, session_name, command_str):

        if session_name and command_str and type(command_str) == str:

            # Check our list of sessions to see if this game ID is in it.
            found = False
            lower_name = session_name.lower()
            for session in self.sessions:
                if session.session_name == lower_name:
                    session.handle(player, command_str)
                    found = True

            if not found:
                player.tell_cc("Game session ^M%s^~ does not exist.\n" % session_name)

        else:
            player.send("Invalid session command.\n")

    def new_session(self, player, game_name, session_name):

        if type(game_name) == str:

            if (type(session_name) != str or not session_name.isalnum()
               or len(session_name) > MAX_SESSION_NAME_LENGTH):
                player.tell_cc("Invalid session name.\n")
                return False

            # Make sure this isn't a duplicate session name.
            lower_session_name = session_name.lower()
            for session in self.sessions:
                if session.session_name == lower_session_name:
                    player.tell_cc("A session named ^R%s^~ already exists.\n" % session_name)
                    return False

            # Check our list of games and see if we have this.
            lower_game_name = game_name.lower()
            if lower_game_name in self.games:
                session = self.games[lower_game_name](session_name)
                self.server.log.log("%s created new session %s of %s (%s)." % (player.display_name, session.session_display_name, session.game_name, session.game_display_name))
                self.sessions.append(session)
                return True

            player.tell_cc("No such game ^R%s^~.\n" % game_name)
            return False

    def list_games(self, player):

        player.tell_cc("\nGames available:\n\n")
        game_names = sorted(self.games.keys())
        state = "magenta"
        msg = "  "
        for game in game_names:
            if state == "magenta":
                msg += "^M%s^~ " % game
                state = "red"
            elif state == "red":
                msg += "^R%s^~ " % game
                state = "magenta"

        player.tell_cc(msg + "\n\n")

    def cleanup(self):

        # Remove sessions whose state is "finished".

        for session in self.sessions:
            if session.state.get() == "finished":

                server.log.log("Deleting stale game session %s (%s)." % (session.display_name, session.game_name))
                self.sessions.remove(session)
                del session
