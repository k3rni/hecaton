#! /usr/bin/env python

from itertools import groupby
from pprint import pprint
import re
import sys
import subprocess
import time
from collections import namedtuple, Counter

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

# for slave devices, rel is their master id
# for master devices, rel is the other device in master pair
XIDevice = namedtuple('XIDevice', 'name id role kind rel')


class XInput(object):
    def __init__(self):
        self.path = XINPUT_BIN

    LINE = re.compile(r'''^.*? # eat characters at start of line
        \b(.*?)\s+ # until we hit a word boundary, which belongs to some device name
       id=(\d+)\s+ # with an id
       \[ # then in square brackets
           (master|slave)\s+(keyboard|pointer)\s+ # device role and kind
           \((\d+)\) # related device id
       \]
    ''', re.VERBOSE)

    def xinput(self):
        return subprocess.check_output(self.path).decode('utf-8')

    def device_list(self):
        lines = self.xinput().splitlines()
        matches = [XInput.LINE.match(line) for line in lines]
        return list(XIDevice(*m.groups()) for m in filter(None, matches))

    def devices(self):
        keyfunc = lambda dev: dev.name  # noqa: E731
        grouped = groupby(sorted(self.device_list(), key=keyfunc), keyfunc)
        return {name: list(devices) for name, devices in grouped}

    def create_master(self, name):
        cmd = [self.path, "create-master", name]
        subprocess.run(cmd)

    def remove_master(self, ident):
        cmd = [self.path, "remove-master", ident]
        subprocess.run(cmd)

    def attach(self, device_id, master_id):
        cmd = [self.path, "reattach", str(device_id), str(master_id)]
        subprocess.run(cmd)

    def get_master_id(self, name, kind):
        try:
            # Newly created masters get the device kind added to their name
            candidates = self.devices()[f"{name} {kind}"]
            device = next(dev for dev in candidates
                          if dev.role == 'master' and dev.kind == kind)  # Role check somewhat redundant
            return device.id
        except (KeyError, StopIteration):
            return None

    def get_or_create_master(self, name, kind):
        existing_id = self.get_master_id(name, kind)
        if existing_id:
            return existing_id

        self.create_master(name)
        return self.get_master_id(name, kind)


class InputEventHandler(object):
    def __init__(self, xinput):
        self.xinput = xinput

    def noop(self, *args):
        pass

    def log_event(self, event, *args):
        if not QUIET:
            sys.stderr.write(f"{event}{args}\n")

    def listdevices(self, device_id):
        pprint(self.xinput.devices())

    def XIDeviceEnabled(self, device_id, input_class, device_name):
        if input_class in ('XIMasterPointer', 'XIMasterKeyboard'):
            return

        if 'XTEST' in device_name:
            # These are added automatically to every master, and we shouldn't manage them
            return

        self.log_event('XIDeviceEnabled', device_id, input_class, device_name)

        new_master = self.time_based_master_name()
        kind = 'pointer' if input_class == 'XISlavePointer' else 'keyboard'

        master_id = self.xinput.get_or_create_master(new_master, kind)
        self.xinput.attach(device_id, master_id)

    def XIDeviceDisabled(self, device_id, input_class, device_name):
        if input_class in ('XIMasterPointer', 'XIMasterKeyboard'):
            return

        if 'XTEST' in device_name:
            return

        self.log_event('XIDeviceDisabled', device_id, input_class, device_name)

        # Check if any master now has no devices (besides the XTEST ones) and remove them.
        devices = self.xinput.devices()
        masters, usage = {}, Counter()
        for name, devs in devices.items():
            for device in devs:
                if device.role == 'master':
                    masters[device.id] = device.rel
                else:
                    usage[device.rel] += 1

        unused = {num for num in masters.keys() if usage[num] <= 1}  # allow XTEST devices
        for master_id in unused:
            other = masters[master_id]
            # Don't remove the pair if the other member still has some devices
            if usage[other] > 1:
                continue

            self.xinput.remove_master(master_id)

    XISlaveRemoved = noop
    XIMasterAdded = noop
    XIMasterRemoved = noop
    XISlaveAdded = noop
    XISlaveAttached = noop
    XISlaveDetached = noop

    @staticmethod
    def time_based_master_name(lag=2):
        now = time.localtime()
        # Returns the same value for `lag` consecutive minutes
        minute = now.tm_min - now.tm_min % lag

        return f"Hecaton Master {now.tm_hour:02}{minute:02}"


if __name__ == "__main__":
    handler = InputEventHandler(XInput())
    event, devid = sys.argv[1:3]
    getattr(handler, event)(devid, *sys.argv[3:])
