# Giles: ataxx.py
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

from giles.state import State
from giles.games.game import Game
from giles.games.seat import Seat
from giles.utils import demangle_move

MIN_SIZE = 5
MAX_SIZE = 26

RED = "red"
BLUE = "blue"
YELLOW = "yellow"
GREEN = "green"
PIT = "pit"

COLS = "abcdefghijklmnopqrstuvwxyz"

class Ataxx(Game):
    """An Ataxx game table implementation.  Invented in 1988 by Dave Crummack
    and Craig Galley.
    """

    def __init__(self, server, table_name):

        super(Ataxx, self).__init__(server, table_name)

        self.game_display_name = "Ataxx"
        self.game_name = "ataxx"
        self.seats = [
            Seat("Red"),
            Seat("Blue"),
        ]
        self.min_players = 2
        self.max_players = 2
        self.state = State("need_players")
        self.prefix = "(^RAtaxx^~): "
        self.log_prefix = "%s/%s: " % (self.table_display_name, self.game_display_name)

        # Ataxx-specific stuff.
        self.board = None
        self.printable_board = None
        self.sides = {}
        self.size = 7
        self.player_mode = 2
        self.turn = None
        self.last_r = None
        self.last_c = None

        self.init_seats()
        self.init_board()

    def init_board(self):

        self.board = []
        for r in range(self.size):
            self.board.append([None] * self.size)

        # Place starting pieces, depending on the number of players.
        bottom_left = BLUE
        bottom_right = RED
        if self.player_mode == 4:
            bottom_left = YELLOW
            bottom_right = GREEN

        self.board[0][0] = RED
        self.board[0][self.size - 1] = BLUE
        self.board[self.size - 1][0] = bottom_left
        self.board[self.size - 1][self.size - 1] = bottom_right

        self.update_printable_board()

    def init_seats(self):

        # If we're in 2-player mode, and there are 4 seats, delete the
        # extras.
        if self.player_mode == 2 and len(self.seats) == 4:
            del self.seats[2]
            del self.seats[2]

        self.sides = {}
        # Set the sides and data for players one and two.
        self.seats[0].data.side = RED
        self.seats[0].data.count = 2
        self.seats[0].data.resigned = False
        self.seats[1].data.side = BLUE
        self.seats[1].data.count = 2
        self.seats[1].data.resigned = False
        self.sides[RED] = self.seats[0]
        self.sides[BLUE] = self.seats[1]

        # If there are four players...
        if self.player_mode == 4:

            # ...and only two seats, create them.
            if len(self.seats) == 2:
                self.seats.append(Seat("Green"))
                self.seats.append(Seat("Yellow"))

            # Either way, set the sides and data.
            self.seats[2].data.side = GREEN
            self.seats[2].data.resigned = False
            self.sides[GREEN] = self.seats[2]
            self.seats[3].data.side = YELLOW
            self.seats[3].data.resigned = False
            self.sides[YELLOW] = self.seats[3]

            self.seats[0].data.count = 1
            self.seats[1].data.count = 1
            self.seats[2].data.count = 1
            self.seats[3].data.count = 1

    def change_player_mode(self, count):

        # Don't bother if it's the mode we're already in.
        if count == self.player_mode:
            return False

        # Don't bother if it's not a valid option either.
        if count != 2 and count != 4:
            return False

        # Okay.  Set values...
        self.player_mode = count
        self.min_players = count
        self.max_players = count

        # ...initialize the seats...
        self.init_seats()

        # ...and reinitialize the board.
        self.init_board()

    def update_printable_board(self):

        self.printable_board = []
        col_str = "    " + "".join([" " + COLS[i] for i in range(self.size)])
        self.printable_board.append(col_str + "\n")
        self.printable_board.append("   ^m.=" + "".join(["=="] * self.size) + ".^~\n")
        for r in range(self.size):
            this_str = "%2d ^m|^~ " % (r + 1)
            for c in range(self.size):
                if r == self.last_r and c == self.last_c:
                    this_str += "^I"
                loc = self.board[r][c]
                if loc == RED:
                    this_str += "^RR^~ "
                elif loc == BLUE:
                    this_str += "^BB^~ "
                elif loc == GREEN:
                    this_str += "^GG^~ "
                elif loc == YELLOW:
                    this_str += "^YY^~ "
                elif loc == PIT:
                    this_str += "^Ko^~ "
                else:
                    this_str += "^M.^~ "
            this_str += "^m|^~ %d" % (r + 1)
            self.printable_board.append(this_str + "\n")
        self.printable_board.append("   ^m`=" + "".join(["=="] * self.size) + "'^~\n")
        self.printable_board.append(col_str + "\n")

    def get_info_str(self):

        if not self.turn:
            return("The game has not yet started.\n")

        if self.turn == RED:
            name = self.seats[0].player_name
            turn_str = "^RRed^~"
        elif self.turn == BLUE:
            name = self.seats[1].player_name
            turn_str = "^BBlue^~"
        elif self.turn == GREEN:
            name = self.seats[2].player_name
            turn_str = "^GGreen^~"
        else:
            name = self.seats[3].player_name
            turn_str = "^YYellow^~"

        info_str = "It is %s's turn (%s).\n" % (name, turn_str)
        info_str += "^RRed^~: %d  ^BBlue^~: %d" % (self.seats[0].data.count, self.seats[1].data.count)
        if self.player_mode == 4:
            info_str += "  ^GGreen^~: %d  ^YYellow^~: %d" % (self.seats[2].data.count, self.seats[3].data.count)
        info_str += "\n"
        return(info_str)

    def show(self, player):

        if not self.printable_board:
            self.update_printable_board()
        for line in self.printable_board:
            player.tell_cc(line)
        player.tell_cc(self.get_info_str())

    def send_board(self):

        for listener in self.channel.listeners:
            self.show(listener)

    def is_valid(self, row, col):

        # Note that this does /not/ care about pits, just about the proper
        # ranges for coordinates.
        if row < 0 or row >= self.size or col < 0 or col >= self.size:
            return False
        return True

    def piece_has_move(self, row, col):

        # Returns whether or not a given piece has a potential move.

        # Bail on dud data.
        if not self.is_valid(row, col) or not self.board[row][col]:
            return False

        # Okay.  A piece can potentially move anywhere in a 5x5 area centered
        # on its location.
        found_move = False
        for r_d in range(-2, 3): # <--- why I hate range syntax.
            for c_d in range(-2, 3):
                if not found_move and (self.is_valid(row + r_d, col + c_d) and
                   not self.board[row + r_d][col + c_d]):
                    found_move = True

        # Return whether we found a move or not.
        return found_move

    def color_has_move(self, color):

        # Returns whether or not a given side has a potential move.

        # Bail immediately if green or yellow and we're in 2p mode.
        if self.player_mode == 2 and (color == YELLOW or color == GREEN):
            return False

        # Bail if this player has resigned.
        if ((color == RED and self.seats[0].data.resigned) or
           (color == BLUE and self.seats[1].data.resigned) or
           (color == GREEN and self.seats[2].data.resigned) or
           (color == YELLOW and self.seats[3].data.resigned)):
            return False

        # Okay.  Scan the board for pieces...
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == color and self.piece_has_move(r, c):
                    return True

        # Found no moves.  This color has no valid moves.
        return False

    def loc_to_str(self, row, col):
        return "%s%s" % (COLS[col], row + 1)

    def move(self, player, src_loc, dst_loc):

        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "You can't move; you're not playing!\n")
            return False

        if self.turn != seat.data.side:
            player.tell_cc(self.prefix + "You must wait for your turn to move.\n")
            return False

        if src_loc == dst_loc:
            player.tell_cc(self.prefix + "You can't make a non-move move!\n")
            return False

        src_c, src_r = src_loc
        dst_c, dst_r = dst_loc
        if not self.is_valid(src_c, src_r) or not self.is_valid(dst_c, dst_r):
            player.tell_cc(self.prefix + "Your move is out of bounds.\n")
            return False

        src_str = self.loc_to_str(src_r, src_c)
        dst_str = self.loc_to_str(dst_r, dst_c)

        # Do they have a piece at the source?
        color = seat.data.side
        if self.board[src_r][src_c] != color:
            player.tell_cc(self.prefix + "You don't have a piece at ^C%s^~.\n" % src_str)
            return False

        # Is the destination within range?
        if abs(src_r - dst_r) > 2 or abs(src_c - dst_c) > 2:
            player.tell_cc(self.prefix + "That move is too far.\n")
            return False

        # Is the destination empty?
        if self.board[dst_r][dst_c]:
            player.tell_cc(self.prefix + "^C%s^~ is already occupied.\n" % dst_str)
            return False

        # In range, to an empty cell.  It's a valid move.  Mark it.
        self.last_r = dst_r
        self.last_c = dst_c

        # Now, is it a split or a leap?
        if abs(src_r - dst_r) < 2 and abs(src_c - dst_c) < 2:
            
            # Split.  Add a new piece, increase the count.
            action_str = "^Mgrew^~ into"
            self.board[dst_r][dst_c] = color
            seat.data.count += 1
        else:

            # Leap.  Move the piece, don't increase the count.
            action_str = "^Cjumped^~ to"
            self.board[src_r][src_c] = None
            self.board[dst_r][dst_c] = color

        # Whichever action occurred, check all cells surrounding the
        # destination.  If they are opponents, transform them.
        change_count = 0
        change_str = ""
        for r_d in range(-1, 2):
            for c_d in range(-1, 2):
                if self.is_valid(dst_r + r_d, dst_c + c_d):
                    occupier = self.board[dst_r + r_d][dst_c + c_d]
                    if occupier and occupier != color and occupier != PIT:

                        # Another player.  Uh oh!  Flip it and decrement that
                        # player's count.
                        self.board[dst_r + r_d][dst_c + c_d] = color
                        seat.data.count += 1
                        self.sides[occupier].data.count -= 1
                        change_count += 1

        if change_count:
            change_str = ", ^!converting %d piece" % change_count
            if change_count != 1:
                change_str += "s"

        # Tell everyone what just happened.
        self.channel.broadcast_cc(self.prefix + "From ^c%s^~, %s %s ^C%s^~%s^~.\n" % (src_str, player, action_str, dst_str, change_str))

        self.update_printable_board()
        return True

    def toggle_pits(self, player, loc_list):

        # Undocumented bonus feature: handles multiple locations, but if
        # any of them are invalid, it'll bail halfway through.  Useful for
        # prepping a particular cool layout with a single cut-and-pasted
        # string, though.
        for loc in loc_list:
            
            col, row = loc

            # Bail if out of bounds.
            if not self.is_valid(row, col):
                player.tell_cc(self.prefix + "Pit out of bounds.\n")
                return

            # Bail if a starting piece is there.
            thing_there = self.board[row][col]
            if thing_there and not (thing_there == PIT):
                player.tell_cc(self.prefix + "Cannot put a pit on a starting piece.\n")
                return

            # Since it's a toggle, figure out what we're toggling to.
            if thing_there:
                new_thing = None
                action_str = "^cremoved^~"
            else:
                new_thing = PIT
                action_str = "^Cadded^~"

            # Tentative place the thing.
            self.board[row][col] = new_thing

            # Does it keep red or blue (which, in a 4p game, is equivalent to
            # all four players) from being able to make a move?  If so, it's
            # invalid.  Put the board back the way it was.
            if not self.color_has_move(RED) or not self.color_has_move(BLUE):
                player.tell_cc(self.prefix + "Players must have a valid move.\n")
                self.board[row][col] = thing_there
                return

            loc_list = [(row, col)]

            edge = self.size - 1

            # In either mode, we place another pit across the center line,
            # but not if that's the same location as the one we just placed
            # (on the center line on odd-sized boards).
            if (edge - row) != row:
                self.board[edge - row][col] = new_thing
                loc_list.append((edge - row, col))

                # Handle the 4p down-reflection if necessary.
                if self.player_mode == 4 and (edge - col) != col:
                    self.board[edge - row][edge - col] = new_thing
                    loc_list.append((edge - row, edge - col))

            # Handle the 4p right-reflection if necessary.
            if self.player_mode == 4 and (edge - col) != col:
                self.board[row][edge - col] = new_thing
                loc_list.append((row, edge - col))

            # Generate the list of locations.
            loc_str = ", ".join(["^C%s^~" % self.loc_to_str(x[0], x[1]) for x in loc_list])

            # Finally, send the string detailing what just happened.
            self.channel.broadcast_cc(self.prefix + "^Y%s^~ has %s a pit at: %s\n" % (player, action_str, loc_str))
            self.update_printable_board()

    def set_size(self, player, size_bits):

        if not size_bits.isdigit():
            player.tell_cc(self.prefix + "Invalid size command.\n")
            return

        size = int(size_bits)

        if size < MIN_SIZE or size > MAX_SIZE:
            player.tell_cc(self.prefix + "Size must be between %d and %d inclusive.\n" % (MIN_SIZE, MAX_SIZE))
            return

        # Valid!
        self.size = size
        self.channel.broadcast_cc(self.prefix + "^R%s^~ has set the board size to ^C%d^~.\n" % (player, size))
        self.init_board()
        self.update_printable_board()

    def set_player_mode(self, player, mode_bits):

        if not mode_bits.isdigit():
            player.tell_cc(self.prefix + "Invalid player mode command.\n")
            return

        mode = int(mode_bits)

        if mode != 2 and mode != 4:
            player.tell_cc(self.prefix + "This game only supports two or four players.\n")
            return

        elif mode == self.player_mode:
            player.tell_cc(self.prefix + "This table is already in that mode.\n")
            return

        else:
            self.change_player_mode(mode)
            self.channel.broadcast_cc(self.prefix + "^Y%s^~ has changed the game to ^C%d-player^~ mode.\n" % (player, mode))

    def resign(self, player):

        seat = self.get_seat_of_player(player)
        if not seat:
            player.tell_cc(self.prefix + "You can't resign; you're not playing!\n")
            return False

        if self.turn != seat.data.side:
            player.tell_cc(self.prefix + "You must wait for your turn to resign.\n")
            return False

        if seat.data.resigned:
            player.tell_cc(self.prefix + "You've already resigned.\n")
            return False

        # They've passed the tests and can resign.
        seat.data.resigned = True
        self.channel.broadcast_cc(self.prefix + "^R%s^~ is resigning from the game.\n" % player)

    def tick(self):

        # If all seats are full and the game is active, autostart.
        active_seats = [x for x in self.seats if x.player]
        if (self.state.get() == "need_players" and
           len(active_seats) == self.player_mode and self.active):
            self.state.set("playing")

            send_str = "^RRed^~: %s; ^BBlue^~: %s" % (self.seats[0].player_name, self.seats[1].player_name)
            if self.player_mode == 4:
                send_str += "; ^GGreen^~: %s; ^YYellow^~: %s" % (self.seats[2].player_name, self.seats[3].player_name)
            self.channel.broadcast_cc(self.prefix + send_str + "\n")
            self.turn = RED
            self.send_board()

    def handle(self, player, command_str):

        # Handle common commands.
        handled = self.handle_common_commands(player, command_str)

        if not handled:

            state = self.state.get()
            command_bits = command_str.split()
            primary = command_bits[0].lower()

            if state == "setup":

                if primary in ("size", "sz",):

                    if len(command_bits) == 2:
                        self.set_size(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid size command.\n")
                    handled = True

                elif primary in ("players", "player", "pl",):
                    if len(command_bits) == 2:
                        self.set_player_mode(player, command_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid player mode command.\n")
                    handled = True

                elif primary in ("pit", "hole",):
                    loc_list = demangle_move(command_bits[1:])
                    if loc_list:
                        self.toggle_pits(player, loc_list)
                    else:
                        player.tell_cc(self.prefix + "Invalid pit command.\n")
                    handled = True

                elif primary in ("ready", "done", "r", "d",):
                    self.channel.broadcast_cc(self.prefix + "The game is now looking for players.\n")
                    self.state.set("need_players")
                    handled = True

            elif state == "need_players":

                if primary in ("config", "setup", "conf",):

                    self.state.set("setup")
                    self.channel.broadcast_cc(self.prefix + "^R%s^~ has switched the game to setup mode.\n" % player)
                    handled = True

            elif state == "playing":

                made_move = False

                if primary in ("move", "play", "mv", "pl",):

                    move_bits = demangle_move(command_bits[1:])
                    if move_bits and len(move_bits) == 2:
                        made_move = self.move(player, move_bits[0], move_bits[1])
                    else:
                        player.tell_cc(self.prefix + "Invalid move command.\n")
                    handled = True

                elif primary in ("resign",):

                    self.resign(player)
                    made_move = True
                    handled = True

                if made_move:

                    # Did someone win?
                    winner = self.find_winner()
                    if winner:
                        self.resolve(winner)
                        self.finish()

                    else:
                        # Okay, well, let's see whose turn it is.  If it comes
                        # back around to us, the game is over anyway.
                        curr_turn = self.turn
                        done = False
                        while not done:
                            if self.turn == RED:
                                self.turn = BLUE
                            elif self.turn == BLUE:

                                # The only tough one; switch depending on mode.
                                if self.player_mode == 2:
                                    self.turn = RED
                                else:
                                    self.turn = GREEN
                            elif self.turn == GREEN:
                                self.turn = YELLOW
                            elif self.turn == YELLOW:
                                self.turn = RED

                            # Now see if this player even has a move.
                            if self.color_has_move(self.turn):
                                done = True
                            elif self.turn == curr_turn:

                                # If we've wrapped back around to the current
                                # turn, no one had a move.  Bail as well.
                                done = True

                        # Check to see if we're back at the mover.
                        if curr_turn == self.turn:

                            # No one had a valid move.  Game's over.
                            self.no_move_resolve()
                            self.finish()

                        else:

                            # Otherwise it's some other player's turn; game on.
                            self.send_board()

        if not handled:
            player.tell_cc(self.prefix + "Invalid command.\n")

    def find_winner(self):

        # Get the list of players that haven't resigned and have at least one
        # piece left on the board.  If that list is only one long, we have a
        # winner.  Otherwise, the game continues.
        live_players = [x for x in self.seats if ((not x.data.resigned) and
           x.data.count)]
        if len(live_players) == 1:
            return live_players[0].player_name
        else:
            return None

    def resolve(self, winner):
        self.send_board()
        self.channel.broadcast_cc(self.prefix + "^C%s^~ wins!\n" % winner)

    def no_move_resolve(self):

        self.send_board()

        # We look at the number of pieces each player has.  Highest wins.
        high_count = -1
        high_list = None
        for seat in self.seats:
            if seat.data.count > high_count:
                high_count = seat.data.count
                high_list = ["^C%s^~" % seat.player_name]
            elif seat.data.count == high_count:

                # Potential tie.
                high_list.append("^C%s^~" % seat.player_name)

        # If a single player has the highest count, they win; otherwise, tie.
        if len(high_list) == 1:
            self.channel.broadcast_cc(self.prefix + "%s wins with ^Y%d^~ pieces!\n" % (high_list[0], high_count))
        else:
            self.channel.broadcast_cc(self.prefix + "These players ^Rtied^~ for first with ^Y%d^~ pieces: %s\n" % (", ".join(high_list)))

    def show_help(self, player):

        super(Ataxx, self).show_help(player)
        player.tell_cc("\nATAXX SETUP PHASE:\n\n")
        player.tell_cc("          ^!setup^., ^!config^., ^!conf^.     Enter setup phase.\n")
        player.tell_cc("             ^!size^. <size>,  ^!sz^.     Set board to <size>.\n")
        player.tell_cc("             ^!players^. 2|4,  ^!pl^.     Set number of players.\n")
        player.tell_cc("                     ^!pit^. <ln>     Add or remove pit at <ln>.\n")
        player.tell_cc("            ^!ready^., ^!done^., ^!r^., ^!d^.     End setup phase.\n")
        player.tell_cc("\nATAXX PLAY:\n\n")
        player.tell_cc("          ^!move^. <ln> <ln2>, ^!mv^.     Move from <ln> to <ln2> (letter number).\n")
        player.tell_cc("                       ^!resign^.     Resign.\n")

