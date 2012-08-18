# Giles: chat.py
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

from state import State

def handle(player):

    state = player.state
    server = player.server

    substate = state.get_sub()

    if substate == None:

        # The player just entered chat.  Welcome them and place them.
        player.tell("\nWelcome to chat.  For help, type 'help' (without the quotes).\n\n")
        player.move(server.get_space("main"), custom_join = "^!%s^. has connected to the server.\n" % player.display_name)
        list_players_in_space(player.location, player)
        state.set_sub("prompt")

    elif substate == "prompt":

        player.tell_cc("[^!%s^.] > " % player.location.name)
        state.set_sub("input")

    elif substate == "input":

        command = player.client.get_command()

        if command:

            # Wipe out extraneous whitespace.
            command = command.strip()

            if len(command):
                # We got what might be a legitimate command.  Parse and manage it.
                parse(command, player)

            else:

                # Just whitespace.  Reprompt.
                state.set_sub("prompt")

def parse(command, player):

    did_quit = False

    # First, handle the weird cases: starting characters with text
    # immediately after.  These are says and emotes.  Everything
    # else is either a token of its own or will be tokenized further
    # by another handler.

    if command[0] == '"' or command[0] == "'":
        
        # It's a say.  Handle it that way.
        say(command[1:].strip(), player)

    elif command[0] == ":" or command[0] == "-":

        # It's an emote.
        emote(command[1:].strip(), player)

    else:
        # All right, now we're into actual commands.  Split into components,
        # lowercase the first one, and pass the rest off as necessary.

        command_elements = command.split()
        primary = command_elements[0].lower()

        if len(command_elements) > 1:
            secondary = " ".join(command_elements[1:])
        else:
            secondary = None

        if primary == "say":
            say(secondary, player)

        elif primary == "emote" or primary == "me":
            emote(secondary, player)

        elif primary == "m" or primary == "move":
            move(secondary, player)

        elif primary == "w" or primary == "who":
            who(secondary, player)

        elif primary == "r" or primary == "roll":
            roll(secondary, player, secret = False)

        elif primary == "sr" or primary == "sroll":
            roll(secondary, player, secret = True)

        elif primary == "set":
            config(secondary, player)

        elif primary == "become":
            become(secondary, player)

        elif primary == "h" or primary == "help":
            print_help(player)

        elif primary == "quit":
            quit(player)
            did_quit = True

        else:
            player.tell_cc("Unknown command.  Type ^!help^. for help.\n")

    # Unless the player quit, we'll want to go back to the prompt.
    if not did_quit:
        player.state.set_sub("prompt")

def say(message, player):

    if message:
        player.location.notify_cc("^Y%s^~: %s^~\n" % (player.display_name, message))

        player.server.log.log("[%s] %s: %s" % (player.location.name, player.display_name, message))

    else:
        player.tell("You must actually say something worthwhile.\n")

def emote(message, player):

    if message:
        player.location.notify_cc("^Y%s^~ %s^~\n" % (player.display_name, message))

        player.server.log.log("[%s] %s %s" % (player.location.name, player.display_name, message))

    else:
        player.tell("You must actually emote something worthwhile.\n")

def list_players_in_space(location, player):

    player.tell_cc("Players in ^Y%s^~:\n" % location.name)

    list_str = "   "
    state = "bold"
    for other in location.players:
        if state == "bold":
            list_str += "^!%s^. " % other.display_name
            state = "regular"
        elif state == "regular":
            list_str += "%s " % other.display_name
            state = "bold"

    player.tell_cc(list_str + "\n\n")

def move(space_name, player):

    if space_name:
        old_space_name = player.location.name
        player.move(player.server.get_space(space_name))
        list_players_in_space(player.location, player)

        player.server.log.log("%s moved from %s to %s." % (player.display_name, old_space_name, space_name))

    else:
        player.tell("You must give a space to move to.\n")

def who(space_name, player):

    if not space_name:
        space_name = player.location.name

    list_players_in_space(player.server.get_space(space_name), player)

def roll(roll_string, player, secret = False):

    if roll_string:
        player.server.die_roller.roll(roll_string, player, secret)

        player.server.log.log("%s rolled %s." % (player.display_name, roll_string))

    else:
        player.tell("Invalid roll.\n")

def config(config_string, player):

    player.server.configurator.handle(config_string, player)

def become(new_name, player):

    did_become = False
    if new_name:
        old_display_name = player.display_name
        did_become = player.set_name(new_name)
        if did_become:
            player.location.notify_cc("^Y%s^~ has become ^Y%s^~.\n" % (old_display_name, player.display_name))

    if not did_become:
        player.tell("Failed to become.\n")

def print_help(player):

    player.tell("\n\nCOMMUNICATION:\n")
    player.tell_cc("               ^!'^.<message>, ^!\"^.      Say <message>.\n")
    player.tell_cc("                 ^!:^.<emote>, ^!-^.      Emote <emote>.\n")
    player.tell("\nWORLD INTERACTION:\n")
    player.tell_cc("             ^!move^. <space>, ^!m^.      Move to space <space>.\n")
    player.tell_cc("              ^!who^. [space], ^!w^.      List players in your space/<space>.\n")
    player.tell("\nGAMING:\n")
    player.tell_cc("   ^!roll^. [X]d<Y>[+/-/*<Z>], ^!r^.      Roll [X] Y-sided/F/% dice [modified].\n")
    player.tell_cc(" ^!sroll^. [X]d<Y>[+/-/*<Z>], ^!sr^.      Secret roll.\n")
    player.tell("\nCONFIGURATION:\n")
    player.tell_cc("^!set timestamp^. on|off, ^!set ts^.      Enable/disable timestamps.\n")
    player.tell("\nMETA:\n")
    player.tell_cc("            ^!become^. <newname>      Set name to <newname>.\n")
    player.tell_cc("                     ^!help^., ^!h^.      Print this help.\n")
    player.tell_cc("                        ^!quit^.      Disconnect.\n")

    player.server.log.log("%s asked for general help." % player.display_name)

def quit(player):

    player.client.deactivate()
    player.state = State("logout")

    player.server.log.log("%s logged out." % player.display_name)
