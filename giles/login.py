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
    client = player.client
    server = player.server

    substate = state.get_sub()

    if substate == None:

        # Just logged in.  Print the helpful banner.
        client.send("Welcome to %s!\n" % server.name)

        state.set_sub("entry_prompt")

    elif substate == "entry_prompt":

        # Ask them for their name and set our state to waiting for an entry.
        client.send("\n\nPlease enter a name: ")

        state.set_sub("name_entry")

    elif substate == "name_entry":

        name = client.get_command()
        if name:

            # We got a name.  Check it against all the other names logged in.
            name = name.strip()
            is_valid = True
            for player in server.players:
                if player.name == name:
                    is_valid = False
                    other_player = player

            if is_valid:

                # Set it, welcome them, and move 'em to chat.
                player.name = name
                client.send("\nWelcome, %s!\n" % name)
                player.state = State("chat")

                server.log.log("%s logged in from %s." % (player.name, client.addrport()))

            else:
                client.send("\nI'm sorry; that name is already taken.\n")
                state.set_sub("entry_prompt")

                server.log.log("%s attempted to use duplicate name %s (already connected from %s)." % (client.addrport(), name, other_player.client.addrport()))
