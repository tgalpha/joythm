import time

import pyjoycon as pj
import matplotlib.pyplot as plt


def plot_sensor_curve():
    joycon_id = pj.get_L_id()
    joycon = pj.JoyCon(*joycon_id)

    data_acc_x = []
    data_gyro_y = []
    last_time = time.perf_counter()
    last_value_acc_x = 0

    sample_interval = []

    for i in range(1000000):
        accel_x = joycon.get_accel_x()
        gyro_y = joycon.get_gyro_y()
        data_acc_x.append(accel_x)
        data_gyro_y.append(gyro_y)

        if last_value_acc_x != accel_x:
            now = time.perf_counter()
            sample_interval.append((now - last_time) * 1000)
            print('\r[{:.2f}] {} {}'.format((now - last_time) * 1000, accel_x, gyro_y), end='', flush=True)
            last_time = now
            last_value_acc_x = accel_x

    print(f'\nAverage delay(ms): {sum(sample_interval) / len(sample_interval)}')
    fig, axs = plt.subplots(2, 1)
    axs[0].plot(data_acc_x)
    axs[0].set_title('Accelerometer X')
    axs[1].plot(data_gyro_y)
    axs[1].set_title('Gyroscope Y')
    plt.show()


if __name__ == '__main__':
    plot_sensor_curve()
