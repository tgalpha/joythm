import enum
import time

# Must import this first to load embedded hidapi
from joythm import hidapi

import pyjoycon as pj
import pyjoycon.constants as pjc
import win32api
import win32con

from joythm.config import Config


def _press_lift_key():
    win32api.keybd_event(Config.airKey, win32api.MapVirtualKey(Config.airKey, 0), 0, 0)


def _release_air_key():
    win32api.keybd_event(Config.airKey, win32api.MapVirtualKey(Config.airKey, 0), win32con.KEYEVENTF_KEYUP, 0)


class JoyConState(enum.Enum):
    putDown = 0
    swingUp = 1
    holdAir = 2
    swingDown = 3


class JoyCon(pj.JoyCon):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = f'Joy-Con ({"L" if self.is_left() else "R"}) {self.serial}'
        self.state = JoyConState.putDown

    def report_battery_level(self):
        print(f'[{self.name}] Battery level:', self.get_battery_level())

    def get_state_report_str(self):
        return f'[{self.name}] State: {self.state.name}'

    def start_monitoring(self):
        self.register_update_hook(self._on_update)

    def _on_update(self, *args):
        def _get_current_state() -> JoyConState:
            accel_x = self.get_accel_x()
            gyro_y = self.get_gyro_y()

            # The value of gyro_y is reversed on the L/R joy-con
            if self.is_left():
                if gyro_y > Config.gyroYThreshold:
                    return JoyConState.swingDown
                if gyro_y < -Config.gyroYThreshold:
                    return JoyConState.swingUp
            else:
                if gyro_y > Config.gyroYThreshold:
                    return JoyConState.swingUp
                if gyro_y < -Config.gyroYThreshold:
                    return JoyConState.swingDown
            if accel_x > Config.accelXThreshold:
                return JoyConState.holdAir
            else:
                return JoyConState.putDown

        self.state = _get_current_state()
        if self.state == JoyConState.swingDown:
            _release_air_key()
        elif self.state == JoyConState.swingUp or self.state == JoyConState.holdAir:
            _press_lift_key()
        else:
            _release_air_key()


class Worker:
    def __init__(self):
        self.joyCons: list[JoyCon] = []
        self.lastValue = {}

    def main(self):
        try:
            self._connect_joy_con()
            self._monitor()
        except KeyboardInterrupt:
            print('\n== Exit ==')
            self._report_battery_info()
            self._disconnect()

    def _connect_joy_con(self):
        def _l_r_jc_connected(_ids):
            return any((_id[1] == pjc.JOYCON_L_PRODUCT_ID for _id in _ids)) \
                and any((_id[1] == pjc.JOYCON_R_PRODUCT_ID for _id in _ids))

        ids = []
        while not _l_r_jc_connected(ids):
            print('Scanning for a pair of L&R Joy-Cons')
            time.sleep(0.5)
            ids = pj.get_device_ids()
            print(f'Found {ids}')
        self.joyCons = [JoyCon(*jc_id) for jc_id in ids]

    def _monitor(self):
        def _print_jc_state():
            print('\r' + ' '.join([jc.get_state_report_str() for jc in self.joyCons]), end='', flush=True)

        print('Start monitoring')
        [jc.start_monitoring() for jc in self.joyCons]
        while True:
            _print_jc_state()
            time.sleep(1/144)

    def _report_battery_info(self):
        [jc.report_battery_level() for jc in self.joyCons]

    def _disconnect(self):
        [jc.disconnect_device() for jc in self.joyCons]


if __name__ == '__main__':
    worker = Worker()
    worker.main()
