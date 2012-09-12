# Giles: three_player_card_game_layout.py
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

from giles.games.layout import Layout
from giles.games.playing_card import card_to_str

EAST = "East"
SOUTH = "South"
WEST = "West"

EAST_POINTER = ">>"
SOUTH_POINTER = "vv"
WEST_POINTER = "<<"
NONE_POINTER = "++"

BLANK_ROW = "       |                    |\n"

class ThreePlayerCardGameLayout(Layout):
    """A standard layout for a 3-player card game.  Much like a 4P one, but
    it ditches North.  This allows reuse of EAST, SOUTH, and WEST in games
    that support both 3 and 4 players.
    """

    def __init__(self):

        self.east_card = None
        self.south_card = None
        self.west_card = None
        self.last_played = None
        self.turn = None
        self.turn_pointer = NONE_POINTER
        self.update()

    def card_str(self, who):

        color_str = "^w"
        if who == self.last_played:
            color_str = "^W"

        card_str = "  "
        if who == EAST:
            card_str = card_to_str(self.east_card)
        elif who == SOUTH:
            card_str = card_to_str(self.south_card)
        elif who == WEST:
            card_str = card_to_str(self.west_card)

        return "%s%s^~" % (color_str, card_str)

    def update(self):

        self.representation = "\n"
        if not self.turn:
            self.representation += "   A shuffled deck of playing cards lies face-down on the table.\n"
            return

        self.representation += "       .--------------------.\n"
        self.representation += BLANK_ROW
        self.representation += "       | ^MWW^~  %s  %s  %s  ^BEE^~ |\n" % (self.card_str(WEST), self.turn_pointer, self.card_str(EAST))
        self.representation += BLANK_ROW
        self.representation += "       |         %s         |\n" % self.card_str(SOUTH)
        self.representation += BLANK_ROW
        self.representation += "       |         ^RSS^~         |\n"
        self.representation += "       `--------------------'\n"

    def change_turn(self, who):

        self.turn = who
        if self.turn == EAST:
            self.turn_pointer = EAST_POINTER
        elif self.turn == SOUTH:
            self.turn_pointer = SOUTH_POINTER
        elif self.turn == WEST:
            self.turn_pointer = WEST_POINTER
        else:
            self.turn_pointer = NONE_POINTER

        self.update()

    def resize(self):

        # Cannot be resized.
        pass

    def place(self, who, card):

        if who == EAST:
            self.east_card = card
        elif who == SOUTH:
            self.south_card = card
        elif who == WEST:
            self.west_card = card

        self.last_played = who
        self.update()

    def move(self):

        # Cards cannot (currently) be moved.
        pass

    def clear(self):

        self.east_card = None
        self.south_card = None
        self.west_card = None
        self.last_played = None
        self.update()

    def remove(self):

        # Cards cannot (currently) be removed; use clear() instead.
        pass
