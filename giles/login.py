# Giles: login.py
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

import player
from state import State

def handle(player):

    state = player.state
    server = player.server

    substate = state.get_sub()

    if substate == None:

        # Just logged in.  Print the helpful banner.
        player.tell("Welcome to %s!\n" % server.name)

        state.set_sub("entry_prompt")

    elif substate == "entry_prompt":

        # Ask them for their name and set our state to waiting for an entry.
        player.tell("\n\nPlease enter a name: ")

        state.set_sub("name_entry")

    elif substate == "name_entry":

        name = player.client.get_command()
        if name:

            # We got a name.  Check it against all the other names logged in.
            name = name.strip()
            is_valid = True
            for other in server.players:
                if other.name == name:
                    is_valid = False
                    player.tell("\nI'm sorry; that name is already taken.\n")

                    other_player = player
                    server.log.log("%s attempted to use duplicate name %s (already connected from %s)." % (player.client.addrport(), name, other_player.client.addrport()))

            # Also make sure it has no carets.  Should do more rigourous
            # checking at some point.
            if "^" in name:
                is_valid = False
                player.tell("\nI'm sorry; that name has invalid characters.\n")
                server.log.log("%s attempted to use invalid name %s." % (player.client.addrport(), name))

            if is_valid:

                # Set it, welcome them, and move 'em to chat.
                player.name = name
                player.tell("\nWelcome, %s!\n" % name)
                player.state = State("chat")

                server.log.log("%s logged in from %s." % (player.name, player.client.addrport()))

            else:
                state.set_sub("entry_prompt")
