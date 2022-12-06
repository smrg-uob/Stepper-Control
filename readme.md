# Stepper Control
Python scripts to control a stepper motor over USB.

Two modules are provided
 - `motor_interface.py`: this script provides an interface to communicate with the stepper motor using text commands
 - `motor_control.py`: this script provides a more abstract interface to communicate with the stepper motor using Python methods


## `motor_interface.py`
As mentioned before, the `motor_interface.py` module uses String commands to communicate with and operate the stepper motor.

The example below shows how a motor interface object can be obtained:
````
from motor.motor_interface import MotorInterface

# the interface requires a COM port, and callback functions for values and messages
mi = MotorInterface('COM1', value_function, msg_function)


# Example value function (value will always be an int):
def value_function(value):
    print('Received value \": ' + str(value) + '\"')


# Example msg function (msg will always be a string):
def msg_function(msg):
    print('Received message \": ' + msg + '\"')


# Start the motor interface connection
mi.start_connection()


# Note that the motor interface requires update ticks,
# this can be done using a seperate clocking thread,
# alternatively, the update_tick() method can be called from an existing clock loop.
# Example for a dedicated thread: 

# Set to False to stop the clock
run = True


def clock_func():
    global run
    while run:
        mi.update_tick()
        time.sleep(0.01)


# Create and start the clock thread
import threading
clock_thread = threading.Thread(target=clock_func)
clock_thread.start()
````

Once an operational motor interface object is obtained, the method `mi.is_running()` can be used to check if the connection is up, and `stop_running()` to terminate the connection.
Then, to operate the motor, a set of text commands are available which can be sent using `mi.send_command(<cmd>)`, where `<cmd>` is a String representing a command from the list below.

#### Commands
- `"stepperControl"`: This is a polling command to which the stepper controller will reply 1, used to verify the presence of the controller.
- `"start"`: Tells the controller to start stepping, a feedback message is sent back.
- `"stop"`: Tells the controller to stop stepping, a feedback message is sent, as well as the number of completed steps.
- `"reset"`: Resets the motor's current step target and rotation direction, sends a feedback message, cannot be called while the motor is stepping.
- `"forwards"`: Tells the motor to rotate clockwise (default direction), sends a feedback message.
- `"backwards"`: Tells the motor to rotate anti-clockwise, sends a feedback message.
- `"getStepCount"`: Sends the current step count.
- `"getStepTarget"`: Sends the current step target.
- `"isForward"`: Sends `1` if the motor is rotating clockwise, `0` otherwise.
- `"isBackward"`: Sends `1` if the motor is rotating anti-clockwise, `0` otherwise.
- `"getDelay"`: Sends the current step delay.
- `"step <x>"`: adds `<x>` steps to the step counter, for example: `step 100` will request 100 steps. Sends a feedback message as well as the value of the current step target.
- `"delay <x>"`: Sets the current step delay to `<x>` (x must be larger than 1), for example `delay 2` will set the step delay to 2.


## `motor_control.py`
Alternatively, the `motor_control.py` module is a further abstraction from these String commands to Python functions.

The example below shows how a motor controller object can be obtained:
````
from motor.motor_control import MotorControl

# create motor controller, which requires a COM port, timeout delay, and a message callback function
mc = MotorControl('COM3', 10, msg_function)
mc.start_connection()

# await validation
if not mc.await_validation():
    print('Motor connection timed out')
    return


# Example message function
def msg_function(msg):
    print(msg)
````

Once an operational motor control object has been obtained, the motor can then be operated using the Python commands available in `motor_control.py`.

#### Commands
 - `mc.start_connection()`: opens the connection with the motor.
 - `mc.await_validation()`: waits until the motor connection has been validated or timed out.
 - `mc.stop_connection()`: stops the connection with the motor.
 - `mc.do_steps(<steps>)`: makes the motor perform `<steps>` (positive values for clockwise, negative for anti-clockwise).
 - `mc.do_steps_and_wait_finish(<steps>)`: same as `mc.do_steps(<steps>)`, but also halts program execution until stepping is completed.
 - `mc.stop_stepping()`: interrupts the motor, forcing it to stop stepping.
 - `mc.set_step_delay(<delay>)`: sets the step delay for the motor (minimum is `2`).
 - `mc.get_step_count()`: queries the motor's current step count, halts program execution until a response is received, or the motor connection times out.
 - `mc.get_step_target()`: queries the motor's current step target, halts program execution until a response is received, or the motor connection times out.
 - `mc.get_last_step_count()`: gets the latest amount of steps that were completed
 - `mc.get_last_step_command()`: gets the latest amount of steps that were sent to the motor as a command
 - `mc.is_forwards()`: queries if the motor is currently running clockwise, halts program execution until a response is received, or the motor connection times out.
 - `mc.is_backwards()`: queries the motor's currently running anti-clockwise, halts program execution until a response is received, or the motor connection times out.
 - `mc.get_delay()`: queries the motor's current step delay, halts program execution until a response is received, or the motor connection times out.
 - `mc.is_valid()`: Checks if the motor is in a valid state and not timed out.
 - `mc.is_validating()`: Checks if the motor is currently validating.
 - `mc.is_valid_or_validating()`: Checks if the motor is in a valid state, or is currently validating.
 - `mc.is_stepping()`: Checks if the motor is currently stepping.
 - `mc.send_command(<cmd>)`: Sends a String command to the motor for execution, same commands as above.
 
 
 ## Arduino
The controller uses an Arduino to interpret the commands and drive the electronics.
The code for the Arduino is provided as well under `\arduino\Stepping_Code`.
