# Giles: location.py
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

class Location(object):
    """A location on Giles.  People are informed when others leave and join
    this location, and new ones are instantiated at will.
    """

    def __init__(self, name):
        self.name = name
        self.players = []

    def add_player(self, player, msg=None):
        if not msg:
            msg = "^Y%s^~ has joined ^!%s^..\n" % (player, self.name)

        if player not in self.players:

            self.notify_cc(msg)
            self.players.append(player)

    def remove_player(self, player, msg=None):

        if not msg:
            msg = "^Y%s^~ has left ^!%s^..\n" % (player, self.name)

        if player in self.players:
            self.players.remove(player)

        self.notify_cc(msg)

    def notify(self, message):
        for player in self.players:
            player.tell(message)

    def notify_cc(self, message):
        for player in self.players:
            player.tell_cc(message)
