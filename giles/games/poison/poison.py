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

from giles.utils import booleanize, get_plural_str
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

TAGS = ["abstract", "bluff", "random", "3p", "4p", "5p", "6p", "7p", "8p",
        "9p", "10p"]

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

    def next_seat(self, seat):

        # Skip players that are dead.
        player_count = len(self.seats)
        index = (self.seats.index(seat) + 1) % player_count
        while self.seats[index].data.is_dead:
            index = (index + 1) % player_count

        return self.seats[index]

    def prev_seat(self, seat):

        # This function is unused in the game, but the default prev_seat() is
        # misleading, so:
        return None

    def count_live_players(self):
        return len([x for x in self.seats if not x.data.is_dead])

    def show(self, player):

        if self.state.get() == "need_players":
            player.tell_cc("The game is not yet active.\n")
        player.tell_cc("\n\nThe goal score for this game is ^C%s^~.\n" %
                       get_plural_str(self.goal, "point"))

    def winnow_seats(self):

        # Peels off seats that aren't actually being used once the game starts.
        self.seats = [x for x in self.seats if x.player]

    def start_game(self):

        # Configure all necessary data once a game starts.
        self.winnow_seats()

        for seat in self.seats:
            seat.data.is_dead = False
            seat.data.score = 0
            seat.data.antidotes = self.antidote_count
            seat.data.poisons = self.poison_count
            seat.data.potion_rack = []

        # Pick a random starting player.
        self.turn = random.choice(self.seats)
        self.bc_pre("Fate has chosen, and the starting player is %s!\n" % self.get_sp_str(self.turn))

        # Shift to initial placement mode.
        self.bc_pre("Players, place your initial potions.\n")
        self.state.set("initial_placement")

    def set_antidote_count(self, player, antidote_str):

        if not antidote_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_count = int(antidote_str)
        if new_count < MIN_ANTIDOTE_COUNT or new_count > MAX_ANTIDOTE_COUNT:
            self.tell_pre(player, "Too small or large.  Must be %s to %s inclusive.\n" %
                          (MIN_ANTIDOTE_COUNT, MAX_ANTIDOTE_COUNT))
            return False

        # Valid choice.
        self.antidote_count = new_count
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the antidote count to ^C%s^~.\n" %
                                  (player, str(new_count)))
        return True

    def set_poison_count(self, player, poison_str):

        if not poison_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_count = int(poison_str)
        if new_count < MIN_POISON_COUNT or new_count > MAX_POISON_COUNT:
            self.tell_pre(player, "Too small or large.  Must be %s to %s inclusive.\n" %
                          (MIN_POISON_COUNT, MAX_POISON_COUNT))
            return False

        # Valid choice.
        self.poison_count = new_count
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the poison count to ^C%s^~.\n" %
                                  (player, str(new_count)))
        return True

    def set_goal(self, player, goal_str):

        if not goal_str.isdigit():
            self.tell_pre(player, "You didn't even send a number!\n")
            return False

        new_goal = int(goal_str)
        if new_goal < MIN_GOAL or new_goal > MAX_GOAL:
            self.tell_pre(player, "Too small or large.  Must be %s to %s inclusive.\n" %
                          (MIN_GOAL, MAX_GOAL))
            return False

        # Valid choice.
        self.goal = new_goal
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the goal score to ^C%s^~.\n" %
                                  (player, str(new_goal)))
        return True

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
        if play_type in ('antidote', 'anti', 'a'):
            attempted_antidote_count = len([x for x in seat.data.potion_rack if
                                            x == "antidote"]) + 1
            if attempted_antidote_count > seat.data.antidotes:
                self.tell_pre(player, "You don't have any antidotes left.\n")
                return False

            potion = "antidote"

        elif play_type in ('poison', 'pois', 'poi', 'p'):
            attempted_poison_count = len([x for x in seat.data.potion_rack if
                                          x == "poison"]) + 1
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

    _PLAY_LIST = ('play', 'place', 'pl')

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()

            command_bits = command_str.split()
            primary = command_bits[0].lower()
            played = False

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

                if primary in self._PLAY_LIST:
                    if len(command_bits) == 2:
                        played = self.play(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid play command.\n")
                    handled = True

            elif state == "playing":

                if primary in self._PLAY_LIST:
                    if len(command_bits) == 2:
                        played = self.play(player, command_bits[1])
                    else:
                        self.tell_pre(player, "Invalid play command.\n")
                    handled = True

                if played:

                    # It's the next player's turn.
                    self.turn = self.next_seat(self.turn)
                    self.tell_pre(self.turn.player, "It is your turn.\n")

            if not handled:
                self.tell_pre(player, "Invalid command.\n")

    def tick(self):

        # If all seats are full and active, autostart.
        active_seats = [x for x in self.seats if x.player]
        state = self.state.get()
        if (state == "need_players" and len(active_seats) == len(self.seats)
           and self.active):
            self.bc_pre("All seats full; game on!\n")
            self.start_game()

        # If we're in the initial placement phase and everyone's done, start
        # proper play.
        elif state == "initial_placement":
            filled_racks = [x.data.potion_rack for x in self.seats if
                            x.data.potion_rack]
            if len(filled_racks) == self.count_live_players():
                self.bc_pre("Initial placement is complete.\n")
                self.tell_pre(self.turn.player, "It is your turn.\n")
                self.state.set("playing")

    def show_help(self, player):

        super(Poison, self).show_help(player)
        player.tell_cc("\nPOISON SETUP PHASE:\n\n")
        player.tell_cc("              ^!antidotes^. <num>     Set the antidote count to <num> (%d-%d).\n" %
                       (MIN_ANTIDOTE_COUNT, MAX_ANTIDOTE_COUNT))
        player.tell_cc("                ^!poisons^. <num>     Set the poison count to <num> (%d-%d).\n" %
                       (MIN_POISON_COUNT, MAX_POISON_COUNT))
        player.tell_cc("                   ^!goal^. <num>     Set the goal score to <num> (%d-%d).\n" %
                       (MIN_GOAL, MAX_GOAL))
        player.tell_cc("                        ^!start^.     Start the game.\n")
        player.tell_cc("\nPOISON PLAY:\n\n")
        player.tell_cc("                 ^!play^. a|p, ^!pl^.     Play an antidote or a poison.\n")
        player.tell_cc("                    ^!bid^. <num>     Bid <num> quaffs.\n")
        player.tell_cc("                         ^!pass^.     Pass on bidding.\n")
        player.tell_cc("       ^!quaff^. <seat>, ^!chug^., ^!ch^.     Quaff freshest potion at <seat>.\n")
