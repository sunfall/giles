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

from giles.state import State
from giles.utils import name_is_valid

import traceback

CHANNEL = "channel"
PLAYER = "player"
TABLE = "table"

class Chat(object):

    def __init__(self, server):

        self.server = server

    def handle(self, player):

        state = player.state

        substate = state.get_sub()

        if substate == None:

            # The player just entered chat.  Welcome them, place them, subscribe
            # them to the global channel.
            player.tell("\nWelcome to chat.  For help, type 'help' (without the quotes).\n\n")
            player.move(self.server.get_space("main"),
                        custom_join="^!%s^. has connected to the server.\n" % player)
            self.list_players_in_space(player.location, player)
            self.server.channel_manager.connect(player, "global")

            # Turn timestamps on for them.
            player.config["timestamps"] = True
            state.set_sub("prompt")

        elif substate == "prompt":

            player.prompt()
            state.set_sub("input")

        elif substate == "input":

            command = player.client.get_command()

            if command:

                # Wipe out extraneous whitespace.
                command = command.strip()

                if len(command):
                    # We got what might be a legitimate command.  Parse and
                    # manage it.  First, see if the player is focused or not.
                    # If they are, we direct everything that doesn't begin
                    # with a '/' to their table; otherwise we send it to the
                    # standard parser.  If they're not focused, we just punt
                    # them to the standard parser to begin with.

                    focus_table = player.config["focus_table"]
                    if focus_table:
                        if command[0] in ('/',):

                            # Make sure the subcommand is actually something.
                            possible_command = command[1:].strip()
                            if len(possible_command):
                                self.parse(command[1:], player)
                            else:
                                state.set_sub("prompt")

                        else:
                            self.table("%s %s" % (focus_table, command), player)

                            # We have to reprompt here.
                            state.set_sub("prompt")

                    else:
                        self.parse(command, player)

                else:

                    # Just whitespace.  Reprompt.
                    state.set_sub("prompt")

    def parse(self, command, player):

        did_quit = False

        # First, handle the weird cases: starting characters with text
        # immediately after.  These are shortcuts for longer commands.
        # Everything else is either a token of its own or will be
        # tokenized further by another handler.

        if command[0] in ('"', "'"):
            # It's a say.  Handle it that way.
            self.say(command[1:].strip(), player)

        elif command[0] in ('-', ','):
            # It's an emote.
            self.emote(command[1:].strip(), player)

        elif command[0] in (':',):
            # It's a send to a channel.
            self.send(command[1:].strip(), player)

        elif command[0] in (';',):
            # It's a send to the last channel.
            self.last_send(command[1:].strip(), player)

        elif command[0] in ('>',):
            # It's a tell.
            self.tell(command[1:].strip(), player)

        elif command[0] in ('/',):
            # It's a command for a game table.
            self.table(command[1:].strip(), player)

        elif command[0] in ('\\',):
            # It's a command for the last game table.
            self.last_table(command[1:].strip(), player)

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
                self.say(secondary, player)

            elif primary in ('emote', 'me', 'em'):
                self.emote(secondary, player)

            elif primary in ('connect', 'co'):
                self.connect(secondary, player)

            elif primary in ('disconnect', 'dc'):
                self.disconnect(secondary, player)

            elif primary in ('channels', 'chan'):
                self.channels(player)

            elif primary in ('invite', 'inv'):
                self.invite(secondary, player)

            elif primary in ('send',):
                self.send(secondary, player)

            elif primary in ('tell', 't'):
                self.tell(secondary, player)

            elif primary in ('move', 'm'):
                self.move(secondary, player)

            elif primary in ('who', 'w'):
                self.who(player)

            elif primary in ('game', 'games', 'g'):
                self.game(secondary, player)

            elif primary in ('table', 'tab'):
                self.table(secondary, player)

            elif primary in ('roll', 'r'):
                self.roll(secondary, player, secret=False)

            elif primary in ('sroll', 'sr'):
                self.roll(secondary, player, secret=True)

            elif primary in ('set',):
                self.config(secondary, player)

            elif primary in ('alias',):
                self.alias(secondary, player)

            elif primary in ('become',):
                self.become(secondary, player)

            elif primary in ('help', 'h', '?'):
                self.show_help(player)

            elif primary in ('admin',):
                self.admin(secondary, player)

            elif primary in ('focus', 'f'):
                self.focus(secondary, player)

            elif primary in ('unfocus', 'defocus', 'unf'):
                self.unfocus(player)

            elif primary in ('uptime',):
                self.uptime(player)

            elif primary in ('quit', 'exit',):
                self.quit(player)
                did_quit = True

            else:
                player.tell_cc("Unknown command.  Type ^!help^. for help.\n")

        # Unless the player quit, we'll want to go back to the prompt.
        if not did_quit:
            player.state.set_sub("prompt")

    def say(self, message, player):

        if message:
            player.location.notify_cc("^Y%s^~: %s^~\n" % (player, message))

            self.server.log.log("[%s] %s: %s" % (player.location.name, player, message))

        else:
            player.tell("You must actually say something worthwhile.\n")

    def emote(self, message, player):

        if message:
            player.location.notify_cc("^Y%s^~ %s^~\n" % (player, message))

            self.server.log.log("[%s] %s %s" % (player.location.name, player, message))

        else:
            player.tell("You must actually emote something worthwhile.\n")

    def connect(self, connect_str, player):

        # If the string has a single element, it's a channel with no key.
        if connect_str:

            connect_bits = connect_str.split()

            # De-alias; bail if it fails.
            channel_name = self.de_alias(player, connect_bits[0], CHANNEL)
            if not channel_name:
                return

            if len(connect_bits) == 1:
                did_connect = self.server.channel_manager.connect(player, channel_name)
            else:
                did_connect = self.server.channel_manager.connect(player, channel_name, " ".join(connect_bits[1:]))

            if did_connect:
                player.config["last_channel"] = channel_name
            else:
                player.tell("Failed to connect to channel.\n")

        else:
            player.tell("You must give a channel to connect to.\n")

    def disconnect(self, disconnect_str, player):

        if disconnect_str:

            # De-alias; bail if it fails.
            channel_name = self.de_alias(player, disconnect_str, CHANNEL)
            if not channel_name:
                return

            self.server.channel_manager.disconnect(player, channel_name)

        else:
            player.tell("You must give a channel to disconnect from.\n")

    def channels(self, player):

        channel_list = self.server.channel_manager.list_player_channel_names(player)
        if channel_list:
            player.tell("Channels you're connected to:\n\n")
            for channel in channel_list:
                player.tell_cc("   ^G%s^~\n" % channel)

        else:
            player.tell("You are not connected to any channels.\n")

    def invite(self, payload, player):
        # Need, at a minimum, two bits: the invitee and the channel.
        if payload:
            elements = payload.split()
            if len(elements) < 2:
                player.tell("You must give a player and a channel.\n")
                return
            target = elements[0]
            intended_channel = elements[1]
            invite_channel = self.server.channel_manager.has_channel(intended_channel)
            invite_player = self.server.get_player(target)

            if not invite_channel:
                player.tell_cc("^!%s^~ doesn't even exist.\n" % (intended_channel))
                self.server.log.log("%s invited to nonextant channel :%s" %
                        (player, intended_channel))
            elif not invite_player:
                player.tell_cc("^!%s^~ does not appear to be connected.\n" %
                        (invite_player))
                self.server.log.log("Non-extant player %s invited to %s by %s" %
                        (target, intended_channel, player))
            elif not invite_channel.is_connected(player):
                player.tell("You can't invite to a channel you're not in.\n")
                self.server.log.log("%s wasn't in %s but tried to invite %s there anyhow" %
                        (player, invite_channel, invite_player))
            elif invite_channel.is_connected(invite_player):
                player.tell_cc("^!%s^~ is already in that channel.\n" %
                        (invite_player))
                self.server.log.log("%s invited %s to %s, where ey already was." %
                        (player, invite_player, invite_channel))
            elif invite_player == player:
                player.tell("Sending an invitation to yourself would be a waste of 47 cents.\n")
                self.server.log.log("%s invited emself to %s." %
                        (player, invite_channel))
            else:
                # Okay, the player is on the channel, and the other player is online and not already in the channel.
                msg_first = ("You invite ^!%s^~ to :^!%s^~.\n" %
                        (invite_player, invite_channel))
                msg_second = ("You have been invited to :^!%s^~ by ^!%s^~.\n" %
                        (invite_channel, invite_player))
                msg_second += ("To join, type: ^!connect %s " %
                        (invite_channel))
                # Let's see whether the channel's keyed or not.
                if invite_channel.key:
                    msg_second += invite_channel.key
                msg_second += "^~\n"
                msg_log = ("%s invites %s to :%s" %
                        (player, invite_player, invite_channel))

                player.tell_cc(msg_first)
                invite_player.tell_cc(msg_second)
                self.server.log.log(msg_log)
        else:
            player.tell("You must give a player and a channel.\n")

    def send(self, send_str, player):

        # Need, at a minimum, two bits: the channel and the message.
        if send_str:

            send_str_bits = send_str.split()
            if len(send_str_bits) < 2:
                player.tell("You must give both a channel and a message.\n")
                return

            # De-alias the channel name; bail if it fails.
            channel_name = self.de_alias(player, send_str_bits[0], CHANNEL)
            if not channel_name:
                return

            success = self.server.channel_manager.send(player, " ".join(send_str_bits[1:]),
               channel_name)
            if not success:
                player.tell("Failed to send.\n")
            else:
                player.config["last_channel"] = channel_name

    def last_send(self, send_str, player):

        channel_name = player.config["last_channel"]
        if not channel_name:
            player.tell("You must have a last channel to use this command.\n")
            return

        to_send = " ".join(send_str.split())
        if to_send:
            self.server.channel_manager.send(player, to_send, channel_name)
        else:
            player.tell("You must actually send some text.\n")

    def tell(self, payload, player):

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

            # De-alias the target.  Return if dealiasing failed.
            target = self.de_alias(player, target, PLAYER)
            if not target:
                return

            other = self.server.get_player(target)
            if other == player:
                player.tell("Talking to yourself?\n")
            elif other:
                msg = " ".join(elements[1:])
                other.tell_cc("^R%s^~ tells you: %s\n" % (player, msg))
                player.tell_cc("You tell ^R%s^~: %s\n" % (other, msg))
                self.server.log.log("%s tells %s: %s" % (player, other, msg))
            else:
                player.tell_cc("Player ^R%s^~ not found.\n" % target)
        else:
            player.tell("You must give a player and a message.\n")

    def list_players_in_space(self, location, player):

        player.tell_cc("Players in ^Y%s^~:\n" % location.name)

        list_str = "   "
        state = "bold"
        for other in location.players:
            if state == "bold":
                list_str += "^!%s^. " % other
                state = "regular"
            elif state == "regular":
                list_str += "%s " % other
                state = "bold"

        player.tell_cc(list_str + "\n\n")

    def list_players_not_in_space(self, location, player):

        player.tell_cc("Players elsewhere:\n")

        list_str = "   "
        state = "bold"
        for other in self.server.players:
            if other.location != location:
                if state == "bold":
                    list_str += "^!%s^. " % other
                    state = "regular"
                elif state == "regular":
                    list_str += "%s " % other
                    state = "bold"

        player.tell_cc(list_str + "\n\n")

    def move(self, space_name, player):

        if space_name:
            old_space_name = player.location.name
            player.move(self.server.get_space(space_name))
            self.list_players_in_space(player.location, player)

            self.server.log.log("%s moved from %s to %s." % (player, old_space_name, space_name))

        else:
            player.tell("You must give a space to move to.\n")

    def who(self, player):

        player.tell("\n")
        self.list_players_in_space(player.location, player)
        self.list_players_not_in_space(player.location, player)

    def roll(self, roll_string, player, secret=False):

        if roll_string:
            self.server.die_roller.roll(roll_string, player, secret)

            self.server.log.log("%s rolled %s." % (player, roll_string))

        else:
            player.tell("Invalid roll.\n")

    # List of shortcuts for "list" and "new".
    _GAME_LIST_COMMANDS = ('list', 'ls', 'l')
    _GAME_NEW_COMMANDS = ('new', 'n')

    def game(self, game_string, player):

        valid = False
        made_new_table = False
        if game_string:

            string_bits = game_string.split()
            primary = string_bits[0].lower()
            if len(string_bits) == 1:

                if primary in self._GAME_LIST_COMMANDS:
                    self.server.game_master.list_games(player)
                    valid = True

                elif primary in ('active', 'ac', 'a'):
                    self.server.game_master.list_tables(player, show_private=False)
                    valid = True

            elif len(string_bits) == 2:

                # Possibly a request to list games with a tag.
                if primary in self._GAME_LIST_COMMANDS:
                    tag = string_bits[1].lower()
                    self.server.game_master.list_games(player, tag)
                    valid = True

            elif len(string_bits) == 3:

                # First is new, second is game, third is table.
                if primary in self._GAME_NEW_COMMANDS:

                    # De-alias the table; bail if it fails.
                    table_name = self.de_alias(player, string_bits[2], TABLE)
                    if not table_name:
                        return

                    valid = self.server.game_master.new_table(player,
                       string_bits[1], table_name)
                    if valid:
                        made_new_table = True

            elif len(string_bits) == 4 or len(string_bits) == 5:

                # New, [private], scope, game, table.
                # Assume we didn't get a private command...
                valid_so_far = True
                private = False
                offset = 0

                if len(string_bits) == 5:
                    # Ah, we did.  Set the private flag and move the scope over.
                    if string_bits[1].lower() in ('private', 'pr', 'p'):
                        private = True
                        offset = 1
                        valid_so_far = True
                    else:
                        valid_so_far = False

                if valid_so_far:
                    scope = string_bits[1 + offset].lower()
                    if scope in ('personal', 'p'):
                        scope = "personal"
                    elif scope in ('global', 'g'):
                        if private:
                            # A private global game?  Makes no sense.
                            valid_so_far = False
                        scope = "global"
                    elif scope in ('local', 'l'):
                        scope = "local"
                    else:
                        valid_so_far = False

                if valid_so_far and primary in self._GAME_NEW_COMMANDS:

                    # De-alias the table; bail if it fails.
                    table_name = self.de_alias(player, string_bits[3 + offset], TABLE)
                    if not table_name:
                        return

                    valid = self.server.game_master.new_table(player,
                        string_bits[2 + offset], table_name, scope, private)
                    if valid:
                        made_new_table = True

        else:
            self.server.game_master.list_games(player)
            valid = True

        if not valid:
            player.tell("Invalid game command.\n")

        # If we made a new table, set the player's last table and channel.
        if made_new_table:
            player.config["last_table"] = table_name
            player.config["last_channel"] = table_name
            player.tell_cc("Your last table and channel have been set to ^R%s^~.\n" % table_name)

    def table(self, table_string, player):

        valid = False
        if table_string:

            # There must be at least two bits: the table name and a command.
            string_bits = table_string.split()
            if len(string_bits) > 1:

                # De-alias the table name and bail if it fails.
                table_name = self.de_alias(player, string_bits[0], TABLE)
                if not table_name:
                    return

                self.server.game_master.handle(player, table_name,
                   " ".join(string_bits[1:]))
                player.config["last_table"] = table_name
                valid = True

        if not valid:
            player.tell("Invalid table command.\n")

    def last_table(self, command_string, player):

        table_name = player.config["last_table"]
        if not table_name:
            player.tell("You must have a last table to use this command.\n")
            return

        if not command_string:
            player.tell("Invalid table command.\n")
            return

        # Pass it on.
        self.server.game_master.handle(player, table_name,
           " ".join(command_string.split()))

    def focus(self, table_name, player):

        if not table_name:
            player.tell("You must have a table to focus on.\n")
            return

        table = self.server.game_master.get_table(table_name)
        if table:
            player.config["focus_table"] = table.table_name
            player.tell_cc("You are now focused on ^G%s^~.\n" % table.table_name)
        else:
            player.tell("You cannot focus on a nonexistent table.\n")

    def unfocus(self, player):

        if not player.config["focus_table"]:
            player.tell("You are already unfocused.\n")
            return

        player.config["focus_table"] = None
        player.tell("You are no longer focused on a table.\n")

    def config(self, config_string, player):

        try:
            self.server.configurator.handle(config_string, player)
        except Exception as e:
            player.tell("Something went horribly awry with configuration.\n")
            self.server.log.log("Configuration failed: %s" % e)

    def de_alias(self, player, alias_str, alias_type):

        # If it's not a number, we don't even bother de-aliasing.  Just return the
        # string.
        if not alias_str.isdigit():
            return alias_str

        # If it's an invalid type, return None; otherwise snag the dictionary
        # we'll be checking against.
        if alias_type == CHANNEL:
            alias_dict = player.config["channel_aliases"]
        elif alias_type == PLAYER:
            alias_dict = player.config["player_aliases"]
        elif alias_type == TABLE:
            alias_dict = player.config["table_aliases"]
        else:
            return None

        # Now, if it /is/ a number, is it in the dictionary?
        alias_num = int(alias_str)

        if alias_num in alias_dict:
            return alias_dict[alias_num]

        player.tell_cc("^R%d^~ is not aliased!\n" % alias_num)
        return None

    def alias(self, alias_string, player):

        if not alias_string:
            player.tell("Invalid alias command.\n")
            return False

        alias_bits = alias_string.split()

        # Bail if we didn't get three bits.
        if len(alias_bits) != 3:
            player.tell("Invalid alias command.\n")
            return False

        # Extract the values from the bits.
        a_type = alias_bits[0]
        a_name = alias_bits[1]
        a_num = alias_bits[2]

        # Bail if the name isn't valid.
        if not name_is_valid(a_name):
            player.tell("Cannot alias an invalid name.\n")
            return False

        # Bail if the number isn't a number or is > 99.  Convert otherwise.
        if not a_num.isdigit():
            player.tell("Cannot alias to a non-number.\n")
            return False

        a_num = int(a_num)
        if a_num > 99:
            player.tell("Cannot alias to a number greater than 99.\n")
            return False

        # Get the type that we're aliasing.  If it's invalid, we'll bail.
        if a_type in ("channel", "chan", "ch", "c",):
            alias_dict = player.config["channel_aliases"]
            type_str = "channel"
        elif a_type in ("player", "pl", "p",):
            alias_dict = player.config["player_aliases"]
            type_str = "player"
        elif a_type in ("table", "tab", "ta", "t",):
            alias_dict = player.config["table_aliases"]
            type_str = "table"
        else:
            player.tell("Invalid type to alias to.  Must be one of channel, player, or table.\n")
            return False

        # Is this already an alias?
        addendum_str = ""
        if a_num in alias_dict:
            addendum_str = ", ^Rreplacing^~ ^c%s^~" % alias_dict[a_num]

        # Either way, add the new alias.
        alias_dict[a_num] = a_name
        player.tell_cc("^C%d^~ is now a ^M%s^~ alias for ^G%s^~%s.\n" % (a_num, type_str, a_name, addendum_str))
        return True

    def become(self, new_name, player):

        did_become = False
        if new_name:
            old_display_name = player.display_name
            did_become = player.set_name(new_name)
            if did_become:
                player.location.notify_cc("^Y%s^~ has become ^Y%s^~.\n" % (old_display_name, player))

        if not did_become:
            player.tell("Failed to become.\n")

    def uptime(self, player):

        startup_datetime = self.server.get_startup_datetime()
        uptime = self.server.get_uptime()
        player.tell_cc("This server was started on ^G%s^~ at ^G%s^~.\n" % (startup_datetime.strftime("%Y-%m-%d"), startup_datetime.strftime("%X")))
        player.tell_cc("It has been up for ^Y%0.2d:%0.2d:%0.2d^~.\n" % (uptime.days, uptime.seconds / 60, uptime.seconds % 60))

    def show_help(self, player):

        player.tell("\n\nCOMMUNICATION:\n")
        player.tell_cc("               ^!'^.<message>, ^!\"^.      Say <message>.\n")
        player.tell_cc("                 ^!-^.<emote>, ^!,^.      Emote <emote>.\n")
        player.tell_cc("   ^!tell^. <player> <msg>, ^!t^., ^!>^.      Tell <player> <msg> privately.\n")
        player.tell_cc(" ^!connect^. <channel> [<k>], ^!co^.      Connect to <channel> [with key <k>].\n")
        player.tell_cc("    ^!disconnect^. <channel>, ^!dc^.      Disconnect from <channel>.\n")
        player.tell_cc("   ^!invite^. <player> <channel>      Invite <player> to <channel>.\n")
        player.tell_cc(" ^!send^. <channel> <message>, ^!:^.      Send <channel> <message>.\n")
        player.tell_cc("                  ^!;^.<message>      Send the last channel used <message>.\n")
        player.tell("\nWORLD INTERACTION:\n")
        player.tell_cc("             ^!move^. <space>, ^!m^.      Move to space <space>.\n")
        player.tell_cc("                      ^!who^., ^!w^.      List players in your space/elsewhere.\n")
        player.tell("\nGAMING:\n")
        player.tell_cc("             ^!game^. list, ^!g^. ls      List available games.\n")
        player.tell_cc("           ^!game^. active, ^!g^. ac      List active tables.\n")
        player.tell_cc(" ^!game^. new <game> <tablename>      New table of <game> named <tablename>.\n")
        player.tell_cc("      ^!table^. <table> <cmd>, ^!/^.      Send <table> <cmd>.\n")
        player.tell_cc("                      ^!\\^.<cmd>      Send the last table played <cmd>.\n")
        player.tell_cc("   ^!roll^. [X]d<Y>[+/-/*<Z>], ^!r^.      Roll [X] Y-sided/F/% dice [modified].\n")
        player.tell_cc(" ^!sroll^. [X]d<Y>[+/-/*<Z>], ^!sr^.      Secret roll.\n")
        player.tell("\nCONFIGURATION:\n")
        player.tell_cc("^!set timestamp^. on|off, ^!set ts^.      Enable/disable timestamps.\n")
        player.tell_cc("     ^!set color^. on|off, ^!set c^.      Enable/disable color.\n")
        player.tell("\nMETA:\n")
        player.tell_cc("            ^!become^. <newname>      Set name to <newname>.\n")
        player.tell_cc("   ^!alias^. <type> <name> <num>      Alias table/channel <name> to <num>.\n")
        player.tell_cc("                      ^!uptime^.      See server start time and uptime.\n")
        player.tell_cc("                     ^!help^., ^!?^.      Print this help.\n")
        player.tell_cc("                        ^!quit^.      Disconnect.\n")

        self.server.log.log("%s asked for general help." % player)

    def admin(self, admin_str, player):

        try:
            self.server.admin_manager.handle(player, admin_str)
        except Exception as e:
            player.tell_cc("The admin manager crashed.  ^RAlert an admin^~.\n")
            self.server.log.log("Admin manager crashed.\n" + traceback.format_exc())

    def quit(self, player):

        player.client.deactivate()
        player.state = State("logout")

        self.server.log.log("%s logged out." % player)
