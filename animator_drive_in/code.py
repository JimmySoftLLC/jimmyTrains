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

#######################################################
# this code requires the following installs

# blinka is a lib that allows you to use circuit python libraries for servos, light etc. search adafruit blinka for instructions

# control lifx lights using lifxlan 1.2.7 and confirm its version
# pip install lifxlan==1.2.7
# pip show lifxlan

# to use lifx lan you must use the bytestring 3.1.9 library and confirm its version
# pip install bitstring==3.1.9
# pip show bitstring

# on screen keyboard, onboard
# sudo apt install onboard

# text to speech using gtts 2.5.3 and confirm its version
# pip install gtts
# pip show gtts

# Units with a touchscreen use a html page and material UI for styling
# Midori, a lightweight browser, is used so it can run on any pi
# install midori and confirm its version
# sudo apt install midori==7.0
# midori --version

# Scripts can be modified via a webpage that the drivein will serve to your location network.
# It might be easier to use a spreadsheet program.  So install libra office on the pi so
# customers can use it to modify scripts too.
# Install with
# sudo apt update
# sudo apt install libreoffice

# The user will want to modify audio files locally so install audocity using
# sudo apt install audacity. Recommend to limit wav music to -10db and wav menu files to -12, mp4 -10


# for touch screen products the display on vnc will default to the touch screen
# resolution which is very low.  During dev you might want to use these three commands
# to set it higher, note these will reset at reboot.  Do not make these permanent.
# xrandr --newmode "1920x1080_60.00"  173.00  1920 2048 2248 2576  1080 1083 1088 1120 -hsync +vsync
# xrandr --addmode HDMI-1 "1920x1080_60.00"
# xrandr --output HDMI-1 --mode "1920x1080_60.00"

# i2s audio is setup on pi itself using an overlay, there is no hardware that needs to be set up in python
# the i2s amps are on the JimmyTrains ANPISBC HAT which provides the audio.  The amps have an audio enable
# feature that is contorlled via pin 26.  It is enabled by this program just before it annouces the animations are active
# The volume is also controlled by this program.  So the volume control on the pi has no effect.
# The amp circuits are set to the highest possible gain so audio tracks and movies should be normalized to -10.0dB to avoid
# clipping.

#######################################################
# prod files are located in the code folder on the user machine
# debug the code.py, files.py and utilities.py in the home directory
# Delete code.py, files.py and utilities.py in the home directory after release

############################################################
# Units will automatically startup up after reboot.   This can happen in a terminal window or in the backgournd.
# To kill the backgournd process enter pkill -f code.py in the terminal

###########################################################
# sudo apt-get install pulseaudio

############################################################
# This code will automatically up mp3 files for folder names to make this work you need gtts and pydub install these as follows
# pip install gtts
# sudo apt install ffmpeg
# pip install pydub


from lifxlan import LifxLAN
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple
import http.server
import socket
import socketserver
import threading
from zeroconf import ServiceInfo, Zeroconf
import json
import os
import gc
import vlc
import board
import digitalio
from adafruit_debouncer import Debouncer
import neopixel_spi
from rainbowio import colorwheel
import pwmio
from adafruit_motor import servo
import pygame
import gc
import files
import utilities
import psutil
import random
from gtts import gTTS
import requests
from lifxlan import BLUE, CYAN, GREEN, LifxLAN, ORANGE, PINK, PURPLE, RED, YELLOW
import subprocess
import time
import netifaces
from collections import OrderedDict
import signal
import copy
from pydub import AudioSegment


# Turn off audio while setting things up
aud_en = digitalio.DigitalInOut(board.D26)
aud_en.direction = digitalio.Direction.OUTPUT
aud_en.value = False


def get_home_path(subpath=""):
    # Get the current user's home directory
    home_dir = os.path.expanduser("~")
    # Return the full path by appending the optional subpath
    return os.path.join(home_dir, subpath)


code_folder = get_home_path() + "code/"
media_folder = get_home_path() + "media/"
plylst_folder = get_home_path() + "media/play lists/"
snd_opt_folder = code_folder + "snd_opt/"

################################################################################
# Loading image as wallpaper on pi

def replace_extension_to_jpg(image_path):
    # Create the new image path with .jpg extension
    new_image_path = os.path.splitext(image_path)[0] + '.jpg'
    
    # Check if the original file exists
    if os.path.exists(new_image_path):
        return new_image_path
    else:
        print(f"File not found: {new_image_path}")
        return None

def change_wallpaper(image_path):
    new_image_path = replace_extension_to_jpg(image_path)

    if new_image_path:
        print(new_image_path)  # Output will be 'path/to/your/image.jpg'
    else:
        new_image_path = media_folder + 'pictures/logo.jpg'

    try:
        # Update the wallpaper in the desktop-items-0.conf file
        config_path = '/home/drivein/.config/pcmanfm/LXDE-pi/desktop-items-0.conf'

        # Read the config file
        with open(config_path, 'r') as file:
            config = file.readlines()

        # Modify the wallpaper path
        with open(config_path, 'w') as file:
            for line in config:
                if line.startswith('wallpaper='):
                    file.write(f'wallpaper={new_image_path}\n')
                else:
                    file.write(line)

        # Refresh the desktop using subprocess
        subprocess.run(['pcmanfm', '--reconfigure'])
    except Exception as e:
        print(f"Image load error: {e}")

change_wallpaper(media_folder + 'pictures/logo.jpg')

def f_exists(filename):
    try:
        status = os.stat(filename)
        f_exists = True
    except OSError:
        f_exists = False
    return f_exists


def gc_col(collection_point):
    gc.collect()
    start_mem = psutil.virtual_memory()[1]
    print("Point " + collection_point +
          " Available memory: {} bytes".format(start_mem))


def restart_pi():
    os.system('sudo reboot')


def restart_pi_timer():
    play_a_0(code_folder + "mvc/restarting_animator_drive_in.wav")
    delay = 2
    timer = threading.Timer(delay, restart_pi)
    timer.start()


gc_col("Imports gc, files")

################################################################################
# config variables

cfg = files.read_json_file(code_folder + "cfg.json")
default_cfg = files.read_json_file(code_folder + "default_cfg.json")


def get_media_files(folder_to_search, extensions):
    media_dict = {}

    # Normalize extensions (e.g., ensure they all start with a dot)
    extensions = [ext if ext.startswith(
        '.') else f'.{ext}' for ext in extensions]

    # Loop through each folder (topic) in the folder_to_search directory
    for topic in os.listdir(folder_to_search):
        topic_path = os.path.join(folder_to_search, topic)

        # Ensure it's a directory before proceeding
        if os.path.isdir(topic_path):
            # Get all files that match the specified extensions
            files = [f for f in os.listdir(topic_path)
                     if os.path.isfile(os.path.join(topic_path, f)) and f.lower().endswith(tuple(extensions))]
            media_dict[topic] = files

    return media_dict


def upd_media():
    global play_list_options, media_list_flattened, media_files, menu_snd_opt

    extensions = ['.mp3', '.wav', '.mp4']  # List of extensions to filter by
    media_files = get_media_files(media_folder, extensions)
    # gets folders in the random_config directory, currently only all and play lists, the folders are empty
    rand_files = get_media_files(media_folder + "random_config/", extensions)
    media_files.update(rand_files)  # add rand_files to media_files dictionary
    # print("All media: " + str(media_files))

    play_list_options = files.return_directory(
        "plylst_", plylst_folder, ".json", True)
    # print("Play lists: " + str(plylst_opt))

    media_list_flattened = []
    for topic, my_files in media_files.items():
        media_list_flattened.extend(
            [f"{topic}/{my_file}" for my_file in my_files])

    # print(str(rand_files.keys))

    menu_snd_opt = []

    for myKey in media_files:
        if myKey != "random_config" and myKey != "pictures":
            menu_snd_opt.append("random_" + myKey + ".mp3")

    # print("Menu sound tracks: " + str(menu_snd_opt))


upd_media()

web = cfg["serve_webpage"]

cfg_main = files.read_json_file(code_folder + "mvc/main_menu.json")
main_m = cfg_main["main_menu"]

cfg_web = files.read_json_file(code_folder + "mvc/web_menu.json")
web_m = cfg_web["web_menu"]

cfg_vol = files.read_json_file(code_folder + "mvc/volume_settings.json")
vol_set = cfg_vol["volume_settings"]

cfg_intermission_settings = files.read_json_file(code_folder + "mvc/intermission_settings.json")
intermission_settings = cfg_intermission_settings["intermission_settings"]

cfg_add_song = files.read_json_file(
    code_folder + "mvc/add_sounds_animate.json")
add_snd = cfg_add_song["add_sounds_animate"]

cont_run = False
ts_mode = False
lst_opt = ''
an_running = False
is_gtts_reachable = False
stop_play_list = False


################################################################################
# Setup io hardware

switch_io_1 = digitalio.DigitalInOut(board.D17)
switch_io_1.direction = digitalio.Direction.INPUT
switch_io_1.pull = digitalio.Pull.UP

switch_io_2 = digitalio.DigitalInOut(board.D27)

switch_io_2.direction = digitalio.Direction.INPUT
switch_io_2.pull = digitalio.Pull.UP

switch_io_3 = digitalio.DigitalInOut(board.D22)
switch_io_3.direction = digitalio.Direction.INPUT
switch_io_3.pull = digitalio.Pull.UP

switch_io_4 = digitalio.DigitalInOut(board.D5)
switch_io_4.direction = digitalio.Direction.INPUT
switch_io_4.pull = digitalio.Pull.UP

l_sw = Debouncer(switch_io_1)
r_sw = Debouncer(switch_io_2)
three_sw = Debouncer(switch_io_3)
four_sw = Debouncer(switch_io_4)

################################################################################
# Setup sound

