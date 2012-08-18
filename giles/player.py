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

class Player(object):
    """A player on Giles.  Tracks their name, current location, and other
    relevant stateful bits.
    """

    def __init__(self, client, server, name="Guest", location=None, state=None):
        self.client = client
        self.server = server
        self.name = name
        self.location = location
        self.state = None

    def move(self, location):
        if location:

            if self.location:
                self.location.remove_player(self)

            self.location = location
            self.location.add_player(self)
