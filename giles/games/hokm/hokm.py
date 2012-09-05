# Giles: hokm.py
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

from giles.games.four_player_card_game_layout import FourPlayerCardGameLayout, NORTH, SOUTH, EAST, WEST
from giles.games.game import Game
from giles.games.hand import Hand
from giles.games.playing_card import new_deck, str_to_card, card_to_str, hand_to_str, SHORT, LONG, CLUBS, DIAMONDS, HEARTS, SPADES
from giles.games.seat import Seat
from giles.games.trick import handle_trick, hand_has_suit, sorted_hand
from giles.state import State
from giles.utils import Struct

import random

class Hokm(Game):
    """A Hokm game table implementation.  Hokm is a Persian trick-taking
    card game of unknown provenance.  This implementation does not
    (currently) allow 3-player Hokm, which is a fascinating game all its
    own.  It also doesn't currently rearrange the seats at the start.
    """

    def __init__(self, server, table_name):

        super(Hokm, self).__init__(server, table_name)

        self.game_display_name = "Hokm"
        self.game_name = "hokm"

        # Hokm goes CCW, not CW, so we just reorder the seats.
        self.seats = [
            Seat("North"),
            Seat("West"),
            Seat("South"),
            Seat("East"),
        ]

        self.min_players = 4
        self.max_players = 4
        self.state = State("need_players")
        self.prefix = "(^RHokm^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Hokm-specific guff.
        self.ns = Struct()
        self.ns.score = 0
        self.ew = Struct()
        self.ew.score = 0
        self.seats[0].data.who = NORTH
        self.seats[1].data.who = WEST
        self.seats[2].data.who = SOUTH
        self.seats[3].data.who = EAST

        self.goal = 7
        self.trick = None
        self.trump_suit = None
        self.led_suit = None
        self.turn = None
        self.dealer = None
        self.hakem = None
        self.winner = None

        self.layout = FourPlayerCardGameLayout()

    def show_help(self, player):

        super(Hokm, self).show_help(player)
        player.tell_cc("\nHOKM SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("            ^!goal^. <num>, ^!score^.     Set the goal score to <num>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nHOKM PLAY:\n\n")
        player.tell_cc("            ^!choose^. <suit>, ^!ch^.     Declare <suit> as trumps.  Hakem only.\n")
        player.tell_cc("              ^!play^. <card>, ^!pl^.     Play <card> from your hand.\n")
        player.tell_cc("                 ^!hand^., ^!inv^., ^!i^.     Look at the cards in your hand.\n")

    def get_point_str(self, num):

        if num == 1:
            return "1 point"
        return "%d points" % num

    def display(self, player):

            player.tell_cc("%s" % self.layout)

    def get_sp_str(self, seat):

        return "^G%s^~ (^C%s^~)" % (seat.player_name, seat)

    def get_metadata(self):

        to_return = "\n\n"
        if self.turn:
            if self.turn == self.seats[0] or self.turn == self.seats[2]:
                seat_color = "^R"
            else:
                seat_color = "^M"
            to_return += "%s is the hakem.\n" % (self.get_sp_str(self.hakem))
            to_return += "It is ^Y%s^~'s turn (%s%s^~).  Trumps are ^C%s^~.\n" % (self.turn.player_name, seat_color, self.turn, self.trump_suit)
            to_return += "Tricks:   ^RNorth/South^~: %d    ^MEast/West^~: %d\n" % (self.ns.tricks, self.ew.tricks)
        to_return += "The goal score for this game is ^C%s^~.\n" % self.get_point_str(self.goal)
        to_return += "          ^RNorth/South^~: %d    ^MEast/West^~: %d\n" % (self.ns.score, self.ew.score)

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
        self.bc_pre("^M%s^~ has changed the goal to ^G%s^~.\n" % (player, self.get_point_str(new_goal)))

    def clear_trick(self):

        # Set the current trick to an empty hand...
        self.trick = Hand()
        self.led_suit = None

        # ...and set everyone's played card to None.
        for seat in self.seats:
            seat.data.card = None

        # Clear the layout as well.
        self.layout.clear()

    def start_deal(self):

        # Set the trick counts to zero.
        self.ns.tricks = 0
        self.ew.tricks = 0

        dealer_name = self.dealer.player_name

        self.bc_pre("^R%s^~ (^C%s^~) gives the cards a good shuffle...\n" % (dealer_name, self.dealer))
        self.deck = new_deck()
        self.deck.shuffle()

        # Deal out five cards each.
        self.bc_pre("^R%s^~ deals five cards out to each of the players.\n" % dealer_name)
        for seat in self.seats:
            seat.data.hand = Hand()
        for i in range(5):
            for seat in self.seats:
                seat.data.hand.draw(self.deck.discard())

        # Sort the hakem's hand.
        self.hakem.data.hand = sorted_hand(self.hakem.data.hand)

        # Show the hakem their hand.
        if self.hakem.player:
            self.tell_pre(self.hakem.player, "Please choose a trump suit for this hand.\n")
            self.show_hand(self.hakem.player)

        # Point to the hakem so everyone knows who is holding up the game.
        self.layout.change_turn(self.hakem.data.who)

        # Shift into "choosing" mode.
        self.state.set("choosing")

    def finish_deal(self):

        self.bc_pre("^R%s^~ finishes dealing the cards out.\n" % self.dealer.player_name)
        for i in range(8):
            for seat in self.seats:
                seat.data.hand.draw(self.deck.discard())

        # Sort everyone's hands now that we have a trump suit.
        for seat in self.seats:
            seat.data.hand = sorted_hand(seat.data.hand, self.trump_suit)

        # Show everyone their completed hands.
        self.show_hands()

        # The hakem leads.
        self.turn = self.hakem
        self.layout.change_turn(self.hakem.data.who)

        # We're playing now.
        self.state.set("playing")

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
            if (this_suit != self.led_suit and
               hand_has_suit(seat.data.hand, self.led_suit)):

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
        self.trick.draw(seat.data.hand.discard_specific(potential_card))
        trump_str = ""
        if potential_card.suit == self.trump_suit:
            trump_str = ", a ^Rtrump^~"
        self.bc_pre("%s %s ^C%s^~%s.\n" % (self.get_sp_str(seat), action_str, card_to_str(potential_card, LONG), trump_str))
        self.layout.place(seat.data.who, potential_card)
        return potential_card

    def tick(self):

        # If all seats are full and active, autostart.
        if (self.state.get() == "need_players" and self.seats[0].player and
           self.seats[1].player and self.seats[2].player and
           self.seats[3].player and self.active):
            self.state.set("playing")
            self.bc_pre("The game has begun.\n")

            # Initialize everything by clearing the (non-existent) trick.
            self.clear_trick()

            # Pick a hakem at random.
            self.hakem = random.choice(self.seats)
            self.bc_pre("Fate has spoken, and the starting hakem is %s!\n" % self.get_sp_str(self.hakem))

            # The dealer is always the player before the hakem.
            self.dealer = self.prev_seat(self.hakem)
            self.start_deal()

    def choose(self, player, choose_str):

        choose_str = choose_str.lower()

        if choose_str in ("clubs", "c",):
            self.trump_suit = CLUBS
        elif choose_str in ("diamonds", "d",):
            self.trump_suit = DIAMONDS
        elif choose_str in ("hearts", "h",):
            self.trump_suit = HEARTS
        elif choose_str in ("spades", "s",):
            self.trump_suit = SPADES
        else:
            self.tell_pre(player, "That's not a valid suit!\n")
            return

        # Success.  Declare it and finish the deal.
        self.bc_pre("%s has picked ^R%s^~ as trumps.\n" % (player, self.trump_suit))
        self.finish_deal()

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

                elif primary in ("done", "ready", "d", "r",):
                    self.bc_pre("The game is now looking for players.\n")
                    self.state.set("need_players")
                    handled = True

            elif state == "need_players":

                if primary in ("config", "setup", "conf",):
                    self.state.set("setup")
                    self.bc_pre("^R%s^~ has switched the game to setup mode.\n" % player)
                    handled = True

            elif state == "choosing":

                if primary in ("hand", "inventory", "inv", "i",):
                    if player == self.hakem.player:
                        self.show_hand(player)
                    else:
                        self.tell_pre(player, "You can't look at your cards yet!\n")
                    handled = True

                elif primary in ("choose", "trump", "ch", "tr",):
                    if player == self.hakem.player:
                        if len(command_bits) == 2:
                            did_choose = self.choose(player, command_bits[1])
                        else:
                            self.tell_pre(player, "Invalid choose command.\n")
                    else:
                        self.tell_pre(player, "You're not hakem!\n")
                    handled = True

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

                        # Did that end the hand?
                        winner = self.find_hand_winner()

                        if winner:

                            # Yup.  Resolve the hand...
                            self.resolve_hand()

                            # And look for a winner.
                            winner = self.find_winner()
                            if winner:

                                # Found a winner.  Finish.
                                self.resolve(winner)
                                self.finish()

                            else:

                                # No winner.  Redeal.
                                self.start_deal()

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

        # Give the trick to the correct partnership.
        if winning_seat == self.seats[0] or winning_seat == self.seats[2]:
            self.ns.tricks += 1
        else:
            self.ew.tricks += 1

        # Clear the trick.
        self.clear_trick()

        # Set the next leader to the player who won.
        self.turn = winning_seat
        self.layout.change_turn(self.turn.data.who)
        if self.turn.player:
            self.show_hand(self.turn.player)

    def find_hand_winner(self):

        if self.ns.tricks > 6:
            return self.ns
        elif self.ew.tricks > 6:
            return self.ew

        return None

    def resolve_hand(self):

        # Which side won more than 6 tricks?  Assume it's the hakem's; adjust.
        hakem_won = True
        if self.ns.tricks > 6:
            winning_str = "^RNorth/South^~"
            winner = self.ns
            if self.hakem != self.seats[0] and self.hakem != self.seats[2]:
                hakem_won = False
            loser = self.ew
        else:
            winning_str = "^MEast/West^~"
            winner = self.ew
            if self.hakem != self.seats[1] and self.hakem != self.seats[3]:
                hakem_won = False
            loser = self.ns

        # Did the loser get no tricks?  If so, the winner swept!
        if loser.tricks == 0:
            action_str = "^Yswept^~"

            # 2 points if the hakem won, 3 if the other team did.
            if hakem_won:
                addend = 2
            else:
                addend = 3
        else:

            # Standard win.  One point.
            action_str = "^Wwon^~"
            addend = 1

        # Let everyone know.
        self.bc_pre("%s %s the hand and gains ^C%s^~.\n" % (winning_str, action_str, self.get_point_str(addend)))

        # Apply the score.
        winner.score += addend

        # Did the hakem not win?  If so, we need to have a new hakem and dealer.
        if not hakem_won:
            self.dealer = self.hakem
            self.hakem = self.next_seat(self.hakem)
            self.bc_pre("The ^Yhakem^~ has been unseated!  The new hakem is %s.\n" % self.get_sp_str(self.hakem))
        else:
            self.bc_pre("%s remains the hakem.\n" % self.get_sp_str(self.hakem))

    def find_winner(self):

        # Easy: has one of the sides reached a winning score?
        if self.ns.score >= self.goal:
            return self.ns
        elif self.ew.score >= self.goal:
            return self.ew

        return None

    def resolve(self, winning_partnership):

        if self.ns == winning_partnership:
            name_one = self.seats[0].player_name
            name_two = self.seats[2].player_name
        else:
            name_one = self.seats[1].player_name
            name_two = self.seats[3].player_name
        self.bc_pre("^G%s^~ and ^G%s^~ win!\n" % (name_one, name_two))
