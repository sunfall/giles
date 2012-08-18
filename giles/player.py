# Giles: player.py
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

import time

class Player(object):
    """A player on Giles.  Tracks their name, current location, and other
    relevant stateful bits.
    """

    def __init__(self, client, server, name="Guest", location=None, state=None):
        self.client = client
        self.server = server
        self.name = name
        self.location = location
        self.timestamps = False
        self.state = None

    def move(self, location, custom_join = None, custom_part = None):
        if location:

            if self.location:
                if custom_part:
                    self.location.remove_player(self, custom_part)
                else:
                    self.location.remove_player(self)

            self.location = location
            if custom_join:
                self.location.add_player(self, custom_join)
            else:
                self.location.add_player(self)

    def config(self, msg):

        invalid = False
        if msg:
            config_bits = msg.lower().split()
            if len(config_bits) == 2 and config_bits[0] == "ts":
                if config_bits[1] == "on":
                    self.timestamps = True
                    self.server.log.log("%s turned timestamps on.\n" % self.name)
                elif config_bits[1] == "off":
                    self.timestamps = False
                    self.server.log.log("%s turned timestamps off.\n" % self.name)
                else:
                    invalid = True
            else:
                invalid = True
        else:
            invalid = True

        if invalid:
            self.tell("Invalid configuration.\n")

    def tell(self, msg):
        if self.timestamps:
            msg = "(%s) %s" % (time.strftime("%H:%M"), msg)
        self.client.send(msg)

    def tell_cc(self, msg):
        if self.timestamps:
            msg = "(^C%s^~) %s" % (time.strftime("%H:%M"), msg)
        self.client.send_cc(msg)
