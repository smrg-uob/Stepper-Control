import serial.tools.list_ports

from motor.motor_control import MotorControl
from motor.motor_interface import MotorInterface


# Creates a new motor controller object
# - port: a string specifying the COM port (e.g. 'COM3')
# - time_out: an integer specifying the time in seconds to wait until no response is considered a time-out
# - message_func: a function reference accepting a single String as parameter
# - debug: a boolean, when True, all communication with the motor will be printed to the console
def create_motor_controller(port, time_out, message_func, debug=False):
    return MotorControl(port, time_out, message_func, debug)


# Creates a new motor interface object
# - port: a string specifying the COM port (e.g. 'COM3')
# - value_func: a function reference accepting a single integer as parameter
# - confirmation_function: a function reference accepting a single integer as parameter
# - message_func: a function reference accepting a single String as parameter
def create_motor_interface(port, value_func, confirmation_function, message_func):
    return MotorInterface(port, value_func, confirmation_function, message_func)


# Lists serial port names
def list_serial_ports():
    return serial.tools.list_ports.comports()
