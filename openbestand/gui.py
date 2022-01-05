#!/usr/bin/env python3
"""
a tkinter GUI to monitor Bestand posture readings.

Todo:
----
- add buttons to indicate (live) status, including virbrate, buzz level, buzz pattern, etc.
- allow changing of level
- set background to red when level is below target

"""
import time

import asyncio
from aioconsole import aprint
import threading

from bleak import BleakClient
from .core import Record, BATTERY_LEVEL, find_device, parse_args

import tkinter as tk

INITIAL_WIDTH = 1024
INITIAL_HEIGHT = 100
DX = 2


class GUIClient(BleakClient):
    """
    GUI client.
    """

    def __init__(self, *args, **kwargs):
        """run from owning thread."""
        super().__init__(*args, **kwargs)
        self.last_buff = None
        self.loop = asyncio.get_event_loop()

    async def connect(self, **kwargs):
        await super().connect(**kwargs)
        await asyncio.sleep(1)
        await self.start_notify(BATTERY_LEVEL, self.notify_cb)

    async def notify_cb(self, sender, buff):
        if buff != self.last_buff:
            self.last_buff = buff
            self.r = Record.from_buffer(buff)
            # await aprint(f'{self.r}')

    def handle(self, keysym):
        self.loop.call_soon_threadsafe(
            self.loop.create_task, self.ahandle(keysym))

    async def ahandle(self, keysym):
        global running
        r = Record.from_buffer(self.last_buff)
        keysym = keysym.lower()
        if keysym == 'h' or keysym == '?':
            print('''
                    h           help

                    q           quit

                    x           power off and quit

                    b           toggle buzzer

                    <down>      lower expectations
                    <up>        raise expectations

                    <right>     increase delay
                    <left>      decrease delay

                    <enter>     print status
        ''')

        elif keysym == 'q':
            running = False
            return
        elif keysym == 'x':
            r.power_off()
            running = False
        elif keysym == 'b':
            r.toggle_buzz()
            await aprint(f'buzz {"on" if r.buzz else "off"}')
        elif keysym == 'down':
            r.target = min(90, r.target + 5)
            await aprint(f'target {r.target}')
        elif keysym == 'up':
            r.target = max(0, r.target - 5)
            await aprint(f'target {r.target}')
        elif keysym == 'right':
            r.delay = min(60, r.delay + 1)
            await aprint(f'delay {r.delay}')
        elif keysym == 'left':
            r.delay = max(0, r.delay - 1)
            await aprint(f'delay {r.delay}')
        elif keysym == 'return':
            await aprint(f'-- {r} --')
            return
        else:
            return
        await self.write_gatt_char(BATTERY_LEVEL, bytes(r), response=True)


class App:
    """
    main application.
    """

    def __init__(self, root, gc):
        self.root = root

        self.gc = gc

        butts = tk.Frame(self.root)
        butt1 = tk.Button(butts, text='butt1')
        butt2 = tk.Button(butts, text='butt2')

        self.canvas = tk.Canvas(
            self.root,
            width=INITIAL_WIDTH,
            height=INITIAL_HEIGHT,
            bg='black')

        self.ind_width = 10
        self.width = INITIAL_WIDTH - self.ind_width
        self.height = INITIAL_HEIGHT

        self.current_target = 0
        self.data = [0] * (self.width // DX + 1)
        self.ids = []
        self.ind_id = None
        self.target_id = None

        self.canvas.bind('<Configure>', self.on_resize)
        self.root.bind('<KeyPress>', self.on_keypress)

        self.canvas.pack(side='bottom', fill='both', expand=True)

        #butts.pack(side='top', fill='x', expand=False)
        butt1.grid(row=0, column=0, sticky='ew')
        butt2.grid(row=0, column=1, sticky='ew')

        # initial resize starts first draw
        self.stepper()

    def on_keypress(self, event):
        self.gc.handle(event.keysym)

    def draw_line(self, i):
        i = i % len(self.data)
        x1 = i * DX
        x2 = x1 + DX
        y1 = self.data2height(self.data[i])
        y2 = self.data2height(self.data[i + 1])
        self.ids[i] = self.canvas.create_line(
            [x1, y1, x2, y2], width=3, fill='white')

    def draw_ind(self):
        y = self.data2height(self.gc.r.ang)
        self.ind_id = self.canvas.create_line(
            [self.width, y, self.width + self.ind_width, y], width=3, fill='green')

    def data2height(self, y):
        return (self.height * y / 90)

    def draw_target(self):
        self.current_target = self.gc.r.target
        y = self.data2height(self.current_target)
        self.target_id = self.canvas.create_line(
            0,
            y,
            self.width + self.ind_width,
            y,
            width=1, fill='red')

    def draw(self):
        self.canvas.delete('all')

        self.draw_target()

        # draw a divider against the indicator
        self.canvas.create_line(
            self.width,
            0,
            self.width,
            self.height,
            width=1,
            fill='grey')

        n = len(self.data)

        # id of line from (x, data[i]) to (x+1, data[i+1])
        self.ids = [None] * (n - 1)

        for i in range(n - 1):
            self.draw_line(i)

        self.draw_ind()

    def on_resize(self, event):
        self.width = event.width - self.ind_width
        self.height = event.height
        oldn = len(self.data)
        n = self.width // DX + 1

        if oldn < n:
            self.data = ([0] * (n - oldn)) + self.data
        else:
            self.data = self.data[-n:]

        # ids will be recreated in draw

        self.draw()

    def add(self, d):
        if len(self.ids) == 0:
            return

        self.canvas.delete(self.ids[0])
        self.canvas.delete(self.ind_id)

        self.data = self.data[1:] + [d]
        self.ids = self.ids[1:] + [None]

        n = len(self.data)

        for i in range(n - 1):
            self.canvas.move(str(self.ids[i]), -DX, 0)

        self.draw_line(-2)
        self.draw_ind()

    def stepper(self):
        global running
        t = self.gc.r.ang
        if t != self.current_target:
            self.canvas.delete(self.target_id)
            self.draw_target()
        self.add(self.gc.r.ang)

        if running:
            self.root.after(500, self.stepper)
        else:
            self.root.destroy()


class BleakThread(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__(daemon=False)
        self.d = None
        self.client = None
        self.kwargs = kwargs

    async def astart(self):
        global running

        self.d = await find_device(**self.kwargs)
        if self.d is None:
            return

        async with GUIClient(self.d, **self.kwargs) as client:
            self.client = client
            while running:
                await asyncio.sleep(1)

    def run(self):
        asyncio.run(self.astart())

    def wait_for_connect(self):
        count = 0
        while self.client is None and count < 10:
            time.sleep(1)
            count += 1
        return self.client is not None


def main():
    """entry point."""
    global running

    kwargs = parse_args()

    running = True

    bt = BleakThread(**kwargs)
    bt.start()

    if not bt.wait_for_connect():
        print("""Bestand not found.  Verify that your device is in pairing mode with a blinking blue light.""")
        return

    root = tk.Tk()
    root.geometry(f'{INITIAL_WIDTH}x{INITIAL_HEIGHT}')
    root.title('openbestand')

    app = App(root, bt.client)

    try:
        root.mainloop()
    finally:
        running = False
        time.sleep(1.1)


if __name__ == '__main__':
    main()
