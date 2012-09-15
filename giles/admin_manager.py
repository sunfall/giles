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

    def game(self, player, game_bits):

        primary = game_bits[0].lower()
        other_bits = game_bits[1:]
        handled = False

        if primary in ("reload_all",):
            self.server.game_master.reload_all_games()
            player.tell_cc("You have reloaded all game modules.\n")
            self.server.log.log("%s reloaded all games." % player)
            handled = True

        elif primary in ("reload_conf",):
            self.server.game_master.unload_all_games()
            self.server.game_master.load_games_from_conf()
            player.tell_cc("You have unloaded all games and reloaded from the conf file.\n")
            self.server.log.log("%s unloaded all games and reloaded from the conf file." % player)
            handled = True

        elif primary in ("reload",):
            if len(other_bits) == 1:
                game_key = other_bits[0].lower()
                if self.server.game_master.is_game(game_key):
                    success = self.server.game_master.reload_game(game_key)
                    if success:
                        player.tell_cc("Game %s reloaded successfully.\n" % game_key)
                        self.server.log.log("%s reloaded game %s." % (player, game_key))
                    else:
                        player.tell_cc("Game %s failed to reload.\n" % game_key)
                        self.server.log.log("%s attempted to reload game %s but the reload failed." % (player, game_key))
                else:
                    player.tell_cc("No such game %s to reload.\n" % game_key)
                    self.server.log.log("%s attempted to reload nonexistent game %s." % (player, game_key))
            else:
                player.tell_cc("Invalid admin game reload command.\n")
                self.server.log.log("%s attempted an invalid admin game reload." % player)
            handled = True

        elif primary in ("unload_all",):
            self.server.game_master.unload_all_games()
            player.tell_cc("You have unloaded all game modules.\n")
            self.server.log.log("%s unloaded all games." % player)
            handled = True

        elif primary in ("unload",):
            if len(other_bits) == 1:
                game_key = other_bits[0].lower()
                if self.server.game_master.is_game(game_key):
                    self.server.game_master.unload_game(game_key)
                    player.tell_cc("Game %s unloaded successfully.\n" % game_key)
                    self.server.log.log("%s unloaded game %s." % (player, game_key))
                else:
                    player.tell_cc("No such game %s to unload.\n" % game_key)
                    self.server.log.log("%s attempted to unload nonexistent game %s." % (player, game_key))
            else:
                player.tell_cc("Invalid admin game unload command.\n")
                self.server.log.log("%s attempted an invalid admin game unload." % player)
            handled = True

        if not handled:
            player.tell_cc("Invalid admin game command.\n")
            self.server.log.log("%s attempted an invalid admin game command." % player)

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

        else:

            # For all other admin commands, you must actually BE an admin.
            if player not in self.admins:
                player.tell_cc("You're not an admin!\n")
                self.server.log.log("%s attempted an admin command but is not an admin." % player)
                return

            if primary in ("off",):
                self.off(player)
                handled = True

            elif primary in ("game",):
                if not len(other_bits):
                    player.tell_cc("Invalid admin game command.\n")
                    self.server.log.log("%s attempted an invalid admin game command." % player)
                else:
                    self.game(player, other_bits)
                handled = True


        if not handled:
            player.tell_cc("Invalid admin command.\n")
            self.server.log.log("%s attempted an invalid admin command." % player)

    def remove_player(self, player):
        if self.is_admin(player):
            self.admins.remove(player)
