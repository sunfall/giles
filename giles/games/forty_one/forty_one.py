# Giles: forty_one.py
# Copyright 2015 Phil Bordelon
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

from giles.games.four_player_card_game_layout import FourPlayerCardGameLayout, NORTH, SOUTH, EAST, WEST
from giles.games.seated_game import SeatedGame
from giles.games.hand import Hand
from giles.games.playing_card import new_deck, str_to_card, card_to_str, hand_to_str, LONG, HEARTS
from giles.games.seat import Seat
from giles.games.trick import handle_trick, hand_has_suit, sorted_hand
from giles.state import State
from giles.utils import booleanize, get_plural_str

import random

TAGS = ["card", "partnership", "random", "trick", "trump", "4p"]

class FortyOne(SeatedGame):
    """An implementation of Forty-One, a quirky combination of solo and
    partnership trick-taking that is apparently popular in Syria.  The only
    real differences from the rules I've seen online are that this version
    supports a 'whist' mode rather than always having Hearts as trump and it
    forces play to continue if winning scores are tied.
    """

    def __init__(self, server, table_name):

        super(FortyOne, self).__init__(server, table_name)

        self.game_display_name = "Forty-One"
        self.game_name = "fortyone"

        # Seat ordering is "Persian."
        self.seats = [
            Seat("North"),
            Seat("West"),
            Seat("South"),
            Seat("East"),
        ]

        self.min_players = 4
        self.max_players = 4
        self.state = State("need_players")
        self.prefix = "(^RForty-One^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # 41-specific stuff.
        self.goal = 41
        self.double = 7
        self.minimum = 11
        self.whist = False
        self.positive = True
        self.trick = None
        self.trump_suit = None
        self.led_suit = None
        self.turn = None
        self.dealer = None
        self.winner = None

        self.north = self.seats[0]
        self.west = self.seats[1]
        self.south = self.seats[2]
        self.east = self.seats[3]

        self.north.data.who = NORTH
        self.west.data.who = WEST
        self.south.data.who = SOUTH
        self.east.data.who = EAST

        self.north.data.partner = self.south
        self.west.data.partner = self.east
        self.south.data.partner = self.north
        self.east.data.partner = self.west

        self.layout = FourPlayerCardGameLayout()

        # Set everyone's score to zero.
        for seat in self.seats:
            seat.data.score = 0

    def show_help(self, player):

        super(FortyOne, self).show_help(player)
        player.tell_cc("\nFORTY-ONE SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("            ^!goal^. <num>, ^!score^.     Set the goal score to <num>.\n")
        player.tell_cc("           ^!double^. <num>, ^!doub^.     Set the lowest doubling to <num>.\n")
        player.tell_cc("           ^!minimum^. <num>, ^!min^.     Set the minimum deal bid to <num>.\n")
        player.tell_cc("         ^!positive^. on|off, ^!pos^.     Require positive partners for wins.\n")
        player.tell_cc("             ^!whist^. on|off, ^!wh^.     Enable whist mode for trumps.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nFORTY-ONE PLAY:\n\n")
        player.tell_cc("            ^!choose^. <suit>, ^!ch^.     Declare <suit> as trumps.  Hakem only.\n")
        player.tell_cc("                 ^!bid^. <num>, ^!b^.     Bid to win <num> tricks.\n")
        player.tell_cc("              ^!play^. <card>, ^!pl^.     Play <card> from your hand.\n")
        player.tell_cc("                 ^!hand^., ^!inv^., ^!i^.     Look at the cards in your hand.\n")

    def display(self, player):

        player.tell_cc("%s" % self.layout)

    def get_color_code(self, seat):
        if seat == self.north or seat == self.south:
            return "^R"
        else:
            return "^M"

    def get_sp_str(self, seat):

        return "^G%s^~ (%s%s^~)" % (seat.player_name, self.get_color_code(seat), seat)

    def get_player_num_str(self, seat, num):

        return "%s%s^~: %d" % (self.get_color_code(seat), seat.player_name, num)

    def get_score_str(self):
        return_str = "       "
        for seat in self.seats:
            return_str += "   %s" % self.get_player_num_str(seat, seat.data.score)
        return_str += "\n"

        return return_str

    def get_trick_str(self):
        return_str = "^CTricks^~:"
        for seat in self.seats:
            return_str += "   %s" % self.get_player_num_str(seat, seat.data.tricks)
        return_str += "\n"

        return return_str

    def get_bid_str(self):
        return_str = "  ^GBids^~:"
        for seat in self.seats:
            return_str += "   %s" % self.get_player_num_str(seat, seat.data.bid)
        return_str += "\n"

        return return_str

    def get_metadata(self):

        to_return = "\n\n"
        if self.turn:
            seat_color = self.get_color_code(self.turn)

            to_return += "It is ^Y%s^~'s turn (%s%s^~)." % (self.turn.player_name, seat_color, self.turn)
            if self.whist:
                to_return += "  Trumps are ^C%s^~." % self.trump_suit
            to_return += "\n" + self.get_trick_str()
            to_return += self.get_bid_str()
        to_return += "\nThe goal score for this game is ^C%s^~.\n" % get_plural_str(self.goal, "point")
        to_return += self.get_score_str()
        if self.positive:
            partner_str = "^Ymust have"
        else:
            partner_str = "^ydo not need to have"
        to_return += "(Both partners %s^~ a positive score to win.)\n" % partner_str
        if self.double != 7:
            if self.double:
                to_return += "Bids double value at ^C%s^~.\n" % get_plural_str(self.double, "trick")
            else:
                to_return += "Bids ^Rnever^~ double their value.\n"
        if self.minimum != 11:
            to_return += "The minimum bid for a deal is ^G%s^~.\n" % get_plural_str(self.minimum, "point")

        return to_return

    def show(self, player):
        self.display(player)
        player.tell_cc(self.get_metadata())

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

    def set_double(self, player, double_str):

        if not double_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_double = int(double_str)

        if new_double > 13:
            self.tell_pre(player, "The doubling value must be at most 13 tricks.\n")
            return False

        # Got a valid double value.
        self.double = new_double
        if self.double:
            self.bc_pre("^M%s^~ has changed the doubling value to ^G%s^~.\n" % (player, get_plural_str(new_double, "trick")))
        else:
            self.bc_pre("^M%s^~ has ^Rdisabled^~ doubling values.\n" % (player,))

    def set_minimum(self, player, minimum_str):

        if not minimum_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_minimum = int(minimum_str)

        # It doesn't make sense for the minimum to be below 4, as that's the
        # lowest possible bid anyhow.  13 is a plausible maximum.
        if new_minimum < 4:
            self.tell_pre(player, "The minimum must be at least 4 points.\n")
            return False

        if new_minimum > 13:
            self.tell_pre(player, "The minimum must be at most 13 points.\n")
            return False

        # Got a valid minimum.
        self.minimum = new_minimum
        self.bc_pre("^M%s^~ has changed the minimum to ^G%s^~.\n" % (player, get_plural_str(new_minimum, "point")))

    def set_positive(self, player, positive_bits):

        positive_bool = booleanize(positive_bits)
        if positive_bool:
            if positive_bool > 0:
                self.positive = True
                display_str = "^Crequires^~"
            elif positive_bool < 0:
                self.positive = False
                display_str = "^cdoes not require^~"
            self.bc_pre("^R%s^~ sets it so that winning %s positive scores.\n" % (player, display_str))
        else:
            self.tell_pre(player, "Not a valid boolean!\n")

    def set_whist(self, player, whist_bits):

        whist_bool = booleanize(whist_bits)
        if whist_bool:
            if whist_bool > 0:
                self.whist = True
                display_str = "^Con^~"
            elif whist_bool < 0:
                self.whist = False
                display_str = "^coff^~"
            self.bc_pre("^R%s^~ has turned whist-style trumps %s.\n" % (player, display_str))
        else:
            self.tell_pre(player, "Not a valid boolean!\n")

    def clear_trick(self):

        # Set the current trick to an empty hand...
        self.trick = Hand()
        self.led_suit = None

        # ...and set everyone's played card to None.
        for seat in self.seats:
            seat.data.card = None

        # Clear the layout as well.
        self.layout.clear()

    def new_deal(self):

        # Set tricks and bids to zero.
        for seat in self.seats:
            seat.data.tricks = 0
            seat.data.bid = 0

        dealer_name = self.dealer.player_name

        self.bc_pre("^R%s^~ (%s%s^~) gives the cards a good shuffle...\n" % (dealer_name, self.get_color_code(self.dealer), self.dealer))
        deck = new_deck()
        deck.shuffle()

        # Deal out all of the cards.
        self.bc_pre("^R%s^~ deals the cards out to all of the players.\n" % dealer_name)
        for seat in self.seats:
            seat.data.hand = Hand()
        for _ in range(13):
            for seat in self.seats:
                seat.data.hand.add(deck.discard())

        # If we're in whist mode, flip the dealer's last card to determine
        # trumps.
        if self.whist:
            last_card = self.dealer.data.hand[-1]
            self.bc_pre("^R%s^~ flips their last card; it is ^C%s^~.\n" % (dealer_name, card_to_str(last_card, LONG)))
            self.trump_suit = last_card.suit
        else:

            # Hearts forever.
            self.trump_suit = HEARTS

        # Sort everyone's hands and show them to everyone.
        for seat in self.seats:
            seat.data.hand = sorted_hand(seat.data.hand, self.trump_suit)
        self.show_hands()

    def show_hand(self, player):

        seat = self.get_seat_of_player(player)

        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return

        print_str = "Your current hand:\n   "
        print_str += hand_to_str(seat.data.hand, self.trump_suit)
        print_str += "\n"
        self.tell_pre(player, print_str)

    def show_hands(self):

        for seat in self.seats:
            if seat.player:
                self.show_hand(seat.player)

    def bid(self, player, bid_str):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        elif seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
            return False

        if not bid_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        bid = int(bid_str)

        if bid < 1:
            self.tell_pre(player, "You must bid at least one point.\n")
            return False

        if bid > 13:
            self.tell_pre(player, "You can't bid more tricks than there are!\n")
            return False

        # Got a valid bid.
        seat.data.bid = bid
        self.bc_pre("%s has bid ^G%s^~.\n" % (self.get_sp_str(seat), get_plural_str(bid, "trick")))
        return True

    def play(self, player, play_str):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        elif seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
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

        # Okay, it's a card in their hand.  First, let's do the "follow the
        # led suit" business.
        action_str = "^Wplays^~"
        if self.led_suit:

            this_suit = potential_card.suit
            if this_suit != self.led_suit and hand_has_suit(seat.data.hand, self.led_suit):

                # You can't play off-suit if you can match the led suit.
                self.tell_pre(player, "You can't throw off; you have the led suit.\n")
                return False

        else:

            # No led suit; they're the leader.
            action_str = "^Yleads^~ with"
            self.led_suit = potential_card.suit

        # They either matched the led suit, didn't have any of it, or they
        # are themselves the leader.  Nevertheless, their play is valid.
        seat.data.card = potential_card
        self.trick.add(seat.data.hand.discard_specific(potential_card))
        trump_str = ""
        if potential_card.suit == self.trump_suit:
            trump_str = ", a ^Rtrump^~"
        self.bc_pre("%s %s ^C%s^~%s.\n" % (self.get_sp_str(seat), action_str, card_to_str(potential_card, LONG), trump_str))
        self.layout.place(seat.data.who, potential_card)
        return potential_card

    def tick(self):

        # If all seats are full and active, autostart.
        active_seats = [x for x in self.seats if x.player]
        if self.state.get() == "need_players" and len(active_seats) == 4 and self.active:
            self.state.set("bidding")
            self.bc_pre("The game has begun.\n")

            # Initialize everything by clearing the (non-existent) trick.
            self.clear_trick()

            # Pick a starting dealer at random.
            self.dealer = random.choice(self.seats)
            self.bc_pre("Fate has spoken, and the starting dealer is %s!\n" % self.get_sp_str(self.dealer))
            self.new_deal()

            # Eldest opens bidding, per usual.
            self.turn = self.next_seat(self.dealer)
            self.layout.change_turn(self.turn.data.who)
            if self.turn.player:
                self.tell_pre(self.turn.player, "It is your turn to bid.\n")

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()

            command_bits = command_str.split()
            primary = command_bits[0].lower()

            if state == "setup":

                if primary in ("goal", "score", "sc", "g",):
                    if len(command_bits) == 2:
                        self.set_goal(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid goal command.\n")
                    handled = True

                elif primary in ("positive", "pos", "po", "p",):
                    if len(command_bits) == 2:
                        self.set_positive(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid positive command.\n")
                    handled = True

                elif primary in ("double", "doub",):
                    if len(command_bits) == 2:
                        self.set_double(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid double command.\n")
                    handled = True

                elif primary in ("minimum", "min",):
                    if len(command_bits) == 2:
                        self.set_minimum(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid minimum command.\n")
                    handled = True

                elif primary in ("whist", "wh",):
                    if len(command_bits) == 2:
                        self.set_whist(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid whist command.\n")
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

            elif state == "bidding":

                if primary in ("hand", "inventory", "inv", "i",):
                    self.show_hand(player)
                    handled = True

                elif primary in ("bid", "b",):
                    if len(command_bits) == 2:
                        bid_made = self.bid(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid bid command.\n")
                    handled = True

                if bid_made:

                    bid_list = [x for x in self.seats if x.data.bid]
                    if len(bid_list) == 4:

                        # Bidding is complete.  Are enough tricks bid?
                        bid_total = 0
                        point_total = 0
                        for seat in self.seats:
                            bid = seat.data.bid
                            bid_total += bid
                            point_total += bid

                            # Bids of self.double or more count double, if set.
                            if self.double:
                                if bid >= self.double:
                                    point_total += bid

                        bid_str = get_plural_str(bid_total, "trick")
                        point_str = get_plural_str(point_total, "point")
                        if point_total >= self.minimum:

                            # Enough indeed.  Start the game proper.
                            self.bc_pre("With ^W%s^~ bid for a total of ^C%s^~, play begins!\n" % (bid_str, point_str))
                            self.state.set("playing")
                            self.turn = self.next_seat(self.turn)
                            if self.turn.player:
                                self.show_hand(self.turn.player)

                        else:

                            # Not enough.  Throw hands in and deal fresh.
                            self.bc_pre("With only ^R%s^~ bid, everyone throws in their hand.\n" % bid_str)
                            self.dealer = self.next_seat(self.dealer)

                            # Deal and set up the first player to bid.
                            self.new_deal()
                            self.turn = self.next_seat(self.dealer)
                            if self.turn.player:
                                self.tell_pre(self.turn.player, "It is your turn to bid.\n")

                    else:

                        # Still need more bids.
                        self.turn = self.next_seat(self.turn)
                        if self.turn.player:
                            self.tell_pre(self.turn.player, "It is your turn to bid.\n")
                            self.show_hand(self.turn.player)

                    # No matter what happened, update the layout.
                    self.layout.change_turn(self.turn.data.who)

            elif state == "playing":

                card_played = False
                if primary in ("hand", "inventory", "inv", "i",):
                    self.show_hand(player)
                    handled = True

                elif primary in ("play", "move", "pl", "mv",):
                    if len(command_bits) == 2:
                        card_played = self.play(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid play command.\n")
                    handled = True

                if card_played:

                    # A card hit the table.  We need to do stuff.
                    if len(self.trick) == 4:

                        # Finish the trick up.
                        self.finish_trick()

                        # Is that the last trick?
                        if self.north.data.tricks + self.west.data.tricks + self.south.data.tricks + self.east.data.tricks == 13:

                            # Resolve the hand...
                            self.resolve_hand()

                            # And look for a winner.
                            winner = self.find_winner()
                            if winner:

                                # Found a winner.  Finish.
                                self.resolve(winner)
                                self.finish()

                            else:

                                # No winner.  Pass the deal to the next player...
                                self.dealer = self.next_seat(self.dealer)

                                # Deal and set up the first player to bid.
                                self.new_deal()
                                self.turn = self.next_seat(self.dealer)
                                self.layout.change_turn(self.turn.data.who)
                                self.state.set("bidding")
                                if self.turn.player:
                                    self.tell_pre(self.turn.player, "It is your turn to bid.\n")

                    else:

                        # Trick not over.  Rotate.
                        self.turn = self.next_seat(self.turn)
                        self.layout.change_turn(self.turn.data.who)
                        if self.turn.player:
                            self.show_hand(self.turn.player)

        if not handled:
            self.tell_pre(player, "Invalid command.\n")

    def finish_trick(self):

        # Okay, we have a trick with four cards.  Which card won?
        winner = handle_trick(self.trick, self.trump_suit)

        # This /should/ just return one seat...
        winning_seat_list = [x for x in self.seats if x.data.card == winner]

        if len(winning_seat_list) != 1:
            self.server.log.log(self.log_prefix + "Something went horribly awry; trick ended without a finish.")
            self.bc_pre("Something went horribly wrong; no one won the trick!  Tell the admin.\n")
            return

        winning_seat = winning_seat_list[0]

        # Print information about the winning card.
        self.bc_pre("%s wins the trick with ^C%s^~.\n" % (self.get_sp_str(winning_seat), card_to_str(winner, LONG)))

        # Give the trick to the correct seat.
        winning_seat.data.tricks += 1

        # Clear the trick.
        self.clear_trick()

        # Set the next leader to the player who won.
        self.turn = winning_seat
        self.layout.change_turn(self.turn.data.who)
        if self.turn.player:
            self.show_hand(self.turn.player)

    def resolve_hand(self):

        for seat in self.seats:

            # Determine the score delta; if the bid is < self.double (or
            # doubling is disabled) it's just the bid, otherwise it's double.
            bid = seat.data.bid
            if bid < self.double or not self.double:
                score_delta = bid
            else:
                score_delta = bid * 2
            score_delta_str = get_plural_str(score_delta, "point")

            result_str = "%s bid ^G%s^~ and " % (self.get_sp_str(seat), get_plural_str(bid, "trick"))

            if bid <= seat.data.tricks:

                # Woot, gain points!
                seat.data.score += score_delta
                result_str += "took ^W%d^~, gaining ^G%s^~.\n" % (seat.data.tricks, score_delta_str)

            else:

                # Aw, lost points.
                seat.data.score -= score_delta
                result_str += "only took ^W%d^~, losing ^R%s^~.\n" % (seat.data.tricks, score_delta_str)

            self.bc_pre(result_str)

        self.bc_pre(self.get_score_str())

    def find_winner(self):

        # The rules don't define what happens if both sides win in the same
        # deal.  I've arbitrarily decided that highest score wins, and if
        # both sides have equivalent high scores, there isn't a winner yet.
        high_count = -1
        high_list = None
        for seat in self.seats:
            if seat.data.score >= self.goal:
                if seat.data.score > high_count:
                    high_count = seat.data.score
                    high_list = [seat]
                elif seat.data.score == high_count:
                    high_list.append(seat)

        # If we're in positive mode, strip entries from the list if their
        # partners don't have a positive score.
        if self.positive:
            high_list = [x for x in high_list if x.data.partner.data.score > 0]

        # If the list is empty, we can flat-out bail.
        if not high_list:
            return None

        # If the list has multiple entries, and they're from different teams,
        # we also don't have a winner.
        if (self.north in high_list or self.south in high_list) and (self.west in high_list or self.east in high_list):

            # This is at least worth reporting.
            self.bc_pre("Both sides are ^Ctied for the win^~!  The game continues...\n")
            return None

        # It's fine if both members of a team won at the same time, but we
        # don't care which, since a partnership wins.
        return high_list[0]

    def resolve(self, winning_seat):

        if self.north == winning_seat or self.south == winning_seat:
            name_one = self.north.player_name
            name_two = self.south.player_name
        else:
            name_one = self.west.player_name
            name_two = self.east.player_name

        self.bc_pre("^G%s^~ and ^G%s^~ win!\n" % (name_one, name_two))
