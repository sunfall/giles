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
    client = player.client
    server = player.server

    substate = state.get_sub()

    if substate == None:

        # The player just entered chat.  Welcome them and place them.
        client.send("\nWelcome to chat.  For help, type 'help' (without the quotes).\n\n")
        player.location = "main"
        state.set_sub("prompt")

    elif substate == "prompt":

        client.send("> ")
        state.set_sub("input")

    elif substate == "input":

        command = client.get_command()

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

        if primary == "say":
            if len(command_elements) > 1:
                # Rejoin say.  Yes, this doesn't have extra internal
                # whitespace.  Tough.  I don't feel like writing a
                # full parser right now.  It's undocumented anyhow.
                say(" ".join(command_elements[1:]), player)
            else:
                # Blank message.
                say("", player)

        elif primary == "emote" or primary == "me":
            if len(command_elements) > 1:
                # Rejoin a la say.
                emote(" ".join(command_elements[1:]), player)
            else:
                # Blank emote.
                emote("", player)

        elif primary == "h" or primary == "help":
            print_help(player)

        elif primary == "quit":
            quit(player)
            did_quit = True

    # Unless the player quit, we'll want to go back to the prompt.
    if not did_quit:
        player.state.set_sub("prompt")

def say(message, player):

    if(len(message)):
        for other in player.server.players:
            if other.location == player.location:
                other.client.send_cc("^Y%s^~: %s\n" % (player.name, message))

        player.server.log.log("%s says %s in %s" % (player.name, message, player.location))

    else:
        player.send("You must actually say something worthwhile.\n")

def emote(message, player):

    if(len(message)):
        for other in player.server.players:
            if other.location == player.location:
                other.client.send_cc("^Y%s^~ %s\n" % (player.name, message))

        player.server.log.log("%s emotes %s in %s" % (player.name, message, player.location))

    else:
        player.emote("You must actually emote something worthwhile.\n")

def print_help(player):

    client = player.client
    client.send("\n\nHELP:\n\n")
    client.send_cc("^!'^.<message>, ^!\"^.<message>: Say <message>.\n")
    client.send_cc("^!:^.<emote>, ^!-^.<emote>: Emote <emote>.\n")
    client.send("\n")
    client.send_cc("^!help^., ^!h^.: Print this help.\n")
    client.send_cc("^!quit^.: Disconnect.\n")

    player.server.log.log("%s asked for general help." % player.name)

def quit(player):

    player.client.deactivate()
    player.state = State("logout")

    player.server.log.log("%s logged out." % player.name)
