# Giles: piece.py
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

from giles.utils import Struct

class Piece(object):
    """A piece meant to be used in a layout.  This is a very simple
    structure; it has a character that represents it (and potentially
    a different "last move indicator" representation) and a color.

    Setters and getters are not implemented, as this is Python.  There
    is also a 'data' element, which is a simple Struct, useful if you
    want to track information directly in the piece (such as the owner).
    """

    def __init__(self, color, char, last_char=None):
        self.color = color
        self.char = char
        if last_char:
            self.last_char = last_char
        else:
            self.last_char = char

        self.data = Struct()
