# Giles: configurator.py
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

from utils import booleanize

class Configurator(object):
    """The overarching configurator.  Allows players to change configurations
    on themselves, spaces, etc.
    """

    def __init__(self):
        pass

    def handle(self, config_string, player):

        is_valid = True
        if not config_string:

            # No actual config.  Definitely not valid.
            is_valid = False

        else:

            # All right.  Configurations are things like:
            # - ts on
            # - chan xxx yyy
            # so they can be broken up into their elements and handled
            # further by other parsers if necessary.  But one absolute
            # is that they all have at least two elements after 'set',
            # as otherwise you don't have a thing you're setting.
            config_bits = config_string.lower().split()

            if len(config_bits) < 2:
                is_valid = False
            else:
                primary = config_bits[0]

                if primary in ('timestamp', 'ts'):
                    if len(config_bits) != 2:
                        is_valid = False
                    else:
                        is_valid = self.set_timestamp(config_bits[1], player)

        if not is_valid:
            player.tell("Invalid configuration.\n")
            player.server.log.log("%s attempted invalid configuration %s." % (player.display_name, config_string))

    def set_timestamp(self, msg, player):

        # Returns whether or not it was successful, not the value set.

        action = booleanize(msg)
        if not action:
            return False

        if action > 0:
            player.config["timestamps"] = True
            player.server.log.log("%s turned timestamps on." % player.display_name)
        else:
            player.config["timestamps"] = False
            player.server.log.log("%s turned timestamps off." % player.display_name)

        return True
