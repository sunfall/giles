# Giles: admin_manager.py
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


class AdminManager(object):

    def __init__(self, server, password = None):
        self.server = server
        self.password = password
        self.admins = []

    def is_admin(self, player):
        return player in self.admins

    def off(self, player):

        if not self.is_admin(player):
            player.tell_cc("You're not an active admin anyway!\n")
            self.server.log.log("%s attempted to de-admin but wasn't an admin." % player)
        else:
            self.admins.remove(player)
            player.tell_cc("You no longer have administrative privileges.\n")
            self.server.log.log("%s de-adminned." % player)

    def on(self, player, pw_str):

        if self.is_admin(player):
            player.tell_cc("You're already an active admin.\n")
            self.server.log.log("%s attempted to admin but already was one." % player)
            return

        if pw_str != self.password:
            player.tell_cc("Invalid admin password.\n")
            self.server.log.log("%s attempted to admin but used the wrong password." % player)
            return

        self.admins.append(player)
        player.tell_cc("You now have administrative privileges.  Use them wisely.\n")
        self.server.log.log("%s adminned." % player)

    def handle(self, player, admin_str):

        if not admin_str or type(admin_str) != str or not len(admin_str):
            player.tell_cc("Invalid admin command.\n")
            self.server.log.log("%s attempted a blank admin command." % player)
            return

        admin_bits = admin_str.split()
        primary = admin_bits[0].lower()
        other_bits = admin_bits[1:]
        handled = False

        if primary in ("on",):
            if len(other_bits) != 1:
                player.tell_cc("Invalid admin on command.\n")
                self.server.log.log("%s attempted an invalid admin on command." % player)
            else:
                self.on(player, other_bits[0])
            handled = True
        elif primary in ("off",):
            self.off(player)
            handled = True

        if not handled:
            player.tell_cc("Invalid admin command.\n")
            self.server.log.log("%s attempted an invalid admin command." % player)

    def remove_player(self, player):
        if self.is_admin(player):
            self.admins.remove(player)
