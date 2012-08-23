# Giles: set.py
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

import random
import time

from giles.state import State
from giles.utils import booleanize
from giles.utils import demangle_move
from giles.games.game import Game
from giles.games.seat import Seat
from giles.utils import Struct

# Some useful default values.
DEFAULT_MAX_CARDS = 24
DEFAULT_DEAL_DELAY = 60

# Numbers!
ONE = Struct()
ONE.display = "one"

TWO = Struct()
TWO.display = "two"

THREE = Struct()
THREE.display = "three"

# Fills!

SMOOTH = Struct()
SMOOTH.display = "smooth"
SMOOTH.edge_art = [".----.", "|%s|", "|%s|", "`----'"]

WAVY = Struct()
WAVY.display = "wavy"
WAVY.edge_art = ["/~~~~\\", "{%s}", "{%s}", "\\~~~~/"]

CHUNKY = Struct()
CHUNKY.display = "chunky"
CHUNKY.edge_art = ["|=||=|", "=%s=", "|%s|", "|=||=|"]

# Colors!
MAGENTA = Struct()
MAGENTA.code = "^M"
MAGENTA.display = "purple"

RED = Struct()
RED.code = "^R"
RED.display = "red"

GREEN = Struct()
GREEN.code = "^G"
GREEN.display = "green"

# Shapes!
BLOB = Struct()
BLOB.art = "oOOo"
BLOB.display = "blob"

LOZENGE = Struct()
LOZENGE.art = "<==>"
LOZENGE.display = "lozenge"

SQUIGGLE = Struct()
SQUIGGLE.art = "/\\/\\"
SQUIGGLE.display = "squiggle"

# Bitfields!
BITFIELDS = [
   {1: ONE, 2: TWO, 4: THREE, ONE: 1, TWO: 2, THREE: 4},
   {1: SMOOTH, 2: WAVY, 4: CHUNKY, SMOOTH: 1, WAVY: 2, CHUNKY: 4},
   {1: MAGENTA, 2: RED, 4: GREEN, MAGENTA: 1, RED: 2, GREEN: 4},
   {1: BLOB, 2: LOZENGE, 4: SQUIGGLE, BLOB: 1, LOZENGE: 2, SQUIGGLE: 4},
]

