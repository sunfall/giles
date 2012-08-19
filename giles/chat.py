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

        # The player just entered chat.  Welcome them, place them, subscribe
        # them to the global channel.
        player.tell("\nWelcome to chat.  For help, type 'help' (without the quotes).\n\n")
        player.move(server.get_space("main"), custom_join = "^!%s^. has connected to the server.\n" % player.display_name)
        list_players_in_space(player.location, player)
        server.channel_manager.connect(player, "global")
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
    # immediately after.  These are says, emotes, and broadcasts to
    # channels.  Everything else is either a token of its own or will
    # be tokenized further by another handler.

    if command[0] in ('"', "'"):
        
        # It's a say.  Handle it that way.
        say(command[1:].strip(), player)

    elif command[0] in ('-', ','):

        # It's an emote.
        emote(command[1:].strip(), player)

    elif command[0] in (':',):

        # It's a send to a channel.
        send(command[1:].strip(), player)

    elif command[0] in ('/'):

        # It's a command for a game table.
        table(command[1:].strip(), player)

    else:
        # All right, now we're into actual commands.  Split into components,
        # lowercase the first one, and pass the rest off as necessary.

        command_elements = command.split()
        primary = command_elements[0].lower()

        if len(command_elements) > 1:
            secondary = " ".join(command_elements[1:])
        else:
            secondary = None

        if primary in ('say',):
            say(secondary, player)

        elif primary in ('emote', 'me', 'em'):
            emote(secondary, player)

        elif primary in ('connect', 'co'):
            connect(secondary, player)

        elif primary in ('disconnect', 'dc'):
            disconnect(secondary, player)

        elif primary in ('send',):
            send(secondary, player)

        elif primary in ('tell', 't'):
            tell(secondary, player)

        elif primary in ('move', 'm'):
            move(secondary, player)

        elif primary in ('who', 'w'):
            who(player)

        elif primary in ('game', 'g'):
            game(secondary, player)

        elif primary in ('table', 'tab'):
            table(secondary, player)

        elif primary in ('roll', 'r'):
            roll(secondary, player, secret = False)

        elif primary in ('sroll', 'sr'):
            roll(secondary, player, secret = True)

        elif primary in ('set',):
            config(secondary, player)

        elif primary in ('become',):
            become(secondary, player)

        elif primary in ('help', 'h', '?'):
            print_help(player)

        elif primary in ('quit',):
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

def connect(connect_str, player):

    # If the string has a single element, it's a channel with no key.
    if connect_str:

        connect_bits = connect_str.split()
        if len(connect_bits) == 1:
            player.server.channel_manager.connect(player, connect_bits[0])
        else:
            player.server.channel_manager.connect(player, connect_bits[0], " ".join(connect_bits[1:]))

    else:
        player.tell("You must give a channel to connect to.\n")

def disconnect(disconnect_str, player):

    if disconnect_str:

        player.server.channel_manager.disconnect(player, disconnect_str)

    else:
        player.tell("You must give a channel to disconnect from.\n")

def send(send_str, player):

    # Need, at a minimum, two bits: the channel and the message.
    if send_str:

        send_str_bits = send_str.split()
        if len(send_str_bits) < 2:
            player.tell("You must give both a channel and a message.\n")
            return

        success = player.server.channel_manager.send(player, " ".join(send_str_bits[1:]),
           send_str_bits[0])
        if not success:
            player.tell("Failed to send.\n")

def tell(payload, player):

    # Need, at a minimum, two bits: the target and the message.
    if payload:
        elements = payload.split()
        if len(elements) < 2:
            player.tell("You must give both a target and a message.\n")
            return
        target = elements[0]
        if target[-1] == ',':
            # Strip comma from target; allows "Tell bob, y helo there"
            target = target[:-1]

        other = player.server.get_player(target)
        if other == player:
            player.tell("Talking to yourself?\n")
        elif other:
            msg = " ".join(elements[1:])
            other.tell_cc("^R%s^~ tells you: %s\n" % (player.display_name, msg))
            player.tell_cc("You tell ^R%s^~: %s\n" % (other.display_name, msg))
            player.server.log.log("%s tells %s: %s" % (player.display_name, other.display_name, msg))
        else:
            player.tell_cc("Player ^R%s^~ not found.\n" % target)
    else:
        player.tell("You must give a player and a message.\n")

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