# Setup the mixer to play wav files
pygame.mixer.init()
mix = pygame.mixer.music

################################################################################
# Setup video hardware

# create vlc media player object for playing video, music etc
instance = vlc.Instance('--aout=alsa')
media_player = vlc.MediaPlayer(instance)


def play_movie_file(movie_filename):
    # Load media
    media = instance.media_new(movie_filename)
    media_player.set_media(media)

    media_player.set_fullscreen(True)

    # Set the volume explicitly for each media file
    upd_vol(0.05)

    # Play the video
    media_player.play()

    while not media_player.is_playing():
        time.sleep(.05)


def pause_movie():
    media_player.pause()


def play_movie():
    media_player.play()


################################################################################
# Setup servo hardware
s_1_pwm = pwmio.PWMOut(board.D23, duty_cycle=2 ** 15, frequency=50)  # D23
s_2_pwm = pwmio.PWMOut(board.D24, duty_cycle=2 ** 15, frequency=50)  # D24
s_3_pwm = pwmio.PWMOut(board.D25, duty_cycle=2 ** 15, frequency=50)  # D25
s_4_pwm = pwmio.PWMOut(board.D6, duty_cycle=2 ** 15, frequency=50)  # D6
s_5_pwm = pwmio.PWMOut(board.D13, duty_cycle=2 ** 15, frequency=50)  # D13
s_6_pwm = pwmio.PWMOut(board.D12, duty_cycle=2 ** 15, frequency=50)  # D12
s_7_pwm = pwmio.PWMOut(board.D16, duty_cycle=2 ** 15, frequency=50)  # D16
s_8_pwm = pwmio.PWMOut(board.D20, duty_cycle=2 ** 15, frequency=50)  # D20

s_1 = servo.Servo(s_1_pwm)
s_2 = servo.Servo(s_2_pwm)
s_3 = servo.Servo(s_3_pwm)
s_4 = servo.Servo(s_4_pwm)
s_5 = servo.Servo(s_5_pwm)
s_6 = servo.Servo(s_6_pwm)
s_7 = servo.Servo(s_7_pwm)
s_8 = servo.Servo(s_8_pwm)

p_arr = [90, 90, 90, 90, 90, 90]

s_arr = [s_1, s_2, s_3, s_4, s_5, s_6]


def m_servo(n, p):
    global p_arr
    if p < 0:
        p = 0
    if p > 180:
        p = 180
    s_arr[n].angle = p
    p_arr[n][n] = p


################################################################################
# Create an ordered dictionary to preserve the order of insertion
neo_changes = OrderedDict(cfg["neo_changes"])

# Get the ordered list of keys
ordered_neo_changes_keys = list(neo_changes.keys())

trees = []
canes = []
ornmnts = []
stars = []
brnchs = []
cane_s = []
cane_e = []

bars = []
bolts = []
noods = []
neos = []

bar_arr = []
bolt_arr = []
neo_arr = []

n_px = 0
led = neopixel_spi.NeoPixel_SPI(
    board.SPI(), n_px, brightness=1.0, auto_write=False)


def bld_tree(p):
    i = []
    for t in trees:
        for ledi in t:
            si = ledi
            break
        if p == "ornaments":
            for ledi in range(0, 7):
                i.append(ledi+si)
        if p == "star":
            for ledi in range(7, 14):
                i.append(ledi+si)
        if p == "branches":
            for ledi in range(14, 21):
                i.append(ledi+si)
    return i


def bld_cane(p):
    i = []
    for c in canes:
        for led_i in c:
            si = led_i
            break
        if p == "end":
            for led_i in range(0, 2):
                i.append(led_i+si)
        if p == "start":
            for led_i in range(2, 4):
                i.append(led_i+si)
    return i


def bld_bar():
    i = []
    for b in bars:
        for l in b:
            si = l
            break
        for l in range(0, 10):
            i.append(l+si)
    return i


def bld_bolt():
    i = []
    for b in bolts:
        for l in b:
            si = l
            break
        if len(b) == 4:
            for l in range(0, 4):
                i.append(l+si)
        if len(b) == 1:
            for l in range(0, 1):
                i.append(l+si)
    return i


def bld_neo():
    i = []
    for n in neos:
        for l in n:
            si = l
            break
        for l in range(0, 6):
            i.append(l+si)
    return i


def show_l():
    led.show()
    time.sleep(.3)
    led.fill((0, 0, 0))
    led.show()


def l_tst():
    global ornmnts, stars, brnchs, cane_s, cane_e, bar_arr, bolt_arr, neo_arr

    # Christmas items
    ornmnts = bld_tree("ornaments")
    stars = bld_tree("star")
    brnchs = bld_tree("branches")
    cane_s = bld_cane("start")
    cane_e = bld_cane("end")

    # Lightning items
    bar_arr = bld_bar()
    bolt_arr = bld_bolt()

    # Neo items
    neo_arr = bld_neo()

    # cane test
    cnt = 0
    for i in cane_s:
        led[i] = (50, 50, 50)
        cnt += 1
        if cnt > 1:
            show_l()
            cnt = 0
    for i in cane_e:
        led[i] = (50, 50, 50)
        cnt += 1
        if cnt > 1:
            show_l()
            cnt = 0

    # tree test
    cnt = 0
    for i in ornmnts:
        led[i] = (50, 50, 50)
        cnt += 1
        if cnt > 6:
            show_l()
            cnt = 0
    for i in stars:
        led[i] = (50, 50, 50)
        cnt += 1
        if cnt > 6:
            show_l()
            cnt = 0
    for i in brnchs:
        led[i] = (50, 50, 50)
        cnt += 1
        if cnt > 6:
            show_l()
            cnt = 0

    # bar test
    for b in bars:
        for l in b:
            led[l] = (50, 50, 50)
        led.show()
        time.sleep(.3)
        led.fill((0, 0, 0))
        led.show()

    # bolt test
    for b in bolts:
        for l in b:
            led[l] = (50, 50, 50)
        led.show()
        time.sleep(.3)
        led.fill((0, 0, 0))
        led.show()

    # nood test
    for n in noods:
        led[n[0]] = (50, 50, 50)
        led.show()
        time.sleep(.3)
        led.fill((0, 0, 0))
        led.show()

    # neo test
    for n in neos:
        for i in n:
            led[i] = (0, 50, 0)
            time.sleep(.3)
            led.show()
            led[i] = (50, 0, 0)
            time.sleep(.3)
            led.show()
            led[i] = (0, 0, 50)
            time.sleep(.3)
            led.show()
            time.sleep(.3)
            led.fill((0, 0, 0))
            led.show()


def upd_l_str():
    global trees, canes, bars, bolts, noods, neos, n_px, led
    trees = []
    canes = []
    bars = []
    bolts = []
    noods = []
    neos = []

    n_px = 0

    els = cfg["light_string"].split(',')

    for el in els:
        p = el.split('-')
        if len(p) == 2:
            typ, qty = p
            qty = int(qty)
            if typ == 'grandtree':
                s = list(range(n_px, n_px + qty))
                trees.append(s)
                n_px += qty
            elif typ == 'cane':
                s = list(range(n_px, n_px + qty))
                canes.append(s)
                n_px += qty
            if typ == 'bar':
                s = list(range(n_px, n_px + qty))
                bars.append(s)
                n_px += qty
            elif typ == 'bolt' and qty < 4:
                s = [n_px, qty]
                noods.append(s)
                n_px += 1
            elif typ == 'bolt' and qty == 4:
                s = list(range(n_px, n_px + qty))
                bolts.append(s)
                n_px += qty
            if typ == 'neo':
                if qty == 6:
                    neoqty = 2
                if qty == 12:
                    neoqty = 4
                s = list(range(n_px, n_px + neoqty))
                neos.append(s)
                n_px += neoqty

    print("Number of pixels total: ", n_px)
    led = None
    led = neopixel_spi.NeoPixel_SPI(
        board.SPI(), n_px, brightness=1.0, auto_write=False)
    led.auto_write = False
    led.brightness = 1.0
    l_tst()


upd_l_str()

# Neo pixel / neo 6 module methods

br = 0


def is_neo(number, nested_array):
    return any(number in sublist for sublist in nested_array)


def set_neo_to(light_n, r, g, b):
    if light_n == -1:
        for i in range(n_px):  # in range(n_px)
            if is_neo(i, neos):
                led[i] = (g, r, b)
            else:
                led[i] = (r, g, b)
    else:
        if is_neo(light_n, neos):
            led[light_n] = (g, r, b)
        else:
            led[light_n] = (r, g, b)
    led.show()


def get_neo_ids():
    matches = []
    for num in range(n_px + 1):
        if any(num == sublist[0] for sublist in neos):
            matches.append(num)
    return matches


def set_neo_module_to(mod_n, ind, v):
    cur = []
    neo_ids = get_neo_ids()
    print(mod_n, ind, v, neo_ids)
    if mod_n == 0:
        for i in neo_ids:
            led[i] = (v, v, v)
            led[i+1] = (v, v, v)
    elif ind == 0:
        led[neo_ids[mod_n-1]] = (v, v, v)
        led[neo_ids[mod_n-1]+1] = (v, v, v)
    elif ind < 4:
        ind -= 1
        if ind == 0:
            ind = 1
        elif ind == 1:
            ind = 0
        cur = list(led[neo_ids[mod_n-1]])
        cur[ind] = v
        led[neo_ids[mod_n-1]] = (cur[0], cur[1], cur[2])
        print(led[neo_ids[mod_n-1]])
    else:
        ind -= 1
        if ind == 3:
            ind = 4
        elif ind == 4:
            ind = 3
        cur = list(led[neo_ids[mod_n-1]+1])
        cur[ind-3] = v
        led[neo_ids[mod_n-1]+1] = (cur[0], cur[1], cur[2])
    led.show()


