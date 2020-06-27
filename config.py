import sys

from collections import namedtuple
from configparser import ConfigParser
from fnmatch import fnmatch
from os import getenv
from pathlib import Path
from typing import Optional


def find_config() -> Optional[Path]:
    config_dir = Path(getenv("XDG_CONFIG_DIR", "~/.config"))
    config_file = Path("hecaton.ini")
    candidates = [Path.cwd() / config_file,
                  config_dir / config_file]

    for path in candidates:
        if path.exists():
            return path

    return None


def parse_config():
    config_path = find_config()
    if not config_path:
        return {}

    parser = ConfigParser(strict=False, allow_no_value=True)
    parser.optionxform = str  # Don't lowercase keys
    parser.read_file(config_path.open())
    return parser


def prefix_match(device_name, pattern):
    return fnmatch(device_name, pattern)


def validate(config):
    Conflict = namedtuple('Conflict', 'defined used')
    core_present = False
    duplicate_devices = {}
    usage = {}
    for section in config.sections():
        if section == 'Core':
            core_present = True

        for devname, _ in config[section].items():
            for pattern in usage:
                if prefix_match(devname, pattern):
                    duplicate_devices.setdefault(devname, []).append(
                        Conflict(usage[pattern], section)
                    )
            usage[devname] = section

    if not core_present:
        print("Error: Core section missing")

    for devname, conflicts in duplicate_devices.items():
        for conflict in conflicts:
            print(f"Error: Device {devname!r} first declared in section [{conflict.defined}] reused in section [{conflict.used}]")

    if core_present and len(duplicate_devices) == 0:
        return

    sys.exit(1)


def print_config():
    config = parse_config()
    validate(config)
    for section in config.sections():
        print(section)
        print(list(config[section].items()))


if __name__ == "__main__":
    print_config()
