// Pin IDs
const int PIN_MOTOR_STEP = 3;
const int PIN_MOTOR_REV = 4;

// command tracking fields
String cmd = "";
bool hasCmd = false;

// status field
//  - 0: standby
//  - 1: running
int mode = 0;

// stepping parameters
int stepCounter = 0;
int stepTarget = 0;
int stepDelay = 5;
bool forward = true;


// method is ran once to initialize the script
void setup() {
  // configure pins
  pinMode(PIN_MOTOR_STEP, OUTPUT);
  pinMode(PIN_MOTOR_REV, OUTPUT);
  // open serial
  Serial.begin(9600);
  // reserve 200 bytes for the command string:
  cmd.reserve(200);
}


// method is called continuously
void loop() {
  // check for a command
  if (hasCmd) {
      // parse the command
      handleCommand();
  } else {
    // perform the logic
    switch(mode) {
      case 0:
        // idle
        break;
      case 1:
        // run logic
        run();
        break;
    }
  }
}


// method is called when serial input is arriving
void serialEvent() {
  // only read serial when it is available
  while(Serial.available()) {
    // read the serial
    char inputChar = (char) Serial.read();
    // check if it is an end of line
    if (inputChar == '\n') {
      // command is complete
      hasCmd = true;
    } else {
      // append it to the commmand
      cmd = cmd + inputChar;
    }
  }
}

// method to handle the commands
void handleCommand() {
  if (!parseCommand()) {
    sendMessage("Invalid command.");
  }  
  // reset the command
  cmd = "";
  hasCmd = false;
}


// method to parse commands
bool parseCommand() {
  // Polling command to confirm the presence of the controller
  if (cmd.equals("stepper_control")) {
    sendConfirmation(1);
    return true;
  }
  // Command to start stepping
  if (cmd.equals("start")) {
    if (mode != 1) {
      // toggle mode to running
      mode = 1;
      // log a message
      String msg = "Stepping ";
      msg = msg + stepTarget + " steps";
      sendMessage(msg);
    } else {
      sendMessage("Already running.");
    }
    return true;
  }
  // Command to stop stepping
  if (cmd.equals("stop")) {
    if (mode == 0) {
      sendMessage("Already in standby.");
    } else {
      // toggle mode to standby    
      sendMessage("Stopping");
      stop();
    }
    return true;
  }
  // Command to reset the step target
  if (cmd.equals("reset")) {
    if (mode == 1) {
      sendMessage("Cannot reset while running.");
    } else {
      sendMessage("Reset state.");
      reset();
    }
    return true;
  }
  // Command to run the motor forwards
  if (cmd.equals("forwards")) {
    // set motor to forwards
    forwards();
    sendMessage("Motor set forward");
    return true;
  }
  // Command to run the motor backwards
  if (cmd.equals("backwards")) {
    // set motor to backwards
    backwards();
    sendMessage("Motor set backward");
    return true;
  }
  // command to get the current step counter
  if (cmd.equals("getStepCount")) {
    sendValue(stepCounter);
    return true;
  }
  // command to get the current step target
  if (cmd.equals("getStepTarget")) {
    sendValue(stepTarget);
    return true;
  }
  // command to check if the motor is currently set to forwards
  if (cmd.equals("isForward")) {
    sendValue(forward);
    return true;
  }
  // command to check if the motor is currently set to backwards
  if (cmd.equals("isBackward")) {
    sendValue(!forward);
    return true;
  }
  // command to get the current step delay
  if (cmd.equals("getDelay")) {
    sendValue(stepDelay);
    return true;
  }
  // Command to add a number of steps to the step target
  if (cmd.indexOf("step ") == 0) {
    // parse steps
    String stepString = cmd.substring(5, cmd.length());
    int steps = stepString.toInt();
    if (steps > 0) {
      // add the steps to the target
      stepTarget = stepTarget + steps;
      // send a confirmation the current step target
      sendConfirmation(stepTarget);
    }
    return true;
  }
  // Command to set the delay between the steps
  if (cmd.indexOf("delay " == 0)) {
    sendMessage(cmd);
    // parse delay
    String delayString = cmd.substring(6, cmd.length());
    int delay = delayString.toInt();
    if (delay > 1) {
      // set the delay
      stepDelay = delay;
    } else {
      // send a message in case of invalid delay
      sendMessage("Delay must be larger than 1 (minimum 2)");
    }
    return true;
  }
  return false;
}


// method to stop stepping
void stop() {
      // Send a confirmation of the number of steps
      sendConfirmation(stepCounter);
      // Log a message
      String msg = "Stopped after ";
      sendMessage(msg + stepCounter + "/" + stepTarget + " steps.");
      // Reset the state
      reset();
}


// method to run main logic
void run() {
  if (stepTarget > 0) {
    // step
    step();
    // increment the step counter
    stepCounter = stepCounter + 1;
    // check if step target is reached
    if (stepCounter >= stepTarget) {
      // Send a confirmation of the number of steps
      sendConfirmation(stepCounter);
      // Log a message
      String msg = "Completed ";
      sendMessage(msg + stepCounter + " steps.");
      // Reset the state
      reset();
    }
  } else {
    // Reset the state
    reset();
  }
}


// method to reset the state
void reset() {
    mode = 0;
    stepTarget = 0;
    stepCounter = 0;
}


// method to run one step
void step() {
  digitalWrite(PIN_MOTOR_STEP, HIGH);
  delay(stepDelay);
  digitalWrite(PIN_MOTOR_STEP, LOW);
  delay(stepDelay);
}


// method to make the motor run forwards
void forwards() {
  forward = true;
  digitalWrite(PIN_MOTOR_REV, LOW);
}


// method to make the motor run backwards
void backwards() {
  forward = false;
  digitalWrite(PIN_MOTOR_REV, HIGH);
}


// method to send a message
void sendMessage(String msg) {
  Serial.println("[m]" + msg);
}


// method to send a value
void sendValue(int value) {
  String msg = "[v]";
  Serial.println(msg + value);
}


// method to send a confirmation
void sendConfirmation(int value) {
  String msg = "[c]";
  Serial.println(msg + value);
}
