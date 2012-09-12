# Giles: square_grid_layout.py
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
from giles.games.piece import Piece

COLS = "abcdefghijklmnopqrstuvwxyz"

class SquareGridLayout(Layout):
    """A standard layout for a square-grid, either square-square or rectangular.
    By default, last_moves is never updated, and you have to update it yourself
    externally (it's a list of (row, col) tuples); that said, all of place, move,
    and remove can optionally replace the list with the destination locations (and,
    in the case of move, both the source /and/ destination).
    """

    def __init__(self, board_color = None, cell_color = None, highlight_color = None):

        super(SquareGridLayout, self).__init__()

        self.last_moves = []
        self.width = 0
        self.height = 0
        self.col_str = ""
        self.top_row = ""
        self.bottom_row = ""
        self.grid = []

        if not board_color:
            board_color = "^m"
        if not cell_color:
            cell_color = "^M"
        if not highlight_color:
            highlight_color = "^5"

        self.board_color = board_color
        self.cell_color = cell_color
        self.highlight_color = highlight_color

    def is_valid(self, row, col):

        if row >= 0 and row < self.height and col >= 0 and col < self.width:
            return True
        else:
            return False

    def update(self):

        self.representation = "\n" + self.col_str
        self.representation += self.top_row
        for r in range(self.height):
            r_disp = r + 1
            this_row = "%2d %s|^~ " % (r_disp, self.board_color)
            for c in range(self.width):
                last_move = False
                if (r, c) in self.last_moves:
                    last_move = True
                    this_row += self.highlight_color
                loc = self.grid[r][c]
                if loc:
                    this_row += loc.color
                    if last_move:
                        this_row += loc.last_char
                    else:
                        this_row += loc.char
                    this_row += "^~ "
                else:
                    this_row += self.cell_color + ".^~ "
            this_row += self.board_color + "|^~ %d\n" % r_disp
            self.representation += this_row
        self.representation += self.bottom_row
        self.representation += self.col_str

    def resize(self, width, height = None):

        if height == None:
            height = width

        if width <= 0 or height <= 0:
            return False

        self.grid = []
        for r in range(height):
            self.grid.append([None] * width)

        self.width = width
        self.height = height

        self.col_str = "    " + "".join([" " + COLS[i] for i in range(self.width)]) + "\n"
        equals_str = "".join(["=="] * self.width)
        self.top_row = "   " + self.board_color + ".=" + equals_str + ".^~\n"
        self.bottom_row = "   " + self.board_color + "`=" + equals_str + "'^~\n"
        self.update()
        return True

    def place(self, piece, row, col, update_last_moves = False):

        if self.is_valid(row, col):
            self.grid[row][col] = piece
            if update_last_moves:
                self.last_moves = [(row, col)]
            self.update()
            return True
        else:
            return False

    def move(self, src_r, src_c, dst_r, dst_c, update_last_moves = False):

        if (self.is_valid(src_r, src_c) and self.is_valid(dst_r, dst_c) and
           self.grid[src_r][src_c]):

            self.grid[dst_r][dst_c] = self.grid[src_r][src_c]
            self.grid[src_r][src_c] = None
            if update_last_moves:
                self.last_moves = [(src_r, src_c), (dst_r, dst_c)]
            self.update()
            return True
        else:
            return False

    def remove(self, row, col, update_last_moves = False):

        if self.is_valid(row, col) and self.grid[row][col]:
            self.grid[row][col] = None
            if update_last_moves:
                self.last_moves = [(row, col)]
            self.update()
            return True
        else:
            return False
