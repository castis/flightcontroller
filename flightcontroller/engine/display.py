import curses
import io
import logging
import os
import psutil


process = psutil.Process(os.getpid())
logger = logging.getLogger('display')


class Display(object):
    screen = None

    def up(self):
        logger.info('up')
        self.screen = curses.initscr()

        # no cursor
        curses.curs_set(0)

        # turn off echoing of keys, and enter cbreak mode,
        # where no buffering is performed on keyboard input
        # curses.noecho()

        # in keypad mode, escape sequences for special keys
        # (like the cursor keys) will be interpreted and
        # a special value like curses.KEY_LEFT will be returned
        self.screen.keypad(1)
        self.screen.nodelay(1)

        # harmless if the terminal doesn't have color;
        # user can test with has_color() later on. the try/catch
        # works around a minor bit of over-conscientiousness in the curses
        # module -- the error return from C start_color() is ignorable.
        try:
            curses.start_color()
        except:
            pass

        self.engine_display = "engine:\n" \
            + " time: {time:.1f}\n" \
            + " sleep: {sleep:.1f}\n" \
            + " run time: {run_time}\n" \
            + " fps: {fps:.1f}\n" \
            + " memory used: {mem:.2f} MiB\n" \
            + " throttle: {throttle:.2f}\n"
        # + " altitude: {altitude:.2f} cm"

        self.motor_screen = curses.newwin(5, 20, 0, 30)
        self.motor_display = "motors:\n" \
            + "{0: 2d}  {1: 2d}\n" \
            + "{2: 2d}  {3: 2d}"

        self.accelerometer_screen = curses.newwin(5, 20, 8, 0)
        self.accelerometer_display = "accelerometer:\n" \
            + " x: {x:>7.3f}\n" \
            + " y: {y:>7.3f}\n" \
            + " z: {z:>7.3f}"

        self.gyroscope_screen = curses.newwin(5, 20, 8, 17)
        self.gyroscope_display = "gyroscope:\n" \
            + " x: {x:>7.3f}\n" \
            + " y: {y:>7.3f}\n" \
            + " z: {z:>7.3f}"

        self.magnet_screen = curses.newwin(5, 20, 8, 32)
        self.magnet_display = "magnet:\n" \
            + " x: {x:>7.3f}\n" \
            + " y: {y:>7.3f}\n" \
            + " z: {z:>7.3f}"

        self.input_screen = curses.newwin(5, 100, 13, 0)
        self.input_display = "input:\n" \
            + " map: {input}\n" \
            + " raw: {raw}"

    def update(self, engine):
        if not self.screen:
            return

        self.screen.erase()

        self.screen.addstr(0, 0, self.engine_display.format(**{
            'time': engine.chronograph.current,
            'sleep': engine.chronograph.sleep,
            'run_time': engine.chronograph,
            'fps': engine.chronograph.fps,
            'mem': process.memory_info().rss / float(2 ** 20),
            'throttle': engine.vehicle.throttle.value,
            # 'altitude': engine.vehicle.altitude,
        }))

        formatted = self.motor_display.format(*[
            engine.vehicle.motors[0].dc, engine.vehicle.motors[1].dc,
            engine.vehicle.motors[2].dc, engine.vehicle.motors[3].dc
        ])
        self.motor_screen.addstr(0, 0, formatted)

        formatted = self.accelerometer_display.format(**engine.vehicle.accel)
        self.accelerometer_screen.addstr(0, 0, formatted)

        formatted = self.gyroscope_display.format(**engine.vehicle.gyro)
        self.gyroscope_screen.addstr(0, 0, formatted)

        formatted = self.magnet_display.format(**engine.vehicle.magnet)
        self.magnet_screen.addstr(0, 0, formatted)

        # print_these = self.stream.getvalue().split("\n")
        # print_these.reverse()
        # i = 10
        # for line in print_these[:10]:
        #     self.screen.addstr(i, 40, line)
        #     i -= 1

        formatted = self.input_display.format(**{
            'input': engine.input.state,
            'raw': engine.input.raw,
        })
        self.input_screen.addstr(0, 0, formatted)

        self.screen.noutrefresh()
        self.motor_screen.noutrefresh()
        self.accelerometer_screen.noutrefresh()
        self.gyroscope_screen.noutrefresh()
        self.magnet_screen.noutrefresh()
        self.input_screen.noutrefresh()

        curses.doupdate()

    def down(self):
        if self.screen:
            curses.echo()
            curses.endwin()
            self.screen = None
            logger.info('down')
