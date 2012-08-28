# Giles: channel_manager.py
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

from channel import Channel

from giles.utils import name_is_valid

class ChannelManager(object):
    """The ChannelManager handles individuals connecting and disconnecting
    to the various channels, maintains the global channel, and so on.
    """

    def __init__(self, server):

        self.server = server

        # Set up the global channel.
        self.channels = [Channel("Global", persistent = True, notifications = False, gameable = False)]

    def add_channel(self, name, persistent = False, notifications = True, gameable = False, key = None):

        if not name_is_valid(name):
            return False

        # Make sure this isn't a duplicate.
        if self.has_channel(name):
            return False

        # Not a duplicate.  Make a new entry.  Like users, 'name' is for
        # comparison; the channel itself tracks its display name.
        self.channels.append(Channel(name, persistent, notifications, gameable, key))
        return self.channels[-1]

    def has_channel(self, name):

        lower_name = name.lower()
        for other in self.channels:
            if other.name == lower_name:
                return other

        return False

    def connect(self, player, name, key = None):

        success = False

        if type(name) == str and len(name) > 0:

            # Does this channel already exist?  If so, snag that.
            lower_name = name.lower()
            for channel in self.channels:
                if channel.name == lower_name:
                    success = channel.connect(player, key)

            if not success:

                # Huh.  All right; let's make it!
                new_channel = self.add_channel(name, key = key)
                if new_channel:

                    # Creation was successful.  Connect the player.
                    success = new_channel.connect(player, key)

        return success

    def disconnect(self, player, name):

        success = False

        if type(name) == str and len(name) > 0:

            lower_name = name.lower()
            for channel in self.channels:
                if channel.name == lower_name:
                    success = channel.disconnect(player)

        return success

    def remove_player(self, player):

        for channel in self.channels:
            if player in channel.listeners:
                channel.disconnect(player)

    def send(self, player, msg, name):

        success = False
        if type(name) == str and len(name) > 0:

            lower_name = name.lower()
            for channel in self.channels:
                if channel.name == lower_name:
                    success = channel.send(player, msg)

        return success

    def cleanup(self):

        # Remove any non-persistent channels with no listeners.
        for channel in self.channels:
            if not channel.persistent and len(channel.listeners) == 0:
                self.server.log.log("Deleting stale channel %s." % channel)
                self.channels.remove(channel)
                del channel
