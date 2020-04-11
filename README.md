
This command line script establishes Serial to MIDI bridge.
It will be useful with micro controller boards such as Arduino, ESP32, they only have UART-USB interface.

I made this since useful [Hairless MIDI Serial bridge](https://github.com/projectgus/hairless-midiserial) program stopped working with OS X Catalina.

It processes most of MIDI messages. I could archive very low latency (probably less than 5ms) so far.

### Requirements / Installation

This script needs [python-rtmidi](https://pypi.org/project/python-rtmidi/), [PySerial](https://pypi.org/project/pyserial/) and Python 3.

1. Install Python 3
2. Install pip
3. `pip install python-rtmidi`
4. `pip install pyserial`
5. Download `serialmidi.py`

## Quickstart
```
MAC OS X example
$ python3 serialmidi.py --serial_name=/dev/cu.SLAB_USBtoUART --midi_in_name="IAC Bus 1" --midi_out_name="IAC Bus 2"

WINDOWS example
$ python.exe .\serialmidi.py --serial_name=COM4 --midi_in_name="loopMIDI Port IN 0" --midi_out_name="loopMIDI Port OUT 2"
```

## setup

1. Run `serialmidi.py -h` to see this help.
```
$ python3 serialmidi.py -h
usage: serialmidi.py [-h] --serial_name SERIAL_NAME [--baud BAUD]
                     [--midi_in_name MIDI_IN_NAME]
                     [--midi_out_name MIDI_OUT_NAME] [--debug]

Serial MIDI bridge

optional arguments:
  -h, --help            show this help message and exit
  --serial_name SERIAL_NAME
                        Serial port name. Required
  --baud BAUD           baud rate. Default is 115200
  --midi_in_name MIDI_IN_NAME
  --midi_out_name MIDI_OUT_NAME
  --debug               Print incoming / outgoing MIDI signals
```

2. Figure out serial port name and baud rate. Baud rate default is 115200.
3. Run `serialmidi.py --serial_name=[serial_port] --baud=[baud]`. Make sure it doesn't say "Serial port opening error.".
4. The script prints recognized MIDI devices. Use one of listed name as argument of `--midi_in_name` and `--midi_out_name`. Here is an example on OS X.
```
INFO:root:IN : 'IAC Bus 1','IAC Bus 2'
INFO:root:OUT : 'IAC Bus 1','IAC Bus 2'
```
You may want to use MIDI loop bus such as IAC Bus for OS X, or [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) for Windows. Also, you need to use different bus in order to avoid signal loop.

5. If it is not working, try `--debug` option. It will dump all incoming / outgoing MIDI messages. Or create an issue on the GitHub page.


### Tested environment
- Tested with OS X Catalina with ESP32 board, and Windows10 with loopMIDI.

### Other notes
- It's made for my ESP32 based synthesizer, so I tested MIDI IN a lot, but MIDI OUT. MIDI OUT message processing might have some bugs. Please let me know if you find it.


