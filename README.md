
This script will establish Serial to MIDI bridge.
It will be useful with micro controller boards such as Arduino, ESP32.

I made this since useful [Hairless MIDI Serial bridge](https://github.com/projectgus/hairless-midiserial) program stopped working with OS X Catalina.

It processes most of MIDI messages. I could archive very low latency (probably less than 5ms) so far.

## Quickstart
```
MAC OS X example
$ python3 serialmidi.py --serial_name=/dev/cu.SLAB_USBtoUART --midi_in_name="IAC Bus 1" --midi_out_name="IAC Bus 2"

WINDOWS example
$ python.exe .\serialmidi.py --serial_name=COM4 --midi_in_name="loopMIDI Port IN 0" --midi_out_name="loopMIDI Port OUT 2"
```
The script will put a list of device names. Use the listed name for --midi_in_name and midi_out_name.

### Requirements

This script needs [python-rtmidi](https://pypi.org/project/python-rtmidi/), [PySerial](https://pypi.org/project/pyserial/) and Python 3.

### Tested environment
- I tested with OS X Catalina with ESP32 board, and Windows10 with loopMIDI.

### Other notes
- I made it for my ESP32 based synthesizer, so I tested MIDI IN a lot, but MIDI OUT. MIDI OUT message processing might have some bugs. Please let me know if you find it.


