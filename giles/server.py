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

class Server(object):
    """The Giles server itself.  Tracks all players, games in progress,
    and so on.
    """

    def __init__(self, name="library-alpha"):
        self.name = name
        self.log = log.Log(name)
        self.clients = []
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
           self.handle_clients()

        self.log.log("Server shutting down.")

    def connect_client(self, client):
        self.log.log("New client connection on port %s." % client.addrport())
        self.clients.append(client)
        client.send("Welcome to %s!\n" % self.name)

    def disconnect_client(self, client):
        self.log.log("Client disconnect on port %s." % client.addrport())
        self.clients.remove(client)

    def handle_clients(self):
        pass

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)
