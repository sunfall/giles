# Giles: playing_card.py
# Copyright 2012 Rob Palkowski, Phil Bordelon
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

from random import choice

from giles.games.hand import Hand

ACE = "Ace"
JACK = "Jack"
QUEEN = "Queen"
KING = "King"
JOKER = "Joker"

CLUBS = "Clubs"
DIAMONDS = "Diamonds"
HEARTS = "Hearts"
SPADES = "Spades"

RANKS = [ACE, '2', '3', '4', '5', '6', '7', '8', '9', '10', JACK, QUEEN, KING]
SUITS = [CLUBS, DIAMONDS, HEARTS, SPADES]

SHORT = "short"
LONG = "long"

class PlayingCard(object):
    """PlayingCard is an implementation of a traditional 52-card deck of playing
    cards.

    Ranks and Suits are built-in, and jokers are supported but not issued by
    default.  While Suits are a dictionary mapping each suit to an integer
    value, they are not checked when comparing cards to each other.  Aces are
    valued at one or 14; Kings at thirteen.  As such, a Queen of Clubs (with a
    .value() of 12) is greater than a ten of Hearts, and the value() of two
    Queens will be equal, but the Queen of Hearts != the Queen of Spades.  This
    is not a bug; it allows for simple constructions such as "if mycard in
    myhand" without having to go through absurd gymnastics.

    Methods of note are:  __repr_(), value(), and all ordinal comparisons, e.g.
    __lt__().
    """

    def __init__(self, r = None, s = None, ace_high = True):
        self.rank = r
        self.suit = s
        self.ace_high = ace_high

    def __repr__(self):
        if self.rank == JOKER:
            return ("the %s Joker" % (self.suit))
        else:
            return ("the %s of %s" % (self.rank, self.suit))

    def __lt__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() < other.value()

    def __le__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() <= other.value()

    def __eq__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            # okay, so here's an interesting edge case.  Cards of differing
            # ranks of course can be compared.  however, the Three of Clubs is
            # not the same card as the Three of Diamonds.
            return self.value() == other.value() and self.suit == other.suit

    def __ne__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() != other.value() or self.suit != other.suit

    def __ge__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() >= other.value()

    def __gt__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() > other.value()

    def value(self):
        r = self.rank
        if r == JOKER:
            return None
        if type(r) == int:
            return r
        if r.isdigit():
            return int(r)
        else:
            if r == ACE:
                if self.ace_high:
                    return 14
                else:
                    return 1
            elif r == JACK:
                return 11
            elif r == QUEEN:
                return 12
            elif r == KING:
                return 13
            else:
                return None

def str_to_card(card_str):

    # This function is meant to take something like "10s" or "KH" and return
    # the card it represents.  It's mainly meant for handling user input.  It
    # does not currently handle jokers.

    # Bail immediately if we don't have last at least two characters, as that
    # can't possibly be a card.
    if not card_str or type(card_str) != str or len(card_str) < 2:
        return None

    # If it's three characters long and the first isn't a 1, it's also not a
    # card.  Same if it's just "10" by itself.
    if (len(card_str) == 3 and card_str[0] != "1") or (card_str == "10"):
        return None

    # This was originally a state machine, but there are only two states, and
    # they always come through in the same order.  So let's just do it.
    rank = None
    suit = None
    rank_char = card_str[0].lower()

    # Assume the suit location is the second character.  This is only untrue
    # if the rank is 10.
    suit_loc = 1

    if rank_char.isdigit():
        # If this isn't a one, it has to be the value.
        if rank_char != "1":
            rank = int(rank_char)
        else:
            # Okay, lookahead.  if the next character is a 0, this is
            # a ten; consume it.  Otherwise this is an ace.
            next_char = card_str[1]
            if next_char == "0":

                # Special case; suit location is the third character.
                rank = 10
                suit_loc = 2
            else:
                rank = ACE
    elif rank_char == "a":
        rank = ACE
    elif rank_char == "k":
        rank = KING
    elif rank_char == "q":
        rank = QUEEN
    elif rank_char == "j":
        rank = JACK
    elif rank_char == "t":
        rank = 10
    else:
        # Not a rank.
        return None

    # Bail if rank is 0 (nice try!) or otherwise unset.
    if not rank:
        return

    # Now, pull the suit character out.
    suit_char = card_str[suit_loc].lower()

    if suit_char == "c":
        suit = CLUBS
    elif suit_char == "d":
        suit = DIAMONDS
    elif suit_char == "h":
        suit = HEARTS
    elif suit_char == "s":
        suit = SPADES
    else:
        # Not a suit.
        return None

    # If we got here, we have a suit and a rank.
    return PlayingCard(rank, suit)

def random_card():
    return PlayingCard(choice(RANKS), choice(SUITS))

def new_deck(ace_high = True):
    deck = Hand()
    for r in RANKS:
        for s in SUITS:
            deck.add(PlayingCard(r, s, ace_high))
    return deck

def card_to_str(card, mode = SHORT):

    # Returns a card in a reasonable text form for printing full hands,
    # etc. when in SHORT mode, or in nice pretty long form when in LONG
    # mode.  Will eventually support coloration.

    if mode == SHORT:

        if not card:
            return "  "
        short_suit = card.suit[0].upper()
        value = card.value()
        if value in range(2,10):
            short_rank = str(value)
        elif value == 10:
            short_rank = "t"
        elif value:
            short_rank = "%s" % card.rank[0].lower()
        else:
            short_rank = "?"
        return ("%s%s" % (short_rank, short_suit))
    elif mode == LONG:
        return (repr(card))

    return ""

def hand_to_str(hand, trump_suit = None, is_sorted = True):

    # Returns a reasonable string representation of a given hand.  Trumps
    # are bolded; if not trump, diamonds and hearts are red, and clubs and
    # spades are gray.  Note that this function expects the hand to be
    # sorted by default, and will put in dividers between suits; if it is
    # not, pass in False to is_sorted, and it won't bother trying to be
    # clever.

    last_suit = None
    to_return = ""
    for card in hand:
        if is_sorted and card.suit != last_suit:
            if last_suit:
               to_return += "/ "
            last_suit = card.suit
        if card.suit == trump_suit:
            color_code = "^W"
        elif card.suit == HEARTS or card.suit == DIAMONDS:
            color_code = "^R"
        else:
            color_code = "^w"
        to_return += "%s%s^~ " % (color_code, card_to_str(card))

    return to_return