class Set(Game):
    """A Set game table implementation.  Invented in 1974 by Marsha Jean Falco.
    """

    def __init__(self, server, table_name):

        super(Set, self).__init__(server, table_name)

        self.game_display_name = "Set"
        self.game_name = "set"
        self.seats = []
        self.min_players = 1
        self.max_players = 32767 # We don't even use this.
        self.state = State("need_players")
        self.prefix = "(^RSet^~): "
        self.log_prefix = "%s/%s" % (self.table_display_name, self.game_display_name)

        # Set-specific stuff.
        self.max_cards_on_table = DEFAULT_MAX_CARDS
        self.deal_delay = DEFAULT_DEAL_DELAY
        self.layout = None
        self.printable_layout = None
        self.deck = None
        self.last_play_time = None
        self.max_card_count = 81
        self.has_borders = True


    def build_deck(self):

        # Generate the deck...
        self.deck = []
        for count in (ONE, TWO, THREE):
            fill_list = (SMOOTH,)
            if self.has_borders:
                fill_list = (SMOOTH, WAVY, CHUNKY)
            for fill in fill_list:
                for color in (MAGENTA, RED, GREEN):
                    for shape in (BLOB, LOZENGE, SQUIGGLE):
                        self.deck.append((count, fill, color, shape))

        # ...and shuffle it.
        random.shuffle(self.deck)

        # Trim it to at most the max count.
        self.deck = self.deck[:self.max_card_count]

    def build_layout(self):

        # Put the first twelve cards on the table.
        self.layout = self.deck[:12]
        self.deck = self.deck[12:]

    def update_layout(self):

        # If the size of the layout is 12 or smaller, this is easy;
        # we just draw cards left (if any) to fill gaps in the board.
        # If it's larger than 12, it's easy too; we rebuild the 
        # layout without any gaps (and then, juuust in case, add
        # blank cards if it somehow got smaller than 12.)

        layout_len = len(self.layout)
        if len(self.layout) <= 12:
            for i in range(layout_len):
                if not self.layout[i] and self.deck:
                    self.layout[i] = self.deck[0]
                    self.deck = self.deck[1:]

        else:
            new_layout = [x for x in self.layout if x]
            while len(new_layout) < 12:
                new_layout.append(None)
            self.layout = new_layout

    def get_card_art_bits(self, card, line_number):
        # .----. 1 /~~~~\ |=||=|
        # |2or3| 2 {    } =    =
        # |1or3| 3 {    } |    |
        # |2or3| 4 {    } =    =
        # `----' 5 \~~~~/ |=||=|
    
        # Just in case...
        if line_number < 1 or line_number > 5:
            return

        # At the end of the game, we will sometimes print blank
        # spaces where cards should go.  Handle that.
        if not card:
            return "      "
        count, fill, color, shape = card

        # If a line has a piece of art, it looks like this...
        art_bit = "%s%s^~" % (color.code, shape.art)
        # ...otherwise this.
        blank_bit = "    "

        if line_number == 1:
            return fill.edge_art[0]
        elif line_number == 2 or line_number == 4:
            center = blank_bit
            if count == TWO or count == THREE:
                center = art_bit
            return fill.edge_art[1] % center
        elif line_number == 3:
            center = blank_bit
            if count == ONE or count == THREE:
                center = art_bit
            return fill.edge_art[2] % center
        elif line_number == 5:
            return fill.edge_art[3]
    
        # Dunno how we got here...
        return "ERROR"

    def update_printable_layout(self):

        self.printable_layout = []
        if not self.layout:
            self.printable_layout.append("The layout is currently ^cempty^~.\n")
            return

        # If the layout doesn't have a number of card spaces divisible
        # by 3, something is horribly wrong, and we should bail.
        if len(self.layout) % 3 != 0:
            self.printable_layout.append("Something is ^Rhorribly wrong^~ with the layout.  Alert an admin.\n")
            return

        # Okay, we have a usable layout.  Generate it!
        cards_per_row = len(self.layout) / 3
        self.printable_layout.append("=======" * cards_per_row + "=\n")
        for row in range(3):
            if row == 0:
                row_char = "A"
            elif row == 1:
                row_char = "B"
            else:
                row_char = "C"
            for card_line in range(1, 6):
                this_line = ""
                for col in range(cards_per_row):
                    this_line += (" %s" % self.get_card_art_bits(self.layout[col * 3 + row], card_line))
                self.printable_layout.append(this_line + "\n")

            # Now we print the codes for each card under the cards.
            this_line = ""
            for col in range(1, cards_per_row + 1):
                this_line += ("   %s%s  " % (row_char, col))
            self.printable_layout.append(this_line + "\n\n")

    def show(self, player):

        if not self.printable_layout:
            self.update_printable_layout()
        for line in self.printable_layout:
            player.tell_cc(line)

    def send_layout(self):
        for listener in self.channel.listeners:
            self.show(listener)

    def join(self, player, join_bits):

        # We have to override join for two reasons: one, we allow players
        # to join during the game (!), and two, we have to create seats
        # for players on the fly, as we have no idea how many there might
        # end up being.

        state = self.state.get()
        if state == "need_players" or state == "playing":
            if len(join_bits) != 0:
                player.tell_cc(self.prefix + "Cannot request a specific seat in Set.\n")
            elif self.get_seat_of_player(player):
                player.tell_cc(self.prefix + "You're already playing!\n")
            else:
                seat = Seat("%s" % str(len(self.seats) + 1))
                seat.data.score = 0
                self.seats.append(seat)
                seat.sit(player)
                player.tell_cc(self.prefix + "You are now sitting in seat %s.\n" % seat)
                if not self.channel.is_connected(player):
                    self.channel.connect(player)
                self.channel.broadcast_cc(self.prefix + "^Y%s^~ is now playing in seat ^C%s^~.\n" % (player, seat))
                self.num_players += 1
        else:
            player.tell_cc(self.prefix + "Not looking for players.\n")

        return True

    def set_max_columns(self, player, column_str):

        if not column_str.isdigit():
            player.tell_cc(self.prefix + "Must provide numbers.\n")
            return

        column_val = int(column_str)
        if column_val < 7 or column_val > 9:
            player.tell_cc(self.prefix + "Must provide a value between 7 and 9 inclusive.\n")
            return

        self.max_cards_on_table = column_val * 3
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ set the maximum columns to ^C%s^~.\n" % (player, str(column_val)))

    def set_delay(self, player, delay_str):

        if not delay_str.isdigit():
            player.tell_cc(self.prefix + "Must provide numbers.\n")
            return

        delay_val = int(delay_str)
        if delay_val < 5 or delay_val > 300:
            player.tell_cc(self.prefix + "Must provide a value between 5 and 300 inclusive.\n")
            return

        self.deal_delay = delay_val
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ set the deal delay to ^C%s^~ seconds.\n" % (player, str(delay_val)))

    def set_max_count(self, player, count_str):

        if not count_str.isdigit():
            player.tell_cc(self.prefix + "Must provide numbers.\n")
            return

        count_val = int(count_str)
        if count_val < 21 or count_val > 81 or count_val %3 != 0:
            player.tell_cc(self.prefix + "Must provide a value between 21 and 81 inclusive, divisible by 3.\n")
            return

        self.max_card_count = count_val
        self.channel.broadcast_cc(self.prefix + "^Y%s^~ set the maximum card count to ^C%s^~ cards.\n" % (player, str(count_val)))

    def set_border(self, player, border_str):

        border_bool = booleanize(border_str)
        if border_bool:
            if border_bool > 0:
                self.has_borders = True
                display_str = "^Con^~"
            else:
                self.has_borders = False
                display_str = "^coff^~"
            self.channel.broadcast_cc(self.prefix + "^R%s^~ has turned borders %s.\n" % (player, display_str))
        else:
            player.tell_cc(self.prefix + "Not a valid boolean!\n")

    def handle(self, player, command_str):

        # Handle common commands first.
        handled = self.handle_common_commands(player, command_str)

        if not handled:
            state = self.state.get()
            command_bits = command_str.split()
            primary = command_bits[0].lower()

            if primary in ("score", "scores"):
                self.show_scores(player)
                handled = True

            elif state == "need_players":
                if primary in ("column", "columns"):
                    if len(command_bits) == 2:
                        self.set_max_columns(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid columns command.\n")
                    handled = True

                elif primary in ("delay",):
                    if len(command_bits) == 2:
                        self.set_delay(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid delay command.\n")
                    handled = True

                elif primary in ("cards", "count"):
                    if len(command_bits) == 2:
                        self.set_max_count(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid cards command.\n")
                    handled = True

                elif primary in ("borders", "border"):
                    if len(command_bits) == 2:
                        self.set_border(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid border command.\n")
                    handled = True

                elif primary in ("start",):
                    if not len(self.seats):
                        player.tell_cc(self.prefix + "Need at least one player!\n")
                    else:
                        self.state.set("playing")
                        self.channel.broadcast_cc(self.prefix + "Game on!\n")
                        self.build_deck()
                        self.build_layout()
                        self.update_printable_layout()
                        self.send_layout()
                        self.last_play_time = time.time()
                    handled = True

            elif state == "playing":

                # Everything at this point should be a move, which consists
                # of a list of 3 card choices.  As always, do the polite thing
                # for players who do the play/pl/move/mv/thing.
                if primary in ('play', 'move', 'pl', 'mv'):
                    play_bits = demangle_move(command_bits[1:])
                else:
                    play_bits = demangle_move(command_bits)

                if len(play_bits) == 3:
                    self.declare(player, play_bits)
                    handled = True

        if not handled:
            player.tell_cc(self.prefix + "Invalid command.\n")

    def tick(self):

        # If the game hasn't started or is finished, don't bother.
        if not self.last_play_time or self.state.get() == "finished":
            return

        # Also don't bother if the maximum number of cards are already
        # on the table.
        if len(self.layout) >= self.max_cards_on_table:
            return

        # Also don't bother if the deck is empty.
        if not self.deck:
            return

        # Okay, so, we're playing.  See if too much time has passed.
        curr_time = time.time()
        if curr_time - self.last_play_time < self.deal_delay:
            return

        # Yup.  Deal out three new cards.
        for i in range(3):
            if self.deck:
                self.layout.append(self.deck[0])
                self.deck = self.deck[1:]

        self.update_printable_layout()
        self.send_layout()
        self.channel.broadcast_cc(self.prefix + "New cards have automatically been dealt.\n")

        # Update the last play time.
        self.last_play_time = time.time()
                
    def declare(self, player, declare_bits):

        if not self.get_seat_of_player(player):
            player.tell_cc(self.prefix + "You're not playing in this game!  (But you should join.)\n")
            return

        # Check the three cards for validity and convert them to locations
        # in our linear array.
        valid = True
        card_locations = []
        cards_per_row = len(self.layout) / 3
        for bit in declare_bits:
            # Letter first.
            if bit[0] < 0 or bit[0] > 2:
                valid = False
            else:
                addend = bit[0]

            # And the number.
            multer = bit[1]
            if multer < 0 or multer >= cards_per_row:
                valid = False
            else:

                # Phew.  Passed all the tests.
                card_locations.append(multer * 3 + addend)

        if not valid:
            player.tell_cc(self.prefix + "You declared an invalid card.\n")
            return

        elif ((card_locations[0] == card_locations[1]) or
           (card_locations[1] == card_locations[2]) or
           (card_locations[0] == card_locations[2])):
            player.tell_cc(self.prefix + "You can't declare duplicate cards.\n")
            return

        # Okay, so, we potentially have valid cards...
        cards = [self.layout[x] for x in card_locations]

        # Bail if any of these are empty locations.
        if not cards[0] or not cards[1] or not cards[2]:
            player.tell_cc(self.prefix + "You can't pick empty spaces.\n")
            return

        # All right.  Three valid, actual cards.  Now let's see if they're
        # actually a set!
        if self.is_a_set(cards):
            seat = self.get_seat_of_player(player)
            seat.data.score += 1
            # zomg.  Is an actual set!  Notify the press.  Update the layout
            # and send it out.
            for i in card_locations:
                self.layout[i] = None
            self.update_layout()
            self.update_printable_layout()
            self.send_layout()
            self.channel.broadcast_cc(self.prefix + "^Y%s^~ found a set! (%s)\n" %
               (player, self.make_set_str(cards)))

            # Determine if the game is over.  If so, we're done!
            if self.no_more_sets():
                self.resolve()
                self.finish()

            # Lastly, mark this as the time of the last valid play.
            self.last_play_time = time.time()

        else:
            player.tell_cc(self.prefix + self.make_set_str(cards) + " is not a set!\n")

    def third_card(self, one, two):

        # For any two cards, the third card to make it a set can be
        # determined easily.  For each element, if the two cards are
        # the same, the third must have the same one as well; if
        # different, use BITFIELDS to find the missing one.  Since
        # there are 3 possible values, subtract 7 from the summation
        # of the two's bit values to get the third one.
        three = []
        for k in range(4):
            if one[k] == two[k]:
                three.append(one[k])
            else:
                three.append(BITFIELDS[k][7 - (BITFIELDS[k][one[k]] +
                   BITFIELDS[k][two[k]])])
        return tuple(three)

    def is_a_set(self, cards):

        return self.third_card(cards[0], cards[1]) == cards[2]

    def make_set_str(self, cards):

        card_str_list = []
        for card in cards:
            card_str = card[2].code + " ".join([x.display for x in card])
            if card[0] != ONE:
               card_str += "s"
            card_str_list.append(card_str + "^~")

        return ", ".join(card_str_list)

    def no_more_sets(self):

        # First, bail if the deck still has any cards whatsoever, as we can't
        # possibly know that there aren't any sets left until the deck is
        # depleted.
        if self.deck:
            return False

        # Okay, now, get a list of cards on the layout.
        cards_left = [x for x in self.layout if x]

        count_left = len(cards_left)
        # If there are more than 20 cards on the table, we know for a fact
        # that there has to be a set left.
        if count_left > 20:
            return False

        # Take every unique pair of cards on the layout and determine what
        # the third card would be that makes them a set.  If that card is
        # still on the table, we have a valid set left.
        for i in range(count_left):
            for j in range(i + 1, count_left):
                if self.third_card(cards_left[i], cards_left[j]) in cards_left:
                    return False

        # No sets found.
        return True

    def resolve(self):

        winner_dict = {}
        for seat in self.seats:
            score = seat.data.score
            if score in winner_dict:
                winner_dict[score].append(seat.player_name)
            else:
                winner_dict[score] = [seat.player_name]

        winner_score_list = sorted(winner_dict.keys(), reverse = True)

        winner_score = winner_score_list[0]
        self.send_scores()
        if len(winner_dict[winner_score]) == 1:
            self.channel.broadcast_cc(self.prefix + "^Y%s^~ is the winner!\n" % (winner_dict[winner_score][0]))
        else:
            self.channel.broadcast_cc(self.prefix + "These players tied for first: ^Y%s^~\n" % (", ".join(winner_dict[winner_score])))

    def show_scores(self, player):

        player.tell_cc("\nSCORES:\n\n")
        state = "yellow"
        for seat in self.seats:
            player_str = seat.player_name
            if state == "yellow":
                name_color_code = "^Y"
                score_color_code = "^C"
                state = "magenta"
            elif state == "magenta":
                name_color_code = "^M"
                score_color_code = "^G"
                state = "yellow"
            tell_string = "   ^R%s^~: %s%s^~, %s%s^~ point" % (seat, name_color_code, player_str, score_color_code, str(seat.data.score))
            if seat.data.score != 1:
                tell_string += "s"
            player.tell_cc(tell_string + "\n")
        player.tell_cc("\n")

    def send_scores(self):
        for player in self.channel.listeners:
            self.show_scores(player)

    def show_help(self, player):

        super(Set, self).show_help(player)
        player.tell_cc("\nSET SETUP PHASE:\n\n")
        player.tell_cc("                ^!columns^. <num>     Set the maximum columns to <num> (7-9).\n")
        player.tell_cc("                  ^!delay^. <sec>     Set the autodeal delay to <sec> secs.\n")
        player.tell_cc("                  ^!cards^. <num>     Set the maximum card count to <num>.\n")
        player.tell_cc("               ^!borders^. on|off     Set the borders on or off.\n")
        player.tell_cc("                        ^!start^.     Start the game.\n")
        player.tell_cc("\nSET PLAY:\n\n")
        player.tell_cc("                   ^!l1^., ^!l2^., ^!l3^.     Declare <l1>, <l2>, <l3> a set.\n")
        player.tell_cc("                       ^!scores^.     See the current scores.\n")
