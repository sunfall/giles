# Giles: poison.py
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

import random

from giles.utils import get_plural_str
from giles.state import State
from giles.games.seated_game import SeatedGame
from giles.games.seat import Seat

# Minimums and maximums.
MIN_ANTIDOTE_COUNT = 1
MAX_ANTIDOTE_COUNT = 8

MIN_POISON_COUNT = 1
MAX_POISON_COUNT = 8

MIN_GOAL = 1
MAX_GOAL = 8

TAGS = ["bluff", "random", "3p", "4p", "5p", "6p", "7p", "8p", "9p", "10p"]

_ANTIDOTE_LIST = ('antidote', 'anti', 'a')
_POISON_LIST = ('poison', 'pois', 'poi', 'p')

_BID_LIST = ('bid', 'b')
_INVENTORY_LIST = ('inventory', 'inv', 'i')
_PICK_LIST = ('pick', 'pi', 'choose', 'ch', 'quaff', 'qu')
_PLAY_LIST = ('play', 'place', 'pl', 'rack', 'ra')

class Poison(SeatedGame):
    """An implementation of 'Skull' by Herve Marly, without any of the
    gorgeous artwork, sadly.
    """

    def __init__(self, server, table_name):

        super(Poison, self).__init__(server, table_name)

        self.game_display_name = "Poison"
        self.game_name = "poison"
        self.seats = [
            Seat("Alpha"),
            Seat("Bravo"),
            Seat("Charlie"),
            Seat("Delta"),
            Seat("Echo"),
            Seat("Foxtrot"),
            Seat("Golf"),
            Seat("Hotel"),
            Seat("India"),
            Seat("Juliet")
        ]
        self.state = State("need_players")
        self.prefix = "(^RPoison^~) "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)
        self.min_players = 3
        self.max_players = 10

        # Default configuration.
        self.antidote_count = 3
        self.poison_count = 1
        self.goal = 2

        # Mutable information.
        self.turn = None
        self.highest_bidder = None

    def get_color_code(self, seat):
        color_index = self.seats.index(seat) % 4

        if color_index == 0:
            return "^R"
        elif color_index == 1:
            return "^Y"
        elif color_index == 2:
            return "^M"
        else:
            return "^C"

    def get_sp_str(self, seat):
        return "^G%s^~ (%s%s^~)" % (seat.player_name, self.get_color_code(seat), seat)

    def next_seat(self, seat, bidding=False):

        # Skip players that are dead and, if bidding, have passed.
        player_count = len(self.seats)
        index = self.seats.index(seat) % player_count
        done = False
        while not done:
            index = (index + 1) % player_count
            this_seat = self.seats[index]
            if not this_seat.data.is_dead:

                # Assume done.
                done = True

                # ...but if we're bidding, that might not be the case.
                if bidding and not this_seat.data.is_bidding:
                    done = False

        return self.seats[index]

    def prev_seat(self, seat):

        # This function is unused in the game, but the default prev_seat() is
        # misleading, so:
        return None

    def _count_live_players(self):
        return len([x for x in self.seats if not x.data.is_dead])

    def _count_racked_potions(self):

        count = 0
        for seat in self.seats:
            if not seat.data.is_dead:
                count += len(seat.data.potion_rack)

        return count

    def show(self, player):

        state = self.state.get()
        if state == "need_players":
            player.tell_cc("The game is not yet active.\n")
        else:
            for seat in self.seats:
                seat_str = "%s [^G%s^~, ^C%s^~]: " % (self.get_sp_str(seat), get_plural_str(seat.data.antidotes + seat.data.poisons, "potion"), get_plural_str(seat.data.score, "point"))
                if seat.data.is_dead:
                    seat_str += "^Rdead!^~"
                else:
                    seat_str += "^!%s^~ racked" % get_plural_str(len(seat.data.potion_rack), "potion")

                if seat == self.turn:
                    if state == "playing":
                        seat_str += " ^C[choosing]^~"
                    elif state == "bidding":
                        seat_str += " ^Y[bidding]^~"
                    elif state == "quaffing":
                        seat_str += " ^R[quaffing]^~"
                elif state == "bidding":
                    if seat.data.is_bidding == False:
                        seat_str += " ^M[passed]^~"
                    elif seat.data.bid:
                        seat_str += " [bid ^G%d^~]" % seat.data.bid
                player.tell_cc("%s\n" % seat_str)

        player.tell_cc("\nThe racks currently hold ^G%s^~.\n" % get_plural_str(self._count_racked_potions(), "potion"))
        player.tell_cc("\n\nThe goal score for this game is ^C%s^~.\n" % get_plural_str(self.goal, "point"))

    def winnow_seats(self):

        # Peels off seats that aren't actually being used once the game starts.
        self.seats = [x for x in self.seats if x.player]

    def new_round(self, starting_seat):

        # Initialize the values that reset per-round.
        for seat in self.seats:
            seat.data.is_bidding = True
            seat.data.bid = 0
            seat.data.quaffed = 0
            seat.data.potion_rack = []

        self.turn = starting_seat

        # Shift to initial placement mode.
        self.bc_pre("Players, place your initial potions.\n")
        self.state.set("initial_placement")

    def start_game(self):

        # Configure all necessary data once a game starts.
        self.winnow_seats()

        for seat in self.seats:
            seat.data.is_dead = False
            seat.data.score = 0
            seat.data.antidotes = self.antidote_count
            seat.data.poisons = self.poison_count

        # Pick a random starting player.
        first_player = random.choice(self.seats)
        self.bc_pre("Fate has chosen, and the starting player is %s!\n" % self.get_sp_str(first_player))
        self.new_round(first_player)

    def set_antidote_count(self, player, antidote_str):

        if not antidote_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_count = int(antidote_str)
        if new_count < MIN_ANTIDOTE_COUNT or new_count > MAX_ANTIDOTE_COUNT:
            self.tell_pre(player, "Too small or large.  Must be %s to %s inclusive.\n" % (MIN_ANTIDOTE_COUNT, MAX_ANTIDOTE_COUNT))
            return False

        # Valid choice.
        self.antidote_count = new_count
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the antidote count to ^C%s^~.\n" % (player, str(new_count)))
        return True

    def set_poison_count(self, player, poison_str):

        if not poison_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_count = int(poison_str)
        if new_count < MIN_POISON_COUNT or new_count > MAX_POISON_COUNT:
            self.tell_pre(player, "Too small or large.  Must be %s to %s inclusive.\n" % (MIN_POISON_COUNT, MAX_POISON_COUNT))
            return False

        # Valid choice.
        self.poison_count = new_count
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the poison count to ^C%s^~.\n" % (player, str(new_count)))
        return True

    def set_goal(self, player, goal_str):

        if not goal_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_goal = int(goal_str)
        if new_goal < MIN_GOAL or new_goal > MAX_GOAL:
            self.tell_pre(player, "Too small or large.  Must be %s to %s inclusive.\n" % (MIN_GOAL, MAX_GOAL))
            return False

        # Valid choice.
        self.goal = new_goal
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the goal score to ^C%s^~.\n" % (player, str(new_goal)))
        return True

    def inventory(self, player):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        self.tell_pre(player, "You have ^C%s^~ and ^R%s^~ overall.\n" % (get_plural_str(seat.data.antidotes, "antidote"), get_plural_str(seat.data.poisons, "poison")))

        rack_str = ""
        for potion in seat.data.potion_rack:
            if potion == "antidote":
                rack_str += "^C[A]^~ "
            elif potion == "poison":
                rack_str += "^R*P*^~ "
            else:
                rack_str += "^Y???^~ "
        if not rack_str:
            rack_str = "^!Empty!^~"

        self.tell_pre(player, "Your current rack: %s\n" % rack_str)

    def play(self, player, play_str):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        if seat.data.is_dead:
            self.tell_pre(player, "You're dead!\n")
            return False

        # There are two times you can play: in the initial placement phase,
        # and during the normal flow of the game.
        state = self.state.get()

        if state == "playing":
            if seat != self.turn:
                self.tell_pre(player, "It's not your turn to play a potion.\n")
                return False

        elif state != "initial_placement":
            self.tell_pre(player, "You can't play a potion right now.\n")
            return False

        # Also bail if they've already placed their initial potion.
        elif state == "initial_placement" and seat.data.potion_rack:
            self.tell_pre(player, "You've already placed your first potion.\n")
            return False

        # Okay, they should actually be placing a potion right now.
        # See if they gave us a valid one.
        play_type = play_str.lower()
        if play_type in _ANTIDOTE_LIST:
            attempted_antidote_count = len([x for x in seat.data.potion_rack if x == "antidote"]) + 1
            if attempted_antidote_count > seat.data.antidotes:
                self.tell_pre(player, "You don't have any antidotes left.\n")
                return False

            potion = "antidote"

        elif play_type in _POISON_LIST:
            attempted_poison_count = len([x for x in seat.data.potion_rack if x == "poison"]) + 1
            if attempted_poison_count > seat.data.poisons:
                self.tell_pre(player, "You don't have any poisons left.\n")
                return False

            potion = "poison"

        else:
            self.tell_pre(player, "That's not a valid potion type!\n")
            return False

        # We've got a valid potion type; add it to the rack...
        seat.data.potion_rack.append(potion)
        self.bc_pre("%s places a potion on their rack.\n" % self.get_sp_str(seat))

        return True

    def bid(self, player, bid_str):

        seat = self.get_seat_of_player(player)
        if not seat:
            self.tell_pre(player, "You're not playing!\n")
            return False

        if seat.data.is_dead:
            self.tell_pre(player, "You're dead!\n")
            return False

        # You can bid either during the 'play' phase or the 'bid' phase.
        state = self.state.get()
        if state != "playing" and state != "bidding":
            self.tell_pre(player, "You can't bid right now.\n")
            return False

        if seat != self.turn:
            self.tell_pre(player, "It's not your turn.\n")
            return False

        # Okay, it's a legitimate time to bid.  Is the bid valid?
        if not bid_str.isdigit():
            self.tell_pre(player, "You didn't even bid a number!\n")
            return False

        bid_value = int(bid_str)

        # It has to be at least one.
        if not bid_value:
            self.tell_pre(player, "Nice try, but you can't bid zero.\n")
            return False

        # Is the bid value <= the number of potions available?
        if bid_value > self._count_racked_potions():
            self.tell_pre(player, "There aren't that many racked potions to quaff!\n")
            return False

        # If we're in the bidding phase, is it higher than the current bid?
        if state == "bidding" and bid_value <= self.highest_bidder.data.bid:
            self.tell_pre(player, "That bid isn't higher than the current bid of ^C%d^~.\n" % self.highest_bidder.data.bid)
            return False

        # Valid bid, phew.  Let everyone know and note it down.
        self.bc_pre("%s has bid to quaff ^C%s^~.\n" % (self.get_sp_str(seat), get_plural_str(bid_value, "potion")))
        seat.data.bid = bid_value
        return True

    def win(self, seat):
        self.bc_pre("^G%s^~ has won the game!\n" % seat.player_name)
        self.finish()

    def drank_poison(self, seat, poisoner):

        # If they only have one potion left, they're dead.
        player = seat.player
        potion_count = seat.data.antidotes + seat.data.poisons
        if potion_count == 1:
            self.bc_pre("%s dies of acute poisoning!\n" % self.get_sp_str(seat))
            seat.data.is_dead = True
            seat.data.potions = 0
            seat.data.antidotes = 0

            # If only one player is left alive, they win.
            live_list = [x for x in self.seats if not x.data.is_dead]
            if len(live_list) == 1:
                self.win(live_list[0])

            # If they poisoned themselves, the next player is chosen by them,
            # otherwise it goes to whoever poisoned them.
            if poisoner == seat:
                self.tell_pre(player, "You must choose the next player.\n")
                self.state.set("choosing_player")
            else:
                self.new_round(poisoner)

        else:

            # If we're in autoquaffing mode, they poisoned themselves and get to
            # choose what card they lose.
            if self.state.get() == "autoquaffing":
                self.tell_pre(player, "You must choose what type of potion to toss.\n")
                self.state.set("tossing")
            else:

                # No need to do the "other player" picks stuff digitally.  They
                # just lose a random one.
                self.bc_pre("%s drops a random potion to the floor as they sicken.\n" %
                            self.get_sp_str(seat))
                potion_list = ["antidote" for _ in range(seat.data.antidotes)]
                potion_list.extend(["poison" for _ in range(seat.data.poisons)])
                dropped_potion = random.choice(potion_list)
                if dropped_potion == "antidote":
                    self.tell_pre(player, "An ^Cantidote^~ shatters on the hard stone.\n")
                    seat.data.antidotes -= 1
                else:
                    self.tell_pre(player, "A ^Rpoison^~ shatters on the hard stone.\n")
                    seat.data.poisons -= 1

                # That done, time to start a new round.  They get to go first.
                self.new_round(seat)

    def drank_antidotes(self, seat):

        # This is way easier than drank_poison; they have gained a point and may
        # have won the game.
        self.bc_pre("%s gains a point!\n" % self.get_sp_str(seat))
        seat.data.score += 1

        if seat.data.score == self.goal:
            self.win(seat)

        else:

            # Didn't win; start a new round with them as the first player.
            self.new_round(seat)

    def autoquaff(self, seat):

        # If the bid is less than the number of potions the player has racked,
        # then we just quaff that many and deal with the consequences.  Otherwise
        # we need to go into proper "quaff" mode.

        seat_rack = seat.data.potion_rack
        bid = seat.data.bid
        if len(seat_rack) > seat.data.bid:
            self.bc_pre("%s chugs ^C%s^~ from their own rack.\n" % (self.get_sp_str(seat), get_plural_str(bid, "potion")))
        else:
            self.bc_pre("%s chugs ^Yall of the potions^~ from their own rack.\n" % self.get_sp_str(seat))

        count = 0
        poisoned = False
        while count < bid and seat_rack:
            potion = seat_rack.pop()
            if potion == "poison":
                poisoned = True
            count += 1

        if poisoned:
            self.bc_pre("%s has managed to ^Rpoison^~ themselves!\n" % self.get_sp_str(seat))
            self.drank_poison(seat, seat)
        else:
            self.bc_pre("%s has managed to survive their own potions.\n" % self.get_sp_str(seat))
            if count == bid:
                self.drank_antidotes(seat)
            else:
                seat.data.quaffed = count
                self.tell_pre(seat.player, "You still must quaff ^C%s^~.\n" % get_plural_str(bid - count, "potion"))
                self.state.set("quaffing")

    def toss(self, player, toss_choice):

        seat = self.get_seat_of_player(player)

        if seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
            return False

        toss_type = toss_choice.lower()
        if toss_type in _ANTIDOTE_LIST:
            if seat.data.antidotes == 0:
                self.tell_pre(player, "You have no more antidotes to toss!\n")
                return False

            self.tell_pre(player, "You toss an ^Cantidote^~ into the fire.\n")
            seat.data.antidotes -= 1

        elif toss_type in _POISON_LIST:
            if seat.data.poisons == 0:
                self.tell_pre(player, "You have no more poisons to toss!\n")
                return False

            self.tell_pre(player, "You toss a ^Rpoison^~ into the fire.\n")
            seat.data.poisons -= 1

        else:
            self.tell_pre(player, "That's not a valid potion type!\n")
            return False

        # Successfully tossed a potion; broadcast that and start a new
        # round.
        self.bc_pre("%s tosses a potion into the fire.\n" % self.get_sp_str(seat))
        self.new_round(seat)

    def pick(self, player, pick_str):

        seat = self.get_seat_of_player(player)

        if seat != self.turn:
            self.tell_pre(player, "It's not your turn!\n")
            return False

        # In the case where we're picking someone to be first player because we
        # killed ourselves via poison, the valid list is those players who are
        # still alive.  If we're quaffing, they have to have potions on their
        # rack.
        state = self.state.get()
        if state == "choosing_player":
            valid_choices = [x for x in self.seats if not x.data.is_dead]
        elif state == "quaffing":
            valid_choices = [x for x in self.seats if x.data.potion_rack]
        else:
            self.tell_pre(player, "Not sure how you got here, but you can't pick!\n")
            return False

        # All right.  Let's try to parse out their pick_str.  We're going to
        # be super-lazy and only use the first letter to match.
        their_pick = pick_str.lower()[0]
        actual_pick = [x for x in valid_choices if x.name[0] == their_pick]

        if not actual_pick:
            self.tell_pre(player, "You can't pick that seat for this!\n")
            return False

        # We got a seat.  Sweet.  If it's for choosing a player, start a new
        # round with them as the start player.
        picked_seat = actual_pick[0]
        if state == "choosing_player":
            self.bc_pre("%s has chosen %s to be the new starting player.\n" % (self.get_sp_str(seat), self.get_sp_str(picked_seat)))
            self.new_round(picked_seat)
            return True
        else: # state == "quaffing"

            # Get the newest potion from that seat.
            potion = picked_seat.data.potion_rack.pop()

            # If it's a poison, we've been poisoned!
            if potion == "poison":
                self.bc_pre("%s chugs a potion from %s and is ^Rpoisoned^~!\n" % (self.get_sp_str(seat), self.get_sp_str(picked_seat)))
                self.drank_poison(seat, picked_seat)

            else:

                # Not a poison; increase quaffing count...
                self.bc_pre("%s chugs a potion from %s and keeps it down somehow.\n" % (self.get_sp_str(seat), self.get_sp_str(picked_seat)))
                seat.data.quaffed += 1

                # If we've drank enough, we're done!
                if seat.data.quaffed == seat.data.bid:
                    self.drank_antidotes(seat)
                    return True

                else:
                    self.tell_pre(seat.player, "You still must quaff ^C%s^~.\n" % get_plural_str(seat.data.bid - seat.data.quaffed, "potion"))
                    return True

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()

            command_bits = command_str.split()
            primary = command_bits[0].lower()
            played = False
            bid = False

            if state == "need_players":

                if primary in ('antidotes', 'anti', 'an'):
                    if len(command_bits) == 2:
                        self.set_antidote_count(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid antidotes command.\n")
                    handled = True

                elif primary in ('poisons', 'pois', 'po'):
                    if len(command_bits) == 2:
                        self.set_poison_count(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid poisons command.\n")
                    handled = True

                elif primary in ('goal', 'score'):
                    if len(command_bits) == 2:
                        self.set_goal(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid goal command.\n")
                    handled = True

                elif primary in ('start',):
                    player_count = len([x for x in self.seats if x.player])
                    if player_count < 3:
                        self.tell_pre(player, "Need at least 3 players!\n")
                    else:
                        self.channel.broadcast_cc(self.prefix + "Game on!\n")
                        self.start_game()
                    handled = True

            elif state == "initial_placement":

                if primary in _PLAY_LIST:
                    if len(command_bits) == 2:
                        played = self.play(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid play command.\n")
                    handled = True
                elif primary in _INVENTORY_LIST:
                    self.inventory(player)
                    handled = True

            elif state == "playing":

                if primary in _PLAY_LIST:
                    if len(command_bits) == 2:
                        played = self.play(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid play command.\n")
                    handled = True
                elif primary in _INVENTORY_LIST:
                    self.inventory(player)
                    handled = True
                elif primary in _BID_LIST:
                    if len(command_bits) == 2:
                        bid = self.bid(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid bid command.\n")
                    handled = True

                if played:

                    # It's the next player's turn.
                    self.turn = self.next_seat(self.turn)
                    self.tell_pre(self.turn.player, "It is your turn.\n")

                elif bid:

                    # If the bid is for "every potion there is," immediately
                    # jump to autoquaff mode.
                    if self._count_racked_potions() == self.turn.data.bid:
                        self.bc_pre("%s has bid for all the potions!\n" % self.get_sp_str(self.turn))
                        self.state.set("autoquaffing")

                    else:

                        # Start of a bidding round.  Make sure everyone can bid.
                        self.state.set("bidding")
                        for seat in self.seats:
                            if seat != self.turn:
                                seat.data.bid = 0
                            if not seat.data.is_dead:
                                seat.data.is_bidding = True

                        # ...set the high bid...
                        self.highest_bidder = self.turn

                        # ...and pass the buck.
                        self.turn = self.next_seat(self.turn, bidding=True)
                        self.tell_pre(self.turn.player, "It is your turn to bid or pass.\n")

            elif state == "bidding":

                if primary in _BID_LIST:
                    if len(command_bits) == 2:
                        bid = self.bid(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid bid command.\n")
                    handled = True

                elif primary in _INVENTORY_LIST:
                    self.inventory(player)
                    handled = True

                elif primary in ('pass', 'pa', 'p'):

                    # No need for a function, as this one's easy.
                    self.turn.data.is_bidding = False
                    self.bc_pre("%s has passed and is no longer bidding.\n" % self.get_sp_str(self.turn))

                    # Get the next player...
                    self.turn = self.next_seat(self.turn, bidding=True)

                    # ...and see if it's the highest bidder.  If it is, they
                    # won the bidding.
                    if self.turn == self.highest_bidder:
                        self.bc_pre("%s has won the bid with ^Y%s^~.\n" % (self.get_sp_str(self.turn), get_plural_str(self.turn.data.bid, "potion")))
                        self.state.set("autoquaffing")
                    else:
                        self.tell_pre(self.turn.player, "It is your turn to bid or pass.\n")

                    handled = True
                if bid:

                    # If the bid is the count of racked potions, we're done.
                    if self._count_racked_potions() == self.turn.data.bid:
                        self.bc_pre("%s has bid for all the potions!\n" % self.get_sp_str(self.turn))
                        self.state.set("autoquaffing")

                    else:

                        # New highest bidder.  Set it and go around.
                        self.highest_bidder = self.turn

                        self.turn = self.next_seat(self.turn, bidding=True)
                        self.tell_pre(self.turn.player, "It is your turn to bid or pass.\n")

            elif state == "choosing_player" or state == "quaffing":

                if primary in _PICK_LIST:
                    if len(command_bits) == 2:
                        self.pick(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid pick command.\n")
                    handled = True

                elif primary in _INVENTORY_LIST:
                    self.inventory(player)
                    handled = True

            elif state == "tossing":

                if primary in ('toss', 'to'):
                    if len(command_bits) == 2:
                        self.toss(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid toss command.\n")
                    handled = True

                elif primary in _INVENTORY_LIST:
                    self.inventory(player)
                    handled = True

            if not handled:
                self.tell_pre(player, "Invalid command.\n")

    def tick(self):

        # If all seats are full and active, autostart.
        active_seats = [x for x in self.seats if x.player]
        state = self.state.get()
        if state == "need_players" and len(active_seats) == len(self.seats) and self.active:
            self.bc_pre("All seats full; game on!\n")
            self.start_game()

        # If we're in the initial placement phase and everyone's done, start
        # proper play.
        elif state == "initial_placement":
            filled_racks = [x.data.potion_rack for x in self.seats if
                            x.data.potion_rack]
            if len(filled_racks) == self._count_live_players():
                self.bc_pre("Initial placement is complete.\n")
                self.tell_pre(self.turn.player, "It is your turn.\n")
                self.state.set("playing")

        elif state == "autoquaffing":
            self.autoquaff(self.turn)

    def show_help(self, player):

        super(Poison, self).show_help(player)
        player.tell_cc("\nPOISON SETUP PHASE:\n\n")
        player.tell_cc("              ^!antidotes^. <num>     Set the antidote count to <num> (%d-%d).\n" % (MIN_ANTIDOTE_COUNT, MAX_ANTIDOTE_COUNT))
        player.tell_cc("                ^!poisons^. <num>     Set the poison count to <num> (%d-%d).\n" % (MIN_POISON_COUNT, MAX_POISON_COUNT))
        player.tell_cc("                   ^!goal^. <num>     Set the goal score to <num> (%d-%d).\n" % (MIN_GOAL, MAX_GOAL))
        player.tell_cc("                        ^!start^.     Start the game.\n")
        player.tell_cc("\nPOISON PLAY:\n\n")
        player.tell_cc("       ^!play^. a|p, ^!pl^., ^!rack^., ^!ra^.     Play an antidote or poison.\n")
        player.tell_cc("            ^!inventory^., ^!inv^., ^!i^.     Check your potion inventory.\n")
        player.tell_cc("                    ^!bid^. <num>     Bid <num> quaffs.\n")
        player.tell_cc("                         ^!pass^.     Pass on bidding.\n")
        player.tell_cc("          ^!pick^. <seat>, ^!pi^., ^!ch^.     Pick potion or player at <seat>.\n")
        player.tell_cc("                     ^!toss^. a|p     Toss an antidote or poison.\n")
