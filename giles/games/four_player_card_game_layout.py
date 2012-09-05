# Giles: 4_player_card_game_layout.py
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

NORTH = "North"
EAST = "East"
SOUTH = "South"
WEST = "West"

NORTH_POINTER = "^^^^" # Due to Miniboa's caret codes.
EAST_POINTER = ">>"
SOUTH_POINTER = "vv"
WEST_POINTER = "<<"
NONE_POINTER = "++"

BLANK_ROW = "       |                    |\n"

class FourPlayerCardGameLayout(Layout):
    """A standard layout for a 4-player card game, with North, East, South,
    and West sitting at a table.
    """

    def __init__(self):

        self.north_card = None
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
        if who == NORTH:
            card_str = card_to_str(self.north_card)
        elif who == EAST:
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
        self.representation += "       |         ^RNN^~         |\n"
        self.representation += BLANK_ROW
        self.representation += "       |         %s         |\n" % self.card_str(NORTH)
        self.representation += BLANK_ROW
        self.representation += "       | ^MWW^~  %s  %s  %s  ^MEE^~ |\n" % (self.card_str(WEST), self.turn_pointer, self.card_str(EAST))
        self.representation += BLANK_ROW
        self.representation += "       |         %s         |\n" % self.card_str(SOUTH)
        self.representation += BLANK_ROW
        self.representation += "       |         ^RSS^~         |\n"
        self.representation += "       `--------------------'\n"

    def change_turn(self, who):

        self.turn = who
        if self.turn == NORTH:
            self.turn_pointer = NORTH_POINTER
        elif self.turn == EAST:
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

        if who == NORTH:
            self.north_card = card
        elif who == EAST:
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

        self.north_card = None
        self.east_card = None
        self.south_card = None
        self.west_card = None
        self.last_played = None
        self.update()

    def remove(self):

        # Cards cannot (currently) be removed; use clear() instead.
        pass
