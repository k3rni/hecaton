import sys

from collections import Counter
from pprint import pprint
from time import localtime

class InputEventHandler(object):
    def __init__(self, xinput, quiet=False):
        self.xinput = xinput
        self.quiet = quiet

    def noop(self, *args):
        pass

    def log_event(self, event, *args):
        if self.quiet:
            return
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
        now = localtime()
        # Returns the same value for `lag` consecutive minutes
        minute = now.tm_min - now.tm_min % lag

        return f"Hecaton Master {now.tm_hour:02}{minute:02}"
