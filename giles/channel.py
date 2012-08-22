# Giles: channel.py
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

class Channel(object):
    """Channels are alternate communication paths that players can
    connect to and disconnect from.  Messages sent to a channel go to
    all players connected to that channel.
    """

    def __init__(self, name, persistent = False, notifications = True, gameable = False, key = None):

        self.display_name = name
        self.name = name.lower()
        self.persistent = persistent
        self.notifications = notifications
        self.gameable = gameable
        self.key = key
        self.listeners = []

    def __repr__(self):
        return self.display_name

    def is_connected(self, player):

        if player in self.listeners:
            return True
        return False

    def connect(self, player, key = None):

        if self.is_connected(player):
            player.tell_cc("Already connected to channel ^G%s^~.\n" % self)
            return False

        elif self.key and key != self.key:
            player.tell("Incorrect key.\n")
            return False

        else:
            if self.notifications:
                self.broadcast_cc("^Y%s^~ has connected to channel ^G%s^~.\n" % (player, self))
            self.listeners.append(player)
            player.tell_cc("Connected to channel ^G%s^~.\n" % self)

            player.server.log.log("%s connected to channel %s." % (player, self))

    def disconnect(self, player):

        if player not in self.listeners:
            player.tell_cc("Cannot disconnect from ^G%s^~; you're not connected.\n" % self)
            return False

        else:
            self.listeners.remove(player)

            if self.notifications:
                self.broadcast_cc("^Y%s^~ has disconnected from channel ^G%s^~.\n" % (player, self))

            player.tell_cc("Disconnected from channel ^G%s^~.\n" % self)

            player.server.log.log("%s disconnected from channel %s." % (player, self))

    def broadcast(self, msg):

        for player in self.listeners:
            player.tell("*%s* %s" % (self, msg))

    def broadcast_cc(self, msg):

        for player in self.listeners:
            player.tell_cc("^G*%s*^~ %s" % (self, msg))

    def send(self, player, msg):

        if player not in self.listeners:
            player.tell_cc("Cannot send message to ^G%s^~; you're not connected.\n" % self)
            player.server.log.log("%s failed to send %s to %s; not connected." % (player, msg, self))
            return False

        else:
            self.broadcast_cc("^Y%s^~: %s\n" % (player, msg))
            player.server.log.log("*%s* %s: %s" % (self, player, msg))
            return True
