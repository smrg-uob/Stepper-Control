import threading
import time
from motor_interface import MotorInterface


# Class to control the stepper motor using Python commands
class MotorControl:
    def __init__(self, port, time_out, message_func, debug=False):
        # message callback function
        self.message_func = message_func
        # motor interface
        self.mi = MotorInterface(port, self.__value_func, self.__confirm_func, self.message_func)
        # state flag:
        #  -1: invalid
        #   0: validating
        #   1: standby
        #   2: await stepping
        #   3: stepping
        self.state = -1
        # command callbacks
        self.command_callbacks = []
        # direction flag
        self.forwards = True
        # step and target flag
        self.last_step_command = 0
        self.last_step_count = -1
        self.step_target = 0
        # time stamp of last command
        self.time_stamp = -1
        # time out limit
        self.time_out = time_out
        # debug mode
        self.debug = debug
        # Thread for handling values
        self.clock_thread = threading.Thread(target=self.__clock_func)

    # method to handle value responses, internal use only, do not call
    def __value_func(self, value):
        # debug
        if self.debug:
            self.message_func('[DEBUG] Received value: \"' + str(value) + '\"')
        if len(self.command_callbacks) > 0:
            # command reply
            command = self.command_callbacks.pop(0)
            command.accept_value(value)
        else:
            self.message_func('Error: received a value without commands')

    # method to handle confirmation responses, internal use only, do not call
    def __confirm_func(self, value):
        # note: Python 2.7 does not have switch case statements yet
        if self.state == -1:
            # Invalid
            return
        elif self.state == 0:
            # validating
            if value == 1:
                # validation passed
                self.state = 1
                self.time_stamp = -1
        elif self.state == 1:
            # standby, do nothing
            pass
        elif self.state == 2:
            # update the step target
            self.step_target = value
            # start stepping
            self.state = 3
            self.time_stamp = -1
        elif self.state == 3:
            # finished stepping
            self.last_step_count = value
            self.state = 1

    # Clock thread function, internal use only, do not call
    def __clock_func(self):
        while self.mi.is_running():
            # tick the interface clock
            self.mi.update_tick()
            # own update logic
            if self.time_stamp < 0:
                # not waiting for a reply, nothing must be done
                pass
            # if we are waiting for a confirmation reply, check for timeout
            elif time.time() - self.time_stamp >= self.time_out:
                # log message
                self.message_func('Connection timed out')
                # toggle flags
                self.state = -1
                self.time_stamp = -1
                # return 'None' on the callbacks
                for command in self.command_callbacks:
                    command.accept_value(None)
                    self.command_callbacks.remove(command)
                # close the connection
                self.stop_connection()
                return
            # check commands for time outs
            for command in self.command_callbacks:
                if command.is_timed_out(self.time_out):
                    command.accept_value(None)
                    self.command_callbacks.remove(command)
            # short delay
            time.sleep(0.1)
        # no longer running: toggle the state:
        self.message_func('Connection lost')
        # toggle flags
        self.state = -1
        self.time_stamp = -1

    # sends a String command to the motor for interpretation, internal use only, do not call
    def __send_string_command(self, cmd):
        if self.debug:
            self.message_func('[DEBUG] Sending command: \"' + cmd + '\"')
        self.mi.send_command(cmd)

    # submits a String command for sending, expecting a reply, internal use only, do not call
    def __submit_value_command(self, command_string):
        # create a value command
        command_object = _ValueCommand()
        # submit the command
        self.__submit_command(command_string, command_object)
        # return the command
        return command_object

    # submits a command, internal use only, do not call
    def __submit_command(self, command_string, command):
        # check if there is a valid connection
        if self.is_valid():
            # add the command to the queue
            self.command_callbacks.append(command)
            # send the string command
            self.__send_string_command(command_string)
        else:
            # if there is not a valid connection, give the command a None reply
            command.accept_value(None)

    # waits for a response or time_out, internal use, do not call

    # waits for a reply on a value command
    def __wait_for_reply_or_time_out(self, value_command):
        # check if it is an actual value command
        if isinstance(value_command, _ValueCommand):
            while True:
                if value_command.has_reply():
                    return value_command.get_value()
                if value_command.is_timed_out(self.time_out):
                    return None
        # default to returning None
        return None

    # get the port used for communicating
    def get_port(self):
        return self.mi.get_port()

    # starts up the connection with the motor
    def start_connection(self):
        # start the connection
        running = self.mi.start_connection()
        # check if the connection is running
        if running:
            # start the clock thread
            self.clock_thread.start()
            # short delay
            time.sleep(1)
            # perform validation test
            self.state = 0
            self.time_stamp = time.time()
            self.__send_string_command('stepper_control')
        return running

