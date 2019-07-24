# Giles: die_roller.py
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

class DieRoller(object):

    def __init__(self):
        pass

    def roll(self, message, player, secret=False):

        # Die rolls are of the format XdY, possibly with a +- bit after.
        # They may also be secret, in which case we just message the
        # player rather than everyone in the space.

        if message:

            # Lowercase it to make parsing easier.  Remove all spaces.
            chomp_str = "".join(message.lower().split())

            is_valid = True
            count = 0
            got_count = False
            die_type = None
            die_sides = 0
            modifier_type = None
            modifier_value = 0

            # We're gonna use a FSM, but no need for substates.

            state = "count"

            while state != "done":

                if len(chomp_str) == 0:
                    # Done.
                    state = "done"
                    continue

                curr_char = chomp_str[0]
                chomp_str = chomp_str[1:]

                if state == "count":
                    if curr_char.isdigit():
                        count *= 10
                        count += int(curr_char)
                        got_count = True
                    elif curr_char == "d":
                        # Done with the count, next is type.
                        state = "type"
                    else:
                        # Huh?  Invalid.
                        is_valid = False
                        state = "done"

                elif state == "type":
                    if curr_char.isdigit():
                        # Ah, a multisided die.  Replace digit and change state.
                        chomp_str = curr_char + chomp_str
                        state = "die_sides"
                    elif curr_char == "f":
                        # Fudge dice; no modifiers allowed.
                        die_type = "Fudge"
                        state = "done"
                    elif curr_char == "%":
                        # d100.  No need to chomp sides; go straight to mods.
                        die_sides = 100
                        state = "subtype"
                    else:
                        # Huh?  Invalid.
                        is_valid = False
                        state = "done"

                elif state == "subtype":
                    # Just need to check some final details...
                    if die_sides == 100:
                        if curr_char == "%":
                            # So, you want a d1000 instead?
                            die_sides = 1000
                            state = "modifier_type"
                        else:
                            # Not meant for us, so replace and change state
                            chomp_str = curr_char + chomp_str
                            state = "modifier_type"

                elif state == "die_sides":
                    if curr_char.isdigit():
                        die_sides *= 10
                        die_sides += int(curr_char)
                    else:
                        # Pop this character back on and see if it's a mod.
                        chomp_str = curr_char + chomp_str
                        state = "modifier_type"

                elif state == "modifier_type":
                    if curr_char == "+":
                        modifier_type = "+"
                        state = "modifier_value"
                    elif curr_char == "-":
                        modifier_type = "-"
                        state = "modifier_value"
                    elif curr_char == "*":
                        modifier_type = "*"
                        state = "modifier_value"
                    else:
                        # Huh?  Unknown modifier.
                        is_valid = False
                        state = "done"

                elif state == "modifier_value":
                    if curr_char.isdigit():
                        modifier_value *= 10
                        modifier_value += int(curr_char)
                    else:
                        # Huh?  Should be nothing but numbers here.
                        is_valid = False
                        state = "done"

            # If we didn't get a count of dice, but we also didn't
            # get a number, that's just 1dX.  (i.e. d6) Otherwise someone
            # actually put zeroes, and that's not valid.
            if count == 0:
                if not got_count:
                    count = 1
                else:
                    is_valid = False

            # If we already know it's invalid, bail.  Also bail:
            # - if we have a modifier type but not a value
            # - if count is > 100
            # - if sides or abs(modifier) are > 1000
            # - if die side count is 0 and we don't have a die type.
            if ((not is_valid) or
               (modifier_type and not modifier_value) or
               (count > 100) or (die_sides > 1000) or (abs(modifier_value) > 1000)
               or (not die_sides and not die_type)):
                player.tell("Invalid die roll.\n")

            else:
                # Okay, we have a legit roll.  Let's do it.
                die_list = []
                roll_result = 0

                for die in range(count):
                    if die_type == "Fudge":
                        val = random.randint(-1, 1)
                        roll_result += val
                        if val == -1:
                            die_list.append("-")
                        elif val == 1:
                            die_list.append("+")
                        else:
                            die_list.append("o")
                    else:
                        val = random.randint(1, die_sides)
                        roll_result += val
                        die_list.append(str(val))

                # Dice are rolled.  Add modifiers, if any.
                if modifier_type:
                    if modifier_type == "+":
                        roll_result += modifier_value
                    elif modifier_type == "-":
                        roll_result -= modifier_value
                    elif modifier_type == "*":
                        roll_result *= modifier_value

                # Whew.  Done!  Send it to the right people.
                if secret:
                    player.tell_cc("You rolled ^G%s^~ in ^Csecret^~; the result is ^Y%s^~. (^M%s^~)\n" % (message, str(roll_result), " ".join(die_list)))
                else:
                    player.location.notify_cc("^Y%s^~ rolled ^G%s^~; the result is ^Y%s^~. (^R%s^~)\n" % (player, message, str(roll_result), " ".join(die_list)))
