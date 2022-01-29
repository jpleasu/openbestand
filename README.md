# openbestand
A basic client for the [Bestand Posture Trainer & Corrector](http://bestand.com/product/Bestand%C2%A0Posture%C2%A0Trainer%C2%A0%26%C2%A0Corrector-151.html) ([Amazon link](https://www.amazon.com/Bestand-Intelligent-Corrector-Strapless-Reminder/dp/B09HGVWYML)).

## Installation

To install or update from a release: 
```bash
pip3 install https://github.com/jpleasu/openbestand/releases/download/openbestand-0.2.0/openbestand-0.2.0.tar.gz
```

## Development

`openbestand` is built with [`poetry`](https://python-poetry.org/). In order to
work with the source first install `poetry`:
```bash
pip3 install poetry
```

To build and install with system `pip`:
```bash
poetry build -f sdist
pip install dist/openbestand-*.tar.gz
```

To run directly from a virtual env without installing to system, first
```bash
poetry install
```
then, e.g.
```bash
poetry run openbestand_gui
```

## Usage

All scripts take the same command line arguments which are ultimately passed to bleak.

### `openbestand_cli`
Turn on the device to to start pairing, it should blink blue.

Run `openbestand_cli` and type `h<enter>`

Press `s<enter>` to start printing notifications.  Notifications will be
asynchronously print to the screen.

Press `q<enter>` to quit.

### `openbestand_rssi`
A simple loop to scan for and show the RSSI for (the first) Bestand BLE device.

It attempts to report every `--timeout` seconds (default of 1).  `--` means the
device wasn't found.

Note: The device has a really small operating distance! Moving it into position
(stuck to your back) can kill the signal entirely.

You might find that an external bluetooth dongle works better.  Use `--adapter`
option in each of the tools:

e.g. 
```
./openbestand_rssi --adapter hci1
```


### `openbestand_gui`
A horrible Tkinter app to track your level.

Press `h` to dump keybindings to stdout.  Type `q` to quit.

