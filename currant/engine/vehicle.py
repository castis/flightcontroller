import time
import logging
import collections
import itertools

import sensors
from utility import PID, GPIO


logger = logging.getLogger("vehicle")
mpu9250 = sensors.MPU9250()


blank_mag = {"x": 0, "y": 0, "z": 0}


class Vehicle(object):
    # accel = None
    # gyro = None
    throttle = 0
    # altitude = 0

    def __init__(self, state):
        # if len(motor_pins) != 4:
        #     raise Exception('incorrect number of motor pins given')

        self.motors = [Motor(pin=pin) for pin in state.motor_pins]

        # one for each measurement we control
        # self.throttle = 0

        self.throttle = PID(p=1, i=0.1, d=0)
        self.pitch = PID(p=1, i=0.1, d=0)
        self.roll = PID(p=1, i=0.1, d=0)
        self.yaw = PID(p=1, i=0.1, d=0)

        # altimeter 1
        # self.hcsr04 = sensors.HCSR04()

        self.accel = mpu9250.readAccel()
        self.gyro = mpu9250.readGyro()
        magnet = mpu9250.readMagnet()

        # only like every 3rd mag read or so comes back with data
        if magnet != blank_mag:
            self.magnet = magnet

        logger.info("up")

    def update(self, state):
        self.accel = mpu9250.readAccel()
        self.gyro = mpu9250.readGyro()

        magnet = mpu9250.readMagnet()
        if magnet != blank_mag:
            self.magnet = magnet

        # self.altitude = self.hcsr04.altitude

        # throttle_in = engine.input.get("RT")
        # throttle_in = 0

        # self.throttle.tick((throttle_in / 255) * 100)
        # self.apply_throttle(self.throttle)

        # if throttle_in > 0:
        #     pitch_delta = self.pitch(self.accel["x"], state.chronograph.delta)
        #     self.apply_pitch(pitch_delta)

        #     roll_delta = self.roll(self.accel["y"], state.chronograph.delta)
        #     self.apply_roll(roll_delta)

        #     yaw_delta = self.yaw(self.accel["y"], state.chronograph.delta)
        #     self.apply_roll(yaw_delta)

        for motor in self.motors:
            motor.tick()

    def apply_throttle(self, throttle):
        for motor in self.motors:
            motor.throttle = throttle

    def apply_pitch(self, delta):
        # pass
        self.motors[0].throttle -= delta * 100
        self.motors[1].throttle -= delta * 100
        self.motors[2].throttle += delta * 100
        self.motors[3].throttle += delta * 100

    def apply_roll(self, delta):
        # pass
        self.motors[0].throttle -= delta * 100
        self.motors[2].throttle -= delta * 100
        self.motors[1].throttle += delta * 100
        self.motors[3].throttle += delta * 100

    def apply_yaw(self, delta):
        # pass
        self.motors[0].throttle -= delta * 100
        self.motors[3].throttle -= delta * 100
        self.motors[1].throttle += delta * 100
        self.motors[2].throttle += delta * 100

    def down(self):
        self.apply_throttle(0)
        for motor in self.motors:
            motor.tick()

        # self.hcsr04.down()

        GPIO.cleanup()

        logger.info("down")


class Motor(object):
    """
    values below 20 produce what appears to be an alarming beep
    and values above like 90 dont produce much of a change
    so keep a range and adjust the throttle within it
    """

    min_duty_cycle = 30
    max_duty_cycle = 80
    duty_cycle_range = None
    pin = None
    throttle = 0
    dc = 0

    def __init__(self, pin=None):
        self.duty_cycle_range = self.max_duty_cycle - self.min_duty_cycle
        GPIO.setup(pin, GPIO.OUT)

        # 500hz appears to reduce the amount of popping from the motor
        # as long as a prop is installed
        self.pin = GPIO.PWM(pin, 500)
        self.pin.start(self.min_duty_cycle)

    def tick(self):
        duty_cycle = int(
            self.min_duty_cycle + (self.throttle * self.duty_cycle_range / 100)
        )
        duty_cycle = max(min(self.max_duty_cycle, duty_cycle), self.min_duty_cycle)

        self.dc = duty_cycle
        self.pin.ChangeDutyCycle(duty_cycle)
