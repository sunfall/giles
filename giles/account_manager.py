# Giles: account_manager.py
# Copyright 2014 Phil Bordelon
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

import os.path
import sqlite3
import sys

# This is hokey, but until I have a better path-handling infrastructure
# it'll do.
ACCOUNT_PATH = os.path.join(sys.path[0], 'data', 'accounts.db')

class AccountManager(object):

    def __init__(self, server):

        self.server = server

        try:
            self.conn = sqlite3.connect(ACCOUNT_PATH)

            # Attempt to set up the database properly.
            cursor = self.conn.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                name TEXT,
                pw_hash TEXT,
                config BLOB
            )""")

            cursor.close()

        except:
            self.log("Unable to open account database.")
            self.conn = None

    def log(self, message):
        self.server.log.log("[ACCT] %s" % message)
