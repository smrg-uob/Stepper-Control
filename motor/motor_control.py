import threading
import time
from motor_interface import MotorInterface


class MotorControl:
    def __init__(self, port, time_out, message_func, debug=False):
        # message callback function
        self.message_func = message_func
        # motor interface
        self.mi = MotorInterface(port, self.value_func, self.message_func)
        # state flag:
        #  -1: invalid
        #   0: validating
        #   1: standby
        #   2: await stepping
        #   3: stepping
        self.state = -1
        # direction flag
        self.forwards = True
        # step and target flag
        self.last_step_command = 0
        self.last_step_count = 0
        self.step_target = 0
        # time stamp of last command
        self.time_stamp = -1
        # time out limit
        self.time_out = time_out
        # debug mode
        self.debug = debug
        # Thread for handling values
        self.clock_thread = threading.Thread(target=self.clock_func)

    # method to handle value responses
    def value_func(self, value):
        # debug
        if self.debug:
            print('[DEBUG] Received value: \"' + str(value) + '\"')
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
            self.state = 1
            self.last_step_count = value
            pass

    # clock thread
    def clock_func(self):
        while self.mi.is_running():
            # tick the interface clock
            self.mi.update_tick()
            # own update logic
            if self.time_stamp < 0:
                # not waiting for a reply, nothing must be done
                pass
            # if we are waiting for a reply, check for timeout
            elif time.time() - self.time_stamp >= self.time_out:
                self.message_func('Connection timed out')
                # toggle flags
                self.state = -1
                self.time_stamp = -1
                # close the connection
                self.stop_connection()
            # short delay
            time.sleep(0.1)

    def start_connection(self):
        # start the connection
        self.mi.start_connection()
        # check if the connection is running
        if self.mi.is_running():
            # start the clock thread
            self.clock_thread.start()
            # perform validation test
            self.state = 0
            # short delay
            time.sleep(1)
            self.time_stamp = time.time()
            self.send_command('stepper_control')

    def await_validation(self):
        while True:
            if self.is_validating():
                # Motor is still validating, wait a bit longer
                time.sleep(1)
            else:
                # Motor has stopped validating
                if self.is_valid():
                    return True
                else:
                    return False

    def stop_connection(self):
        self.state = -1
        self.mi.stop_connection()

    def do_steps(self, steps):
        if self.is_valid():
            if self.is_stepping():
                # motor is already stepping
                if self.forwards and steps > 0:
                    # forwards: add the steps
                    self.state = 2
                    self.last_step_command += steps
                    self.send_command('step ' + str(steps))
                elif (not self.forwards) and steps < 0:
                    # backwards: add the steps
                    self.state = 2
                    self.last_step_command -= steps
                    self.send_command('step ' + str(abs(steps)))
                else:
                    self.message_func('Motor is currently stepping in the opposite direction, ignoring command')
            else:
                # check direction
                if steps < 0:
                    # tell the motor to turn backwards
                    self.forwards = False
                    self.send_command('backwards')
                elif steps > 0:
                    # tell the motor to turn forwards
                    self.forwards = True
                    self.send_command('forwards')
                else:
                    # we just ignore zero steps
                    return
                # send the number of steps
                self.last_step_count = 0
                self.last_step_command = abs(steps)
                self.send_command('step ' + str(abs(steps)))
                # start stepping
                self.state = 2
                self.time_stamp = time.time()
                self.send_command('start')

    def stop_stepping(self):
        if self.is_stepping():
            # toggle flags
            self.state = 1
            self.time_stamp = -1
            # send stop command
            self.send_command('stop')

    def set_step_delay(self, delay):
        self.send_command('delay ' + str(delay))

    def is_valid(self):
        return self.state > 0

    def is_validating(self):
        return self.state == 0

    def is_valid_or_validating(self):
        return self.state >= 0

    def is_stepping(self):
        return self.state >= 2

    def send_command(self, cmd):
        if self.debug:
            print('[DEBUG] Sending command: \"' + cmd + '\"')
        self.mi.send_command(cmd)
