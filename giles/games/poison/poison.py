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

from giles.utils import booleanize
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

        # Game-mutable data.
        self.player_count = 0

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
        index = (self.seats.index(seat) + 1) % self.player_count
        while self.seats[index].is_dead:
            index = (index + 1) % self.player_count

    def prev_seat(self, seat):

        # This function is unused in the game, but the default prev_seat() is
        # misleading, so:
        pass

    def winnow_seats(self):

        # Peels off seats that aren't actually being used once the game starts.
        self.seats = [x for x in self.seats if x.player]

    def start_game(self):

        # Configure all necessary data once a game starts.
        self.winnow_seats()

        for seat in self.seats:
            seat.is_dead = False
            seat.data.score = 0
            seat.data.antidotes = self.antidote_count
            seat.data.poisons = self.poison_count

        # Pick a random starting player.
        self.turn = random.choice(self.seats)
        self.bc_pre("Fate has chosen, and the starting player is %s!\n" % self.get_sp_str(self.turn))

        # Shift to initial placement mode.
        self.bc_pre("Players, place your starting potions.\n")
        self.state.set("initial_placement")

    def set_antidote_count(self, player, antidote_str):

        if not antidote_str.isdigit():
            player.tell_cc(self.prefix + "You didn't even send a number!\n")
            return False

        new_count = int(antidote_str)
        if new_count < MIN_ANTIDOTE_COUNT or new_count > MAX_ANTIDOTE_COUNT:
            player.tell_cc(self.prefix + "Too small or large.  Must be %s to %s inclusive.\n" %
                           (MIN_ANTIDOTE_COUNT, MAX_ANTIDOTE_COUNT))
            return False

        # Valid choice.
        self.antidote_count = new_count
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the antidote count to ^C%s^~.\n" %
                                  (player, str(new_count)))
        return True

    def set_poison_count(self, player, poison_str):

        if not poison_str.isdigit():
            player.tell_cc(self.prefix + "You didn't even send a number!\n")
            return False

        new_count = int(poison_str)
        if new_count < MIN_POISON_COUNT or new_count > MAX_POISON_COUNT:
            player.tell_cc(self.prefix + "Too small or large.  Must be %s to %s inclusive.\n" %
                           (MIN_POISON_COUNT, MAX_POISON_COUNT))
            return False

        # Valid choice.
        self.poison_count = new_count
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the poison count to ^C%s^~.\n" %
                                  (player, str(new_count)))
        return True

    def set_goal(self, player, goal_str):

        if not goal_str.isdigit():
            player.tell_cc(self.prefix + "You didn't even send a number!\n")
            return False

        new_goal = int(goal_str)
        if new_goal < MIN_GOAL or new_goal > MAX_GOAL:
            player.tell_cc(self.prefix + "Too small or large.  Must be %s to %s inclusive.\n" %
                           (MIN_GOAL, MAX_GOAL))
            return False

        # Valid choice.
        self.goal = new_goal
        self.channel.broadcast_cc(self.prefix + "^M%s^~ has changed the goal score to ^C%s^~.\n" %
                                  (player, str(new_goal)))
        return True

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()

            command_bits = command_str.split()
            primary = command_bits[0].lower()

            if state == "need_players":

                if primary in ('antidotes', 'anti', 'an'):
                    if len(command_bits) == 2:
                        self.set_antidote_count(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid antidotes command.\n")
                    handled = True

                elif primary in ('poisons', 'pois', 'po'):
                    if len(command_bits) == 2:
                        self.set_poison_count(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid poisons command.\n")
                    handled = True

                elif primary in ('goal', 'score'):
                    if len(command_bits) == 2:
                        self.set_goal(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid goal command.\n")
                    handled = True

                elif primary in ('start',):
                    player_count = len([x for x in self.seats if x.player])
                    if player_count < 3:
                        player.tell_cc(self.prefix + "Need at least 3 players!\n")
                    else:
                        self.channel.broadcast_cc(self.prefix + "Game on!\n")
                        self.start_game()
                    handled = True

            if not handled:
                player.tell_cc(self.prefix + "Invalid command.\n")

    def tick(self):

        # If all seats are full and active, autostart.
        active_seats = [x for x in self.seats if x.player]
        if (self.state.get() == "need_players" and
            len(active_seats) == len(self.seats) and self.active):
            self.bc_pre("All seats full; game on!\n")
            self.start_game()


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
