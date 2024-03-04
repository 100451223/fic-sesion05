import threading as th
import signal
import sys
import RPi.GPIO as GPIO
import time, math

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

def button_callback(channel):
    global power_on
    power_on = not power_on
    print('Vehicle power is', 'on' if power_on else 'off')

def button_thread():
    # Button thread shall live as long as the program is runnin

    print("Button thread started")
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.RISING, callback=button_callback, bouncetime=50)
    while True:
        time.sleep(0.1)

def set_servomotor_angle(servomotor_object, angle):
    print("Setting angle to:", angle, "...")
    angle = max(0, min(180, angle))
    start = 4
    end = 12.5
    ratio = (end - start) / 180
    angle_as_percent = angle * ratio
    servomotor_object.ChangeDutyCycle(angle_as_percent)
    print("New angle set successfully!")

def servomotor_thread():

    print("Servomotor thread started")
    servomotor_object = GPIO.PWM(SERVO_GPIO, 50)
    servomotor_object.start(0)
    print("Servomotor object started")

    while power_on:
        target_angle = None
        try:
            target_angle = int(input("Enter the angle: "))
            if target_angle < 0 or target_angle > 180:
                print("Invalid angle")
                continue
        except:
            print("Invalid input")
            continue

        if target_angle is not None:
            set_servomotor_angle(servomotor_object, target_angle)

        time.sleep(1)

    print("Servomotor thread ended. Resetting servomotor...")
    servomotor_object.ChangeDutyCycle(0)
    servomotor_object.stop()


def launch_threads():
    print("Launching threads...")
    try:
        th.Thread(target=servomotor_thread, daemon=True).start()
        return 0
    except:
        return -1

    

if __name__ == "__main__":
    power_on = False
    threads_initialized = False

    setup_devices()
    
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