gc_col("Neopixels setup")


################################################################################
# Setup lifx lights

# Create an ordered dictionary to preserve the order of insertion
scene_changes = OrderedDict(cfg["scene_changes"])

# Get the ordered list of keys
ordered_scene_changes_keys = list(scene_changes.keys())

devices = []
lifx = {}


def discover_lights():
    if cfg["lifx_enabled"] == False:
        return
    global devices, lifx
    play_a_0(code_folder + "mvc/" + "discovering_lifx_lights" + ".wav")
    lifx = LifxLAN(18)  # Assuming 2 is the number of lights

    # Discover LIFX devices on the local network
    devices = lifx.get_devices()

    # Report the count of discovered devices
    device_count = len(devices)
    spk_str(str(device_count), False)
    play_a_0(code_folder + "mvc/" + "lifx_lights_found" + ".wav")

    print(f"Discovered {device_count} device(s).")

    lifx.set_power_all_lights("on")

    # Iterate over each discovered device and control it
    # for device in devices:
    #     try:
    #         # print(f"Found device: {device.get_label()}")
    #         device.set_color(rgb_to_hsbk(50, 50, 50))  # Set initial color
    #         device.set_power("on")
    #     except Exception as e:
    #         print(f"Error setting color for {device.get_label()}: {e}")


def set_light_color_threaded(device, r, g, b):
    """Function to set the light color, executed in a thread."""
    try:
        # Set color instantly
        device.set_color(rgb_to_hsbk(r, g, b), duration=0)
        print(f"Setting color for {device.get_label()} to RGB({r}, {g}, {b})")
    except Exception as e:
        print(f"Error setting color for {device.get_label()}: {e}")


def set_all_lights_parallel(r, g, b):
    """Set color for all lights in parallel using threads."""
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(
            set_light_color_threaded, device, r, g, b) for device in devices]
        for future in futures:
            future.result()  # Wait for all threads to complete


def set_light_color(light_n, r, g, b):
    if cfg["lifx_enabled"] == "false":
        return
    """Set color for a specific light or all lights."""
    if light_n == -1:
        # Set color for all lights in parallel
        lifx.set_color_all_lights(rgb_to_hsbk(r, g, b))
        # set_all_lights_parallel(r, g, b)
    else:
        # Set color for a specific light
        devices[light_n].set_color(rgb_to_hsbk(r, g, b))


################################################################################
# Color helpers


def scene_change(type, start, end, time=5, increments=100):
    """Handle a scene change by interpolating between two times and cycling RGB values."""
    rgb_cycle = interpolate(type, start, end)
    cycle_rgb_values(type, rgb_cycle, time, increments)


def interpolate_color(start_color, end_color, steps):
    """Gradually interpolate between two RGB colors."""
    r_step = (end_color[0] - start_color[0]) / steps
    g_step = (end_color[1] - start_color[1]) / steps
    b_step = (end_color[2] - start_color[2]) / steps

    interpolated_colors = []

    for step in range(steps + 1):
        r = int(start_color[0] + r_step * step)
        g = int(start_color[1] + g_step * step)
        b = int(start_color[2] + b_step * step)
        interpolated_colors.append((r, g, b))

    return interpolated_colors


def interpolate(type, start_key: str, end_key: str):
    """Interpolate between the start and end keys in the scene_changes dictionary."""
    try:
        if type == "lifx":
            start_index = ordered_scene_changes_keys.index(start_key)
            end_index = ordered_scene_changes_keys.index(end_key)
        elif type == "neo":
            start_index = ordered_neo_changes_keys.index(start_key)
            end_index = ordered_neo_changes_keys.index(end_key)

    except ValueError:
        raise ValueError("Invalid key provided.")

    if start_index > end_index:
        # Reverse interpolation
        if type == "lifx":
            interpolated_values = [cfg["scene_changes"][key]
                                   # end_index is exclusive
                                   for key in ordered_scene_changes_keys[start_index:end_index:-1]]
            # Ensure inclusion of end_index
            interpolated_values.append(
                cfg["scene_changes"][ordered_scene_changes_keys[end_index]])
        elif type == "neo":
            interpolated_values = [cfg["neo_changes"][key]
                                   # end_index is exclusive
                                   for key in ordered_neo_changes_keys[start_index:end_index:-1]]
            # Ensure inclusion of end_index
            interpolated_values.append(
                cfg["neo_changes"][ordered_neo_changes_keys[end_index]])
    else:
        # Forward interpolation
        if type == "lifx":
            interpolated_values = [cfg["scene_changes"][key]
                                   # end_index is inclusive
                                   for key in ordered_scene_changes_keys[start_index:end_index + 1]]
        elif type == "neo":
            interpolated_values = [cfg["neo_changes"][key]
                                   # end_index is inclusive
                                   for key in ordered_neo_changes_keys[start_index:end_index + 1]]

    return interpolated_values


def rgb_to_hsbk(r, g, b):
    import colorsys

    # Normalize RGB values to the range 0-1
    r, g, b = r / 255.0, g / 255.0, b / 255.0

    # Convert RGB to HSB (Hue, Saturation, Brightness)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    # Convert HSB to LIFX HSBK
    hue = int(h * 65535)          # Hue in range 0-65535
    saturation = int(s * 65535)    # Saturation in range 0-65535
    brightness = int(v * 65535)    # Brightness in range 0-65535
    # Fixed Kelvin value (can adjust for white balance)
    kelvin = 3500

    return [hue, saturation, brightness, kelvin]


def cycle_rgb_values(type, rgb_values, transition_time=2, steps=100):
    """Cycles through a list of RGB tuples, transitioning between each in order."""
    for i in range(len(rgb_values) - 1):
        start_color = rgb_values[i]
        end_color = rgb_values[i + 1]
        color_transition = interpolate_color(start_color, end_color, steps)

        for color in color_transition:
            # Use threading to set color for all lights at once
            if type == "lifx":
                set_light_color(-1, color[0], color[1], color[2])
            elif type == "neo":
                set_neo_to(-1, color[0], color[1], color[2])
            print(f"Setting color to {color}")
            # Adjust sleep time for smooth transitions
            time.sleep(transition_time / steps)

################################################################################
# Requests

import requests

class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def get(self, endpoint, params=None):
        """Perform a GET request."""
        response = requests.get(f"{self.base_url}/{endpoint}", params=params)
        return self.handle_response(response)

    def post(self, endpoint, data=None):
        """Perform a POST request."""
        response = requests.post(f"{self.base_url}/{endpoint}", json=data)
        return self.handle_response(response)

    def put(self, endpoint, data=None):
        """Perform a PUT request."""
        response = requests.put(f"{self.base_url}/{endpoint}", json=data)
        return self.handle_response(response)

    def delete(self, endpoint):
        """Perform a DELETE request."""
        response = requests.delete(f"{self.base_url}/{endpoint}")
        return self.handle_response(response)

    def handle_response(self, response):
        """Handle the HTTP response."""
        if response.status_code == 200:
            return response.json()  # or response.text for raw text
        else:
            response.raise_for_status()  # Raise an error for bad responses

def send_animator_post(url, endpoint, new_data):
    new_url = "http://" + url
    new_data = json.loads(new_data)

    api_client = ApiClient(new_url)
    created_data = api_client.post(endpoint, data=new_data)
    print("POST response:", created_data)


################################################################################
# Setup wifi and web server
number_tries = 0


def get_default_gateway():
    gateways = netifaces.gateways()
    default_gateway = gateways.get('default', {}).get(netifaces.AF_INET)
    if default_gateway:
        return default_gateway[0]
    return None


def wait_for_network():
    global number_tries
    if number_tries > 10:
        print("Network not available after multiple tries.")
        return
    while True:
        try:
            gateway_ip = get_default_gateway()
            if gateway_ip is None:
                raise OSError("No default gateway found")

            # Ping the default gateway
            response = os.system(f"ping -c 1 {gateway_ip}")
            if response == 0:
                print("Wi-Fi is connected to the LAN!")
                return
            else:
                raise OSError("No response from gateway")
        except OSError:
            print("Waiting for Wi-Fi connection to LAN...")
            time.sleep(1)
            number_tries += 1


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def close_midori():
    try:
        subprocess.run(['pkill', 'midori'], check=True)
        print("Midori closed successfully.")
    except subprocess.CalledProcessError:
        print("Midori was not running.")


def open_midori():
    if cfg["show_webpage"] == False: return
    try:
        command = "midori -e Fullscreen http://animator-drive-in.local:8083/"
        subprocess.Popen(command, shell=True)
        print("Midori launched.")
    except Exception as e:
        print(f"Failed to start Midori: {e}")



