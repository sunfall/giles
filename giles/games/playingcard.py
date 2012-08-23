from card import Card
class PlayingCard(Card):
    """PlayingCard is an implementation of a traditional 52-card deck of playing cards.

    Ranks and Suits are built-in, and jokers are supported but not issued by default.
    While Suits are a dictionary mapping each suit to an integer value, they are not checked
    when comparing cards to each other.  Aces are valued at one; Kings at thirteen.  As such,
    a Queen of Clubs (with a .value() of 12) is greater than a ten of Hearts, and the value()
    of two Queens will be equal, but the Queen of Hearts != the Queen of Spades.  This is not
    a bug; it allows for simple constructions such as "if mycard in myhand" without having to
    go through absurd gymnastics.

    Methods of note are:  __repr_(), value(), and all ordinal comparisons, e. g. __lt__().

    The static variable display_mode should be set to 'short' or long', and will change the
    behavior of __repr__() to suit.  Eventually, I hope to add 'colorshort' and 'colorlong'.

    PlayingCard.display_mode defaults to 'long'

    The static method new_deck() returns a Hand containing one of each card.

    The static method random_card() returns one random card.  Duplicates are not tracked.
    """

    ranks = ['Ace', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King']
    suits = {'Clubs': 1, 'Diamonds': 2, 'Hearts': 3, 'Spades': 4}

    display_mode = 'long'

    def __init__(self, r = None, s = None ):
        self.properties = {}
        self.properties['rank'] = r
        self.properties['suit'] = s

    def __repr__(self):
        if self.display_mode == 'short':
            short_suit = self.properties['suit'][0].upper()
            if self.value() in range(2,11):
                short_rank = str(self.value()).ljust(2)
            elif self.value():
                short_rank = "%s " % self.properties['rank'][0].lower()
            else:
                short_rank = "? "
            return ("%s%s" % (short_rank, short_suit) )
        else:
            if self.properties['rank'] == 'joker':
                return ("the %s Joker" % (self.properties['suit']))
            else:
                return ("the %s of %s" % (self.properties['rank'], self.properties['suit']))

    def __lt__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() < other.value()

    def __gt__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() > other.value()

    def __le__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() <= other.value()

    def __gt__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() >= other.value()

    def __eq__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            # okay, so here's an interestind edge case.  Cards of differing ranks of course can be
            # compared.  however, the Three of Clubs is not the same card as the Three of Diamonds.
            return self.value() == other.value() and self.properties['suit'] == other.properties['suit']

    def __ne__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() != other.value()

    def __net__(self, other):
        if not (self.value() or other.value()):
            return NotImplemented
        else:
            return self.value() < other.value()

    def value(self):
        R = self.properties['rank']
        if R.lower() == 'joker':
            return None
        if type(R) == int:
            return R
        if R.isdigit():
            return int(R)
        else:
            if R[0] in ('A', 'a'):
                return 1
            elif R[0] in ('J', 'j'):
                return 11
            elif R[0] in ('Q', 'q'):
                return 12
            elif R[0] in ('K', 'k'):
                return 13
            else:
                return None

    @staticmethod
    def random_card():
        from random import choice
        return PlayingCard(choice(PlayingCard.ranks), choice(PlayingCard.suits.keys()))

    @staticmethod
    def new_deck():
        from hand import Hand
        deck = Hand()
        for R in PlayingCard.ranks:
            for S in PlayingCard.suits:
                deck.draw(PlayingCard(R, S))
        return deck
