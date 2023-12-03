import enum
import time

# Must import this first to load embedded hidapi
from joythm import hidapi

import pyjoycon as pj
import pyjoycon.constants as pjc
import win32api
import win32con


class JoyConState(enum.Enum):
    putDown = 0
    swingUp = 1
    holdAir = 2
    swingDown = 3


class JoyCon(pj.JoyCon):
    def report_battery_level(self):
        name = f'Joy-Con ({"L" if self.is_left() else "R"}) {self.serial}'
        print(f'Battery level of {name}:', self.get_battery_level())


class Worker:
    def __init__(self):
        self.joyCons: list[JoyCon] = []
        self.lastValue = {}
        self.dirty = False

        # TODO: Move configuration out of source code?
        # region Config
        self.accelXThreshold = 2500
        self.gyroYThreshold = 2000
        self.airKey = win32con.VK_SPACE
        # endregion Config

    def main(self):
        try:
            self._connect_joy_con()
            self._monitor()
        except KeyboardInterrupt:
            print('\n== Exit ==')
            self._report_battery_info()
            # self._disconnect()

    def _connect_joy_con(self):
        def _l_r_jc_connected(_ids):
            return any((_id[1] == pjc.JOYCON_L_PRODUCT_ID for _id in _ids)) and any((_id[1] == pjc.JOYCON_R_PRODUCT_ID for _id in _ids))

        ids = []
        while not _l_r_jc_connected(ids):
            print('Scanning for a pair of L&R Joy-Cons')
            time.sleep(0.5)
            ids = pj.get_device_ids()
            print(f'Found {ids}')
        self.joyCons = [JoyCon(*jc_id) for jc_id in ids]

    def _monitor(self):
        def _get_current_state(_joy_con: pj.JoyCon) -> JoyConState:
            accel_x = _joy_con.get_accel_x()
            gyro_y = _joy_con.get_gyro_y()
            if self.lastValue.get(_joy_con.serial, None) != accel_x:
                self.lastValue[_joy_con.serial] = accel_x
                self.dirty = True

            # The value of gyro_y is reversed on the L/R joy-con
            if _joy_con.is_left():
                if gyro_y > self.gyroYThreshold:
                    return JoyConState.swingDown
                if gyro_y < -self.gyroYThreshold:
                    return JoyConState.swingUp
            else:
                if gyro_y > self.gyroYThreshold:
                    return JoyConState.swingUp
                if gyro_y < -self.gyroYThreshold:
                    return JoyConState.swingDown
            if accel_x > self.accelXThreshold:
                return JoyConState.holdAir
            else:
                return JoyConState.putDown

        print('Start monitoring')
        while True:
            states = [_get_current_state(jc) for jc in self.joyCons]
            self._process_joy_con_states(states)

    def _process_joy_con_states(self, states: list[JoyConState]):
        def _press_lift_key():
            win32api.keybd_event(self.airKey, win32api.MapVirtualKey(self.airKey, 0), 0, 0)
            time.sleep(0.005)

        def _release_air_key():
            win32api.keybd_event(self.airKey, win32api.MapVirtualKey(self.airKey, 0), win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.005)

        def _exist_state(_states, excepted):
            return any((state == excepted for state in _states))

        # avoid keyboard spamming
        if not self.dirty:
            return

        if _exist_state(states, JoyConState.swingDown):
            _release_air_key()
        if _exist_state(states, JoyConState.swingUp) or _exist_state(states, JoyConState.holdAir):
            _press_lift_key()
        _release_air_key()

        self.dirty = False
        print('\rCurrent state: ' + ' '.join([s.name for s in states]), flush=True, end='')

    def _report_battery_info(self):
        [jc.report_battery_level() for jc in self.joyCons]

    def _disconnect(self):
        [jc.disconnect_device() for jc in self.joyCons]


if __name__ == '__main__':
    worker = Worker()
    worker.main()