################################################################################
# Setup routes

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            print(self.path)
            self.handle_serve_file("/code/index.html")
        elif self.path.endswith(".css"):
            print(self.path)
            self.handle_serve_file("/code" + self.path, "text/css")
        elif self.path.endswith(".js"):
            print(self.path)
            self.handle_serve_file("/code" + self.path,
                                   "application/javascript")
        else:
            self.handle_serve_file(self.path)

    def do_POST(self):
        if self.path == "/upload":
            self.handle_file_upload()
        else:
            self.handle_generic_post(self.path)

    def handle_serve_file(self, path, content_type="text/html"):
        file_path = path.lstrip("/")
        try:
            with open(file_path, 'rb') as file:
                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"File not found")

    def handle_serve_file_name(self, f_n, content_type="text/html"):
        try:
            with open(f_n, 'rb') as file:
                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"File not found")

    def handle_file_upload(self):
        content_length = int(self.headers['Content-Length'])
        content_type = self.headers['Content-Type']

        if 'multipart/form-data' in content_type:
            boundary = content_type.split("boundary=")[1].encode()
            body = self.rfile.read(content_length)
            parts = body.split(b'--' + boundary)

            for part in parts:
                gc.collect()
                if part:
                    try:
                        headers, content = part.split(b'\r\n\r\n', 1)
                    except ValueError:
                        continue
                    content = content.rstrip(b'\r\n--')
                    header_lines = headers.decode().split('\r\n')
                    headers_dict = {}
                    for line in header_lines:
                        if ': ' in line:
                            key, value = line.split(': ', 1)
                            headers_dict[key] = value

                    if 'Content-Disposition' in headers_dict:
                        disposition = headers_dict['Content-Disposition']
                        if 'filename=' in disposition:
                            file_name = disposition.split(
                                'filename=')[1].strip('"')
                            # Ensure the uploads directory exists
                            os.makedirs("uploads", exist_ok=True)
                            file_path = os.path.join("uploads", file_name)

                            with open(file_path, "wb") as f:
                                f.write(content)

                            self.send_response(200)
                            self.send_header(
                                "Content-type", "application/json")
                            self.end_headers()
                            response = {"status": "success",
                                        "message": "File uploaded successfully"}
                            self.wfile.write(json.dumps(
                                response).encode('utf-8'))
                            return

            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "error", "message": "No file part"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(400)
            self.end_headers()

    def handle_generic_post(self, path):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print(f"Received POST data: {post_data.decode('utf-8')}")
        # Decode the byte string to a regular string
        post_data_obj = {}
        post_data_str = post_data.decode('utf-8')
        if post_data_str != '':
            post_data_obj = json.loads(post_data_str)
        if self.path == "/animation":
            self.animation_post(post_data_obj)
        elif self.path == "/mode":
            self.mode_post(post_data_obj)
        elif self.path == "/defaults":
            self.defaults_post(post_data_obj)
        elif self.path == "/get-all-media":
            self.get_all_media_post(post_data_obj)
        elif self.path == "/speaker":
            self.speaker_post(post_data_obj)
        elif self.path == "/get-light-string":
            self.get_light_string_post(post_data_obj)
        elif self.path == "/get-scene-changes":
            self.get_scene_changes_post(post_data_obj)
        elif self.path == "/get-neo-changes":
            self.get_neo_changes_post(post_data_obj)
        elif self.path == "/update-host-name":
            self.update_host_name_post(post_data_obj)
        elif self.path == "/update-light-string":
            self.update_light_string_post(post_data_obj)
        elif self.path == "/lights":
            self.lights_post(post_data_obj)
        elif self.path == "/lights-scene":
            self.lights_scene_post(post_data_obj)
        elif self.path == "/lights-neo":
            self.lights_neo_post(post_data_obj)
        elif self.path == "/set-item-lights":
            self.set_item_lights(post_data_obj)
        elif self.path == "/update-host-name":
            self.update_host_name_post(post_data_obj)
        elif self.path == "/get-host-name":
            self.get_host_name_post(post_data_obj)
        elif self.path == "/update-volume":
            self.update_volume_post(post_data_obj)
        elif self.path == "/update-volume":
            self.update_volume_post(post_data_obj)
        elif self.path == "/set-lifx-enabled":
            self.set_lifx_enabled(post_data_obj)
        elif self.path == "/get-volume":
            self.get_volume_post(post_data_obj)
        elif self.path == "/get-lifx-enabled":
            self.get_lifx_enabled(post_data_obj)
        elif self.path == "/get-scripts":
            self.get_scripts_post(post_data_obj)
        elif self.path == "/create-playlist":
            self.create_playlist_post(post_data_obj)
        elif self.path == "/get-animation":
            self.get_animation_post(post_data_obj)
        elif self.path == "/delete-playlist":
            self.delete_playlist_post(post_data_obj)
        elif self.path == "/save-data":
            self.save_data_post(post_data_obj)
        elif self.path == "/rename-playlist":
            self.rename_playlist_post(post_data_obj)
        elif self.path == "/stop":
            self.stop_post(post_data_obj)
        elif self.path == "/test-animation":
            self.test_animation_post(post_data_obj)

    def test_animation_post(self, rq_d):
        set_hdw(rq_d["an"], 3)
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "Set hardware: " + rq_d["an"]
        self.wfile.write(response.encode('utf-8'))
        print("Response sent:", response)

    def stop_post(self, rq_d):
        rst_an()
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "rst an"
        self.wfile.write(response.encode('utf-8'))
        print("Response sent:", response)

    def rename_playlist_post(self, rq_d):
        global data
        snd = rq_d["fo"].replace("plylst_", "")
        fo = plylst_folder + snd + ".json"
        fn = plylst_folder + rq_d["fn"] + ".json"
        os.rename(fo, fn)
        upd_media()
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "your response message"
        self.wfile.write(response.encode('utf-8'))
        print("Response sent:", response)

    data = []

    def save_data_post(self, rq_d):
        global data
        try:
            if rq_d[0] == 0:
                data = []
            data.extend(rq_d[2])
            if rq_d[0] == rq_d[1]:
                f_n = ""
                an = rq_d[3].split("_")
                if "plylst" == an[0]:
                    snd_f = rq_d[3].replace("plylst_", "")
                    snd_f = snd_f.replace(".mp3", "")
                    snd_f = snd_f.replace(".mp4", "")
                    snd_f = snd_f.replace(".wav", "")
                    f_n = plylst_folder + \
                        snd_f + ".json"
                else:
                    snd_f = rq_d[3].replace(".mp3", "")
                    snd_f = snd_f.replace(".mp4", "")
                    snd_f = snd_f.replace(".wav", "")
                    f_n = media_folder + snd_f + ".json"
                files.write_json_file(f_n, data)
                upd_media()
                data = []
        except:
            data = []
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            response = "out of memory"
            self.wfile.write(response.encode('utf-8'))
            print("Response sent:", response)
            return
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "success"
        self.wfile.write(response.encode('utf-8'))
        print("Response sent:", response)

    def delete_playlist_post(self, rq_d):
        snd_f = rq_d["fn"].replace("plylst_", "")
        f_n = plylst_folder + snd_f + ".json"
        os.remove(f_n)
        upd_media()
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = rq_d["fn"] + " playlist file deleted"
        self.wfile.write(response.encode('utf-8'))

    def get_animation_post(self, rq_d):
        global cfg, cont_run, ts_mode
        snd_f = rq_d["an"]
        snd_f = snd_f.replace(".mp3", "")
        snd_f = snd_f.replace(".mp4", "")
        snd_f = snd_f.replace(".wav", "")
        if "plylst_" in snd_f:
            snd_f = snd_f.replace("plylst_", "")
            if (f_exists(plylst_folder + snd_f + ".json") == True):
                f_n = plylst_folder + snd_f + ".json"
                self.handle_serve_file_name(f_n)
                return
            else:
                f_n = code_folder + "t_s_def/timestamp mode.json"
                self.handle_serve_file_name(f_n)
                return
        elif (f_exists(media_folder + snd_f + ".json") == True):
            f_n = media_folder + snd_f + ".json"
            self.handle_serve_file_name(f_n)
            return
        else:
            f_n = code_folder + "t_s_def/timestamp mode.json"
            self.handle_serve_file_name(f_n)
            return

    def get_scripts_post(self, rq_d):
        sounds = []
        sounds.extend(play_list_options)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = sounds
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def create_playlist_post(self, rq_d):
        global data
        f_n = plylst_folder + rq_d["fn"] + ".json"
        files.write_json_file(f_n, ["0.0|", "1.0|"])
        upd_media()
        gc_col("created playlist")
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "created " + rq_d["fn"] + " playlist"
        self.wfile.write(response.encode('utf-8'))

    def update_light_string_post(self, rq_d):
        global cfg
        if rq_d["action"] == "save" or rq_d["action"] == "clear" or rq_d["action"] == "defaults":
            cfg["light_string"] = rq_d["text"]
            print("action: " +
                  rq_d["action"] + " data: " + cfg["light_string"])
            files.write_json_file(code_folder + "cfg.json", cfg)
            upd_l_str()
            play_a_0(code_folder + "mvc/all_changes_complete.wav")
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            response = cfg["light_string"]
            self.wfile.write(response.encode('utf-8'))
            return
        if cfg["light_string"] == "":
            cfg["light_string"] = rq_d["text"]
        else:
            cfg["light_string"] = cfg["light_string"] + \
                "," + rq_d["text"]
        print("action: " + rq_d["action"] +
              " data: " + cfg["light_string"])
        files.write_json_file(code_folder + "cfg.json", cfg)
        upd_l_str()
        play_a_0(code_folder + "mvc/all_changes_complete.wav")
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["light_string"]
        self.wfile.write(response.encode('utf-8'))

    def mode_post(self, rq_d):
        print(rq_d)
        global cfg, cont_run, ts_mode
        if rq_d["an"] == "cont_mode_on":
            play_a_0(code_folder + "mvc/continuous_mode_activated.wav")
            cont_run = True
        elif rq_d["an"] == "cont_mode_off":
            play_a_0(code_folder + "mvc/continuous_mode_deactivated.wav")
            cont_run = False
        elif rq_d["an"] == "timestamp_mode_on":
            play_a_0(code_folder + "mvc/timestamp_mode_on.wav")
            play_a_0(code_folder + "mvc/timestamp_instructions.wav")
            ts_mode = True
        elif rq_d["an"] == "timestamp_mode_off":
            play_a_0(code_folder + "mvc/timestamp_mode_off.wav")
            ts_mode = False
        elif "intermission_" in rq_d["an"]:
            rq_d_split = rq_d["an"].split("_")
            cfg["intermission"] = rq_d_split[1]
            files.write_json_file(code_folder + "cfg.json", cfg)
            play_a_0(code_folder + "mvc/all_changes_complete.wav")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"mode processed": rq_d["an"]}
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def animation_post(self, rq_d):
        global cfg, cont_run, ts_mode, stop_play_list
        cfg["option_selected"] = rq_d["an"]
        files.write_json_file(code_folder + "cfg.json", cfg)
        stop_play_list = False
        add_command(cfg["option_selected"])
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"Animation added to queue: ": cfg["option_selected"]}
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def defaults_post(self, rq_d):
        global cfg
        if rq_d["an"] == "reset_to_defaults":
            rst_def()
            files.write_json_file(code_folder + "cfg.json", cfg)
            play_a_0(code_folder + "mvc/all_changes_complete.wav")
            st_mch.go_to('base_state')
        elif rq_d["an"] == "reset_scene_to_defaults":
            cfg["scene_changes"] = copy.deepcopy(default_cfg["scene_changes"])
            files.write_json_file(code_folder + "cfg.json", cfg)
            play_a_0(code_folder + "mvc/all_changes_complete.wav")
            st_mch.go_to('base_state')
        elif rq_d["an"] == "reset_neo_to_defaults":
            cfg["neo_changes"] = copy.deepcopy(default_cfg["neo_changes"])
            files.write_json_file(code_folder + "cfg.json", cfg)
            play_a_0(code_folder + "mvc/all_changes_complete.wav")
            st_mch.go_to('base_state')
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = rq_d["an"]
        self.wfile.write(response.encode('utf-8'))

    def speaker_post(self, rq_d):
        global cfg
        if rq_d["an"] == "speaker_test":
            cmd_snt = "speaker_test"
            play_a_0(code_folder + "mvc/left_speaker_right_speaker.wav")
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = rq_d["an"]
        self.wfile.write(response.encode('utf-8'))

    def get_light_string_post(self, rq_d):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["light_string"]
        self.wfile.write(response.encode('utf-8'))

    def get_scene_changes_post(self, rq_d):
        response = cfg["scene_changes"]
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def get_neo_changes_post(self, rq_d):
        response = cfg["neo_changes"]
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def update_host_name_post(self, rq_d):
        global cfg
        cfg["HOST_NAME"] = rq_d["text"]
        files.write_json_file(code_folder + "cfg.json", cfg)
        spk_web()
        restart_pi_timer()
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["HOST_NAME"]
        self.wfile.write(response.encode('utf-8'))

    def get_host_name_post(self, rq_d):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["HOST_NAME"]
        self.wfile.write(response.encode('utf-8'))

    def update_volume_post(self, rq_d):
        global cfg
        ch_vol(rq_d["action"])
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["volume"]
        self.wfile.write(response.encode('utf-8'))

    def set_lifx_enabled(self, rq_d):
        global cfg
        cfg["lifx_enabled"] = rq_d["enabled"]
        if cfg["lifx_enabled"] == True:
            discover_lights()
        files.write_json_file(code_folder + "cfg.json", cfg)
        response = cfg["lifx_enabled"]
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def get_volume_post(self, rq_d):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["volume"]
        self.wfile.write(response.encode('utf-8'))

    def get_lifx_enabled(self, rq_d):
        response = cfg["lifx_enabled"]
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def get_all_media_post(self, rq_d):
        upd_media()
        response = media_files
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def lights_post(self, rq_d):
        set_hdw(rq_d["an"], 1)
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = rq_d["an"]
        self.wfile.write(response.encode('utf-8'))

    current_neo = ""

    def lights_neo_post(self, rq_d):
        global current_neo
        current_neo = rq_d["an"]
        rgb_value = cfg["neo_changes"][current_neo]
        set_hdw("LN0_" + str(rgb_value[0]) + "_" +
                str(rgb_value[1]) + "_" + str(rgb_value[2]), 0)
        response = rgb_value
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    current_scene = ""

    def lights_scene_post(self, rq_d):
        global current_scene
        current_scene = rq_d["an"]
        rgb_value = cfg["scene_changes"][current_scene]
        set_hdw("LX0_" + str(rgb_value[0]) + "_" +
                str(rgb_value[1]) + "_" + str(rgb_value[2]), 0)
        response = rgb_value
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def set_item_lights(self, rq_d):
        if rq_d["item"] == "lifx":
            set_hdw("LX0_" + str(rq_d["r"]) + "_" +
                    str(rq_d["g"]) + "_" + str(rq_d["b"]), 0)
            if current_scene != "":
                cfg["scene_changes"][current_scene] = [
                    rq_d["r"], rq_d["g"], rq_d["b"]]
        elif rq_d["item"] == "neo":
            set_hdw("LN0_" + str(rq_d["r"]) + "_" +
                    str(rq_d["g"]) + "_" + str(rq_d["b"]), 0)
            if current_neo != "":
                cfg["neo_changes"][current_neo] = [
                    rq_d["r"], rq_d["g"], rq_d["b"]]
        files.write_json_file(code_folder + "cfg.json", cfg)
        response = rq_d
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

