import pickle
import re

from dataclasses import dataclass
from fnmatch import fnmatch
from itertools import groupby
from os import readlink, environ
from pathlib import Path
from subprocess import run, check_output

__all__ = ["XInput"]


def sysfsid(path):
    devpath = path.resolve().relative_to('/sys/devices')

    while True:
        devpath = devpath.parent
        if devpath.stem == 'input':
            return devpath.parent

# for slave devices, rel is their master id
# for master devices, rel is the other device in master pair
@dataclass
class XIDevice:
    name: str
    id: str
    role: str
    kind: str
    properties: dict

    def __getitem__(self, key):
        return self.properties[key]

    def __setitem__(self, key, value):
        self.properties[key] = value

    def load_system_info(self):
        try:
            node = self['Device Node']
            evdev = Path(node).stem
        except KeyError:
            # Not all devices have a device node. Nothing to do here.
            return

        sys_path = Path("/sys/class/input") / evdev
        target = Path(readlink(sys_path))
        self['sysfs'] = str(sysfsid(sys_path.parent / target))

    def match(self, pattern):
        if 'sysfs' in self.properties and fnmatch(self['sysfs'], pattern):
            return True
        # Device Node
        if 266 in self.properties and fnmatch(self[266], pattern):
            return True
        # Device Product ID
        if 267 in self.properties and fnmatch(self[267], pattern):
            return True

        return fnmatch(self.name, pattern)


# TODO: Detect floating devices
DEV_LINE = re.compile(r'''
   ^.*?          # eat characters at start of line
   \b(.*?)\s+    # until we hit a word boundary, which belongs to some device name
   id=(\d+)\s+   # with an id
   \[            # then in square brackets
       (master|slave)\s+(keyboard|pointer)\s+ # device role and kind
       \((\d+)\) # related device id
   \]
''', re.VERBOSE)

PROPS_DEVICE = re.compile(r"^Device '(.*)':$")
PROPS_LINE = re.compile(r'\t(.*)\s\((\d+)\):\t(.*)$')


def transform_property(value, num, key):
    parse = lambda x: x
    if 'Matrix' in key:
        parse = float
    elif 'Enabled' in key:
        parse = lambda x: bool(int(x))
    else:
        parse = int

    if num == 267:  # Device ID
        ids = [int(v) for v in value.split(', ')]
        return ':'.join(f"{id:04X}" for id in ids)
    elif num in (266,):  # String properties
        return value.replace('"', '')
    elif num in (289, 290):  # Floats
        return float(value)
    elif num in (143, 263, 264, 265, 280, 281, 282, 291, 292, 293, 296):  # Lists
        if value == '<no items>':
            return []
        return [parse(v) for v in value.split(', ')]
    return parse(value)


def parse_props(lines):
    props = None
    for line in lines:
        head = PROPS_DEVICE.match(line)
        if head:
            if props:
                yield props
            props = {'label': head.group(1)}
            continue

        row = PROPS_LINE.match(line)
        if row:
            num = int(row.group(2))
            key = row.group(1)
            value = transform_property(row.group(3), num, key)
            props[num] = value
            props[key] = value

    yield props

class XInput(object):
    def __init__(self, executable=None):
        self.executable = executable or '/usr/bin/xinput'

    def cachefile(self):
        cachedir = environ.get('XDG_RUNTIME_DIR', '/tmp')
        return Path(cachedir) / 'hecaton_xinput_cache'

    # NOTE: this whole caching mechanism isn't very important, as the full xinput query
    # requires only two invocations of xinput. May not be as useful as originally thought.
    @property
    def device_list(self):
        cache = self.cachefile()
        if cache.exists():
            try:
                self._device_list = pickle.load(cache.open('rb'))
                return self._device_list
            except (IOError, EOFError):
                pass

        self._device_list = self.fetch_device_list()
        pickle.dump(self._device_list, cache.open('wb'))
        return self._device_list

    def invalidate(self):
        if self.cachefile().exists():
            # Python 3.8 has unlink(missing_ok=True)
            self.cachefile().unlink()

    def fetch_device_list(self):
        xinput_out = check_output(self.executable, encoding='utf-8')

        matches = [DEV_LINE.match(line) for line in xinput_out.splitlines()]
        devices = list(XIDevice(*m.groups()) for m in matches if m)

        device_ids = [dev.id for dev in devices]
        command = [self.executable, 'list-props', *device_ids]
        props_out = check_output(command, encoding='utf-8')
        for i, props in enumerate(parse_props(props_out.splitlines())):
            devices[i].properties = props
            devices[i].load_system_info()

        self._device_list = devices
        return devices

    def devices(self):
        keyfunc = lambda dev: dev.name  # noqa: E731
        grouped = groupby(sorted(self.device_list(), key=keyfunc), keyfunc)
        return {name: list(devices) for name, devices in grouped}

    def __getitem__(self, key: str):
        # Lookup by device id
        for device in self.device_list:
            if device.id == key:
                return device

        raise KeyError(f"Device with id {key} unknown")

    def create_master(self, name):
        self.invalidate()
        run([self.executable, "create-master", name])

    def remove_master(self, ident):
        self.invalidate()
        run([self.executable, "remove-master", ident])

    def attach(self, device_id, master_id):
        run([self.executable, "reattach", str(device_id), str(master_id)])

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


if __name__ == "__main__":
    x = XInput()
    from pprint import pprint
    for dev in x.device_list:
        pprint(dev)
