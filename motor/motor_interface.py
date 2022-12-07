import serial
import threading
import time
import traceback
from serial.serialutil import SerialException


# Class to interface with the stepper motor using String commands
class MotorInterface:
    def __init__(self, port, value_func, message_func):
        # Serial
        self.port = port
        self.ser = None
        # Run flag
        self.running = False
        # Buffers
        self.command_buffer = []
        self.value_buffer = []
        # Callbacks
        self.value_func = value_func
        self.message_func = message_func
        # Thread for reading messages
        self.read_thread = threading.Thread(target=self.__read_func)
        # Thread for writing messages
        self.write_thread = threading.Thread(target=self.__write_func)

    # method for reading, to be ran on a separate thread, internal use only, do not call
    def __read_func(self):
        while self.running:
            # read the line
            try:
                ln = self.ser.readline()
            except SerialException:
                self.message_func('Error while reading serial port ' + str(self.get_port()))
                self.message_func(traceback.format_exc())
                self.running = False
                continue
            if ln == '' or ln is None:
                # if the line is empty, simply do nothing
                continue
            else:
                # if the line starts with a prefix, handle accordingly
                prefix = ln[0:3]
                if prefix == '[m]':
                    # handle the message
                    self.__handle_message(ln[3:])
                elif prefix == '[v]':
                    # handle a value
                    try:
                        self.__handle_value(int(ln[3:]))
                    except ValueError:
                        self.__handle_invalid_value(ln[3:])
            # short delay
            time.sleep(0.05)

    # method for writing, to be ran on a separate thread, internal use only, do not call
    def __write_func(self):
        while self.running:
            # if there are commands to send, send them one by one
            if len(self.command_buffer) > 0:
                # get the next command
                command = self.command_buffer.pop(0)
                # send it
                try:
                    self.ser.write(command + '\n')
                except SerialException:
                    self.message_func('Error sending command \"' + command + '\" over  port ' + str(self.get_port()))
                    self.message_func(traceback.format_exc())
                    self.running = False
            # short delay
            time.sleep(0.05)

    # method to handle feedback, internal use only, do not call
    def __handle_message(self, message):
        self.message_func(message.rstrip())

    # method to handle value replies, internal use only, do not call
    def __handle_value(self, value):
        # we need a buffer here to handle them on the main thread
        self.value_buffer.append(value)

    # method to handle invalid values, internal use only, do not call
    def __handle_invalid_value(self, message):
        self.__handle_message(("Received invalid value: " + str(message)))

    # get the port used for communicating
    def get_port(self):
        return self.port

    # tick loop method, must be called externally
    def update_tick(self):
        if len(self.value_buffer) > 0:
            # Make a copy of the value buffer and reset it
            values = self.value_buffer[:]
            self.value_buffer = []
            # Handle all values
            for value in values:
                self.value_func(value)

    # logs a command to be sent
    def send_command(self, cmd):
        self.command_buffer.append(cmd)

    # method to start the connection
    def start_connection(self):
        if self.ser is None:
            try:
                self.ser = serial.Serial(port=self.port, baudrate=9600, timeout=0.1)
            except SerialException:
                print(traceback.format_exc())
                self.ser = None
                return False
            # start the threads
            self.running = True
            self.read_thread.start()
            self.write_thread.start()
            return True
        return self.running

    # method to stop the connection
    def stop_connection(self):
        self.running = False
        if self.ser is not None:
            self.ser.close()

    # method to check if the connection is running
    def is_running(self):
        return self.running

