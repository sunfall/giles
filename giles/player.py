# Giles: player.py
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

from giles.utils import name_is_valid, MAX_NAME_LENGTH

class Player(object):
    """A player on Giles.  Tracks their name, current location, and other
    relevant stateful bits.
    """

    def __init__(self, client, server, name="Guest", location=None, state=None):
        self.client = client
        self.server = server
        self.display_name = name
        self.name = name.lower()
        self.location = location
        self.config = {
            "channel_aliases": {},
            "player_aliases": {},
            "table_aliases": {},

            "last_channel": None,
            "last_table": None,

            "timestamps": False,
        }
        self.state = None

    def __repr__(self):
        return self.display_name

    def set_name(self, name):

        name = name.strip()
        lower_name = name.lower()

        # Fail if:
        # - The name is already in use;
        # - The name has invalid characters;
        # - The name is too long.
        for other in self.server.players:
            if other.name == lower_name and self != other:
                self.tell("That name is already in use.\n")
                self.server.log.log("%s attempted to change name to in-use name %s." % (self.name, other.name))
                return False

        if len(name) > MAX_NAME_LENGTH:
            self.tell("Names must be less than %d characters long.\n" % MAX_NAME_LENGTH)
            self.server.log.log("%s attempted to change to too-long name %s." % (self.name, name))
            return False

        if not name_is_valid(name):
            self.tell("Names must be alphanumeric and start with a letter.\n")
            self.server.log.log("%s attempted to change to non-valid name %s." % (self.name, name))
            return False

        # Okay, the name looks legitimate.
        self.server.log.log("%s is now known as %s." % (self, name))
        self.display_name = name
        self.name = lower_name
        self.tell("Your name is now %s.\n" % name)
        return True

    def move(self, location, custom_join = None, custom_part = None):
        if location:

            if self.location:
                if custom_part:
                    self.location.remove_player(self, custom_part)
                else:
                    self.location.remove_player(self)

            self.location = location
            if custom_join:
                self.location.add_player(self, custom_join)
            else:
                self.location.add_player(self)

    def tell(self, msg):
        if self.config["timestamps"]:
            msg = "(%s) %s" % (self.server.timestamp, msg)
        self.client.send(msg)

    def tell_cc(self, msg):
        if self.config["timestamps"]:
            msg = "(^C%s^~) %s" % (self.server.timestamp, msg)
        self.client.send_cc(msg)

    def prompt(self):
        if self.server.admin_manager.is_admin(self):
            loc_color_code = "^R"
            ts_color_code = "^R"
        else:
            loc_color_code = "^!"
            ts_color_code = "^C"
        msg = "[%s%s^~] > " % (loc_color_code, self.location.name)
        if self.config["timestamps"]:
            msg = "(%s%s^~) %s" % (ts_color_code, self.server.timestamp, msg)
        self.client.send_prompt_cc(msg)
