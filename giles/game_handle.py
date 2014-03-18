# Giles: game_handle.py
# Copyright 2014 Phil Bordelon
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

"""
game_handle.py: Control object for a particular game implementation.

GameHandles are meant to be the method by which new instances of games
('tables', in Giles-speak) are instantiated and how game implementations
themselves are reloaded on-the-fly.  In addition, they currently have a
very basic ACL implementation; games can optionally be instantiated only
by admins.  This is meant for both testing and for long-term games where
only one or two instances are meant to be running at the same time.
"""

class GameHandle(object):
    """Implementation of the GameHandle concept, explained above."""

    def __init__(self, path, class_name, admin_only=False):

        self.path = path
        self.class_name = class_name
        self.name = ".".join((path, class_name))
        self.admin_only = admin_only

        # Load in the game.
        self.game_class = None
        self.reload_game()

    def reload_game(self):
        """Forcibly reload the game implementation."""

        self.game_class = _get_loaded_game_module(self.path, self.class_name)


def _get_loaded_game_module(path, class_name):
    """Loads a game module given a path and class name."""

    mod = __import__(path, globals(), locals(), [class_name])
    reload(mod)
    return mod.__dict__[class_name]
