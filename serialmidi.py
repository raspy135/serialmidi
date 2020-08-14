from PyInquirer import style_from_dict, Token, prompt
from rtmidi.midiutil import open_midiinput
from serial.tools import list_ports
import queue
import rtmidi
import serial
import threading
import logging
import sys
import time
import argparse

# Serial MIDI Bridge
# Ryan Kojima and Skyler Lewis

style = style_from_dict({
    Token.Separator: '#cc5454',
    Token.QuestionMark: '#673ab7 bold',
    Token.Selected: '#cc5454',  # default
    Token.Pointer: '#673ab7 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#f44336 bold',
    Token.Question: '',
})

questions = [
    {
        'type': 'list',
        'name': 'serial_port_name',
        'message': 'Which serial port do you want to use',
        'choices': [port[0] for port in serial.tools.list_ports.comports() if port[2] != 'n/a']
    }
]

parser = argparse.ArgumentParser(description="Serial MIDI bridge")
parser.add_argument("--serial_name", default=False, type=str, help="Serial port name. Required")
parser.add_argument("--baud", type=int, default=115200, help="baud rate. Default is 115200")
parser.add_argument("--midi_in_name", type=str, default="IAC Bus 1")
parser.add_argument("--midi_out_name", type=str, default="IAC Bus 2")
parser.add_argument("--debug", action="store_true", help="Print incoming / outgoing MIDI signals")
args = parser.parse_args()
thread_running = True

serial_port_name = args.serial_name
if not serial_port_name:  # You didn't provide --serial-name, prompt for ports we can find.
    answers = prompt(questions)
    serial_port_name = answers['serial_port_name']

# Arguments
serial_baud = args.baud
given_port_name_in = args.midi_in_name  # "IAC Bus 1"
given_port_name_out = args.midi_out_name  # "IAC Bus 2"

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

midi_ready = False
midiin_message_queue = queue.Queue()
midiout_message_queue = queue.Queue()


def get_midi_length(message):
    if len(message) == 0:
        return 100
    opcode = message[0]
    if opcode >= 0xf4:
        return 1
    if opcode in [0xf1, 0xf3]:
        return 2
    if opcode == 0xf2:
        return 3
    if opcode == 0xf0:
        if message[-1] == 0xf7:
            return len(message)

    opcode = opcode & 0xf0
    if opcode in [0x80, 0x90, 0xa0, 0xb0, 0xe0]:
        return 3
    if opcode in [0xc0, 0xd0]:
        return 2

    return 100


def serial_writer():
    while not midi_ready:
        time.sleep(0.1)
    while thread_running:
        try:
            message = midiin_message_queue.get(timeout=0.4)
        except queue.Empty:
            continue
        logging.debug(message)
        value = bytearray(message)
        ser.write(value)


def serial_watcher():
    receiving_message = []
    running_status = 0

    while not midi_ready:
        time.sleep(0.1)

    while thread_running:
        data = ser.read()
        if data:
            for elem in data:
                receiving_message.append(elem)
            # Running status
            if len(receiving_message) == 1:
                if (receiving_message[0] & 0xf0) != 0:
                    running_status = receiving_message[0]
                else:
                    receiving_message = [running_status, receiving_message[0]]

            message_length = get_midi_length(receiving_message)
            if message_length <= len(receiving_message):
                logging.debug(receiving_message)
                midiout_message_queue.put(receiving_message)
                receiving_message = []


class MidiInputHandler(object):
    def __init__(self, port):
        self.port = port
        self._wallclock = time.time()

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        print('Message received: ', "[%s] @%0.6f %r" % (self.port, self._wallclock, message))
        midiin_message_queue.put(message)


def midi_watcher():
    global midi_ready, thread_running
    midiin = rtmidi.MidiIn()
    midiout = rtmidi.MidiOut()
    available_ports_in = midiin.get_ports()
    available_ports_out = midiout.get_ports()

    # Get an midi out port
    if available_ports_out:
        logging.info("OUT : '" + "','".join(available_ports_out) + "'")
        for i, s in enumerate(available_ports_out):
            if given_port_name_out in s:
                out_port_name = midiout.open_port(i)
                print('Opening given out port', out_port_name)
                break
        else:
            print('Opening available out port', available_ports_out)
            out_port_name = midiout.open_port(0)
    else:
        vport_name = 'python virtual midiout port'
        out_port_name = midiout.open_virtual_port(vport_name)
        print('Opening Virtial out port: ', vport_name)

    # Get an midi in port
    if available_ports_in:
        logging.info("IN : '" + "','".join(available_ports_in) + "'")
        for i, s in enumerate(available_ports_in):
            if given_port_name_in in s:
                in_port_name = midiin.open_port(i)
                print('Opening given in port', in_port_name)
                break
        else:
            print('Opening available in port', available_ports_in)
            in_port_name = midiin.open_port(0)
    else:
        vport_name = 'python virtual midiin port'
        in_port_name = midiin.open_virtual_port(vport_name)
        print('Opening Virtial in port: ', vport_name)

    print("Hit ctrl-c to exit")
    midi_ready = True
    # midiin.ignore_types(sysex=False, timing=False, active_sense=False)
    midiin.set_callback(MidiInputHandler(in_port_name))

    while thread_running:
        try:
            message = midiout_message_queue.get(timeout=0.4)
        except queue.Empty:
            continue
        midiout.send_message(message)


try:
    ser = serial.Serial(serial_port_name, serial_baud)
except serial.serialutil.SerialException as e:
    if e.errno == 16:
        print('Serial port is busy')
        sys.exit()
    else:
        print("Serial port opening error occurred:", e)
        sys.exit()
else:
    print(f'Serial port connected successfully: {serial_port_name}')


ser.timeout = 0.4

s_watcher = threading.Thread(target=serial_watcher)
s_writer = threading.Thread(target=serial_writer)
m_watcher = threading.Thread(target=midi_watcher)

s_watcher.start()
s_writer.start()
m_watcher.start()

# Ctrl-C handler
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Terminating.")
    thread_running = False
    sys.exit(0)