if (web):
    # Get the local IP address
    local_ip = get_local_ip()
    print(f"Local IP address: {local_ip}")

    # Set up the HTTP server
    PORT = 8083  # Use port 80 for default HTTP access
    handler = MyHttpRequestHandler
    httpd = socketserver.TCPServer((local_ip, PORT), handler)
    httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


    def start_server():
        print(f"Serving on {local_ip}:{PORT}")
        httpd.serve_forever()


    # Set up mDNS service info
    name_str = cfg["HOST_NAME"] + "._http._tcp.local."
    server_str = cfg["HOST_NAME"] + ".local."
    desc = {'path': '/'}
    info = ServiceInfo(
        "_http._tcp.local.",
        name_str,
        addresses=[socket.inet_aton(local_ip)],
        port=PORT,
        properties=desc,
        server=server_str
    )

gc_col("web server")


################################################################################
# Command queue

import queue
import threading
import time

# Create a FIFO queue
command_queue = queue.Queue()
stop_flag = False

def add_command(command):
    """Add a command to the queue."""
    command_queue.put(command)
    print(f"Command added: {command}")

def process_commands():
    """Continuously process commands from the queue."""
    global stop_flag, cfg
    while not stop_flag:
        if not command_queue.empty():
            command = command_queue.get()
            print(f"Processing command: {command}")
            an(command)
            command_queue.task_done()
        else:
            time.sleep(1)  # Sleep for a while if the queue is empty

def clear_queue():
    """Clear the queue."""
    with command_queue.mutex:
        command_queue.queue.clear()
    print("Command queue cleared.")

def stop_all_queue_commands():
    """Stop processing and clear the queue."""
    global stop_flag
    stop_flag = True  # Set the stop flag to True
    clear_queue()     # Clear the queue
    print("Processing stopped and command queue cleared.")

################################################################################
# Global Methods


def rst_def():
    global cfg
    cfg["HOST_NAME"] = "animator-drive-in"
    cfg["option_selected"] = "random all"
    cfg["volume"] = "20"

################################################################################
# Dialog and sound play methods


def upd_vol(seconds):
    volume = int(cfg["volume"])
    mix.set_volume(volume/100)
    media_player.audio_set_volume(volume)
    time.sleep(seconds)


def ch_vol(action):
    v = int(cfg["volume"])
    if "volume" in action:
        v = action.split("volume")
        v = int(v[1])
    if action == "lower1":
        v -= 1
    elif action == "raise1":
        v += 1
    elif action == "lower":
        if v <= 10:
            v -= 1
        else:
            v -= 10
    elif action == "raise":
        if v < 10:
            v += 1
        else:
            v += 10
    if v > 100:
        v = 100
    if v < 1:
        v = 1
    cfg["volume"] = str(v)
    cfg["volume_pot"] = False
    upd_vol(.01)
    files.write_json_file(code_folder + "cfg.json", cfg)
    play_a_0(code_folder + "mvc/volume.wav")
    spk_str(cfg["volume"], False)


def play_a_0(file_name, wait_until_done=True, allow_exit=True):
    print("playing " + file_name)
    if mix.get_busy():
        stop_media()
        while mix.get_busy():
            time.sleep(0.1)
    mix.load(file_name)
    upd_vol(.001)
    mix.play(loops=0)
    while mix.get_busy() and wait_until_done:
        if allow_exit:
            exit_early()
    print("done playing")


def wait_snd():
    while mix.get_busy() or media_player.is_playing():
        exit_early()
    print("done playing")


def stop_media():
    media_player.stop()
    mix.stop()
    while mix.get_busy() or media_player.is_playing():
        pass


def exit_early():
    l_sw.update()
    r_sw.update()
    if l_sw.fell:
        stop_media()
    time.sleep(0.1)


def spk_str(str_to_speak, addLocal):
    for character in str_to_speak:
        try:
            if character == " ":
                character = "space"
            if character == "-":
                character = "dash"
            if character == ".":
                character = "dot"
            play_a_0(code_folder + "mvc/" + character + ".wav")
        except Exception as e:
            files.log_item(e)
            print("Invalid character in string to speak")
    if addLocal:
        play_a_0(code_folder + "mvc/dot_local_colon_8083.wav")


def l_r_but():
    play_a_0(code_folder + "mvc/press_left_button_right_button.wav")


def sel_web():
    play_a_0(code_folder + "mvc/web_menu.wav")
    l_r_but()


def opt_sel():
    play_a_0(code_folder + "mvc/option_selected.wav")


def spk_sng_num(song_number):
    play_a_0(code_folder + "mvc/song.wav")
    spk_str(song_number, False)


def no_trk():
    play_a_0(code_folder + "mvc/no_user_soundtrack_found.wav")
    while True:
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            break
        if r_sw.fell:
            play_a_0(code_folder + "mvc/create_sound_track_files.wav")
            break


