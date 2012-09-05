# Giles: layout.py
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

class Layout(object):
    """A layout for a game.  For a board game, this would be the board and
    representations of the pieces on that board; for a card game, this
    would be some sort of display that shows the cards on the table.

    Importantly, layouts are not meant to understand the games they represent.
    The idea is that you tell a layout "there is a piece at location x, y
    colored black in the shape of an x," and it keeps a visual representation
    of that handy, but it doesn't grasp that said piece is actually for a
    particular player or with a particular purpose.

    Layouts should auto-update an internal string representation when changed
    via resize(), move(), place(), or remove().  When the layout's look is
    gathered via get() or __str__(), it will simply spit out the saved
    representation.  If you muck with a layout in other ways, be forewarned
    that the internal strings will need to be updated as well.
    """

    def __init__(self):

        self.representation = ""

    def __repr__(self):

        return self.representation

    def __str__(self):

        return self.__repr__()

    def get(self):

        return self.__repr__()

    def update(self):

        # Override this function with the bits that actually generate the
        # internal representation based on the current state.

        self.representation = "I have been updated.\n"

    def resize(self):

        # Override this function (presumably with parameters) with the bits
        # that handle resizing layouts (assuming your layout /can/ be resized.)
        #
        # If you like, remember to call this via super() and it'll do the
        # updating for you.
        self.update()

    def place(self):

        # Override this function (presumably with parameters) with the bits
        # that handle placing a piece (whatever that might be) on the layout.
        #
        # If you like, remember to call this via super() and it'll do the
        # updating for you.
        self.update()

    def move(self):

        # Override this function (presumably with parameters) with the bits
        # that handle moving a piece (whatever that might mean) on the layout.
        #
        # If you like, remember to call this via super() and it'll do the
        # updating for you.
        self.update()

    def remove(self):

        # Override this function (presumably with parameters) with the bits
        # that handle removing a piece (whatever that might mean) from the
        # layout.
        #
        # If you like, remember to call this via super() and it'll do the
        # updating for you.
        self.update()
