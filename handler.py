import sys

from collections import Counter
from pprint import pprint


class InputEventHandler(object):
    def __init__(self, xinput, config):
        self.xinput = xinput
        self.config = config
        # TODO: extract from config
        self.quiet = False

    def noop(self, *args):
        pass

    def invalidate(self, *args):
        self.xinput.invalidate()

    def log_event(self, event, *args):
        if self.quiet:
            return
        sys.stderr.write(f"{event}{args}\n")

    def listdevices(self, device_id):
        pprint(self.xinput.device_list)

    def find_master_for(self, device_id):
        device = self.xinput[device_id]
        for section in self.config.sections():
            if section in ('Core', 'Disabled', 'General'):
                continue
            for pattern in self.config[section].keys():
                if device.match(pattern):
                    return section
        return None

    def find_or_create_master(self, name, kind):
        # 1. If device list already contains a master with this name, return its id
        for device in self.xinput.device_list:
            if device.name == f"{name} {kind}" and device.role == 'master':
                return device.id

        # 2. None found. Create one, then return here and find it.
        self.xinput.create_master(name)
        return self.find_or_create_master(name, kind)

    def disable(self, name):
        # TODO: Look in config['Disabled'], match device.
        return False

    def XIDeviceEnabled(self, device_id, input_class, device_name):
        if input_class in ('XIMasterPointer', 'XIMasterKeyboard'):
            return

        if 'XTEST' in device_name:
            # These are added automatically to every master, and we shouldn't manage them
            return

        self.log_event('XIDeviceEnabled', device_id, input_class, device_name)

        if self.disable(device_id):
            # TODO: issue an xinput command to disable. Or should this be on attach?
            return

        master_name = self.find_master_for(device_id)
        if master_name is None:
            # No rules for this device. Ignore.
            return

        kind = 'pointer' if input_class == 'XISlavePointer' else 'keyboard'
        master_id = self.find_or_create_master(master_name, kind)
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

    XISlaveRemoved = invalidate
    XIMasterAdded = invalidate
    XIMasterRemoved = invalidate
    XISlaveAdded = invalidate
    XISlaveAttached = noop
    XISlaveDetached = noop