def spk_web():
    play_a_0(code_folder + "mvc/animator_available_on_network.wav")
    play_a_0(code_folder + "mvc/to_access_type.wav")
    if cfg["HOST_NAME"] == "animator-drive-in":
        play_a_0(code_folder + "mvc/animator_dash_drive_dash_in.wav")
        play_a_0(code_folder + "mvc/dot_local_colon_8083.wav")
    else:
        spk_str(cfg["HOST_NAME"], True)
    play_a_0(code_folder + "mvc/in_your_browser.wav")


def get_random_joke():
    url = "https://official-joke-api.appspot.com/jokes/random"
    response = requests.get(url)

    if response.status_code == 200:
        joke = response.json()
        print(f"{joke['setup']} - {joke['punchline']}")
    else:
        print("Failed to retrieve a joke.")

    text_to_mp3_file(joke['setup'], "myjoke.mp3", 2)
    text_to_mp3_file(joke['punchline'], "myjoke.mp3", 2)

###############################################################################
# Text to speech


def check_gtts_status():
    if web == False: return False
    try:
        # gTTS API endpoint
        url = "https://translate.google.com"

        # Send a simple GET request
        response = requests.get(url, timeout=5)

        # Check the status code
        if response.status_code == 200:
            print("gTTS service is reachable.")
            return True
        else:
            print("gTTS service returned an unexpected status code: " +
                  response.status_code)
            return False

    except requests.ConnectionError:
        print("Failed to connect to gTTS service.")
        return False
    except requests.Timeout:
        print("The request to gTTS service timed out.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


# Custom exception for timeout
class TimeoutException(Exception):
    pass


# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutException("The operation timed out!")


# Set up a signal to call the handler after a timeout
signal.signal(signal.SIGALRM, timeout_handler)


def text_to_mp3_file(text, file_name, timeout_duration):
    global is_gtts_reachable
    if is_gtts_reachable == False: return
    try:
        # Set the timeout (in seconds)
        signal.alarm(timeout_duration)

        # Convert text to mp3 file
        # text = files.strip_path_and_extension(f_nm)
        tts = gTTS(text=text, lang='en')
        tts.save(file_name)

        # Cancel the alarm if operation completes before timeout
        signal.alarm(0)

        # Load the audio file with pydub
        audio = AudioSegment.from_file(file_name)

        # Adjust the volume
        volume_change = -5  # Decrease volume by 5db
        adjusted_audio = audio + volume_change

        # Save the adjusted audio
        adjusted_audio.export(file_name, format="mp3")
        print(f"MP3 for {file_name} generated and volume adjusted.")

        play_a_0(file_name)

    except TimeoutException:
        print("TTS operation timed out.")
        is_gtts_reachable = False
    except Exception as e:
        print(f"An error occurred: {e}")
        is_gtts_reachable = False


def generate_mp3_from_filename(file_name):
    if is_gtts_reachable == False: return
    text_to_speak = file_name.replace("_", " ")
    text_to_speak = text_to_speak.replace(".mp3", "")

    mp3_file = os.path.join(
        snd_opt_folder, f"{os.path.splitext(file_name)[0]}.mp3")

    # If mp3 already exists, skip
    if os.path.exists(mp3_file):
        print(f"MP3 for {file_name} already exists. Skipping...")
        return

    # Generate speech from text
    tts = gTTS(text=text_to_speak, lang='en')
    tts.save(mp3_file)

    # Load the audio file with pydub
    audio = AudioSegment.from_file(mp3_file)

    # Adjust the volume
    volume_change = -5  # Decrease volume by 5db
    adjusted_audio = audio + volume_change

    # Save the adjusted audio
    adjusted_audio.export(mp3_file, format="mp3")
    print(f"MP3 for {file_name} generated and volume adjusted.")


def manage_audio_files():
    if is_gtts_reachable == False: return

    # Get all files in the folder
    files = os.listdir(snd_opt_folder)

    mp3_files = {f for f in files if f.endswith('.mp3')}

    # Generate mp3s for valid files
    for my_file in menu_snd_opt:
        generate_mp3_from_filename(my_file)

    # Delete orphaned mp3 files (those without a corresponding key in menu_snd_opt)
    for mp3_file in mp3_files:
        if f"{os.path.splitext(mp3_file)[0]}.mp3" not in menu_snd_opt:
            os.remove(os.path.join(snd_opt_folder, mp3_file))
            print(f"Deleted orphaned MP3: {mp3_file}")


################################################################################
# Animation methods

def rst_an():
    change_wallpaper(media_folder + 'pictures/welcome-show-starting.jpg')
    stop_media()
    media_player.stop()
    led.fill((0, 0, 0))
    led.show()

def an(f_nm):
    global cfg, lst_opt, an_running
    print("Filename: " + f_nm)
    try:
        cur_opt = return_file_to_use(f_nm)
        if ts_mode:
            an_ts(cur_opt)
            gc_col("animation cleanup")
        else:
            an_light(cur_opt)
            gc_col("animation cleanup")
            if rnd_prob (float(cfg["intermission"])):
                cur_opt = return_file_to_use("random_intermission")
                an_light(cur_opt)
                gc_col("animation cleanup")
    except Exception as e:
        files.log_item(e)
        no_trk()
        cfg["option_selected"] = "random_all"
        return
    gc_col("Animation complete.")

def return_file_to_use (f_nm):
    global cfg, lst_opt, an_running
    cur_opt = f_nm
    if f_nm == "random_play lists":
        h_i = len(play_list_options) - 1
        cur_opt = play_list_options[random.randint(
            0, h_i)]
        while lst_opt == cur_opt and len(play_list_options) > 1:
            cur_opt = play_list_options[random.randint(
                0, h_i)]
        lst_opt = cur_opt
        print("Random sound option: " + f_nm)
        print("Sound file: " + cur_opt)
    elif f_nm == "random_all":
        h_i = len(media_list_flattened) - 1
        cur_opt = media_list_flattened[random.randint(
            0, h_i)]
        while lst_opt == cur_opt and len(media_list_flattened) > 1:
            cur_opt = media_list_flattened[random.randint(
                0, h_i)]
        lst_opt = cur_opt
        print("Random sound option: " + f_nm)
        print("Sound file: " + cur_opt)
    elif "random_" in f_nm:
        # Specify the folder name
        folder_name = f_nm.split("_")
        # Filter the media list to only include items from the specified folder
        filtered_list = [
            item for item in media_list_flattened if item.startswith(folder_name[1])]
        h_i = len(filtered_list) - 1
        cur_opt = filtered_list[random.randint(
            0, h_i)]
        while lst_opt == cur_opt and len(filtered_list) > 1:
            cur_opt = filtered_list[random.randint(
                0, h_i)]
        lst_opt = cur_opt
        print("Random sound option: " + f_nm)
        print("Sound file: " + cur_opt)
    return cur_opt


def an_light(f_nm):
    global ts_mode, an_running
    an_running = True
    if stop_play_list:
        return

    time.sleep(.1)

    plylst_f = "plylst_" in f_nm
    is_video = ".mp4" in f_nm
    json_fn = f_nm.replace(".mp4", "")
    json_fn = json_fn.replace(".wav", "")

    flsh_t = []

    if plylst_f:
        f_nm = f_nm.replace("plylst_", "")
        flsh_t = files.read_json_file(plylst_folder + f_nm + ".json")
    else:
        if (f_exists(media_folder + json_fn + ".json") == True):
            flsh_t = files.read_json_file(
                media_folder + json_fn + ".json")

    flsh_i = 0

    ft1 = []
    ft2 = []

    ft1 = flsh_t[len(flsh_t)-1].split("|")
    tm = float(ft1[0]) + 1
    flsh_t.append(str(tm) + "|E")
    flsh_t.append(str(tm + 1) + "|E")

    if not plylst_f:
        media0 = media_folder + f_nm
        if is_video:
            play_movie_file(media0)
        else:
            change_wallpaper(media0)
            play_a_0(media0, False)

    srt_t = time.monotonic()  # perf_counter

    while True:
        t_past = time.monotonic()-srt_t

        if flsh_i < len(flsh_t)-1:
            ft1 = flsh_t[flsh_i].split("|")
            ft2 = flsh_t[flsh_i+1].split("|")
            dur = float(ft2[0]) - float(ft1[0]) - 0.25
        else:
            dur = 0.25
        if dur < 0:
            dur = 0
        if t_past > float(ft1[0]) - 0.25 and flsh_i < len(flsh_t)-1:
            t_elaspsed = "{:.1f}".format(t_past)
            files.log_item("Time elapsed: " + str(t_elaspsed) +
                           " Timestamp: " + ft1[0])
            resp = set_hdw(ft1[1], dur)
            if resp == "STOP":
                rst_an()
                time.sleep(.2)
                an_running = False
                return
            flsh_i += 1
        if not mix.get_busy() and not media_player.is_playing():  # and not plylst_f and not an_running
            mix.stop()
            media_player.stop()
            rst_an()
            time.sleep(.2)
            an_running = False
            return "DONE"
        if flsh_i > len(flsh_t)-1:
            mix.stop()
            media_player.stop()
            rst_an()
            time.sleep(.2)
            an_running = False
            return "DONE"
        time.sleep(.1)


def an_ts(f_nm):
    print("time stamp mode")
    global ts_mode, an_running
    an_running = True

    cust_f = "customers_owned_music_" in f_nm
    is_video = ".mp4" in f_nm
    json_fn = f_nm.replace(".mp4", "")
    json_fn = json_fn.replace(".wav", "")
    json_fn = json_fn.replace("customers_owned_music_", "")

    t_s = []

    media0 = media_folder + f_nm

    if is_video:
        play_movie_file(media0)
    else:
        play_a_0(media0, False)

    startTime = time.perf_counter()
    time.sleep(.1)

    while True:
        t_elsp = round(time.perf_counter()-startTime, 1)
        r_sw.update()
        if r_sw.fell:
            t_s.append(str(t_elsp) + "|")
            files.log_item(t_elsp)
        if not mix.get_busy() and not media_player.is_playing():
            led.fill((0, 0, 0))
            led.show()
            if cust_f:
                files.write_json_file(
                    media_folder + "customers_owned_music/" + json_fn + ".json", t_s)
            else:
                files.write_json_file(
                    media_folder + "sndtrk/" + json_fn + ".json", t_s)
            break

    ts_mode = False
    rst_an()
    play_a_0(code_folder + "mvc/timestamp_saved.wav")
    play_a_0(code_folder + "mvc/timestamp_mode_off.wav")
    play_a_0(code_folder + "mvc/animations_are_now_active.wav")


###############
# Animation helpers

def rnd_prob(random_value):
    print("Using random value: " + str(random_value))
    if random_value == 0:
        return False
    elif random_value == 1:
        return True
    else:
        y = random.random()
        if y < random_value: return True
    return False

def set_hdw(cmd, dur):
    global sp, br, stop_play_list

    if cmd == "":
        return "NOCMDS"

    # Split the input string into segments
    segs = cmd.split(",")

    # Process each segment
    try:
        for seg in segs:
            f_nm = ""
            if seg[0] == 'E':  # end an
                return "STOP"
            # MAXXX/XXXX = Play Media, A (M play music, W play music wait, A play animation, P play list), XXX/XXX (folder/filename)
            elif seg[0] == 'M':
                stop_media()
                if seg[1] == "P":
                    f_nm = pylst_folder + "plylst_" + seg[2:]
                else:
                    f_nm = media_folder + seg[2:]
                if seg[1] == "W" or seg[1] == "M":
                    play_a_0(f_nm, False)
                if seg[1] == "A":
                    f_nm = seg[2:]
                    stop_play_list = False
                    res = an(f_nm)
                    if res == "STOP":
                        return "STOP"
                if seg[1] == "W":
                    wait_snd()
            # lights LNZZZ_R_G_B = Neopixel lights/Neo 6 modules ZZZ (0 All, 1 to 999) RGB 0 to 255
            elif seg[:2] == 'LN':
                segs_split = seg.split("_")
                light_n = int(segs_split[0][2:])-1
                r = int(segs_split[1])
                g = int(segs_split[2])
                b = int(segs_split[3])
                set_neo_to(light_n, r, g, b)
            # lights LXZZZ_R_G_B = Lifx lights ZZZ (0 All, 1 to 999) RGB 0 to 255
            elif seg[:2] == 'LX':
                segs_split = seg.split("_")
                light_n = int(segs_split[0][2:])-1
                r = int(segs_split[1])
                g = int(segs_split[2])
                b = int(segs_split[3])
                set_light_color(light_n, r, g, b)
            # modules NMZZZ_I_XXX = Neo 6 modules only ZZZ (0 All, 1 to 999) I index (0 All, 1 to 6) XXX 0 to 255</div>
            elif seg[0] == 'N':
                segs_split = seg.split("_")
                mod_n = int(segs_split[0][1:])
                index = int(segs_split[1])
                v = int(segs_split[2])
                set_neo_module_to(mod_n, index, v)
            # brightness BXXX = Brightness XXX 000 to 100
            elif seg[0] == 'B':
                br = int(seg[2:])
                led.brightness = float(br/100)
                led.show()
            # fade in or out FXXX_TTT = Fade brightness in or out XXX 0 to 100, TTT time between transitions in decimal seconds
            elif seg[0] == 'F':
                segs_split = seg.split("_")
                v = int(segs_split[0][1:])
                s = float(segs_split[1])
                while not br == v:
                    if br < v:
                        br += 1
                        led.brightness = float(br/100)
                    else:
                        br -= 1
                        led.brightness = float(br/100)
                    led.show()
                    time.sleep(s)
            # ZRAND = Random rainbow, fire, or color change
            elif seg[0:] == 'ZRAND':
                random_effect(1, 3, dur)
            # ZRTTT = Rainbow, TTT cycle speed in decimal seconds
            elif seg[:2] == 'ZR':
                v = float(seg[2:])
                rbow(v, dur)
            # ZFIRE = Fire
            elif seg[0:] == 'ZFIRE':
                random_effect(3, 3, dur)
            # ZCOLCH = Color change
            elif seg[0:] == 'ZCOLCH':
                random_effect(2, 2, dur)
            # ZL_S_E_T_I = Scene change S start E end using (daylight,afternoon,....), time, increments
            elif seg[:2] == 'ZL':
                segs_split = seg[3:].split("_")
                scene_change("lifx", segs_split[0], segs_split[1],
                             float(segs_split[2]), int(segs_split[3]))
            # ZN_S_E_T_I = Scene change S start E end using (red,green,....), time, increments
            elif seg[:2] == 'ZN':
                segs_split = seg[3:].split("_")
                scene_change("neo", segs_split[0], segs_split[1],
                             float(segs_split[2]), int(segs_split[3]))
            # ZJ = Joke
            elif seg[:2] == 'ZJ':
                get_random_joke()
            # image IXXX/XXX XXX/XXXX(folder/filename)
            elif seg[0] == 'I':
                f_nm = media_folder + seg[1:]
                change_wallpaper(f_nm)
            # SNXXX = Servo N (0 All, 1-6) XXX 0 to 180
            if seg[0] == 'S':  # servos S
                num = int(seg[1])
                v = int(seg[2:])
                if num == 0:
                    for i in range(6):
                        s_arr[i].angle = v
                else:
                    s_arr[num-1].angle = int(v)
                        # SNXXX = Servo N (0 All, 1-6) XXX 0 to 180
            if seg[0] == 'Q':  # QXXX/XXX = Add media to queue XXX/XXX (folder/filename)
                file_nm = seg[1:]
                stop_play_list = False
                add_command(file_nm)
            if seg[:3] == 'API':  # API_UUU_EEE_DDD = Api POST call UUU base url, EEE endpoint, DDD data object i.e. {"an": data_object}
                seg_split = seg.split("_")
                send_animator_post(seg_split[1], seg_split[2], seg_split[3])
            # C_NN,..._TTT = Cycle, NN one or many commands separated by slashes, TTT interval in decimal seconds between commands
            elif seg[0] == 'C':
                print("not implemented")
    except Exception as e:
        files.log_item(e)

##############################
# Led color effects


def random_effect(il, ih, d):
    i = random.randint(il, ih)
    if i == 1:
        rbow(.005, d)
    elif i == 2:
        multi_color()
        time.sleep(d)
    elif i == 3:
        fire(d)


def rbow(spd, dur):
    st = time.monotonic()
    te = time.monotonic()-st
    while te < dur:
        for j in range(0, 255, 1):
            if not an_running:
                return
            for i in range(n_px):
                pixel_index = (i * 256 // n_px) + j
                led[i] = colorwheel(pixel_index & 255)
            led.show()
            time.sleep(spd)
            te = time.monotonic()-st
            if te > dur:
                return
        for j in reversed(range(0, 255, 1)):
            for i in range(n_px):
                pixel_index = (i * 256 // n_px) + j
                led[i] = colorwheel(pixel_index & 255)
            led.show()
            time.sleep(spd)
            te = time.monotonic()-st
            if te > dur:
                return


def fire(dur):
    st = time.monotonic()

    firei = []

    firei.extend(ornmnts)
    firei.extend(cane_s)
    firei.extend(cane_e)

    stari = []
    stari.extend(stars)

    for i in stari:
        led[i] = (255, 255, 255)

    brnchsi = []
    brnchsi.extend((brnchs))

    for i in brnchsi:
        led[i] = (50, 50, 50)

    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)

    print(len(firei))

    # Flicker, based on our initial RGB values
    while True:
        for i in firei:
            if not an_running:
                return
            f = random.randint(0, 110)
            r1 = bnd(r-f, 0, 255)
            g1 = bnd(g-f, 0, 255)
            b1 = bnd(b-f, 0, 255)
            led[i] = (r1, g1, b1)
            led.show()
        time.sleep(random.uniform(0.05, 0.1))
        te = time.monotonic()-st
        if te > dur:
            return


def multi_color():
    for i in range(0, n_px):
        if not an_running:
            return
        r = random.randint(128, 255)
        g = random.randint(128, 255)
        b = random.randint(128, 255)
        c = random.randint(0, 2)
        if c == 0:
            r1 = r
            g1 = 0
            b1 = 0
        elif c == 1:
            r1 = 0
            g1 = g
            b1 = 0
        elif c == 2:
            r1 = 0
            g1 = 0
            b1 = b
        led[i] = (r1, g1, b1)

    stari = []
    stari.extend(stars)

    for i in stari:
        led[i] = (255, 255, 255)

    brnchsi = []
    brnchsi.extend((brnchs))

    for i in brnchsi:
        led[i] = (7, 163, 30)

    canei = []
    canei.extend(cane_e)
    for i in canei:
        led[i] = (255, 255, 255)
    led.show()


def bnd(c, l, u):
    if (c < l):
        c = l
    if (c > u):
        c = u
    return c

################################################################################
# State Machine


class StMch(object):

    def __init__(self):
        self.state = None
        self.states = {}
        self.paused_state = None

    def add(self, state):
        self.states[state.name] = state

    def go_to(self, state_name):
        if self.state:
            self.state.exit(self)
        self.state = self.states[state_name]
        self.state.enter(self)

    def upd(self):
        if self.state:
            self.state.upd(self)

################################################################################
# States

# Abstract parent state class.


class Ste(object):

    def __init__(self):
        pass

    @property
    def name(self):
        return ''

    def enter(self, mch):
        pass

    def exit(self, mch):
        pass

    def upd(self, mch):
        pass


class BseSt(Ste):

    def __init__(self):
        pass

    @property
    def name(self):
        return 'base_state'

    def enter(self, mch):
        play_a_0(code_folder + "mvc/animations_are_now_active.wav")
        files.log_item("Entered base state")
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        global cont_run, an_running, stop_play_list
        if an_running:
            switch_state = utilities.switch_state_four_switches(
                l_sw, r_sw, three_sw, four_sw, time.sleep, 3.0)
            if switch_state == "left" and cfg["can_cancel"]:
                an_running = False
                mix.stop()
                media_player.stop()
                rst_an()
                time.sleep(.5)
            if switch_state == "right" and cfg["can_cancel"]:
                an_running = False  
                stop_play_list = True
                mix.stop()
                media_player.stop()
                rst_an()
                time.sleep(.5)
            if switch_state == "three":
                print("sw three fell")
                ch_vol("lower")
            if switch_state == "four":
                print("sw four fell")
                ch_vol("raise")
        else:
            switch_state = utilities.switch_state(
                l_sw, r_sw, time.sleep, 3.0)
            if switch_state == "left_held":
                if cont_run:
                    cont_run = False
                    play_a_0(code_folder + "mvc/continuous_mode_deactivated.wav")
                else:
                    cont_run = True
                    play_a_0(code_folder + "mvc/continuous_mode_activated.wav")
            elif switch_state == "left" or cont_run:
                stop_play_list = False
                add_command(cfg["option_selected"])
                time.sleep(.5)
            elif switch_state == "right":
                mch.go_to('main_menu')
        time.sleep(.1)

class Main(Ste):

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'main_menu'

    def enter(self, mch):
        files.log_item('Main menu')
        play_a_0(code_folder + "mvc/main_menu.wav")
        l_r_but()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            play_a_0(code_folder + "mvc/" + main_m[self.i] + ".wav")
            self.sel_i = self.i
            self.i += 1
            if self.i > len(main_m)-1:
                self.i = 0
        if r_sw.fell:
            sel_mnu = main_m[self.sel_i]
            if sel_mnu == "choose_sounds":
                mch.go_to('choose_sounds')
            elif sel_mnu == "add_sounds_animate":
                mch.go_to('add_sounds_animate')
            elif sel_mnu == "web_options":
                mch.go_to('web_options')
            elif sel_mnu == "volume_level_adjustment":
                mch.go_to('volume_level_adjustment')
            elif sel_mnu == "intermission_settings":
                mch.go_to('intermission_settings')
            else:
                play_a_0(code_folder + "mvc/all_changes_complete.wav")
                mch.go_to('base_state')


class Snds(Ste):

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'choose_sounds'

    def enter(self, mch):
        files.log_item('Choose sounds menu')
        play_a_0(code_folder + "mvc/sound_selection_menu.wav")
        l_r_but()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            try:
                play_a_0(code_folder + "snd_opt/" + menu_snd_opt[self.i])
            except Exception as e:
                files.log_item(e)
                spk_sng_num(str(self.i+1))
            self.sel_i = self.i
            self.i += 1
            if self.i > len(menu_snd_opt)-1:
                self.i = 0
        if r_sw.fell:
            cfg["option_selected"] = menu_snd_opt[self.sel_i][:-4]
            files.write_json_file(code_folder + "cfg.json", cfg)
            play_a_0(code_folder + "mvc/option_selected.wav", "rb")
            mch.go_to('base_state')


class IntermissionSettings(Ste):

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'intermission_settings'

    def enter(self, mch):
        files.log_item('Intermission settings')
        play_a_0(code_folder + "mvc/intermission_settings_menu.wav")
        l_r_but()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        global cfg
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            play_a_0(
                code_folder + "mvc/" + intermission_settings[self.i] + ".wav")
            self.sel_i = self.i
            self.i += 1
            if self.i > len(intermission_settings)-1:
                self.i = 0
        if r_sw.fell:
            sel_mnu = intermission_settings[self.sel_i]
            if sel_mnu == "intermission_off":
                cfg["intermission"] = "0"
                files.write_json_file(code_folder + "cfg.json", cfg)
                play_a_0(code_folder + "mvc/all_changes_complete.wav")
                mch.go_to('base_state')
            elif sel_mnu == "intermission_infreq":
                cfg["intermission"] = "0.33"
                files.write_json_file(code_folder + "cfg.json", cfg)
                play_a_0(code_folder + "mvc/all_changes_complete.wav")
                mch.go_to('base_state')
            elif sel_mnu == "intermission_freq":
                cfg["intermission"] = "0.66"
                files.write_json_file(code_folder + "cfg.json", cfg)
                play_a_0(code_folder + "mvc/all_changes_complete.wav")
                mch.go_to('base_state')
            elif sel_mnu == "intermission_always":
                cfg["intermission"] = "1"
                files.write_json_file(code_folder + "cfg.json", cfg)
                play_a_0(code_folder + "mvc/all_changes_complete.wav")
                mch.go_to('base_state')

class AddSnds(Ste):

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'add_sounds_animate'

    def enter(self, mch):
        files.log_item('Add sounds animate')
        play_a_0(code_folder + "mvc/add_sounds_animate.wav")
        l_r_but()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        global ts_mode
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            play_a_0(
                code_folder + "mvc/" + add_snd[self.i] + ".wav")
            self.sel_i = self.i
            self.i += 1
            if self.i > len(add_snd)-1:
                self.i = 0
        if r_sw.fell:
            sel_mnu = add_snd[self.sel_i]
            if sel_mnu == "hear_instructions":
                play_a_0(code_folder + "mvc/drive_in_media_instructions.wav")
            elif sel_mnu == "timestamp_mode_on":
                ts_mode = True
                play_a_0(code_folder + "mvc/timestamp_mode_on.wav")
                play_a_0(code_folder + "mvc/timestamp_instructions.wav")
                mch.go_to('base_state')
            elif sel_mnu == "timestamp_mode_off":
                ts_mode = False
                play_a_0(code_folder + "mvc/timestamp_mode_off.wav")
            else:
                play_a_0(code_folder + "mvc/all_changes_complete.wav")
                mch.go_to('base_state')


class VolumeLevelAdjustment(Ste):

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'volume_level_adjustment'

    def enter(self, mch):
        files.log_item('Set Web Options')
        play_a_0(code_folder + "mvc/volume_adjustment_menu.wav")
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        done = False
        while not done:
            switch_state = utilities.switch_state(
                l_sw, r_sw, time.sleep, 3.0)
            if switch_state == "left":
                ch_vol("lower")
            elif switch_state == "right":
                ch_vol("raise")
            elif switch_state == "right_held":
                files.write_json_file(
                    code_folder + "cfg.json", cfg)
                play_a_0(code_folder + "mvc/all_changes_complete.wav")
                done = True
                mch.go_to('base_state')
            time.sleep(0.1)
            pass


class WebOpt(Ste):
    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'web_options'

    def enter(self, mch):
        files.log_item('Set Web Options')
        sel_web()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        global cfg
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            play_a_0(code_folder + "mvc/" + web_m[self.i] + ".wav")
            self.sel_i = self.i
            self.i += 1
            if self.i > len(web_m)-1:
                self.i = 0
        if r_sw.fell:
            selected_menu_item = web_m[self.sel_i]
            if selected_menu_item == "web_on":
                cfg["serve_webpage"] = True
                opt_sel()
                files.write_json_file(code_folder + "cfg.json", cfg)
                restart_pi_timer()
            elif selected_menu_item == "web_off":
                cfg["serve_webpage"] = False
                opt_sel()
                files.write_json_file(code_folder + "cfg.json", cfg)
                restart_pi_timer()
            elif selected_menu_item == "hear_url":
                spk_str(cfg["HOST_NAME"], True)
                sel_web()
            elif selected_menu_item == "hear_instr_web":
                play_a_0(code_folder + "mvc/hear_instr_web_drive_in.wav")
                sel_web()
            else:
                mch.go_to('base_state')

###############################################################################
# Create the state machine


st_mch = StMch()
st_mch.add(BseSt())
st_mch.add(Main())
st_mch.add(Snds())
st_mch.add(AddSnds())
st_mch.add(VolumeLevelAdjustment())
st_mch.add(WebOpt())
st_mch.add(IntermissionSettings())


time.sleep(0)
aud_en.value = True
upd_vol(1)

if (web):
    files.log_item("starting server...")
    try:
        # Wait for the network to be ready before continuing
        wait_for_network()

        # Register mDNS service
        zeroconf = Zeroconf()
        print("Registering mDNS service...")
        zeroconf.register_service(info)

        # Run the server in a separate thread to allow mDNS to work simultaneously
        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True
        server_thread.start()
        spk_web()
    except OSError:
        time.sleep(5)
        files.log_item("server did not start...")

discover_lights()

is_gtts_reachable = check_gtts_status()

manage_audio_files()

st_mch.go_to('base_state')
files.log_item("animator has started...")
gc_col("animations started.")


def run_state_machine():
    while True:
        st_mch.upd()
        time.sleep(.1)


# Start the state machine in a separate thread
state_machine_thread = threading.Thread(target=run_state_machine)

# Daemonize the thread to end with the main program
state_machine_thread.daemon = True
state_machine_thread.start()

# Start the queue processing thread
command_queue_processing_thread = threading.Thread(target=process_commands)

# Daemonize the thread to end with the main program
command_queue_processing_thread.daemon = True
command_queue_processing_thread.start()

if (web):
    close_midori()
    open_midori()

while True:
    try:
        input("Press enter to exit...\n\n")
    finally:
        stop_all_queue_commands()
        command_queue_processing_thread.join() # Wait for the command queue processing thread to finish
        if (web):
            print("Unregistering mDNS service...")
            zeroconf.unregister_service(info)
            zeroconf.close()
            httpd.shutdown()
        rst_an()
        quit()


# type: ignore
