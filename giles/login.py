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

            # Attempt to set their name to the one they requested.
            is_valid = player.set_name(name)

            if is_valid:

                # Welcome them and move them to chat.
                player.tell("\nWelcome, %s!\n" % name)
                player.state = State("chat")

                server.log.log("%s logged in from %s." % (player.name, player.client.addrport()))

            else:
                state.set_sub("entry_prompt")