#    # halts program execution until the motor connection has been validated or timed out
#    def await_validation(self):
#        while True:
#            if self.is_validating():
#                # Motor is still validating, wait a bit longer
#                time.sleep(1)
#            else:
#                # Motor has stopped validating
#                if self.is_valid():
#                    return True
#                else:
#                    return False

    # stops the motor connection
    def stop_connection(self):
        self.state = -1
        self.mi.stop_connection()
        # clear all commands
        for command in self.command_callbacks:
            command.accept_value(None)
        self.command_callbacks = []

    # sends a command to the motor to execute a number of steps
    # only works if the motor is not currently stepping, or already stepping in the same direction
    # pass in positive value to step clockwise, a negative value to step anti-clockwise
    def do_steps(self, steps):
        if self.is_valid():
            if self.is_stepping():
                # motor is already stepping
                if self.forwards and steps > 0:
                    # forwards: add the steps
                    self.state = 2
                    self.last_step_command += steps
                    self.__send_string_command('step ' + str(steps))
                elif (not self.forwards) and steps < 0:
                    # backwards: add the steps
                    self.state = 2
                    self.last_step_command -= steps
                    self.__send_string_command('step ' + str(abs(steps)))
                else:
                    self.message_func('Motor is currently stepping in the opposite direction, ignoring command')
            else:
                # check direction
                if steps < 0:
                    # tell the motor to turn backwards
                    self.forwards = False
                    self.__send_string_command('backwards')
                elif steps > 0:
                    # tell the motor to turn forwards
                    self.forwards = True
                    self.__send_string_command('forwards')
                else:
                    # we just ignore zero steps
                    return
                # send the number of steps
                self.last_step_count = -1
                self.last_step_command = abs(steps)
                self.__send_string_command('step ' + str(abs(steps)))
                # start stepping
                self.state = 2
                self.time_stamp = time.time()
                self.__send_string_command('start')

    # same as 'do_steps()', but also halts program execution until the motor has finished stepping
    def do_steps_and_wait_finish(self, steps):
        # do the steps
        self.do_steps(steps)
        # wait until done stepping
        while self.is_stepping():
            # wait
            time.sleep(0.05)
        # return the number of steps
        return self.last_step_count

    # sends a command to the motor to stop stepping
    def stop_stepping(self):
        if self.is_stepping():
            # toggle flags
            self.state = 3
            self.time_stamp = -1
            # send stop command
            self.__send_string_command('stop')

    # sets the stepping delay, minimum value is 2
    def set_step_delay(self, delay):
        self.__send_string_command('delay ' + str(delay))

    # sends a command to the motor to query its current step count
    # halts program execution until a reply has been received, or the connection has timed out
    # returns None if the connection has been lost or is timed out
    def get_step_count(self):
        # send the command
        command = self.__submit_value_command('getStepCount')
        # wait for response or timeout
        return self.__wait_for_reply_or_time_out(command)

    # gets the latest amount of steps that were completed
    def get_last_step_count(self):
        return self.last_step_count

    # gets the latest amount of steps that were sent to the motor as a command
    def get_last_step_command(self):
        return self.last_step_command

    # sends a command to the motor to query its current step target
    # halts program execution until a reply has been received, or the connection has timed out
    # returns None if the connection has been lost or is timed out
    def get_step_target(self):
        # send the command
        command = self.__submit_value_command('getStepTarget')
        # wait for response or timeout
        return self.__wait_for_reply_or_time_out(command)

    # sends a command to the motor to query if it's running clockwise
    # halts program execution until a reply has been received, or the connection has timed out
    # returns None if the connection has been lost or is timed out
    def is_forwards(self):
        # send the command
        command = self.__submit_value_command('isForward')
        # wait for response or timeout
        return self.__wait_for_reply_or_time_out(command)

    # sends a command to the motor to query if it's running anti-clockwise
    # halts program execution until a reply has been received, or the connection has timed out
    # returns None if the connection has been lost or is timed out
    def is_backwards(self):
        # send the command
        command = self.__submit_value_command('isBackward')
        # wait for response or timeout
        return self.__wait_for_reply_or_time_out(command)

    # sends a command to the motor to query its current step delay
    # halts program execution until a reply has been received, or the connection has timed out
    # returns None if the connection has been lost or is timed out
    def get_delay(self):
        # send the command
        command = self.__submit_value_command('getDelay')
        # wait for response or timeout
        return self.__wait_for_reply_or_time_out(command)

    # polls the step count by sending a command to query its current step count
    # the callback function is called whenever the reply is received
    # the callback will be called with 'None' if the connection is been lost or timed out
    def poll_step_count(self, callback):
        # submit the command
        self.__submit_command('getStepCount', _Command(callback))

    # polls the step target by sending a command to query its current step target
    # the callback function is called whenever the reply is received
    # the callback will be called with 'None' if the connection is been lost or timed out
    def poll_step_target(self, callback):
        # submit the command
        self.__submit_command('getStepTarget', _Command(callback))

    # polls the forwards state by sending a command to query if it's currently running clockwise
    # the callback function is called whenever the reply is received
    # the callback will be called with 'None' if the connection is been lost or timed out
    def poll_forwards(self, callback):
        # submit the command
        self.__submit_command('isForward', _Command(callback))

    # polls the backwards state by sending a command to query if it's currently running anti-clockwise
    # the callback function is called whenever the reply is received
    # the callback will be called with 'None' if the connection is been lost or timed out
    def poll_backwards(self, callback):
        # submit the command
        self.__submit_command('isBackward', _Command(callback))

    # polls the step delay by sending a command to query its current step delay
    # the callback function is called whenever the reply is received
    # the callback will be called with 'None' if the connection is been lost or timed out
    def poll_delay(self, callback):
        # submit the command
        self.__submit_command('getDelay', _Command(callback))

    # checks if the motor control is in a valid state, meaning it is connected to the controller with an open connection
    def is_valid(self):
        return self.state > 0

    # checks if the motor control is currently validating, meaning it is not yet in a valid state, but might be soon
    def is_validating(self):
        return self.state == 0

    # checks if the motor control is currently valid, or still validating
    def is_valid_or_validating(self):
        return self.state >= 0

    # checks if the motor is currently stepping
    def is_stepping(self):
        return self.state >= 2


# Helper class to treat and queue commands to the motor
class _Command:
    def __init__(self, callback):
        self.callback = callback
        self.reply = False
        self.time_stamp = time.time()

    # called when a reply has been received
    def accept_value(self, value):
        self.callback(value)
        self.reply = True

    # checks if a reply has been received
    def has_reply(self):
        return self.reply

    # checks if the command has timed out
    def is_timed_out(self, limit):
        return (time.time() - self.time_stamp) > limit


# Helper class to treat and queue commands to the motor, storing the reply on the object itself
class _ValueCommand(_Command):
    def __init__(self):
        # call super constructor
        _Command.__init__(self, self.set_value)
        # initialize field for reply value
        self.value = None

    # setter for the reply value
    def set_value(self, value):
        self.value = value

    # getter for the reply value
    def get_value(self):
        return self.value
