import logging
from time import sleep

from utility.bluetoothctl import Bluetoothctl
from evdev import InputDevice, categorize, ecodes


logger = logging.getLogger("controller")


class Controller(object):
    device = None
    raw = {}

    class State:
        a = False
        b = False
        x = False
        y = False
        l1 = False
        r1 = False
        l2 = False
        r2 = False
        l3 = False
        r3 = False
        start = False
        select = False
        rsy = 0
        rsx = 0
        lsy = 0
        lsx = 0
        up = False
        down = False
        left = False
        right = False
        menu = False

        def get(*args, **kwargs):
            return getattr(*args, **kwargs)

    def __init__(self, state):
        try:
            name = "/dev/input/event0"
            self.device = InputDevice(name)
            logger.info("up")
        except FileNotFoundError:
            logger.error(f"cannot open {name}")
        state.controller = self.State

    # dont do this here, display all the buttons in Display()
    # def __repr__(self):
    #     return "LT: RT:%s" % (self.state["RT"],)

    def get(self, button, default=False):
        return getattr(self.State, button, default)

    def update(self, state):
        if self.device:
            try:
                for event in self.device.read():
                    self.receive_event(event, state)
            except BlockingIOError:
                pass

    # mapping for an 8bitdo sn30 pro
    def receive_event(self, event, state):
        self.raw[event.code] = event.value

        # print(categorize(event))
        # print(event.value)

        if event.code == 305:  # east
            self.State.a = event.value == 1

        elif event.code == 304:  # south
            self.State.b = event.value == 1

        elif event.code == 307:  # north
            self.State.x = event.value == 1

        elif event.code == 306:  # west
            self.State.y = event.value == 1

        elif event.code == 308:
            self.State.l1 = event.value == 1

        elif event.code == 309:
            self.State.r1 = event.value == 1

        elif event.code == ecodes.ABS_Z:
            self.State.l2 = event.value > 0

        elif event.code == ecodes.ABS_RZ:
            self.State.r2 = event.value > 0

        elif event.code == 312:
            self.State.l3 = event.value > 0

        elif event.code == 313:
            self.State.r3 = event.value > 0

        elif event.code == 310:
            self.State.select = event.value == 1

        elif event.code == 311:
            self.State.start = event.value == 1

        elif event.code == ecodes.ABS_RY:
            self.State.rsy = -(event.value - 32768)

        elif event.code == ecodes.ABS_RX:
            self.State.rsx = (event.value - 32768)

        elif event.code == ecodes.ABS_Y:
            self.State.lsy = -(event.value - 32768)

        elif event.code == ecodes.ABS_X and event.type == 3:
            self.State.lsx = (event.value - 32768)

        elif event.code == ecodes.ABS_HAT0Y:
            self.State.up = event.value == -1
            self.State.down = event.value == 1

        elif event.code == ecodes.ABS_HAT0X:
            self.State.left = event.value == -1
            self.State.right = event.value == 1

        elif event.code == ecodes.KEY_MENU:
            self.State.menu = event.value > 0
            if self.State.menu:
                state.running = False

    def down(self):
        if self.device:
            self.device.close()
            self.device = None
        logger.info("down")