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
        player.move(server.get_room("main"), custom_join = "^!%s^. has connected to the server.\n" % player.name)
        state.set_sub("prompt")

    elif substate == "prompt":

        player.tell("[%s] > " % player.location.name)
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
        player.location.notify_cc("^Y%s^~: %s^~\n" % (player.name, message))

        player.server.log.log("[%s] %s: %s" % (player.location.name, player.name, message))

    else:
        player.tell("You must actually say something worthwhile.\n")

def emote(message, player):

    if message:
        player.location.notify_cc("^Y%s^~ %s^~\n" % (player.name, message))

        player.server.log.log("[%s] %s %s" % (player.location.name, player.name, message))

    else:
        player.tell("You must actually emote something worthwhile.\n")

def move(room_name, player):

    if room_name:
        old_room_name = player.location.name
        player.move(player.server.get_room(room_name))

        player.server.log.log("%s moved from %s to %s." % (player.name, old_room_name, room_name))

    else:
        player.tell("You must give a room to move to.\n")

def print_help(player):

    player.tell("\n\nCOMMUNICATION:\n")
    player.tell_cc("^!'^.<message>, ^!\"^.<message>: Say <message>.\n")
    player.tell_cc("^!:^.<emote>, ^!-^.<emote>: Emote <emote>.\n")
    player.tell("\nINTERACTION:\n")
    player.tell_cc("^!move^. <room>, ^!m^. <room>: Move to room <room>.\n")
    player.tell("\nMETA:\n")
    player.tell_cc("^!help^., ^!h^.: Print this help.\n")
    player.tell_cc("^!quit^.: Disconnect.\n")

    player.server.log.log("%s asked for general help." % player.name)

def quit(player):

    player.client.deactivate()
    player.state = State("logout")

    player.server.log.log("%s logged out." % player.name)
