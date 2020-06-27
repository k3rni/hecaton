# TODO
# Move xinput class from hecaton main here.
# Add methods to find a slave device by name, with wildcards
# Add methods to find a slave device by usbid. This requires iteration and running xinput many times, or finding a better way to read all props.
# Add methods to find a slave device by eventdev, concerns identical to usbid.

# Caching
# Between DeviceAdded/DeviceRemoved events, the state is assumed not to change, therefore can be easily cached in $XDG_RUNTIME_DIR.
# Use that.
import re
import subprocess

from collections import namedtuple
from itertools import groupby

# for slave devices, rel is their master id
# for master devices, rel is the other device in master pair
XIDevice = namedtuple('XIDevice', 'name id role kind rel')


class XInput(object):
    def __init__(self, executable=None):
        self.executable = executable or '/usr/bin/xinput'

    LINE = re.compile(r'''
       ^.*?          # eat characters at start of line
       \b(.*?)\s+    # until we hit a word boundary, which belongs to some device name
       id=(\d+)\s+   # with an id
       \[            # then in square brackets
           (master|slave)\s+(keyboard|pointer)\s+ # device role and kind
           \((\d+)\) # related device id
       \]
    ''', re.VERBOSE)

    def query(self):
        return subprocess.check_output(self.executable).decode('utf-8')

    def device_list(self):
        lines = self.query().splitlines()
        matches = [XInput.LINE.match(line) for line in lines]
        return list(XIDevice(*m.groups()) for m in filter(None, matches))

    def devices(self):
        keyfunc = lambda dev: dev.name  # noqa: E731
        grouped = groupby(sorted(self.device_list(), key=keyfunc), keyfunc)
        return {name: list(devices) for name, devices in grouped}

    def create_master(self, name):
        cmd = [self.executable, "create-master", name]
        subprocess.run(cmd)

    def remove_master(self, ident):
        cmd = [self.executable, "remove-master", ident]
        subprocess.run(cmd)

    def attach(self, device_id, master_id):
        cmd = [self.executable, "reattach", str(device_id), str(master_id)]
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
