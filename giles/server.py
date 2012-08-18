# Giles: server.py
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

from miniboa import TelnetServer
import log
import player
import state

import chat
import login

class Server(object):
    """The Giles server itself.  Tracks all players, games in progress,
    and so on.
    """

    def __init__(self, name="library-alpha"):
        self.name = name
        self.log = log.Log(name)
        self.players = []
        self.should_run = True
        self.log.log("Server started up.")

    def instantiate(self, port=9435, timeout=.05):
        self.telnet = TelnetServer(
           port = port,
           address = '',
           on_connect = self.connect_client,
           on_disconnect = self.disconnect_client,
           timeout = timeout)

    def loop(self):
        while self.should_run:
           self.telnet.poll()
           self.handle_players()

        self.log.log("Server shutting down.")

    def connect_client(self, client):

        # Log the connection and instantiate a new player for this connection.
        self.log.log("New client connection on port %s." % client.addrport())
        new_player = player.Player(client, self)
        self.players.append(new_player)

        # Now set their state to the name entry screen.
        new_player.state = state.State("login")

    def disconnect_client(self, client):
        self.log.log("Client disconnect on port %s." % client.addrport())
        for player in self.players:
           if client == player.client:
              self.players.remove(player)

    def handle_players(self):
        for player in self.players:
            curr_state = player.state.get()
            if curr_state == "login":
                login.handle(player)
            elif curr_state == "chat":
                chat.handle(player)

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)
