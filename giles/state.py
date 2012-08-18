# Giles: state.py
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

class State(object):
    """A state, whether for a game or a player or whatever.  States
    are meant to be semi-opaque.  The idea is that there is a top-level
    descriptor, like "name_entry" or "waiting_for_config," that can be
    poked at and used to determine the appropriate handler; the handler
    can then use the substate element how it sees fit (strings, objects,
    whatever).  That substate is eliminated every time the primary state
    changes.
    """

    def __init__(self):
        self.set("")

    def get(self):
        """Return the primary state."""

        return(self.primary)

    def get_sub(self):
        """Return the substate."""

        return self.secondary

    def set(self, val):
        """Set the primary state.  Always eliminates the substate."""

        self.primary = val
        self.secondary = None

    def set_sub(self, val):
        """Set the substate.  Does not modify the primary state."""

        self.secondary = val
