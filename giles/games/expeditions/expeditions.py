# Giles: expeditions.py
# Copyright 2013 Phil Bordelon
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

from giles.games.seated_game import SeatedGame
from giles.games.hand import Hand
from giles.games.seat import Seat
from giles.state import State
from giles.utils import Struct, get_plural_str

from giles.games.expeditions.expeditions_card import ExpeditionsCard
from giles.games.expeditions.expeditions_card import card_to_str, get_color_code, hand_to_str, value_to_str, sorted_hand, str_to_card, str_to_suit
from giles.games.expeditions.expeditions_card import DEFAULT_SUITS, YELLOW, BLUE, WHITE, GREEN, RED, CYAN, MAGENTA
from giles.games.expeditions.expeditions_card import AGREEMENT, SHORT, LONG

# Some useful default values.
MIN_SUITS = 2
MAX_SUITS = 7

MIN_HAND_SIZE = 2
MAX_HAND_SIZE = 13

MIN_AGREEMENTS = 0
MAX_AGREEMENTS = 6

MIN_PENALTY = 0
MAX_PENALTY = 50

LEFT = "left"
RIGHT = "right"

NUMERICAL_RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10']

TAGS = ["abstract", "card", "random", "2p"]

class Expeditions(SeatedGame):
    """A Expeditions game table implementation.  Based on a game invented in
    1999 by Reiner Knizia.
    """

    def __init__(self, server, table_name):

        super(Expeditions, self).__init__(server, table_name)

        self.game_display_name = "Expeditions"
        self.game_name = "expeditions"
        self.seats = [
            Seat("Left"),
            Seat("Right")
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RExpeditions^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Expeditions-specific stuff.
        self.suit_count = 5
        self.agreement_count = 3
        self.penalty = 20
        self.bonus = True
        self.bonus_length = 8
        self.bonus_points = 20
        self.hand_size = 8
        self.goal = 1

        self.turn = None
        self.draw_pile = None
        self.discards = []
        self.left = self.seats[0]
        self.right = self.seats[1]
        self.left.data.side = LEFT
        self.left.data.curr_score = 0
        self.left.data.overall_score = 0
        self.left.data.hand = None
        self.left.data.expeditions = []
        self.right.data.side = RIGHT
        self.right.data.curr_score = 0
        self.right.data.overall_score = 0
        self.right.data.hand = None
        self.right.data.expeditions = []
        self.resigner = None
        self.first_player = None
        self.just_discarded_to = None

        self.printable_layout = None
        self.init_hand()

    def init_hand(self):

        # Depending on the number of suits requested for play, we build
        # structures.
        suit_list = DEFAULT_SUITS[:]
        if self.suit_count >= 6:
            suit_list.append(CYAN)
        if self.suit_count == 7:
            suit_list.append(MAGENTA)

        # If, on the other hand, the number of suits is /less/ than five,
        # we use a subset of the default suits.
        if self.suit_count < 5:
            suit_list = DEFAULT_SUITS[:self.suit_count]

        # All right, we have a list of suits involved in this game.  Let's
        # build the various piles that are based on those suits.
        self.left.data.expeditions = []
        self.right.data.expeditions = []
        self.discards = []
        for suit in suit_list:
            discard_pile = Struct()
            left_expedition = Struct()
            right_expedition = Struct()
            for pile in (discard_pile, left_expedition, right_expedition):
                pile.suit = suit
                pile.hand = Hand()
                pile.value = 0
            self.left.data.expeditions.append(left_expedition)
            self.right.data.expeditions.append(right_expedition)
            self.discards.append(discard_pile)

        # We'll do a separate loop for generating the deck to minimize
        # confusion.
        self.draw_pile = Hand()
        for suit in suit_list:
            for rank in NUMERICAL_RANKS:
                self.draw_pile.add(ExpeditionsCard(rank, suit))

            # Add as many agreements as requested.
            for agreement in range(self.agreement_count):
                self.draw_pile.add(ExpeditionsCard(AGREEMENT, suit))

        # Lastly, shuffle the draw deck and initialize hands.
        self.draw_pile.shuffle()
        self.left.data.hand = Hand()
        self.right.data.hand = Hand()

    def get_discard_str(self, pos):

        discard_pile = self.discards[pos]
        if len(discard_pile.hand):
            return(value_to_str(discard_pile.hand[-1].value()))
        return "."

    def get_expedition_str(self, expedition):

        to_return = ""
        for card in expedition:
            to_return += value_to_str(card.value())

        return to_return

    def get_sp_str(self, seat):

        if seat == self.left:
            return "^C%s^~" % self.left.player_name
        else:
            return "^M%s^~" % self.right.player_name

    def update_printable_layout(self):

        self.printable_layout = []
        self.printable_layout.append("                   .---.\n")

        # Loop through all table rows.
        for row in range(self.suit_count):
            left = self.left.data.expeditions[row]
            right = self.right.data.expeditions[row]
            suit_char = left.suit[0].upper()
            left_suit_char = suit_char
            right_suit_char = suit_char
            expedition_str = get_color_code(left.suit)
            expedition_str += self.get_expedition_str(left.hand.reversed()).rjust(18)
            if self.bonus and len(left.hand) >= self.bonus_length:
                left_suit_char = "*"
            if self.bonus and len(right.hand) >= self.bonus_length:
                right_suit_char = "*"
            expedition_str += " %s %s %s " % (left_suit_char, self.get_discard_str(row), right_suit_char)
            expedition_str += self.get_expedition_str(right.hand)
            expedition_str += "^~\n"
            self.printable_layout.append(expedition_str)
            self.printable_layout.append("                   |   |\n")

        # Replace the last unnecessary separator row with the end of the board.
        self.printable_layout[-1] = "                   `---'\n"

    def get_metadata_str(self):

        to_return = "^Y%s^~ remain in the draw pile.\n" % get_plural_str(len(self.draw_pile), "card")
        if not self.turn:
            to_return += "The game has not started yet.\n"
        else:
            to_return += "It is %s's turn to " % self.get_sp_str(self.turn)
            sub = self.state.get_sub()
            if sub == "play":
                to_return += "^cplay a card^~.\n"
            else:
                to_return += "^cdraw a card^~.\n"
        to_return += "The goal score for this game is ^Y%s^~.\n" % get_plural_str(self.goal, "point")
        to_return += "Overall:      %s: %s     %s: %s\n" % (self.get_sp_str(self.left), self.left.data.overall_score, self.get_sp_str(self.right), self.right.data.overall_score)

        return to_return

    def show(self, player, show_metadata=True):

        if not self.printable_layout:
            self.update_printable_layout()
        player.tell_cc("%s         %s\n" % (self.get_sp_str(self.left).rjust(21), self.get_sp_str(self.right)))
        for line in self.printable_layout:
            player.tell_cc(line)
        if show_metadata:
            player.tell_cc("\n" + self.get_metadata_str())

    def show_hand(self, player):

        seat = self.get_seat_of_player(player)

        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return

        print_str = "Your current hand:\n   "
        print_str += hand_to_str(seat.data.hand)
        print_str += "\n"
        self.tell_pre(player, print_str)

    def send_layout(self, show_metadata=True):

        for player in self.channel.listeners:
            self.show(player, show_metadata)
        for seat in self.seats:
            if seat.player:
                self.show_hand(seat.player)

    def deal(self):

        # Deal cards until each player has hand_size cards.
        self.bc_pre("A fresh hand is dealt to both players.\n")
        for i in range(self.hand_size):
            self.left.data.hand.add(self.draw_pile.discard())
            self.right.data.hand.add(self.draw_pile.discard())

        # Sort hands.
        self.left.data.hand = sorted_hand(self.left.data.hand)
        self.right.data.hand = sorted_hand(self.right.data.hand)

        # Clear scores.
        self.left.data.curr_score = 0
        self.right.data.curr_score = 0

    def tick(self):

        # If both seats are full and the game is active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player
           and self.seats[1].player and self.active):
            self.state.set("playing")
            self.state.set_sub("play")
            self.bc_pre("^CLeft^~: ^Y%s^~; ^MRight^~: ^Y%s^~\n" %
               (self.left.player_name, self.right.player_name))
            self.turn = self.left
            self.first_player = self.left
            self.deal()
            self.send_layout()

    def calculate_deck_size(self, suits, agrees):

        # Eventually this will depend on just what cards are in the deck,
        # but for now there are 9 point cards per suit plus the agreements.
        return (9 + agrees) * suits

    def set_suits(self, player, suit_str):

        if not suit_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_suit_count = int(suit_str)
        if new_suit_count < MIN_SUITS or new_suit_count > MAX_SUITS:
            self.tell_pre(player, "The number of suits must be between %d and %d inclusive.\n" % (MIN_SUITS, MAX_SUITS))
            return False

        # Does this give too few cards for the hand size?
        if self.calculate_deck_size(new_suit_count, self.agreement_count) <= self.hand_size * 2:
            self.tell_pre(player, "That number of suits is too small for the hand size.\n")
            return False

        # Valid.
        self.suit_count = new_suit_count
        self.bc_pre("^M%s^~ has changed the suit count to ^G%s^~.\n" % (player, new_suit_count))
        self.init_hand()
        self.update_printable_layout()

    def set_agreements(self, player, agree_str):

        if not agree_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_agree_count = int(agree_str)
        if new_agree_count < MIN_AGREEMENTS or new_agree_count > MAX_AGREEMENTS:
            self.tell_pre(player, "The number of agreements must be between %d and %d inclusive.\n" % (MIN_AGREEMENTS, MAX_AGREEMENTS))
            return False

        # Does this give too few cards for the hand size?
        if self.calculate_deck_size(self.suit_count, new_agree_count) <= self.hand_size * 2:
            self.tell_pre(player, "That number of agreements is too small for the hand size.\n")
            return False

        # Valid.
        self.agreement_count = new_agree_count
        self.bc_pre("^M%s^~ has changed the agreement count to ^G%s^~.\n" % (player, new_agree_count))
        self.init_hand()
        self.update_printable_layout()

    def set_hand(self, player, hand_str):

        if not hand_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_hand_size = int(hand_str)
        if new_hand_size < MIN_HAND_SIZE or new_hand_size > MAX_HAND_SIZE:
            self.tell_pre(player, "The hand size must be between %d and %d inclusive.\n" % (MIN_HAND_SIZE, MAX_HAND_SIZE))
            return False

        # If the drawn hands are greater than or equal to the actual card
        # count, that doesn't work either.
        if (new_hand_size * 2) >= len(self.draw_pile):
            self.tell_pre(player, "The hand size is too large for the number of cards in play.\n")
            return False

        # Valid.
        self.hand_size = new_hand_size
        self.bc_pre("^M%s^~ has changed the hand size to ^G%s^~.\n" % (player, new_hand_size))

    def set_penalty(self, player, penalty_str):

        if not penalty_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_penalty = int(penalty_str)
        if new_penalty < MIN_PENALTY or new_penalty > MAX_PENALTY:
            self.tell_pre(player, "The penalty must be between %d and %d inclusive.\n" % (MIN_PENALTY, MAX_PENALTY))
            return False

        # Valid.
        self.penalty = new_penalty
        self.bc_pre("^M%s^~ has changed the penalty to ^G%s^~.\n" % (player, new_penalty))

    def set_bonus(self, player, bonus_bits):

        if len(bonus_bits) == 1:

            bonus = bonus_bits[0]
            # Gotta be 'none' or 0.
            if bonus in ("none", "n", "0",):
                self.bonus = False
                self.bc_pre("^M%s^~ has disabled the expedition bonuses.\n" % player)
                return True
            else:
                self.tell_pre(player, "Invalid bonus command.\n")
                return False

        elif len(bonus_bits) == 2:

            points, length = bonus_bits

            if not points.isdigit() or not length.isdigit():
                self.tell_pre(player, "Invalid bonus command.\n")
                return False

            points = int(points)
            length = int(length)

            if not points or not length:
                self.bonus = False
                self.bc_pre("^M%s^~ has disabled the expedition bonuses.\n" % player)
                return True
            else:
                self.bonus = True
                self.bonus_points = points
                self.bonus_length = length
                self.bc_pre("^M%s^~ has set the expedition bonuses to ^C%s^~ at length ^R%s^~.\n" % (player, get_plural_str(points, "point"), length))
                return True

        else:
            self.tell_pre(player, "Invalid bonus command.\n")
            return False

    def set_goal(self, player, goal_str):

        if not goal_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_goal = int(goal_str)
        if new_goal < 1:
            self.tell_pre(player, "The goal must be at least one point.\n")
            return False

        # Got a valid goal.
        self.goal = new_goal
        self.bc_pre("^M%s^~ has changed the goal to ^G%s^~.\n" % (player, get_plural_str(new_goal, "point")))

    def suit_to_loc(self, suit):

        if suit in DEFAULT_SUITS:
            return DEFAULT_SUITS.index(suit)
        elif suit == CYAN:
            return 5
        elif suit == MAGENTA:
            return 6

        return None

    def evaluate(self, player):

        for seat in self.seats:
            score_str = "%s: " % seat.player_name
            score_str += " + ".join(["%s%s^~" % (get_color_code(x.suit), x.value) for x in seat.data.expeditions])
            score_str += " = %s\n" % (get_plural_str(seat.data.curr_score, "point"))
            self.tell_pre(player, score_str)

    def play(self, player, play_str):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        elif seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
            return False

        substate = self.state.get_sub()
        if substate != "play":
            self.tell_pre(player, "You should be drawing or retrieving, not playing!\n")
            return False

        # Translate the play string into an actual card.
        potential_card = str_to_card(play_str)

        if not potential_card:
            self.tell_pre(player, "That's not a valid card!\n")
            return False

        # Do they even have this card?
        if potential_card not in seat.data.hand:
            self.tell_pre(player, "You don't have that card!\n")
            return False

        # All right.  Grab the hand for that expedition.
        exp_hand = seat.data.expeditions[self.suit_to_loc(potential_card.suit)].hand

        # If this card is a lower value than the top card of the hand, nope.
        if len(exp_hand) and potential_card < exp_hand[-1]:
            self.tell_pre(player, "You can no longer play this card on this expedition.\n")
            return False

        # If it's the same value and not an agreement, nope.
        elif (len(exp_hand) and potential_card == exp_hand[-1] and
           potential_card.rank != AGREEMENT):
            self.tell_pre(player, "You cannot play same-valued point cards on an expedition.\n")
            return False

        # Passed the tests.  Play it and clear the discard tracker.
        exp_hand.add(seat.data.hand.discard_specific(potential_card))
        self.just_discarded_to = None

        self.bc_pre("%s played %s.\n" % (self.get_sp_str(seat),
                       card_to_str(potential_card, mode=LONG)))
        return True

    def discard(self, player, play_str):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        elif seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
            return False

        substate = self.state.get_sub()
        if substate != "play":
            self.tell_pre(player, "You should be drawing or retrieving, not discarding!\n")
            return False

        # Translate the play string into an actual card.
        potential_card = str_to_card(play_str)

        if not potential_card:
            self.tell_pre(player, "That's not a valid card!\n")
            return False

        # Do they even have this card?
        if potential_card not in seat.data.hand:
            self.tell_pre(player, "You don't have that card!\n")
            return False

        # All right, they can discard it.  Get the appropriate discard pile...
        discard_pile = self.discards[self.suit_to_loc(potential_card.suit)].hand

        discard_pile.add(seat.data.hand.discard_specific(potential_card))

        # Note the pile we just discarded to, so the player can't just pick it
        # back up as their next play.
        self.just_discarded_to = potential_card.suit

        self.bc_pre("%s discarded %s.\n" % (self.get_sp_str(seat),
                          card_to_str(potential_card, mode=LONG)))
        return True

    def draw(self, player):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        elif seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
            return False

        substate = self.state.get_sub()
        if substate != "draw":
            self.tell_pre(player, "You should be playing or discarding, not drawing!\n")
            return False

        # Draw a card.  This one's easy!
        draw_card = self.draw_pile.discard()
        seat.data.hand.add(draw_card)

        # Resort the hand.
        seat.data.hand = sorted_hand(seat.data.hand)

        self.bc_pre("%s drew a card.\n" % (self.get_sp_str(seat)))
        self.tell_pre(player, "You drew %s.\n" % card_to_str(draw_card, mode=LONG))
        return True

    def retrieve(self, player, retrieve_str):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        elif seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
            return False

        substate = self.state.get_sub()
        if substate != "draw":
            self.tell_pre(player, "You should be playing or discarding, not retrieving!\n")
            return False

        # Turn the retrieve string into an actual suit.
        suit = str_to_suit(retrieve_str)
        if not suit:
            self.tell_pre(player, "That's not a valid suit!\n")
            return False

        # Is that a valid location in this game?
        loc = self.suit_to_loc(suit)
        if loc >= self.suit_count:
            self.tell_pre(player, "That suit isn't in play this game.\n")
            return False

        # Is there actually a card there /to/ draw?
        discard_pile = self.discards[loc].hand
        if not len(discard_pile):
            self.tell_pre(player, "There are no discards of that suit.\n")
            return False

        # Is it the card they just discarded?
        if suit == self.just_discarded_to:
            self.tell_pre(player, "You just discarded that card!\n")
            return False

        # Phew.  All tests passed.  Give them the card.
        dis_card = discard_pile.discard()
        seat.data.hand.add(dis_card)
        seat.data.hand = sorted_hand(seat.data.hand)

        self.bc_pre("%s retrieved %s from the discards.\n" % (self.get_sp_str(seat),
                                                  card_to_str(dis_card, mode=LONG)))
        return True

    def resign(self, player):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You can't resign; you're not playing!\n")
            return False

        if self.turn != seat:
            self.tell_pre(player, "You must wait for your turn to resign.\n")
            return False

        self.resigner = seat
        self.bc_pre("%s is resigning from the game.\n" % self.get_sp_str(seat))
        return True

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.lower().split()
            primary = command_bits[0]

            if state == "setup":

                if primary in ("suits",):

                    if len(command_bits) == 2:
                        self.set_suits(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid suits command.\n")
                    handled = True

                elif primary in ("agreements", "agree",):

                    if len(command_bits) == 2:
                        self.set_agreements(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid agree command.\n")
                    handled = True

                elif primary in ("hand",):

                    if len(command_bits) == 2:
                        self.set_hand(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid hand command.\n")
                    handled = True

                elif primary in ("penalty",):

                    if len(command_bits) == 2:
                        self.set_penalty(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid penalty command.\n")
                    handled = True

                elif primary in ("bonus",):

                    if len(command_bits) >= 2:
                        self.set_bonus(player, command_bits[1:])
                    else:
                        self.tell_pre(player, "Invalid bonus command.\n")
                    handled = True

                elif primary in ("goal", "score",):

                    if len(command_bits) == 2:
                        self.set_goal(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid goal command.\n")
                    handled = True

                elif primary in ("done", "ready", "d", "r",):

                    self.bc_pre("The game is now looking for players.\n")
                    self.state.set("need_players")
                    handled = True

            elif state == "need_players":

                if primary in ("config", "setup", "conf",):

                    self.state.set("setup")
                    self.bc_pre("^R%s^~ has switched the game to setup mode.\n" % player)
                    handled = True

            elif state == "playing":

                made_move = False

                if primary in ("hand", "inventory", "inv", "i",):
                    self.show_hand(player)
                    handled = True

                elif primary in ("evaluate", "eval", "score", "e", "s",):
                    self.evaluate(player)
                    handled = True

                elif primary in ("move", "play", "mv", "pl",):

                    if len(command_bits) == 2:
                        made_move = self.play(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid play command.\n")
                    handled = True

                elif primary in ("discard", "toss", "di", "to",):
                    if len(command_bits) == 2:
                        made_move = self.discard(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid discard command.\n")
                    handled = True

                elif primary in ("draw", "dr",):
                    made_move = self.draw(player)
                    handled = True

                elif primary in ("retrieve", "re",):
                    if len(command_bits) == 2:
                        made_move = self.retrieve(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid retrieve command.\n")
                    handled = True

                elif primary in ("resign",):

                    if self.resign(player):
                        made_move = True
                    handled = True

                if made_move:

                    substate = self.state.get_sub()

                    # Okay, something happened on the layout.  Update scores
                    # and the layout.
                    self.update_scores()
                    self.update_printable_layout()

                    # Is the game over?
                    if not len(self.draw_pile) or self.resigner:

                        # Yup.  Resolve the game.
                        self.resolve_hand()

                        # Is there an overall winner?
                        winner = self.find_winner()

                        if winner:
                            self.resolve(winner)
                            self.finish()

                        else:

                            # Hand over, but not the game itself.  New deal.
                            self.bc_pre("The cards are collected for another hand.\n")
                            self.init_hand()

                            # Switch dealers.
                            self.first_player = self.next_seat(self.first_player)
                            self.turn = self.first_player
                            self.state.set("playing")
                            self.state.set_sub("play")
                            self.deal()
                            self.update_printable_layout()
                            self.send_layout()

                    else:

                        # If we're in the play substate, switch to the draw.
                        if substate == "play":
                            self.state.set_sub("draw")

                        else:

                            # After draw, switch turns and resend the board.
                            self.state.set_sub("play")
                            self.turn = self.next_seat(self.turn)
                            self.send_layout(show_metadata=False)

        if not handled:
            self.tell_pre(player, "Invalid command.\n")

    def update_scores(self):

        for seat in self.left, self.right:

            # Start at 0.
            total = 0

            # For each expedition, if they're even on it...
            for exp in seat.data.expeditions:

                curr = 0
                multiplier = 1

                if len(exp.hand):

                    # Immediately assign the penalty.
                    curr -= self.penalty

                    # Now loop through the cards.
                    for card in exp.hand:

                        value = card.value()
                        if value == 1:

                            # Agreement; adjust multiplier.
                            multiplier += 1

                        else:

                            # Scoring card; increase current score.
                            curr += value

                    # Adjust the current score by the multiplier.
                    curr *= multiplier

                    # If bonuses are active, and this meets it, add it.
                    if self.bonus and len(exp.hand) >= self.bonus_length:
                        curr += self.bonus_points

                # No matter what, add curr to total and set it on the
                # pile.
                total += curr
                exp.value = curr

            # Set the current score for the seat.
            seat.data.curr_score = total

    def resolve_hand(self):

        for seat in self.left, self.right:

            addend = seat.data.curr_score
            if addend > 0:
                adj_str = "^Ygains ^C%s^~" % get_plural_str(addend, "point")
            elif addend < 0:
                adj_str = "^yloses ^c%s^~" % get_plural_str(-addend, "point")
            else:
                adj_str = "^Wsomehow manages to score precisely zero points^~"

            # Actually adjust the scores by the proper amounts, and inform
            # everyone of the result.
            seat.data.overall_score += addend

            # If someone resigned, scores don't matter, so don't show them.
            if not self.resigner:
                self.bc_pre("%s %s, giving them ^G%s^~.\n" % (self.get_sp_str(seat), adj_str, seat.data.overall_score))

    def find_winner(self):

        # If someone resigned, this is the easiest thing ever.
        if self.resigner == self.left:
            return self.right
        elif self.resigner == self.right:
            return self.left

        # If one player has a higher score than the other and that score
        # is higher than the goal, they win.
        if (self.left.data.overall_score > self.right.data.overall_score and
           self.left.data.overall_score >= self.goal):
            return self.left
        elif (self.right.data.overall_score > self.left.data.overall_score and
           self.right.data.overall_score >= self.goal):
            return self.right

        # Either we haven't reached the goal or there's a tie.  We'll print a
        # special message if there's a tie, because that's kinda crazy.
        if self.left.data.overall_score == self.right.data.overall_score:
            self.bc_pre("The players are tied!\n")

        # No matter what, there's no winner.
        return None

    def resolve(self, winner):
        self.bc_pre("%s wins!\n" % self.get_sp_str(winner))

    def show_help(self, player):

        super(Expeditions, self).show_help(player)
        player.tell_cc("\nEXPEDITIONS SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("                  ^!suits^. <num>     Play with <num> suits.\n")
        player.tell_cc("                  ^!agree^. <num>     Suits have <num> agreements.\n")
        player.tell_cc("                   ^!hand^. <num>     Hands have <num> cards.\n")
        player.tell_cc("                ^!penalty^. <num>     Expeditions start down <num> points.\n")
        player.tell_cc("     ^!bonus^. <pts> <len> | none     Bonus is <pts> at length <len>/none.\n")
        player.tell_cc("            ^!goal^. <num>, ^!score^.     Play until <num> points.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nEXPEDITIONS PLAY:\n\n")
        player.tell_cc("              ^!play^. <card>, ^!pl^.     Play <card> from your hand.\n")
        player.tell_cc("         ^!discard^. <card>, ^!toss^.     Discard <card> from your hand.\n")
        player.tell_cc("                     ^!draw^., ^!dr^.     Draw from the draw pile.\n")
        player.tell_cc("          ^!retrieve^. <suit>, ^!re^.     Retrieve top discard of <suit>.\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")
        player.tell_cc("                 ^!hand^., ^!inv^., ^!i^.     Look at the cards in your hand.\n")
        player.tell_cc("               ^!evaluate^., ^!eval^.     Evaluate the current scores.\n")
