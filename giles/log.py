# Giles: log.py
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

import time

class Log(object):
    """The log.  Right now it just prints it locally.
    """

    def __init__(self, prefix=None):
        if prefix:
            self.prefix = prefix + ":"
        else:
            self.prefix = ""

    def log(self, message):
        timestamp = time.strftime("%Y%m%d.%H%M%S")
        print("%s [%s] %s" % (self.prefix, timestamp, message))
