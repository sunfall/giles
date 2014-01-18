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
import sys
import time
import traceback

import admin_manager
import die_roller
import channel_manager
import configurator
import game_master

import chat
import location
import login

# How many ticks should pass between cleanup sweeps?
CLEANUP_TICK_INTERVAL = 100

# What about keepalives?
KEEPALIVE_TICK_INTERVAL = 1000

# And game ticks?
GAME_TICK_INTERVAL = 20

class Server(object):
    """The Giles server itself.  Tracks all players, games in progress,
    and so on.
    """

    def __init__(self, name="Giles", source_url = None, admin_password = None):

        if not source_url:
            print("Nice try setting source_url to nothing.  Bailing.")
            sys.exit(1)

        self.name = name
        self.source_url = source_url
        self.log = log.Log(name)
        self.players = []
        self.spaces = []
        self.should_run = True
        self.timestamp = None
        self.current_day = None
        self.update_timestamp()
        self.update_day()

        # Initialize the various workers.
        self.die_roller = die_roller.DieRoller()
        self.configurator = configurator.Configurator()
        self.channel_manager = channel_manager.ChannelManager(self)
        self.game_master = game_master.GameMaster(self)
        self.chat = chat.Chat(self)
        self.login = login.Login(self)

        # The admin manager needs the channel manager.
        self.admin_manager = admin_manager.AdminManager(self, admin_password)

        # Set up the global channel for easy access.
        self.wall = self.channel_manager.channels[0]
        self.log.log("Server started up.")

    def instantiate(self, port=9435, timeout=.05):
        self.telnet = TelnetServer(
           port = port,
           address = '',
           on_connect = self.connect_client,
           on_disconnect = self.disconnect_client,
           timeout = timeout)
        self.update_timestamp()

    def update_timestamp(self):
        old_timestamp = self.timestamp
        self.timestamp = time.strftime("%H:%M")
        return (old_timestamp != self.timestamp)

    def update_day(self):
        old_day = self.current_day
        self.current_day = time.strftime("%A, %B %d, %Y")
        return (old_day != self.current_day)

    def loop(self):

        cleanup_ticker = 0
        keepalive_ticker = 0
        game_ticker = 0
        while self.should_run:
            self.telnet.poll()
            self.handle_players()

            # Handle the tickers.
            cleanup_ticker += 1
            if (cleanup_ticker % CLEANUP_TICK_INTERVAL) == 0:
                self.cleanup()
                self.channel_manager.cleanup()
                self.game_master.cleanup()
                cleanup_ticker = 0

            keepalive_ticker += 1
            if (keepalive_ticker % KEEPALIVE_TICK_INTERVAL) == 0:
                self.keepalive()
                keepalive_ticker = 0

            game_ticker += 1
            if (game_ticker % GAME_TICK_INTERVAL) == 0:
                self.game_master.tick()
                game_ticker = 0

                # Since this is roughly once a second, abuse it to update
                # the timestamp as well. If the timestamp actually changed
                # then update the prompts for all players.
                if self.update_timestamp():
                    if self.update_day():
                        self.announce_midnight()
                    self.update_prompts()

        self.log.log("Server shutting down.")

    def connect_client(self, client):

        # Log the connection and instantiate a new player for this connection.
        self.log.log("New client connection on port %s." % client.addrport())
        new_player = player.Player(client, self)
        self.players.append(new_player)

        # Now set their state to the name entry screen.
        new_player.state = state.State("login")

        # Enable echo/char mode on the client connection
        client.request_will_echo()
        client.request_will_sga()

    def disconnect_client(self, client):
        self.log.log("Client disconnect on port %s." % client.addrport())

        for player in self.players:
            if client == player.client:
                self.admin_manager.remove_player(player)
                self.channel_manager.remove_player(player)
                self.game_master.remove_player(player)
                self.players.remove(player)
                if player.location:
                    player.location.remove_player(player, "^!%s^. has disconnected from the server.\n" % player)

    def handle_players(self):
        for player in self.players:
            curr_state = player.state.get()
            if curr_state == "login":
                try:
                    self.login.handle(player)
                except Exception as e:
                    player.tell_cc("^RSomething went horribly awry with login.  Logging.^~\n")
                    self.log.log("The login module bombed with player %s: %s\n%s" % (player.name, e, traceback.format_exc()))
            elif curr_state == "chat":
                try:
                    self.chat.handle(player)
                except Exception as e:
                    player.tell_cc("^RSomething went horribly awry with chat.  Logging.^~\n")
                    self.log.log("The chat module bombed with player %s: %s\n%s" % (player.name, e, traceback.format_exc()))
                    player.prompt()

    def announce_midnight(self):
        for player in self.players:
            player.tell_cc("It is now ^C%s^~.\n" % self.current_day)

    def update_prompts(self):
        for player in self.players:
            if player.state.get() == "chat" and player.config["timestamps"]:
                player.prompt()

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)

    def get_space(self, space_name):

        for space in self.spaces:
            if space.name == space_name:
                return space

        # Didn't find the space.
        new_space = location.Location(space_name)
        self.spaces.append(new_space)
        return new_space

    def get_player(self, player_name):

        lower_name = player_name.lower()
        for player in self.players:
            if player.name == lower_name:
                return player

        return None

    def cleanup(self):

        for space in self.spaces:
            if len(space.players) == 0:
                self.log.log("Deleting stale space %s." % space.name)
                self.spaces.remove(space)
                del space

    def keepalive(self):

        # For now, just request a window size negotiation.  Unexciting,
        # but it /is/ traffic over the TCP connection.
        for player in self.players:
            player.client.request_naws()
