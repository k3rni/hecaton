#! /usr/bin/env python

import sys

from xinput import XInput
from handler import InputEventHandler

## Configuration
"""Time in minutes, during which connecting new devices *doesn't* create new
pointers.  This is expressed not in time since connection, but rather as a
number of wall clock minutes. For example, with this set to 2, if we plug a
device at an *even* minute, like 10:00, then all further devices plugged during
10:00 and 10:01 will be assigned to the same pointer+keyboard pair. Plugging
more devices at 10:02 will create another new pair."""
LAG = 2

"""Path to xinput binary, useful for running under restricted environment."""
XINPUT_BIN = "/usr/bin/xinput"

"""Suppress all logging."""
QUIET = True
## End of configuration ##


if __name__ == "__main__":
    handler = InputEventHandler(XInput(XINPUT_BIN))
    event, devid = sys.argv[1:3]
    getattr(handler, event)(devid, *sys.argv[3:])
