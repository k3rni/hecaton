#! /usr/bin/env python

import sys

from xinput import XInput
from config import parse_config, validate
from handler import InputEventHandler

if __name__ == "__main__":
    config = parse_config()
    validate(config)

    if 'General' in config.sections():
        path = config['General']['Path']
    else:
        path = '/usr/bin/xinput'

    handler = InputEventHandler(XInput(path), config)
    event, devid = sys.argv[1:3]
    getattr(handler, event)(devid, *sys.argv[3:])