def list_players_not_in_space(location, player):

    player.tell_cc("Players elsewhere:\n")

    list_str = "   "
    state = "bold"
    for other in player.server.players:
        if other.location != location:
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

def who(player):

    player.tell("\n")
    list_players_in_space(player.location, player)
    list_players_not_in_space(player.location, player)

def roll(roll_string, player, secret = False):

    if roll_string:
        player.server.die_roller.roll(roll_string, player, secret)

        player.server.log.log("%s rolled %s." % (player.display_name, roll_string))

    else:
        player.tell("Invalid roll.\n")

def game(game_string, player):

    valid = False
    if game_string:

        string_bits = game_string.split()
        primary = string_bits[0].lower()
        if len(string_bits) == 1:

            # Gotta be 'list'.
            if primary in ('list', 'ls', 'l'):
                player.server.game_master.list_games(player)
                valid = True
        elif len(string_bits) == 3:

            # First is new, second is game, third is table.
            if primary in ('new', 'n'):
                valid = player.server.game_master.new_table(player,
                   string_bits[1], string_bits[2])

        elif len(string_bits) == 4:

            # New, scope, game, table.
            scope = string_bits[1].lower()
            have_scope = True

            if scope in ('private', 'p'):
                scope = "private"
            elif scope in ('global', 'g'):
                scope = "global"
            elif scope in ('local', 'l'):
                scope = "local"
            else:
                have_scope = False

            if have_scope and primary in ('new', 'n'):
                valid = player.server.game_master.new_table(player,
                    string_bits[2], string_bits[3], scope)

    else:
        player.server.game_master.list_games(player)
        valid = True

    if not valid:
        player.tell("Invalid game command.\n")

def table(table_string, player):

    valid = False
    if table_string:

        # There must be at least two bits: the table name and a command.
        string_bits = table_string.split()
        if len(string_bits) > 1:
            player.server.game_master.handle(player, string_bits[0],
               " ".join(string_bits[1:]))
            valid = True

    if not valid:
        player.tell("Invalid table command.\n")

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
    player.tell_cc("                 ^!-^.<emote>, ^!,^.      Emote <emote>.\n")
    player.tell_cc("  ^!tell^. <player> <message>, ^!t^.      Tell <player> <message> privately.\n")
    player.tell_cc(" ^!connect^. <channel> [<k>], ^!co^.      Connect to <channel> [with key <k>].\n")
    player.tell_cc("    ^!disconnect^. <channel>, ^!dc^.      Disconnect from <channel>.\n")
    player.tell_cc(" ^!send^. <channel> <message>, ^!:^.      Send <channel> <message>.\n")
    player.tell("\nWORLD INTERACTION:\n")
    player.tell_cc("             ^!move^. <space>, ^!m^.      Move to space <space>.\n")
    player.tell_cc("                      ^!who^., ^!w^.      List players in your space/elsewhere.\n")
    player.tell("\nGAMING:\n")
    player.tell_cc("                ^!game^. list, ^!g^.      List available games.\n")
    player.tell_cc(" ^!game^. new <game> <tabnam>, ^!g^.      New table of <game> named <tabnam>.\n")
    player.tell_cc("      ^!table^. <table> <cmd>, ^!/^.      Send <table> <cmd>.\n")
    player.tell_cc("   ^!roll^. [X]d<Y>[+/-/*<Z>], ^!r^.      Roll [X] Y-sided/F/% dice [modified].\n")
    player.tell_cc(" ^!sroll^. [X]d<Y>[+/-/*<Z>], ^!sr^.      Secret roll.\n")
    player.tell("\nCONFIGURATION:\n")
    player.tell_cc("^!set timestamp^. on|off, ^!set ts^.      Enable/disable timestamps.\n")
    player.tell("\nMETA:\n")
    player.tell_cc("            ^!become^. <newname>      Set name to <newname>.\n")
    player.tell_cc("                     ^!help^., ^!?^.      Print this help.\n")
    player.tell_cc("                        ^!quit^.      Disconnect.\n")

    player.server.log.log("%s asked for general help." % player.display_name)

def quit(player):

    player.client.deactivate()
    player.state = State("logout")

    player.server.log.log("%s logged out." % player.display_name)
