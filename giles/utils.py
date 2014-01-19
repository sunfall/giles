# Giles: utils.py
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

class Struct(object):
    # Empty class, useful for making "structs."

    def __init__(self, attributes={}):

        # For convenience, it supports getting a dictionary of attributes to
        # set.
        for attribute in attributes:
            setattr(self, attribute, attributes[attribute])

def booleanize(msg):
    # This returns:
    # -1 for False
    # 1 for True
    # 0 for invalid input.

    if type(msg) != str:
        return 0

    msg = msg.strip().lower()
    if msg in ('1', 'true', 't', 'yes', 'y', 'on'):
        return 1
    elif msg in ('0', 'false', 'f', 'no', 'n', 'off'):
        return -1

    return 0

LETTERS = "abcdefghijklmnopqrstuvwxyz"
def demangle_move(move_list):

    # Most games take a move in the format Ln, where L is a letter
    # and n is some number.  They make take more than one such move,
    # for games where you move a piece from a to b.  Rather than
    # force every game to reimplement all the various ways players
    # might want to enter this, this function does the best it can
    # to return a valid set of coordinates.  It assumes zero-based
    # indexing, letter first; you may have to reverse entries, etc.
    # to get it how you want, but at least you don't have to parse
    # wacky strings.  This function will properly handle:
    # * a2
    # * a2 b2
    # * a2-b2
    # * a2,b2
    # * a2/b2
    # * a2, b2
    # ...and further coordinated versions of the same, including
    # mixed versions, ones with too many dashes, and so on.  It
    # returns a list of tuples representing the 0-indexed
    # letter/number sets, and a None if any of the entries were
    # nonsense ("aa5", "0", "b", et cetera).

    # Okay, so, to start, let's concatenate whatever list of
    # strings we got...
    move_str = " ".join(move_list)

    # ...and then replace every random character we see in the
    # string with a space.
    new_str = ""
    for char in move_str:
        if char.isalnum():
            new_str += char
        else:
            new_str += " "

    # Now we lowercase it and split it back out into components.
    new_str_bits = new_str.lower().split()

    # Now let's work on each of the bits...
    to_return = []
    for bit in new_str_bits:

        # Is it at least two and at most three characters long?
        if len(bit) < 2 or len(bit) > 3:
            return None

        # Is the first bit a letter and the rest a number?
        if not bit[0].isalpha() or not bit[1:].isdigit():
            return None

        # Okay, good.  Let's get the values.  Remember that it's zero-based,
        # so the number needs to be decremented by one.
        letter_val = LETTERS.index(bit[0])
        number_val = int(bit[1:]) - 1

        to_return.append((letter_val, number_val))

    # Since we never bailed due to bad data, let's return the list.
    return to_return

MAX_NAME_LENGTH = 16
def name_is_valid(name_str):

    # A name in Giles, whether it's a player, table, or channel, must follow
    # a specific pattern:
    # - It must be alphanumeric only;
    # - It must start with a letter, not a number (aliases are numerical);
    # - It must be at most MAX_NAME_LENGTH long.

    # Bail on the easy duds.
    if not name_str or type(name_str) != str or len(name_str) > MAX_NAME_LENGTH:
        return False

    # Is it fully alphanumeric and is the first character not a digit?
    if not name_str.isalnum() or name_str[0].isdigit():
        return False

    # Passed the tests.
    return True

def get_plural_str(count, base):

    if count == 1:
        return "1 " + base
    return "%s %ss" % (count, base)
