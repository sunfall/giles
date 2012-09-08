# Giles: trick.py
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

# This file holds a number of functions useful for card games, specifically
# trick-taking games such as Whist, Spades, Bridge, Bourre, Hokm, and Hearts.

from giles.games.hand import Hand

def handle_trick(hand, trump_suit = None, last_wins = False):

    # handle_trick() is a utility function for the vast majority of
    # trick-tacking games, whether or not they use the PlayingCard
    # class.  It takes a Hand of cards (actually anything that can
    # be dug at via len() and foo[0], foo[1], etc.) and a value
    # representing the trump suit.  It starts with the first card
    # in the hand--i.e., the led card--and then checks each further
    # card in sequence.  It then returns the winner, where the
    # winner is:
    #
    # - the highest trump led, if any trumps are led;
    # - otherwise the highest card of the suit led.
    #
    # (Yes, this means the elements need to be comparable and have,
    # at a minimum, a .suit.  Otherwise handle_trick doesn't care.)
    #
    # If no trump suit is specified, then there are no trumps.  There
    # is also an optional parameter, last_wins, which defaults to false;
    # if two cards have the same value and the same suit, the first card
    # of that value that shows up is considered the winner--unless, of
    # course, last_wins.  This isn't very helpful with the default
    # PlayingCard class, as duplicate cards are indistinguishable, but
    # could be useful for other types which /do/ distinguish between
    # identically-valued cards.

    # Bail immediately if there are no cards in the hand.
    if not len(hand):
        return None

    # The first card is the presumptive winner.
    winner = hand[0]
    led_suit = winner.suit

    # If a trump was led, that's all that can possibly win.
    trumps_played = False
    if led_suit == trump_suit:
        trumps_played = True

    for this_card in hand[1:]:

        # We always evaluate trumps.
        if this_card.suit == trump_suit:
            if not trumps_played:

                # First trump.  It's a winner no matter what.
                winner = this_card
                trumps_played = True

            else:

                # See if it's higher (or the same and last wins).
                if this_card > winner or (this_card == winner and last_wins):
                    winner = this_card

        # We only continue evaluation if trumps haven't been played.  If they
        # have, there's no way that this card can win, since it's not a trump.
        elif not trumps_played:

            # It must match the led suit to have a chance to win.
            if this_card.suit == led_suit:

                # See if it's higher (or the same and last wins).
                if this_card > winner or (this_card == winner and last_wins):
                    winner = this_card

    # Return the winning card.
    return winner

def hand_has_suit(hand, suit):

    # Returns true if the hand has at least one card in a given suit.
    cards_in_suit = [x for x in hand if x.suit == suit]
    if len(cards_in_suit):
        return True
    return False

def sorted_hand(hand, trump_suit = None):

    # Sorts a hand of cards.  Puts trumps first, if any, then sorts the
    # remaining suits arbitrarily.  Returns this newly-sorted hand.

    trump_cards = Hand()
    other_suits = {}
    for card in hand:
        this_suit = card.suit
        if card.suit == trump_suit:
            hand_to_add_to = trump_cards
        else:
            if this_suit not in other_suits:
                other_suits[this_suit] = Hand()
            hand_to_add_to = other_suits[this_suit]
        hand_to_add_to.add(card)

    # Now that they're sorted out, combine them back together.
    s_hand = Hand()
    trump_cards.sort()
    for card in trump_cards:
        s_hand.add(card)
    for suit in sorted(other_suits.keys()):
        suit_hand = other_suits[suit]
        suit_hand.sort()
        for card in suit_hand:
            s_hand.add(card)

    return s_hand
