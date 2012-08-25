# Giles: goban.py
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

from bitstring.bitstring import Bits
import copy

WHITE = "white"
BLACK = "black"

MIN_SIZE = 3
MAX_SIZE = 26

# Deltas for a square grid.  Pretty easy.
SQUARE_DELTAS = ((-1, 0), (1, 0), (0, -1), (0, 1))

# Bitstring values for None, Black, and White.
NONE_BITS = "00"
BLACK_BITS = "01"
WHITE_BITS = "10"

from giles.utils import LETTERS

class Goban(object):
    """A Goban (Go board) implementation, meant for use by various games
    that use Go's rules of capture.
    """

    def __init__(self):

        self.width = 19
        self.height = 19
        self.board = None
        self.printable_board = None

        self.last_row = None
        self.last_col = None

        # TODO: Use a more efficient bitfield representation of a board,
        # so storing all the previous boards is way less memory intensive
        # than it currently is.
        self.prev_board_list = []

        self.init_board()

    def init_board(self):

        # Build a new, empty board at the current size.
        self.board = []
        for r in range(self.height):
            self.board.append([None] * self.width)

        # Update the printable version.
        self.update_printable_board()

    def update_printable_board(self):

        self.printable_board = []
        col_str = "    " + "".join([" " + LETTERS[i] for i in range(self.width)])
        self.printable_board.append(col_str + "\n")
        self.printable_board.append("   ^m.=" + "".join(["=="] * self.width) + ".^~\n")
        for r in range(self.height):
            this_str = "%2d ^m|^~ " % (r + 1)
            for c in range(self.width):
                if r == self.last_row and c == self.last_col:
                    this_str += "^5"
                loc = self.board[r][c]
                if loc == WHITE:
                    this_str += "^Wo^~ "
                elif loc == BLACK:
                    this_str += "^Kx^~ "
                else:
                    this_str += "^M.^~ "
            this_str += "^m|^~ %d" % (r + 1)
            self.printable_board.append(this_str + "\n")
        self.printable_board.append("   ^m`=" + "".join(["=="] * self.width) + "'^~\n")
        self.printable_board.append(col_str + "\n")

    def resize(self, width, height):

        # Bail if the size isn't realistic for a goban.
        if (width < MIN_SIZE or width > MAX_SIZE or
           height < MIN_SIZE or height > MAX_SIZE):
            return None

        # Okay, it's fine.
        self.width = width
        self.height = height
        self.init_board()

    def invert(self, reflect = False):

        # Inverts the colour of all pieces on the board.  Useful for games
        # with a pie rule.  First, build a blank new board.
        new_board = []
        for r in range(self.height):
            new_board.append([None] * self.width)

        # Now, loop through the current board and get actual pieces.  If
        # invert is on, we need to flip both location and colour; else we
        # just flip the color.  The last stone flipped will be the one we
        # mark as the "last move;" this is a bit hacky, but I can live with
        # it.
        for r in range(self.height):
            for c in range(self.width):

                if reflect:
                    dest_r = c
                    dest_c = r
                else:
                    dest_r = r
                    dest_c = c

                if self.board[r][c] == BLACK:
                    new_board[dest_r][dest_c] = WHITE
                    self.last_row = dest_r
                    self.last_col = dest_c
                elif self.board[r][c] == WHITE:
                    new_row[dest_r][dest_c] = BLACK
                    self.last_row = dest_r
                    self.last_col = dest_c

        self.board = new_board
        self.update_printable_board()

    def is_valid(self, row, col):

        if row >= 0 and row < self.height and col >= 0 and col < self.width:
            return True
        return False

    def board_to_bits(self, board):

        # This function takes a board and generates a bitstring out of it.

        bit_str = "0b"
        for r in range(self.height):
            for c in range(self.width):
                if board[r][c] == BLACK:
                    bit_str += BLACK_BITS
                elif board[r][c] == WHITE:
                    bit_str += WHITE_BITS
                else:
                    bit_str += NONE_BITS

        return Bits(bin=bit_str)

    def move_causes_repeat(self, color, row, col):

        # This function fakes a play, gets its results, and compares it to
        # the list of board positions already seen.

        # Bail on the error cases.
        if not self.is_valid(row, col):
            return False

        if self.board[row][col]:
            return False

        # Make a backup of the board.
        board_backup = copy.deepcopy(self.board)

        # Place the piece.
        self.board[row][col] = color

        # Get capture information, and apply it.
        color_captured, capture_list = self.go_find_captures(row, col)

        if color_captured:
            for capture_row, capture_col in capture_list:
                self.board[capture_row][capture_col] = None

        # Now, is this list in the list of previous boards?
        board_bits = self.board_to_bits(self.board)

        if board_bits in self.prev_board_list:
            to_return = True
        else:
            to_return = False

        # Either way, replace the board with the backup...
        self.board = board_backup

        # ...and return the result.
        return to_return

    def go_play(self, color, row, col, suicide_is_valid = True):

        # The meat of this class.  This function returns one of two things:
        # - None if the play is invalid;
        # - A 3-tuple if the play is valid, containing:
        #    * The coordinates of the successful play;
        #    * BLACK or WHITE if those colour pieces were captured, else None;
        #    * A list of captured pieces, else [].

        # Bail quick if the move is invalid.
        if not self.is_valid(row, col):
            return None

        # Is the space already occupied?
        if self.board[row][col]:
            return None

        # Does this move result in a repeat of a previous board?
        if self.move_causes_repeat(color, row, col):
            return None

        if not suicide_is_valid and self.move_is_suicidal(color, row, col):
            return None

        # Okay, it's an unoccupied space.  Let's place the piece...
        self.board[row][col] = color
        self.last_row = row
        self.last_col = col

        # ..and then get back capture information, if any.
        color_captured, capture_list = self.go_find_captures(row, col)

        # If stones can be captured, capture them!
        if color_captured:
            for capture_row, capture_col in capture_list:
                self.board[capture_row][capture_col] = None


        # Update the printable board representation...
        self.update_printable_board()

        # ...add it to the list of previous board layouts...
        self.prev_board_list.append(self.board_to_bits(self.board))

        # ...and return the information about the successful play.
        return ((row, col), color_captured, capture_list)

    def go_find_captures(self, row, col):

        # If we somehow get called with an empty space, bail quick.
        color = self.board[row][col]
        if not color:
            return (None, [])

        # All right, we have work to do.  We will check all adjacent pieces
        # of the /other/ color first, because if those are captured we don't
        # have to check the pieces that are the same color.
        opponent_piece_list = []
        empty_space_adjacent = False
        for delta in SQUARE_DELTAS:
            new_row = row + delta[0]
            new_col = col + delta[1]
            if self.is_valid(new_row, new_col):
                piece_at_loc = self.board[new_row][new_col]
                if piece_at_loc and piece_at_loc != color:
                    opponent_color = self.board[new_row][new_col]
                    opponent_piece_list.append((new_row, new_col))
                elif not piece_at_loc:
                    # Empty space adjacent.  This can't be a suicide, and any
                    # adjacent pieces of this color also don't need to be
                    # checked, as we just found a liberty.
                    empty_space_adjacent = True

        # Any adjacent pieces of our color are obviously connected in a group
        # with this new piece, so with a recursive determiner we only need to
        # check this one piece.

        if opponent_piece_list or not empty_space_adjacent:

            capture_list = []
            for opponent_piece in opponent_piece_list:

                # Build a fresh visitation table.  We need to do this because
                # we often "bail fast" if we discover a liberty, and there's
                # no simple way to paint those cells as "leads to liberty."
                # I can think of some ways involving look-up tables, but for
                # now we suck up the overhead of the visitation table rebuild,
                # since it happens at most four times per play.  TODO: Implement
                # such a method.
                visit_table = []
                for i in range(self.height):
                    visit_table.append([None] * self.width)

                capture_list.extend(self.recurse_captures(opponent_color,
                   opponent_piece[0], opponent_piece[1], visit_table))

            if capture_list:

                # This move captured some opponent's pieces!  Awesome.  Done.
                to_return = (opponent_color, capture_list)

            else:
                
                # Ugh, we have to check ourselves to see if this was a suicide.
                visit_table = []
                for i in range(self.height):
                    visit_table.append([None] * self.width)
                capture_list.extend(self.recurse_captures(color, row, col,
                   visit_table))
                if capture_list:

                    # Suicide.
                    to_return = (color, capture_list)

                else:

                    # No captures either way.
                    to_return = (None, [])
        else:

            # No opponent's pieces nearby, and we have a liberty.  Absolutely
            # no capture possible here.
            to_return = (None, [])

        # Either way, return what we've found.
        return to_return

    def recurse_captures(self, color, row, col, visit_table):

        # Bail if this is a bad coordinate.
        if not self.is_valid(row, col):
            return None
        
        # Bail if we've been here before.
        if visit_table[row][col]:
            return None

        # Okay, so, is this an empty cell?  If so, we found a liberty, and
        # whatever group we're checking is safe.
        if not self.board[row][col]:
            return []

        # If it's the wrong color, no dice either.
        if self.board[row][col] != color:
            return None

        # Okay, so, it's a piece of the right color we haven't visited before.
        # Mark it as visited...
        visit_table[row][col] = True

        # ...and start up a list of further calls.  If any of them return an
        # empty list, we know this group has a liberty and can return [];
        # otherwise we have to return a concatenation of the lists of all
        # pieces found further on.
        return_list = [(row, col)]
        found_liberty = False
        for delta in SQUARE_DELTAS:
            recurse_return = self.recurse_captures(color, row + delta[0],
               col + delta[1], visit_table)
            if recurse_return == []:

                # A liberty found!  Bail immediately.
                return []

            elif recurse_return:

                # Some sub-group with no liberties.  Extend our list.
                return_list.extend(recurse_return)

        # If we never returned, we never found a liberty.  We need to return
        # the list of pieces, since as far as we can tell we have no liberties.
        return return_list

    def move_is_suicidal(self, color, row, col):

        # First, make sure the space is empty.
        if self.board[row][col]:
            return False

        # Okay, so, this is actually pretty easy.  Put a fake piece here...
        self.board[row][col] = color

        # ...and see if go_find_captures returns captures of our color.
        capture_return = self.go_find_captures(row, col)

        # Make sure to remove that temporary piece.
        self.board[row][col] = None

        if capture_return[0] == color:
            # The captures are of the same color.  This is suicidal.
            return True
        else:
            return False
