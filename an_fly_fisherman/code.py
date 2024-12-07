# MIT License
#
# Copyright (c) 2024 JimmySoftLLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import files
import utilities
import time
import board
import microcontroller
import pwmio
import digitalio
import random
import gc

from analogio import AnalogIn
from adafruit_motor import servo
from adafruit_debouncer import Debouncer


def gc_col(collection_point):
    gc.collect()
    start_mem = gc.mem_free()
    files.log_item(
        "Point " + collection_point +
        " Available memory: {} bytes".format(start_mem)
    )


def reset_pico():
    microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
    microcontroller.reset()

################################################################################
# Setup hardware


# Setup the servo this animation can have up to two servos
# also get the programmed values for position which is stored on the pico itself
servo_1 = pwmio.PWMOut(board.GP2, duty_cycle=2 ** 15,
                       frequency=50)  # first prototype used GP10
servo_2 = pwmio.PWMOut(board.GP3, duty_cycle=2 ** 15, frequency=50)

servo_1 = servo.Servo(servo_1, min_pulse=500, max_pulse=2500)
servo_2 = servo.Servo(servo_2, min_pulse=500, max_pulse=2500)

prev_pos_arr = [180, 180]

servo_arr = [servo_1, servo_2]

# Setup the switches
l_sw = board.GP11
r_sw = board.GP20

l_sw = digitalio.DigitalInOut(l_sw)
l_sw.direction = digitalio.Direction.INPUT
l_sw.pull = digitalio.Pull.UP
l_sw = Debouncer(l_sw)

r_sw = digitalio.DigitalInOut(r_sw)
r_sw.direction = digitalio.Direction.INPUT
r_sw.pull = digitalio.Pull.UP
r_sw = Debouncer(r_sw)

################################################################################
# get the calibration settings from the picos flash memory
cfg = files.read_json_file("/cfg.json")

main_m = cfg["main_menu"]

rand_timer = 0

################################################################################
# Servo methods


def move_at_speed(n, new_position, speed):
    global prev_pos_arr
    sign = 1
    if prev_pos_arr[n] > new_position:
        sign = - 1
    for servo_pos in range(prev_pos_arr[n], new_position, sign):
        m_servo(n, servo_pos)
        time.sleep(speed)
    m_servo(n, new_position)


def m_servo(n, p):
    global prev_pos_arr
    if p < 0:
        p = 0
    if p > 180:
        p = 180
    servo_arr[n].angle = p
    prev_pos_arr[n] = p


################################################################################
# animations
def s_1_wiggle_movement(n, center_pt, cyc, spd, wiggle_amount=7):
    for _ in range(cyc):
        move_at_speed(n, center_pt-wiggle_amount, spd)
        move_at_speed(n, center_pt+wiggle_amount, spd)


def an():
    move_at_speed(0, cfg["wiggle_pos"], cfg["gentle_speed"])
    cyc = random.randint(cfg["wiggle_cycles_low"], cfg["wiggle_cycles_high"])
    s_1_wiggle_movement(0, cfg["wiggle_pos"], cyc, cfg["wiggle_speed"])
    time.sleep(.1)
    move_at_speed(0, cfg["cast_pos"], cfg["cast_speed"])


# Initialize all servos to 90 degree position upon startup
move_at_speed(0, cfg["wiggle_pos"], cfg["gentle_speed"])

################################################################################
# State Machine


class StMch(object):

    def __init__(s):
        s.ste = None
        s.stes = {}
        s.paused_state = None

    def add(s, ste):
        s.stes[ste.name] = ste

    def go_to(s, ste):
        if s.ste:
            s.ste.exit(s)
        s.ste = s.stes[ste]
        s.ste.enter(s)

    def upd(s):
        if s.ste:
            s.ste.upd(s)

################################################################################
# States

# Abstract parent state class.


class Ste(object):

    def __init__(s):
        pass

    @property
    def name(s):
        return ""

    def enter(s, mch):
        pass

    def exit(s, mch):
        pass

    def upd(s, mch):
        pass


class BseSt(Ste):
    global rand_timer

    def __init__(self):
        pass

    @property
    def name(self):
        return "base_state"

    def enter(self, mch):
        # set servos to starting position
        files.log_item("Entered base Ste")
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        global rand_timer
        sw = utilities.switch_state(l_sw, r_sw, time.sleep, 3.0)
        if sw == "left_held":
            move_at_speed(0, cfg["wiggle_pos"], cfg["wiggle_speed"])
            move_at_speed(0, cfg["cast_pos"], cfg["wiggle_speed"])
            rand_timer = 0
            if cfg["timer"] == True:
                cfg["timer"] = False
                files.write_json_file("cfg.json", cfg)
            elif cfg["timer"] == False:
                cfg["timer"] = True
                files.write_json_file("cfg.json", cfg)
        elif cfg["timer"] == True:
            if rand_timer <= 0:
                an()
                timer_val_split = cfg["timer_val"].split("_")
                if timer_val_split[0] == "random":
                    rand_timer = random.uniform(
                        float(timer_val_split[1]), float(timer_val_split[2]))
                if timer_val_split[0] == "timer":
                    rand_timer = float(timer_val_split[1])
                    next_time = "{:.1f}".format(rand_timer)
                print("Next time : " + next_time)
            else:
                rand_timer -= .1
        elif sw == "left":
            an()
            print("an done")
        elif sw == "right":
            mch.go_to("main_menu")


class Main(Ste):
    global rand_timer

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return "main_menu"

    def enter(self, mch):
        files.log_item("Main menu")
        move_at_speed(0, cfg["wiggle_pos"], cfg["wiggle_speed"])
        move_at_speed(0, cfg["cast_pos"], cfg["wiggle_speed"])
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            self.sel_i = self.i
            self.i += 1
            if self.i > len(main_m) - 1:
                self.i = 0
            print(main_m[self.sel_i])
            if self.sel_i == len(main_m) - 1:
                move_at_speed(0, cfg["wiggle_pos"], cfg["wiggle_speed"])
                move_at_speed(0, cfg["cast_pos"], cfg["wiggle_speed"])
            else:
                s_1_wiggle_movement(
                    0, cfg["cast_pos"], self.sel_i+1, cfg["wiggle_speed"], 14)
        if r_sw.fell:
            sel_i = main_m[self.sel_i]
            if sel_i == "exit_this_menu":
                print(sel_i)
                cfg["timer"] = False
                rand_timer = 0
                files.write_json_file("cfg.json", cfg)
                mch.go_to("base_state")
            else:
                print(sel_i)
                cfg["timer"] = True
                cfg["timer_val"] = sel_i
                rand_timer = 0
                files.write_json_file("cfg.json", cfg)
                mch.go_to("base_state")


###############################################################################
# Create the Ste mch

st_mch = StMch()
st_mch.add(BseSt())
st_mch.add(Main())

time.sleep(5)

st_mch.go_to("base_state")
files.log_item("animator has started...")
gc_col("animations started")

while True:
    st_mch.upd()
    time.sleep(0.1)
