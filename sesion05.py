import threading as th
import signal
import sys
import RPi.GPIO as GPIO
import time
from command_reader import load_commands

BUTTON_GPIO = 16
CC_MOTOR_ENABLE = 13
CC_MOTOR_INPUT_A = 5 # Input 1
CC_MOTOR_INPUT_B = 6 # Input 2
SERVO_GPIO = 26

def signal_handler(sig, frame):
    global power_on

    print("Exiting program.\nThank you for playing!")
    power_on = False
    GPIO.cleanup()
    sys.exit(0)

def setup_devices():
    print("Setting up devices")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(CC_MOTOR_ENABLE, GPIO.OUT)
    GPIO.setup(CC_MOTOR_INPUT_A, GPIO.OUT)
    GPIO.setup(CC_MOTOR_INPUT_B, GPIO.OUT)
    GPIO.setup(SERVO_GPIO, GPIO.OUT)

def button_thread():
    # Button thread shall live as long as the program is runnin
    global power_on

    print("Button thread started")
    while True:
        if not GPIO.input(BUTTON_GPIO):
            power_on = not power_on
            time.sleep(0.5)
        time.sleep(0.1)

def set_servomotor_angle(angle):
    print("Setting angle to:", angle, "...")
    angle = max(0, min(180, angle))
    start = 2
    end = 12
    ratio = (end - start) / 180
    angle_transformed = angle * ratio + start
    servomotor_object.ChangeDutyCycle(angle_transformed)
    print("New angle set successfully!")

def initialize_dc_motor():
    GPIO.output(CC_MOTOR_INPUT_A, True)
    GPIO.output(CC_MOTOR_INPUT_B, False)
    GPIO.output(CC_MOTOR_ENABLE, True)
    dc_motor_object.start(0)
    dc_motor_object.ChangeDutyCycle(0)

def turn_off_dc_motor():
    dc_motor_object.stop()
    dc_motor_object.ChangeDutyCycle(0)
    GPIO.output(CC_MOTOR_INPUT_A, False)
    GPIO.output(CC_MOTOR_INPUT_B, False)
    GPIO.output(CC_MOTOR_ENABLE, False)

def motor_thread():
    global power_on
    print("Motor thread started")
    print("Starting engine...")
    # Start DC motor
    initialize_dc_motor()
    # Start Servomotor
    servomotor_object.start(0)
    set_servomotor_angle(90)
    print("Engine started successfully!")
    # Start the main loop
    command_time = 0
    last_command = None
    while power_on:
        # If is the first command or the time of the current command has been reached
        if last_command is None or command_time >= last_command["Time"]:
            if len(commands) == 0:
                break
            print("Current command:", commands[0])
            # Set servo angle
            set_servomotor_angle(commands[0]["SteeringAngle"])
            # Set DC motor speed
            dc_motor_object.ChangeDutyCycle(commands[0]["Speed"])
            # Reset the time and save the current command
            command_time = 0
            last_command = commands.pop(0)
        command_time += 0.1
        time.sleep(0.1)
    # Calculate the remaining time of the last command
    if last_command is not None and last_command["Time"] > command_time:
        last_command["Time"] = last_command["Time"] - command_time
        commands.insert(0, last_command)

    print("Stopping engine...")
    turn_off_dc_motor()

def launch_threads():
    print("Launching threads...")
    try:
        th.Thread(target=motor_thread, daemon=True).start()
        return 0
    except:
        return -1

if __name__ == "__main__":
    power_on = False
    threads_initialized = False
    setup_devices()
    servomotor_object = GPIO.PWM(SERVO_GPIO, 50)
    dc_motor_object = GPIO.PWM(CC_MOTOR_ENABLE, 100)
    commands = load_commands()

    signal.signal(signal.SIGINT, signal_handler)

    # Start button thread
    th.Thread(target=button_thread, daemon=True).start()
    while True:
        if power_on:
            if not threads_initialized:
                if(launch_threads() == 0):
                    threads_initialized = True
                else:
                    print("[ERROR] Something went wrong while initializing the threads")
                    break
        else:
            threads_initialized = False
        time.sleep(0.1)
