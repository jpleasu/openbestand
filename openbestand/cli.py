#!/usr/bin/env python3
"""
open source interface to bestand posture corrector.

vibration is set with bits 2&3 of the control register.
    3 -> vibration on
    2 -> vibration off

everything else is set by updating the notification data and sending it back
with a counter of 0.


"""

import re

import asyncio
from bleak import BleakClient, BleakScanner

from .core import Record, BATTERY_LEVEL, find_device, parse_args

from aioconsole import ainput, aprint


class ConsoleClient(BleakClient):
    """
    console client.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_buff = None
        self.output = False

    async def connect(self, **kwargs):
        await super().connect(**kwargs)
        await asyncio.sleep(1)
        await self.start_notify(BATTERY_LEVEL, self.notify_cb)
        await aprint(f'connected to device with address {self.address}')

    async def notify_cb(self, sender, buff):
        if buff != self.last_buff:
            if self.output:
                r = Record.from_buffer(buff)
                await aprint(f"\n-- {r} --", end='')
            self.last_buff = buff

    async def console_prompt(self) -> bool:  # noqa
        """
        present a debug prompt.. return False on disconnect.
        """
        ret = True
        x = await ainput('> ')
        r = Record.from_buffer(self.last_buff[:])
        if x.strip() == '':
            await aprint(f"-- {r} --")
            return ret

        if x == 'h' or x == 'help' or x == '?':
            await aprint('''\
                    h        : help

                    <enter>  : print state
                    q        : quit
                    x        : power off

                    s        : start/stop notifications

                    c        : calibrate

                    t <ang>  : set the target to angle ang
                    d <secs> : set delay to secs seconds

                    b        : toggle buzzer
                    b+       : raise the buzz strength
                    b-       : lower the buzz strength
                    b[0-2]   : set the buzz strength

                    p[0-f]   : set the buzz pattern
            ''')
            return ret
        elif x == 'q':
            return False
            await aprint('Quitting.')

        elif x == 'x':
            r.power_off()
            ret = False
            await aprint('Turning off.')

        elif x == 's':
            self.output = not self.output
            self.last_buff = None
            if self.output:
                await aprint('Starting notifications.')
            else:
                await aprint('Stopping notifications.')
            return True

        elif x == 'c':
            r.calibrating = True
            # must be sent twice *shrug*
            await aprint('Calibrating')
            await self.write_gatt_char(BATTERY_LEVEL, bytes(r))
            await asyncio.sleep(.1)
            await self.write_gatt_char(BATTERY_LEVEL, bytes(r))

            # 3 seconds to calibrate should be plenty
            for count in range(6):
                r = Record.from_buffer(self.last_buff)
                if not r.calibrating:
                    break
                await aprint('Calibrating ..')
                await asyncio.sleep(.5)
            r.calibrating = False
            await aprint('Done calibrating')

        elif x.startswith('t '):
            r.target = int(x.split()[1])
            await aprint(f'Setting target to {r.target}.')

        elif x.startswith('d '):
            r.delay = int(x.split()[1], 0)
            await aprint(f'Setting delay to {r.delay}.')

        elif x == 'b':
            r.toggle_buzz()
            await aprint(f'Setting buzzer to {"on" if r.buzz else "off"}.')
        elif x == 'b+':
            r.buzz_strength = min(2, r.buzz_strength + 1)
            await aprint(f'Setting buzz strength to {r.buzz_strength}.')
        elif x == 'b-':
            r.buzz_strength = max(0, r.buzz_strength - 1)
            await aprint(f'Setting buzz strength to {r.buzz_strength}.')
        elif x in ['b0', 'b1', 'b2']:
            r.buzz_strength = int(x[1])
            await aprint(f'Setting buzz strength to {r.buzz_strength}.')
        elif re.match('p[0-f]', x):
            r.buzz_pattern = x[1]
            await aprint(f'Setting buzz pattern to {r.buzz_pattern}.')

        await self.write_gatt_char(BATTERY_LEVEL, bytes(r))
        return ret


async def amain(**kwargs):
    d = await find_device(**kwargs)
    if d is None:
        await aprint("""Bestand not found.  Verify that your device is in pairing mode with a blinking blue light.""")
        return

    async with ConsoleClient(d) as client:
        while client.is_connected:
            if not await client.console_prompt():
                break


def main():
    """entry point."""
    try:
        asyncio.run(amain(**parse_args()))
    except KeyboardInterrupt:
        pass
    print()


async def amain_rssi(**kwargs):
    # use timeout as an interval
    timeout = kwargs.pop('timeout', 1.0)
    loop = asyncio.get_event_loop()
    while True:
        t0 = loop.time()
        device = await find_device(**kwargs)
        if device is None:
            await aprint('---')
        else:
            print(device.rssi)
            t1 = loop.time()
            d = t1 - t0
            if d < timeout:
                await asyncio.sleep(timeout - d)


def main_rssi():
    """entry point for RSSI monitoring."""
    try:
        asyncio.run(amain_rssi(**parse_args()))
    except KeyboardInterrupt:
        pass
    print()
