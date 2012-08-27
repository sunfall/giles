class Hand(object):
    """A Hand, as in a hand of cards

    Can be used for any collection of items accrued in a game, as it just stores a list of objects.  It
    was built originally as a vessel for the PlayingCard (and Card) class, but I realized pretty early on
    that it could be more versatile, and this proved to be true.

    Methods of note:  show(), discard(), discard_specific(), draw(), muck(), shuffle(), and sort().  The
    latter is not tested with items that are not able to be compared to each other.
    """
    from random import shuffle, choice

    def __init__(self):
        self.cards = []     # This should host a list of Cards; ordered 'bottom' to 'top'

    #   All comparison operators should be handled by specific type-of-card implementations.
    #   As such, for generic arbitrary cards, NotImplemented will do.

    def __len__(self):
        return len(self.cards)

    def __getitem__(self,key):
        return self.cards[key]

    def __setitem__(self,key,value):
        return self.cards.__setitem__(key,value)

    def __delitem__(self,key):
        return self.cards.__delitem__(key)

    def __iter__(self):
        return self.cards.__iter__()

    def __contains__(self,needle):
        if needle in self.cards:
            return True
        else:
            return False

    def discard(self, n = -1):
        """Discard from a hand.  By default, discards the top item (item [-1]), or None if empty. Discard is returned."""
        if self.cards and n in range( -1 * len(self.cards), len(self.cards) ):
            return self.cards.pop(n)
        else:
            return None

    def muck(self):
        """Discard all of the items in a hand.  Returns a Hand containing all of the mucked items, or an empty Hand if empty."""
        mucked_cards = Hand()
        while self.show():
            mucked_cards.draw( self.discard() )
        return mucked_cards


    def show(self, n = -1):
        """Returns the item specified from a hand. By default, the top item (item [-1], or None if empty.  Hand is unchanged."""
        if self.cards and n in range( -1 * len(self.cards), len(self.cards) ):
            return self.cards[n]
        else:
            return None

    def discard_specific(self, needle):
        """Used to discard a specific item by example, or None if not found in the Hand.  Discard is returned."""
        if needle in self.cards:
            self.cards.remove( needle )
            return needle
        else:
            return None

    def discard_random(self):
        """Discard a random item from the Hand, or None if empty."""
        from random import choice
        if len(self.cards) == 0:
            return None
        else:
            chosen_card = choice( self.cards )
            return self.discard_specific(chosen_card)

    def draw(self, c):
        """Add the provided item to the Hand, at the top.  Will refuse to add anything that evaluates to False (e. g. None, [])"""
        if c:
            self.cards.append(c)
            return True
        return False

    def shuffle(self):
        from random import shuffle
        shuffle(self.cards)
        return None

    def sort(self):
        self.cards.sort()

