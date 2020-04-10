import time
import queue
import rtmidi
import serial
import threading
import logging
import sys
import time
import argparse

# Serial MIDI Bridge
# Tested with Mac OX X Catalina and ESP32
# Example (For synthesizer, input latency is critical)
# python3 serialmidi.py --serial_name=/dev/cu.SLAB_USBtoUART --midi_in_name="IAC Bus 1" --midi_out_name="IAC Bus 2" --in_latency=0.001 --out_latency=0.05
# For MIDI controller, set lower value to out_latency and higher value to in_latency.
#


parser = argparse.ArgumentParser(description = "Serial MIDI bridge")

parser.add_argument("--serial_name", type=str)
parser.add_argument("--baud", type=int, default=115200)
parser.add_argument("--out_latency", type=float, default=0.01, help="Output (Serial->MIDI) max latency in sec. Lower latency may use more CPU power.")
parser.add_argument("--in_latency", type=float, default=0.01, help="Input (MIDI->Serial) max latency in sec. Lower latency may use more CPU power.")
parser.add_argument("--midi_in_name", type=str, default = "IAC Bus 1")
parser.add_argument("--midi_out_name", type=str, default = "IAC Bus 2")
parser.add_argument("--debug", action = "store_true")

args = parser.parse_args()



# Arguments
serial_port_name = args.serial_name #'/dev/cu.SLAB_USBtoUART'
serial_baud = args.baud
# Low latency = more CPU power
out_latency = args.out_latency #0.05
in_latency = args.in_latency #0.001
given_port_name_in = args.midi_in_name #"IAC Bus 1"
given_port_name_out = args.midi_out_name #"IAC Bus 2"

if args.debug:
    logging.basicConfig(level = logging.DEBUG)
else:
    logging.basicConfig(level = logging.INFO)

ser = serial.Serial(serial_port_name,serial_baud)

ser.timeout = in_latency

midiin_message_queue = queue.Queue()
midiout_message_queue = queue.Queue()

def get_midi_length(message):
    if len(message) == 0:
        return 100
    opcode = message[0]
    if opcode >= 0xf4:
        return 1
    if opcode in [ 0xf1, 0xf3 ]:
        return 2
    if opcode == 0xf2:
        return 3
    if opcode == 0xf0:
        if message[-1] == 0xf7:
            return len(message)

    opcode = opcode & 0xf0
    if opcode in [ 0x80, 0x90, 0xa0, 0xb0, 0xe0 ]:
        return 3
    if opcode in [ 0xc0, 0xd0 ]:
        return 2

    return 100


def serial_watcher():
    receiving_message = []
    running_status = 0

    while(True):
        data = ser.read()
        if data:
            for elem in data:
                receiving_message.append(elem)
            #Running status
            if len(receiving_message) == 1:
                if (receiving_message[0]&0xf0) != 0:
                    running_status = receiving_message[0]
                else:
                    receiving_message = [ running_status, receiving_message[0] ]

            message_length = get_midi_length(receiving_message)
            if message_length <= len(receiving_message):
                logging.debug(receiving_message)
                midiout_message_queue.put(receiving_message)
                receiving_message = []

        if midiin_message_queue.empty() == False:
            message = midiin_message_queue.get()
            logging.debug(message)
            value = bytearray(message)
            ser.write(value)


class midi_input_handler(object):
    def __init__(self, port):
        self.port = port
        self._wallclock = time.time()

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        #logging.debug("[%s] @%0.6f %r" % (self.port, self._wallclock, message))
        midiin_message_queue.put(message)


def midi_watcher():
    midiin = rtmidi.MidiIn()
    midiout = rtmidi.MidiOut()
    available_ports_out = midiout.get_ports()
    available_ports_in = midiin.get_ports()
    logging.info("IN : " + " , ".join(available_ports_in))
    logging.info("OUT : " + " , ".join(available_ports_out))

    for i, s in enumerate(available_ports_in):
        if given_port_name_in in s:
            port_index_in = i
    for i, s in enumerate(available_ports_out):
        if given_port_name_out in s:
            port_index_out = i

    if available_ports_out:
        midiout.open_port(port_index_out)
    else:
        print("No output device detected")
        sys.exit()
    if available_ports_in:
        in_port_name = midiin.open_port(port_index_in)
    else:
        print("No input device detected")
        sys.exit()

    midiin.ignore_types(sysex = False, timing = False, active_sense = False)
    midiin.set_callback(midi_input_handler(in_port_name))

    while(True):
        time.sleep(out_latency) #MIDI out (Serial -> CoreMIDI) latency
        if midiout_message_queue.empty() == False:
            message = midiout_message_queue.get()
            midiout.send_message(message)



s_watcher = threading.Thread(target = serial_watcher)
m_watcher = threading.Thread(target = midi_watcher)

s_watcher.start()
m_watcher.start()
