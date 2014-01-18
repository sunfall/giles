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

import sys
import traceback

class AdminManager(object):

    def __init__(self, server, password = None):
        self.server = server
        self.password = password
        self.admins = []

        # We make a custom private channel that skips the channel_manager
        # infrastructure for admin logging.
        self.channel = self.server.channel_manager.has_channel("Admin")

    def is_admin(self, player):
        return player in self.admins

    def log(self, message):
        self.server.log.log("[ADMIN] %s" % message)
        self.channel.broadcast_cc("[^RADMIN^~] %s\n" % message)

    def off(self, player):

        self.admins.remove(player)
        self.channel.disconnect(player)
        player.tell_cc("You no longer have administrative privileges.\n")
        self.log("%s de-adminned." % player)

    def on(self, player, pw_str):

        if self.is_admin(player):
            player.tell_cc("You're already an active admin.\n")
            self.log("%s attempted to admin but already was one." % player)
            return

        if pw_str != self.password:
            player.tell_cc("Invalid admin password.\n")
            self.log("%s attempted to admin but used the wrong password." % player)
            return

        self.admins.append(player)
        self.channel.connect(player)
        player.tell_cc("You now have administrative privileges.  Use them wisely.\n")
        self.log("%s adminned." % player)

    def game(self, player, game_bits):

        primary = game_bits[0].lower()
        other_bits = game_bits[1:]
        handled = False

        if primary in ("reload_all",):
            self.server.game_master.reload_all_games()
            player.tell_cc("You have reloaded all game modules.\n")
            self.log("%s reloaded all games." % player)
            handled = True

        elif primary in ("reload_conf",):
            self.server.game_master.unload_all_games()
            self.server.game_master.load_games_from_conf()
            player.tell_cc("You have unloaded all games and reloaded from the conf file.\n")
            self.log("%s unloaded all games and reloaded from the conf file." % player)
            handled = True

        elif primary in ("reload",):
            if len(other_bits) == 1:
                game_key = other_bits[0].lower()
                if self.server.game_master.is_game(game_key):
                    success = self.server.game_master.reload_game(game_key)
                    if success:
                        player.tell_cc("Game %s reloaded successfully.\n" % game_key)
                        self.log("%s reloaded game %s." % (player, game_key))
                    else:
                        player.tell_cc("Game %s failed to reload.\n" % game_key)
                        self.log("%s attempted to reload game %s but the reload failed." % (player, game_key))
                else:
                    player.tell_cc("No such game %s to reload.\n" % game_key)
                    self.log("%s attempted to reload nonexistent game %s." % (player, game_key))
            else:
                player.tell_cc("Invalid admin game reload command.\n")
                self.log("%s attempted an invalid admin game reload." % player)
            handled = True

        elif primary in ("unload_all",):
            self.server.game_master.unload_all_games()
            player.tell_cc("You have unloaded all game modules.\n")
            self.log("%s unloaded all games." % player)
            handled = True

        elif primary in ("unload",):
            if len(other_bits) == 1:
                game_key = other_bits[0].lower()
                if self.server.game_master.is_game(game_key):
                    self.server.game_master.unload_game(game_key)
                    player.tell_cc("Game %s unloaded successfully.\n" % game_key)
                    self.log("%s unloaded game %s." % (player, game_key))
                else:
                    player.tell_cc("No such game %s to unload.\n" % game_key)
                    self.log("%s attempted to unload nonexistent game %s." % (player, game_key))
            else:
                player.tell_cc("Invalid admin game unload command.\n")
                self.log("%s attempted an invalid admin game unload." % player)
            handled = True

        elif primary in ("load",):
            if len(other_bits) == 2:
                game_key = other_bits[0].lower()
                class_path = other_bits[1]
                if not self.server.game_master.is_game(game_key):
                    success = self.server.game_master.load_game(game_key, class_path)
                    if success:
                        player.tell_cc("Game %s loaded successfully.\n" % game_key)
                        self.log("%s loaded game %s (%s)." % (player, game_key, class_path))
                    else:
                        player.tell_cc("Game %s failed to load.  Check the log.\n" % game_key)
                        self.log("%s attempted to load game %s (%s) but the load failed." % (player, game_key, class_path))
                else:
                    player.tell_cc("Another game is already loaded with that key.\n")
                    self.log("%s attempted to load game %s (%s) but the key existed already." % (player, game_key, class_path))
            else:
                player.tell_cc("Invalid admin game load command.\n")
                self.log("%s attempted an invalid admin game load." % player)
            handled = True

        if not handled:
            player.tell_cc("Invalid admin game command.\n")
            self.log("%s attempted an invalid admin game command." % player)

    def reload_admin(self):

        try:

            # First, reload the module itself.
            admin_mod = reload(sys.modules["giles.admin_manager"])

            # Now, replace the server's admin_manager with the new one.
            self.server.admin_manager = admin_mod.AdminManager(self.server, self.password)

            # Preload the admins.
            self.server.admin_manager.admins = self.admins
            return True

        except Exception as e:
            self.log("Failed to reload admin module.\nException: %s\n%s" % (e, traceback.format_exc()))
            return False

    def reload_channel_manager(self):

        try:

            # Snag the active channels first, since we'll need to drop
            # them back into the new channel manager.

            channels = self.server.channel_manager.channels

            # Reload the module.
            channel_manager_mod = reload(sys.modules["giles.channel_manager"])

            # Replace the server's channel manager with the new one.
            self.server.channel_manager = channel_manager_mod.ChannelManager(self.server)

            # Drop in the existing channels.
            self.server.channel_manager.channels = channels

            return True

        except Exception as e:
            self.log("Failed to reload channel manager module.\nException: %s\n%s" % (e, traceback.format_exc()))
            return False

    def reload_chat(self):

        try:

            # Reload the chat module itself.
            chat_mod = reload(sys.modules["giles.chat"])

            # Now, replace the server's chat with the new one.
            self.server.chat = chat_mod.Chat(self.server)

            return True

        except Exception as e:
            self.log("Failed to reload chat module.\nException: %s\n%s" % (e, traceback.format_exc()))
            return False

    def reload_login(self):

        try:

            # Reload the login module itself.
            login_mod = reload(sys.modules["giles.login"])

            # Now, replace the server's login module with the new one.
            self.server.login = login_mod.Login(self.server)

            return True

        except Exception as e:
            self.log("Failed to reload login module.\nException: %s\n%s" % (e, traceback.format_exc()))
            return False

    def reload_by_name(self, player, module_name):

        try:
            reload(sys.modules[module_name])
            player.tell_cc("Module %s reloaded-by-name successfully.\n" % module_name)
            self.log("%s reloaded-by-name module %s." % (player, module_name))

        except Exception as e:
            player.tell_cc("Module %s failed to reload-by-name.\n" % module_name)
            self.log("Failed to reload-by-name module %s.\nException: %s\n%s" % (module_name, e, traceback.format_exc()))

    def reload(self, player, reload_bits):

        primary = reload_bits[0].lower()
        other_bits = reload_bits[1:]
        handled = False

        if primary in ("admin",):
            success = self.reload_admin()
            if success:
                player.tell_cc("Admin module reloaded successfully.\n")
                self.log("%s reloaded the admin module." % player)
            else:
                player.tell_cc("Admin module failed to reload.  Check the log.\n")
                self.log("%s attempted to reload the admin module but the reload failed." % player)
            handled = True
        elif primary in ("chat",):
            success = self.reload_chat()
            if success:
                player.tell_cc("Chat module reloaded successfully.\n")
                self.log("%s reloaded the chat module." % player)
            else:
                player.tell_cc("Chat module failed to reload.  Check the log.\n")
                self.log("%s attempted to reload the chat module but the reload failed." % player)
            handled = True
        elif primary in ("channel_manager",):
            success = self.reload_channel_manager()
            if success:
                player.tell_cc("Channel manager module reloaded successfully.\n")
                self.log("%s reloaded the channel manager module." % player)
            else:
                player.tell_cc("Channel manager module failed to reload.  Check the log.\n")
                self.log("%s attempted to reload the channel manager module but the reload failed." % player)
            handled = True
        elif primary in ("login",):
            success = self.reload_login()
            if success:
                player.tell_cc("Login module reloaded successfully.\n")
                self.log("%s reloaded the login module." % player)
            else:
                player.tell_cc("Login module failed to reload.  Check the log.\n")
                self.log("%s attempted to reload the login module but the reload failed." % player)
            handled = True

        if not handled:
            player.tell_cc("Invalid admin reload command.\n")
            self.log("%s attempted an invalid admin reload command." % player)

    def handle(self, player, admin_str):

        if not admin_str or type(admin_str) != str or not len(admin_str):
            player.tell_cc("Invalid admin command.\n")
            self.log("%s attempted a blank admin command." % player)
            return

        admin_bits = admin_str.split()
        primary = admin_bits[0].lower()
        other_bits = admin_bits[1:]
        handled = False

        if primary in ("on",):
            if len(other_bits) != 1:
                player.tell_cc("Invalid admin on command.\n")
                self.log("%s attempted an invalid admin on command." % player)
            else:
                self.on(player, other_bits[0])
            handled = True

        else:

            # For all other admin commands, you must actually BE an admin.
            if player not in self.admins:
                player.tell_cc("You're not an admin!\n")
                self.log("%s attempted an admin command but is not an admin." % player)
                return

            if primary in ("off",):
                self.off(player)
                handled = True

            elif primary in ("game",):
                if not len(other_bits):
                    player.tell_cc("Invalid admin game command.\n")
                    self.log("%s attempted an invalid admin game command." % player)
                else:
                    self.game(player, other_bits)
                handled = True

            elif primary in ("reload",):
                if not len(other_bits):
                    player.tell_cc("Invalid admin reload command.\n")
                    self.log("%s attempted an invalid admin reload command." % player)
                else:
                    self.reload(player, other_bits)
                handled = True

            elif primary in ("reload_by_name",):
                if len(other_bits) != 1:
                    player.tell_cc("Invalid admin reload_by_name command.\n")
                    self.log("%s attempted an invalid admin reload_by_name command." % player)
                else:
                    self.reload_by_name(player, other_bits[0])
                handled = True

        if not handled:
            player.tell_cc("Invalid admin command.\n")
            self.log("%s attempted an invalid admin command." % player)

    def remove_player(self, player):
        if self.is_admin(player):
            self.admins.remove(player)
            self.channel.disconnect(player)
