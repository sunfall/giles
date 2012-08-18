# Giles: rps.py
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

from giles.state import State

MAX_SESSION_NAME_LENGTH = 16

class RockPaperScissors(object):
    """A Rock-Paper-Scissors game session implementation.
    """

    def __init__(self, session_name):

        self.game_display_name = "Rock-Paper-Scissors"
        self.game_name = "rps"
        self.session_display_name = session_name
        self.session_name = session_name.lower()
        self.state = State("initial")

    def handle(self, player, command_str):
        player.tell_cc("RPS session ^M%s^~ reporting for duty.\n" % self.session_display_name)
