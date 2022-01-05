"""
common / core module for openbestand.
"""
from ctypes import Structure, c_uint8
from bleak import BleakScanner

import argparse


BATTERY_LEVEL = '00002a19-0000-1000-8000-00805f9b34fb'
SERVICE_CHANGED = '00002a05-0000-1000-8000-00805f9b34fb'

async def find_device(**kwargs):
    """return a Bestand BLEDevice or None if one isn't found."""
    return await BleakScanner.find_device_by_filter(lambda d, ad: d.name == 'Bestand', service_uuids=['1812'], **kwargs)


class Record(Structure):
    """primarily packet structure, presumably raw device registers."""

    _pack_ = 1
    _fields_ = [
        ('x0a', c_uint8),  # beats me, maybe protocol/firmware version
        ('x07', c_uint8),  #

        ('batt', c_uint8),

        ('ang', c_uint8),

        # if ang > target then buzz
        ('target', c_uint8),

        # high nibble is strength:  0: medium, 1: low, 2: high, low nibble is
        # pattern
        ('buzzv', c_uint8),

        ('delay', c_uint8),

        # bit 0x04 indicates vibration is on
        ('status', c_uint8),

        #
        ('ctrl', c_uint8),
        ('count', c_uint8),
    ]

    def __str__(self):
        return \
            f'batt {self.batt:3}%  {self.ang:02}/{self.target:02}  ' + \
            f'delay {self.delay:2}  ' + \
            f'buzz {"on " if self.buzz else "off"} ' + \
            f'buzz_str {self.buzz_strength} ' + \
            f'buzz_pat {self.buzz_pattern} ' + \
            f'status {self.status:02x}'

    @property
    def buzz(self):
        return (self.status & 4) != 0

    @buzz.setter
    def buzz(self, value: bool):
        # the change to status is unnecessary for configuring the device, but
        # keeps Record.buzz coherent.
        if value:
            self.ctrl = (self.ctrl & (0xff ^ 4)) | 8
            self.status = self.status | 4
        else:
            self.ctrl = (self.ctrl & (0xff ^ 8)) | 4
            self.status = self.status & (0xff ^ 4)

    @property
    def buzz_strength(self):
        """0:low, 1:mid, 2:high."""
        x = self.buzzv >> 4
        if x == 0:
            return 1
        elif x == 1:
            return 0
        elif x == 2:
            return 2
        else:
            return x

    @buzz_strength.setter
    def buzz_strength(self, value: int):
        """0:low, 1:mid, 2:high."""
        if value == 0:
            self.buzzv = (1 << 4) | (0xf & self.buzzv)
        elif value == 1:
            self.buzzv = (0 << 4) | (0xf & self.buzzv)
        elif value == 2:
            self.buzzv = (2 << 4) | (0xf & self.buzzv)
        else:
            self.buzzv = value | (0xf & self.buzzv)

    def toggle_buzz(self):
        self.buzz = not self.buzz

    @property
    def buzz_pattern(self):
        return f'{self.buzzv & 0xf:x}'

    @buzz_pattern.setter
    def buzz_pattern(self, value: str):
        self.buzzv = (self.buzzv & 0xf0) | (0xf & int(value, 16))

    @property
    def calibrating(self) -> bool:
        return (self.status & 1) != 0

    @calibrating.setter
    def calibrating(self, value: bool):
        if value:
            self.ctrl = self.ctrl | 1
        else:
            self.ctrl = (self.ctrl & 0xfe)

    def power_off(self):
        self.ctrl |= 0x40


def parse_args():
    """parse arguments and return common kwargs for bleak constructors."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--adapter', help='Bluetooth adapter, e.g. hci0')
    parser.add_argument('--timeout', type=float, help='Timeout in seconds')
    args = parser.parse_args()
    return {k: v for k, v in args.__dict__.items() if v is not None}
