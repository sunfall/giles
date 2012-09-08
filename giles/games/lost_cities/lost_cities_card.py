# Giles: lost_cities_card.py
# Copyright 2012 Phil Bordelon, Rob Palkowski
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

from giles.games.hand import Hand
from giles.games.playing_card import PlayingCard

# trick.py's implementation of sorted_hand() is perfectly servicable for
# us, so no reason to reinvent the wheel...
from giles.games.trick import sorted_hand

AGREEMENT = "Agreement"

# The five standard suits...
BLUE = "Blue"
GREEN = "Green"
RED = "Red"
WHITE = "White"
YELLOW = "Yellow"

# ...and two more.
CYAN = "Cyan"
MAGENTA = "Magenta"

RANKS = [AGREEMENT, '2', '3', '4', '5', '6', '7', '8', '9', '10']

SHORT = "short"
LONG = "long"

DEFAULT_SUITS = [YELLOW, BLUE, WHITE, GREEN, RED]

class LostCitiesCard(PlayingCard):
    """Implements a Lost Cities card.  By default there are five suits; each
    suit has one card of every rank from 2 to 10, along with three identical
    Agreement cards.  Of course, this class merely implements the cards
    themselves; the utility functions in this module handle the default deck
    creation.
    """

    def __init__(self, r = None, s = None):
        self.rank = r
        self.suit = s

    def __repr__(self):
        if self.rank == AGREEMENT:
            return ("a %s Agreement" % (self.suit))
        else:
            return ("a %s %s" % (self.suit, self.rank))

    def value(self):
        r = self.rank
        if r == AGREEMENT:
            return 1
        if type(r) == int:
            return r
        if r.isdigit():
            return int(r)

SUIT_SHORTHANDS = ['y', 'b', 'w', 'g', 'r', 'c', 'm', 'p']
AGREEMENT_SHORTHANDS = ['a', 'h', 'i', '1']

def new_standard_deck():
    deck = Hand()

    # Add two more agreements to the list of ranks for a total of 3.
    ranks = [AGREEMENT, AGREEMENT]
    ranks.extend(RANKS)

    for r in ranks:
        for s in DEFAULT_SUITS:
            deck.add(LostCitiesCard(r, s))
    return deck

def str_to_card(card_str):

    # This function is meant to take something like "3w" or "ga" and return
    # the card it represents.  It's mainly meant for handling user input.  It
    # handles both orderings, and also handles 10 or 't' for the ten.  Possible
    # options for an agreement are 'a', 'h', 'i', and '1' ("handshake" and the
    # official "investment;" Giles uses "agreement" because it keeps the Ace
    # motif).  Magenta can also be chosen via 'p' (for purple).

    # Bail immediately if we don't have last at least two characters, as that
    # can't possibly be a card.
    if not card_str or type(card_str) != str or len(card_str) < 2:
        return None

    # Unlike with playing cards, we really do need to use a simple state machine
    # here, as either the rank or the suit can come first.
    card_str = card_str.lower()
    suit = None
    rank = None

    if card_str[0] in SUIT_SHORTHANDS:
        state = "suit"
    else:
        state = "rank"

    curr_pos = 0
    str_len = len(card_str)
    while (not suit) or (not rank):
        if curr_pos == str_len:

            # We've reached the end of the string and we're still not done?
            # Bad input.
            return None

        # Okay, fetch the current character.
        curr_char = card_str[curr_pos]
        if state == "suit":

            if curr_char not in SUIT_SHORTHANDS:

                # We're in suit mode but this isn't a suit.  Bad card.
                return None

            else:
                suit = str_to_suit(curr_char)

            # Okay, we got the suit; shift state to rank.  If we already got
            # the rank this is harmless as the while loop will terminate.
            state = "rank"

        elif state == "rank":

            if curr_char.isdigit():

                # We'd like to think this is the easy case, but no, we have to
                # deal with 10.
                if curr_char == '1':

                    # Assume rank is an Agreement.
                    rank = AGREEMENT

                    # Is there even a next character?
                    if curr_pos + 1 < str_len:

                        next_char = card_str[curr_pos + 1]

                        # Is it a 0?
                        if next_char == '0':

                            # Ten!  Increment curr_pos because it takes two.
                            rank = 10
                            curr_pos += 1

                        elif next_char.isdigit():

                            # Huh?  11?  17?  Not a valid card.
                            return None

                else:

                    # Standard case of digits.
                    rank = int(curr_char)

            elif curr_char == "t":
                rank = 10
            elif curr_char in AGREEMENT_SHORTHANDS:
                rank = AGREEMENT
            else:

                # Invalid rank representation.
                return None

            # Okay, we got the rank; shift state to suit.  If we already got
            # the suit this is harmless as the while loop will terminate.
            state = "suit"

        # No matter what state we just finished with, increment our string
        # position.
        curr_pos += 1

    # If someone was clever and set the rank to 0, that's not a card.
    if not rank:
        return None

    # Otherwise, we have a valid suit and rank.  Create a matching card.
    return LostCitiesCard(rank, suit)

def str_to_suit(suit_str):

    suit_str = suit_str.lower()

    if suit_str in ("y", "yellow",):
        return YELLOW
    elif suit_str in ("b", "blue",):
        return BLUE
    elif suit_str in ("w", "white",):
        return WHITE
    elif suit_str in ("g", "green",):
        return GREEN
    elif suit_str in ("r", "red",):
        return RED
    elif suit_str in ("c", "cyan",):
        return CYAN
    elif suit_str in ("m", "magenta", "p", "purple",):
        return MAGENTA

    return None

def get_color_code(suit):

    # Returns the color code for a suit.
    color_code = "^w"
    if suit == YELLOW:
        color_code = "^Y"
    elif suit == BLUE:
        color_code = "^B"
    elif suit == WHITE:
        color_code = "^W"
    elif suit == GREEN:
        color_code = "^G"
    elif suit == RED:
        color_code = "^R"
    elif suit == CYAN:
        color_code = "^C"
    elif suit == MAGENTA:
        color_code = "^M"

    return color_code

def card_to_str(card, mode = SHORT, colored = True):

    # Returns a card in a reasonable text form for printing full hands,
    # etc. when in SHORT mode, or in nice pretty long form when in LONG
    # mode.  If colored is set, use the color code too.

    if colored:
        color_code = get_color_code(card.suit)

    if mode == SHORT:

        if not card:
            return "  "
        short_suit = card.suit[0].upper()
        short_rank = value_to_str(card.value())

        if colored:
            return "%s%s%s^~" % (color_code, short_suit, short_rank)
        else:
            return "%s%s" % (short_suit, short_rank)

    elif mode == LONG:
        if colored:
            return "%s%s^~" % (color_code, repr(card))
        else:
            return repr(card)

def hand_to_str(hand, colored = True, is_sorted = True):

    # Returns a reasonable string representation of a given hand.
    # Note that this function expects the hand to be sorted by default, and
    # will put in dividers between suits; if it is not, pass in False to
    # is_sorted.

    last_suit = None
    to_return = ""
    for card in hand:
        if is_sorted and card.suit != last_suit:
            if last_suit:
               to_return += "/ "
            last_suit = card.suit
        to_return += card_to_str(card, colored = colored) + " "

    return to_return

def value_to_str(value):

    if value in range(2, 10):
        return str(value)
    elif value == 10:
        return "t"
    elif value == 1:
        return "a"
    else:
        return "?"
