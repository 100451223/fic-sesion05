import threading as th
import signal
import sys
import RPi.GPIO as GPIO
import time, math
from command_reader import load_commands

BUTTON_GPIO = 16
LDR_GPIO = 4
TRIGGER_GPIO = 23
ECHO_GPIO = 24
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
    GPIO.setup(LDR_GPIO, GPIO.IN)
    GPIO.setup(TRIGGER_GPIO, GPIO.OUT)
    GPIO.setup(ECHO_GPIO, GPIO.IN)
    GPIO.setup(CC_MOTOR_ENABLE, GPIO.OUT)
    GPIO.setup(CC_MOTOR_INPUT_A, GPIO.OUT)
    GPIO.setup(CC_MOTOR_INPUT_B, GPIO.OUT)
    GPIO.setup(SERVO_GPIO, GPIO.OUT)

def get_luminosity(PIN_LDR):
    count = 0

    GPIO.setup(PIN_LDR, GPIO.OUT)
    GPIO.output(PIN_LDR, GPIO.LOW)
    time.sleep(0.1)

    # Change the pin back to input
    GPIO.setup(PIN_LDR, GPIO.IN)

    # Count until the pin goes high
    while (GPIO.input(PIN_LDR) == GPIO.LOW):
        count += 1

    return count

def get_distance(PIN_TRIGGER, PIN_ECHO):
    # Initialize the trigger pin to low
    GPIO.output(PIN_TRIGGER, GPIO.LOW)
    time.sleep(0.5)

    GPIO.output(PIN_TRIGGER, GPIO.HIGH)
    # 0.01 miliseconds
    time.sleep(0.00001)
    GPIO.output(PIN_TRIGGER, GPIO.LOW)

    pulse_start = time.time()
    while GPIO.input(PIN_ECHO) == GPIO.LOW:
        pulse_start = time.time()

    pulse_end = time.time()
    while GPIO.input(PIN_ECHO) == GPIO.HIGH:
        pulse_end = time.time()

    # If the pulse_end is greater than pulse_start, then calculate the distance
    pulse_duration = pulse_end - pulse_start

    return pulse_duration * 17150

def print_luminosity(light_count):
    MAX = 1000000
    # Ensure light is not zero to avoid math error
    if light_count == 0:
        light_count = 1

    # Calculate logarithmic scale.
    log_light = math.log10(light_count)

    # Normalize log_light to the range 0-1
    normalized_light = log_light / math.log10(MAX)

    print("Luminosity:")
    print("\t|" + ("#" * int(40 * (1 - normalized_light))) + (" " * int(40 * normalized_light)) + "|")
    print("\tCapacitor charge count:", light_count)

# def button_callback(channel):
#     global power_on

#     # Check if button is pressed
#     if not GPIO.input(BUTTON_GPIO):
#         power_on = not power_on

#     print('Vehicle power is', 'on' if power_on else 'off')

def button_thread():
    # Button thread shall live as long as the program is runnin
    global power_on

    print("Button thread started")
    # GPIO.add_event_detect(BUTTON_GPIO, GPIO.RISING, callback=button_callback, bouncetime=50)
    while True:
        if not GPIO.input(BUTTON_GPIO):
            power_on = not power_on
            time.sleep(0.5)
        time.sleep(0.1)

def luminosity_thread():
    global power_on

    print("Luminosity sensor thread started")
    while power_on:
        print_luminosity(get_luminosity(LDR_GPIO))
        time.sleep(0.1)

def distance_thread():
    global power_on

    print("Distance sensor thread started")
    while power_on:
        print("Distance:", get_distance(TRIGGER_GPIO, ECHO_GPIO), "cm")
        time.sleep(0.1)

def ask_for_motor_speed(lower_limit=0, upper_limit=120):
    while True:
        try:
            speed = int(input("Enter speed (0-100): "))
            if speed < lower_limit or speed > upper_limit:
                print("Speed must be between 0 and 100")
                continue
            break
        except:
            print("Invalid input. Please enter a number")
    return speed

def set_servomotor_angle(angle):
    print("Setting angle to:", angle, "...")
    angle = max(0, min(180, angle))
    start = 2
    end = 12
    ratio = (end - start) / 180
    angle_transformed = angle * ratio + start
    # angle_as_percent = angle / 180 + 2
    servomotor_object.ChangeDutyCycle(angle_transformed)
    print("New angle set successfully!")

def setup_dc_motor():
    GPIO.output(CC_MOTOR_INPUT_A, True)
    GPIO.output(CC_MOTOR_INPUT_B, False)
    GPIO.output(CC_MOTOR_ENABLE, True)

def turn_off_dc_motor():
    GPIO.output(CC_MOTOR_INPUT_A, False)
    GPIO.output(CC_MOTOR_INPUT_B, False)
    GPIO.output(CC_MOTOR_ENABLE, False)

def motor_thread():
    global power_on
    print("Motor thread started")

    print("Starting engine...")
    # Start DC motor
    setup_dc_motor()
    dc_motor_object.start(0)
    dc_motor_object.ChangeDutyCycle(0)
    # Start Servomotor
    servomotor_object.start(0)
    set_servomotor_angle(90)
    print("Engine started successfully!")
    command_time = 0
    last_command = None
    while power_on:
        if command_time >= commands[0]["Time"]:
            print("Current command:", commands[0])
            set_servomotor_angle(commands[0]["SteeringAngle"])
            dc_motor_object.ChangeDutyCycle(commands[0]["Speed"])
            command_time = 0
            last_command = commands.pop(0)
        command_time += 0.1
        time.sleep(0.1)
    if last_command is not None and last_command["Time"] > command_time:
        last_command["Time"] = last_command["Time"] - command_time
        commands.insert(0, last_command)

    print("Stopping engine...")
    dc_motor_object.stop()
    dc_motor_object.ChangeDutyCycle(0)
    turn_off_dc_motor()


def launch_threads():
    print("Launching threads...")
    try:
        # th.Thread(target=luminosity_thread, daemon=True).start()
        # th.Thread(target=distance_thread, daemon=True).start()
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
