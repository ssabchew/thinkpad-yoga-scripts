#!/usr/bin/env python2
"""
thinkpad-rotate.py

Rotates any detected screen, wacom digitizers, touchscreens,
touchpad/trackpoint based on orientation gathered from accelerometer. 

Tested with Lenovo Thinkpad Yoga S1

https://github.com/admiralakber/thinkpad-yoga-scripts

Acknowledgements:
Modified from source:
https://gist.githubusercontent.com/ei-grad/4d9d23b1463a99d24a8d/raw/rotate.py

"""
from time import sleep
from os import path as op
import sys
from subprocess import check_call, check_output
from glob import glob

def bdopen(fname):
    return open(op.join(basedir, fname))


def read(fname):
    return bdopen(fname).read()


for basedir in glob('/sys/bus/iio/devices/iio:device*'):
    if 'accel' in read('name'):
        break
else:
    sys.stderr.write("Can't find an accellerator device!\n")
    sys.exit(1)


env = {}
env['XAUTHORITY'] = check_output(['ls -1 /home/*/.Xauthority | head -n 1'],shell=True).strip()
env['DISPLAY'] = check_output(['echo ":`ls -1 /tmp/.X11-unix/ | sed -e s/^X//g | head -n 1`"'],shell=True).strip()

devices = check_output(['xinput', '--list', '--name-only'],env=env).splitlines()

touchscreen_names = ['touchscreen']
touchscreens = [i for i in devices if any(j in i.lower() for j in touchscreen_names)]

wacoms = [i for i in devices if any(j in i.lower() for j in ['wacom'])]

# WARNING: Don't use disable_touchpads in conjunction with the ACPI hook.
disable_touchpads = False

touchpad_names = ['touchpad', 'trackpoint']
touchpads = [i for i in devices if any(j in i.lower() for j in touchpad_names)]

scale = float(read('in_accel_scale'))

g = 7.0  # (m^2 / s) sensibility, gravity trigger

STATES = [
    {'rot': 'normal', 'pen': 'none', 'coord': '1 0 0 0 1 0 0 0 1', 'touchpad': 'enable',
     'check': lambda x, y: y <= -g},
    {'rot': 'inverted', 'pen': 'half', 'coord': '-1 0 1 0 -1 1 0 0 1', 'touchpad': 'disable',
     'check': lambda x, y: y >= g},
    {'rot': 'left', 'pen': 'ccw', 'coord': '0 -1 1 1 0 0 0 0 1', 'touchpad': 'disable',
     'check': lambda x, y: x >= g},
    {'rot': 'right', 'pen': 'cw', 'coord': '0 1 0 -1 0 1 0 0 1', 'touchpad': 'disable',
     'check': lambda x, y: x <= -g},
]


def rotate(state):
    s = STATES[state]
    check_call(['xrandr', '-o', s['rot']],env=env)
    for dev in touchscreens if disable_touchpads else (touchscreens + touchpads):
        check_call([
            'xinput', 'set-prop', dev,
            'Coordinate Transformation Matrix',
        ] + s['coord'].split(),env=env)
    for dev in wacoms:
        check_call([
            'xsetwacom','set', dev,
            'rotate',s['pen']],env=env)
    if disable_touchpads:
        for dev in touchpads:
            check_call(['xinput', s['touchpad'], dev],env=env)

def read_accel(fp):
    fp.seek(0)
    return float(fp.read()) * scale


if __name__ == '__main__':

    accel_x = bdopen('in_accel_x_raw')
    accel_y = bdopen('in_accel_y_raw')

    current_state = None

    while True:
        x = read_accel(accel_x)
        y = read_accel(accel_y)
        for i in range(4):
            if i == current_state:
                continue
            if STATES[i]['check'](x, y):
                current_state = i
                rotate(i)
                break
        sleep(1)
