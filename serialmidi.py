import time
import queue
import rtmidi
import serial
import threading
import logging
import sys
import time
import argparse
import os

# Serial MIDI Bridge
# Ryan Kojima


def main():
    global ser, midi_ready, thread_running, args
    global serial_port_name, serial_baud, given_port_name_in, given_port_name_out
    
    parser = argparse.ArgumentParser(description = "Serial MIDI bridge")

    parser.add_argument("--serial_name", type=str, required = True, help = "Serial port name. Required")
    parser.add_argument("--baud", type=int, default=115200, help = "baud rate. Default is 115200")
    parser.add_argument("--midi_in_name", type=str, default = "IAC Bus 1")
    parser.add_argument("--midi_out_name", type=str, default = "IAC Bus 2")
    parser.add_argument("--debug", action = "store_true", help = "Print incoming / outgoing MIDI signals")
    parser.add_argument("--string", action = "store_true", help = "Print sysEx logging message (For Qun Mk2)")

    args = parser.parse_args()
    
    # Arguments
    serial_port_name = args.serial_name
    serial_baud = args.baud
    given_port_name_in = args.midi_in_name
    given_port_name_out = args.midi_out_name

    if args.debug:
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.INFO)

    try:
        ser = serial.Serial(serial_port_name,serial_baud)
    except serial.serialutil.SerialException:
        print("Serial port opening error.")
        midi_watcher()
        sys.exit()

    ser.timeout = 0.4

    s_watcher = threading.Thread(target = serial_watcher, daemon=True)
    s_writer = threading.Thread(target = serial_writer, daemon=True)
    m_watcher = threading.Thread(target = midi_watcher, daemon=True)

    s_watcher.start()
    s_writer.start()
    m_watcher.start()

    #Ctrl-C handler
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Terminating.")
        thread_running = False
        os._exit(0)

thread_running = True
args = None
ser = None
serial_port_name = None
serial_baud = 115200
given_port_name_in = "IAC Bus 1"
given_port_name_out = "IAC Bus 2"
midi_ready = False
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
    
def process_serial_data(data, receiving_message, running_status):
    completed_messages = []
    for elem in data:
        # System Real-Time messages (0xF8 - 0xFF) can be interleaved anywhere
        # and should be processed immediately without affecting current message or running status.
        if elem >= 0xf8:
            completed_messages.append([elem])
            continue

        receiving_message.append(elem)
        # Running status
        if len(receiving_message) > 0:
            if receiving_message[0] >= 0x80:
                if receiving_message[0] < 0xf0:
                    running_status = receiving_message[0]
                else:
                    running_status = 0 # System common items reset running status.
            else:
                if running_status != 0:
                    receiving_message.insert(0, running_status)

        message_length = get_midi_length(receiving_message)
        if message_length <= len(receiving_message):
            logging.debug(receiving_message)
            completed_messages.append(receiving_message)

            if args.string:
                if receiving_message[0] == 0xf0:
                    print_message = []
                    for elem in receiving_message:
                        if elem < 0xf0:
                            print_message.append(chr(elem))
                    print_message_str = ''.join(print_message)
                    print(print_message_str)
            receiving_message = []
    return receiving_message, running_status, completed_messages

def serial_writer():
    while midi_ready == False:
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

    while midi_ready == False:
        time.sleep(0.1)

    while thread_running:
        data = ser.read()
        if data:
            receiving_message, running_status, messages = process_serial_data(data, receiving_message, running_status)
            for msg in messages:
                midiout_message_queue.put(msg)



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
    global midi_ready, thread_running

    midiin = rtmidi.MidiIn()
    midiout = rtmidi.MidiOut()
    available_ports_out = midiout.get_ports()
    available_ports_in = midiin.get_ports()
    logging.info("IN : '" + "','".join(available_ports_in) + "'")
    logging.info("OUT : '" + "','".join(available_ports_out) + "'")
    logging.info("Hit ctrl-c to exit")

    port_index_in = -1
    port_index_out = -1
    for i, s in enumerate(available_ports_in):
        if given_port_name_in in s:
            port_index_in = i
    for i, s in enumerate(available_ports_out):
        if given_port_name_out in s:
            port_index_out = i

    if port_index_in == -1:
        print("MIDI IN Device name is incorrect. Please use listed device name.")
    if port_index_out == -1:
        print("MIDI OUT Device name is incorrect. Please use listed device name.")
    if port_index_in == -1 or port_index_out == -1:
        thread_running = False
        midi_ready = True
        sys.exit()

    midiout.open_port(port_index_out)
    in_port_name = midiin.open_port(port_index_in)

    midi_ready = True

    midiin.ignore_types(sysex = False, timing = False, active_sense = False)
    midiin.set_callback(midi_input_handler(in_port_name))

    while thread_running:
        try:
            message = midiout_message_queue.get(timeout = 0.4)
        except queue.Empty:
            continue
        midiout.send_message(message)


if __name__ == "__main__":
    main()
