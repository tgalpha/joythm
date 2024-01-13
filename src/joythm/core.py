import enum
import time
import threading

# Must import this first to load embedded hidapi
from joythm import hidapi

import hid
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

    def is_alive(self):
        return self._update_input_report_thread.is_alive()

    def report_battery_level(self):
        print(f'[{self.name}] Battery level: ', self.get_battery_level())

    def get_state_report_str(self):
        is_alive = self.is_alive()
        return f'[{self.name} ({is_alive=})] State: {self.state.name}'

    def start_monitoring(self):
        if self._on_update in self._input_hooks:
            return
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
        self.scanJoyConThread = None

    def main(self):
        try:
            while True:
                self.monitor()
                time.sleep(1 / 144)
        except KeyboardInterrupt:
            print('\n== Exit ==')
            self._clear_inactive_joy_cons()
            self._report_battery_info()
            self._disconnect()

    def monitor(self):
        if any((not jc.is_alive() for jc in self.joyCons)) or len(self.joyCons) < 2:
            self._rescan_joy_cons_on_the_fly()

        print('\r' + ' '.join([jc.get_state_report_str() for jc in self.joyCons]), end='', flush=True)

    def _rescan_joy_cons_on_the_fly(self):
        def _scan_joy_con():
            def _l_r_jc_connected(_ids):
                return any((_id[1] == pjc.JOYCON_L_PRODUCT_ID for _id in _ids)) \
                    and any((_id[1] == pjc.JOYCON_R_PRODUCT_ID for _id in _ids))

            ids = []
            while not _l_r_jc_connected(ids):
                print('Scanning for a pair of L&R Joy-Cons')
                time.sleep(0.5)
                ids = pj.get_device_ids()
                print(f'Found {ids}')

            self._clear_inactive_joy_cons()
            registered_jc_serials = {jc.serial for jc in self.joyCons}
            unregistered_jcs = [jc_id for jc_id in ids if jc_id[2] not in registered_jc_serials]
            self.joyCons.extend([JoyCon(*jc_id) for jc_id in unregistered_jcs])
            [jc.start_monitoring() for jc in self.joyCons]

        if self.scanJoyConThread is not None and self.scanJoyConThread.is_alive():
            return
        self.scanJoyConThread = threading.Thread(target=_scan_joy_con)
        self.scanJoyConThread.daemon = True
        self.scanJoyConThread.start()

    def _clear_inactive_joy_cons(self):
        self.joyCons = [jc for jc in self.joyCons if jc.is_alive()]

    def _report_battery_info(self):
        [jc.report_battery_level() for jc in self.joyCons]

    def _disconnect(self):
        if Config.disconnectJoyConAtExit:
            [jc.disconnect_device() for jc in self.joyCons]


def main():
    worker = Worker()
    worker.main()


if __name__ == '__main__':
    main()
