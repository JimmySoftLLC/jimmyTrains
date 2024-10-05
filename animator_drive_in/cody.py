import http.server
import socket
import socketserver
import threading
from zeroconf import ServiceInfo, Zeroconf
import json
import os
import gc
import vlc
import time
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

aud_en = digitalio.DigitalInOut(board.D26)
aud_en.direction = digitalio.Direction.OUTPUT
aud_en.value = False


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
    delay = 5
    timer = threading.Timer(delay, restart_pi)
    timer.start()


gc_col("Imports gc, files")

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
w_sw = Debouncer(switch_io_3)
b_sw = Debouncer(switch_io_4)

################################################################################
# Setup sound
# i2s audio is setup on pi with an overlay

# Setup the mixer to play wav files
pygame.mixer.init()
mix = pygame.mixer.music

################################################################################
# Setup video hardware

# create vlc media player object for playing video, music etc
media_player = vlc.MediaPlayer()
media_player.toggle_fullscreen()


def pause_movie():
    media_player.pause()


def play_movie():
    media_player.play()


def play_movie_file(movie_filename):
    media = vlc.Media(movie_filename)
    media_player.set_media(media)
    media_player.play()
    while not media_player.is_playing():
        upd_vol(.1)


################################################################################
# Setup servo hardware
m1_pwm = pwmio.PWMOut(board.D6, duty_cycle=2 ** 15, frequency=50)  # D23
m2_pwm = pwmio.PWMOut(board.D13, duty_cycle=2 ** 15, frequency=50)  # D24
m3_pwm = pwmio.PWMOut(board.D23, duty_cycle=2 ** 15, frequency=50)  # D25
m4_pwm = pwmio.PWMOut(board.D24, duty_cycle=2 ** 15, frequency=50)  # D6
m5_pwm = pwmio.PWMOut(board.D25, duty_cycle=2 ** 15, frequency=50)  # D13
m6_pwm = pwmio.PWMOut(board.D12, duty_cycle=2 ** 15, frequency=50)  # D12
m7_pwm = pwmio.PWMOut(board.D16, duty_cycle=2 ** 15, frequency=50)  # D16
m8_pwm = pwmio.PWMOut(board.D20, duty_cycle=2 ** 15, frequency=50)  # D20

m1_servo = servo.Servo(m1_pwm)
m2_servo = servo.Servo(m2_pwm)
m3_servo = servo.Servo(m3_pwm)
m4_servo = servo.Servo(m4_pwm)
m5_servo = servo.Servo(m5_pwm)
m6_servo = servo.Servo(m6_pwm)
m7_servo = servo.Servo(m7_pwm)
m8_servo = servo.Servo(m8_pwm)

m1_servo.angle = 90
m2_servo.angle = 90
m3_servo.angle = 90
m4_servo.angle = 90
m5_servo.angle = 90
m6_servo.angle = 90
m7_servo.angle = 90
m8_servo.angle = 90

################################################################################
# Setup neo pixels
num_px = 10
led = neopixel_spi.NeoPixel_SPI(
    board.SPI(), num_px, brightness=1.0, auto_write=False)

################################################################################
# Sd card config variables

cfg = files.read_json_file("/home/pi/cfg.json")


def upd_media():
    global sndtrk_opt, plylst_opt, mysndtrk_opt, all_snd_opt, menu_snd_opt
    sndtrk_opt = files.return_directory("", "/home/pi/sndtrk", ".wav", False)
    video_opt = files.return_directory("", "/home/pi/sndtrk", ".mp4", False)
    sndtrk_opt.extend(video_opt)
    print("Sound tracks: " + str(sndtrk_opt))

    plylst_opt = files.return_directory("plylst_", "/home/pi/plylst", ".json", True)
    print("Play lists: " + str(plylst_opt))

    mysndtrk_opt = files.return_directory(
        "customers_owned_music_", "/home/pi/customers_owned_music", ".wav", False)
    myvideo_opt = files.return_directory(
        "customers_owned_music_", "/home/pi/customers_owned_music", ".mp4", False)
    mysndtrk_opt.extend(myvideo_opt)
    print("My sound tracks: " + str(mysndtrk_opt))

    all_snd_opt = []
    all_snd_opt.extend(plylst_opt)
    all_snd_opt.extend(sndtrk_opt)
    all_snd_opt.extend(mysndtrk_opt)

    menu_snd_opt = []
    menu_snd_opt.extend(plylst_opt)
    rnd_opt = ['rnd plylst', 'rnd sndtrk', 'rnd mysndtrk', 'rnd all']
    menu_snd_opt.extend(rnd_opt)
    menu_snd_opt.extend(sndtrk_opt)
    menu_snd_opt.extend(mysndtrk_opt)

    print("Menu sound tracks: " + str(menu_snd_opt))


upd_media()

web = cfg["serve_webpage"]

cfg_main = files.read_json_file("/home/pi/mvc/main_menu.json")
main_m = cfg_main["main_menu"]

cfg_web = files.read_json_file("/home/pi/mvc/web_menu.json")
web_m = cfg_web["web_menu"]

cfg_vol = files.read_json_file("/home/pi/mvc/volume_settings.json")
vol_set = cfg_vol["volume_settings"]

cfg_add_song = files.read_json_file(
    "/home/pi/mvc/add_sounds_animate.json")
add_snd = cfg_add_song["add_sounds_animate"]

cont_run = False
ts_mode = False
lst_opt = ''
an_running = False


################################################################################
# Setup wifi and web server

def wait_for_network():
    while True:
        try:
            # Attempt to connect to Google's public DNS server to check network availability
            socket.create_connection(("8.8.8.8", 53))
            print("Network is ready!")
            return
        except OSError:
            print("Waiting for network...")
            time.sleep(1)


# Wait for the network to be ready before continuing
wait_for_network()


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

################################################################################
# Setup routes


class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self.handle_serve_file("/index.html")
        elif self.path.endswith(".css"):
            self.handle_serve_file(self.path, "text/css")
        elif self.path.endswith(".js"):
            self.handle_serve_file(self.path, "application/javascript")
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
        elif self.path == "/get-built-in-sound-tracks":
            self.get_built_in_sound_tracks_post(post_data_obj)
        elif self.path == "/get-customers-sound-tracks":
            self.get_customers_sound_tracks_post(post_data_obj)
        elif self.path == "/speaker":
            self.speaker_post(post_data_obj)
        elif self.path == "/get-light-string":
            self.get_light_string_post(post_data_obj)
        elif self.path == "/update-host-name":
            self.update_host_name_post(post_data_obj)
        elif self.path == "/update-light-string":
            self.update_light_string_post(post_data_obj)
        elif self.path == "/defaults":
            self.defaults_post(post_data_obj)
        elif self.path == "/lights":
            self.lights_post(post_data_obj)
        elif self.path == "/update-host-name":
            self.update_host_name_post(post_data_obj)
        elif self.path == "/get-host-name":
            self.get_host_name_post(post_data_obj)
        elif self.path == "/update-volume":
            self.update_volume_post(post_data_obj)
        elif self.path == "/get-volume":
            self.get_volume_post(post_data_obj)
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
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "Set hardware: " + rq_d["an"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly
        print("Response sent:", response)

    def stop_post(self, rq_d):
        rst_an()
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "rst an"
        self.wfile.write(response.encode('utf-8'))  # Write the string directly
        print("Response sent:", response)

    def rename_playlist_post(self, rq_d):
        global data
        snd = rq_d["fo"].replace("plylst_", "")
        fo = "/home/pi/plylst/" + snd + ".json"
        fn = "/home/pi/plylst/" + rq_d["fn"] + ".json"
        os.rename(fo, fn)
        upd_media()
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "your response message"
        self.wfile.write(response.encode('utf-8'))  # Write the string directly
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
                    f_n = "/home/pi/plylst/" + \
                        snd_f + ".json"
                elif "customers" == an[0]:
                    snd_f = rq_d[3].replace("customers_owned_music_", "")
                    f_n = "/home/pi/customers_owned_music/" + \
                        snd_f + ".json"
                else:
                    f_n = "/home/pi/sndtrk/" + \
                        rq_d[3] + ".json"
                files.write_json_file(f_n, data)
                upd_media()
                data = []
        except:
            data = []
            self.send_response(500)
            # Change the content type to text/plain
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            response = "out of memory"
            # Write the string directly
            self.wfile.write(response.encode('utf-8'))
            print("Response sent:", response)
            return
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "success"
        self.wfile.write(response.encode('utf-8'))  # Write the string directly
        print("Response sent:", response)

    def delete_playlist_post(self, rq_d):
        snd_f = rq_d["fn"].replace("plylst_", "")
        f_n = "/home/pi/plylst/" + snd_f + ".json"
        os.remove(f_n)
        upd_media()
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = rq_d["fn"] + " playlist file deleted"
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def get_animation_post(self, rq_d):
        global cfg, cont_run, ts_mode
        snd_f = rq_d["an"]
        if "plylst_" in snd_f:
            snd_f = snd_f.replace("plylst_", "")
            if (f_exists("/home/pi/plylst/" + snd_f + ".json") == True):
                f_n = "/home/pi/plylst/" + snd_f + ".json"
                self.handle_serve_file_name(f_n)
                return
            else:
                f_n = "/home/pi/t_s_def/timestamp mode.json"
                self.handle_serve_file_name(f_n)
                return
        if "customers_owned_music_" in snd_f:
            snd_f = snd_f.replace("customers_owned_music_", "")
            if (f_exists("/home/pi/customers_owned_music/" + snd_f + ".json") == True):
                f_n = "/home/pi/customers_owned_music/" + snd_f + ".json"
                self.handle_serve_file_name(f_n)
            else:
                f_n = "/home/pi/t_s_def/timestamp mode.json"
                self.handle_serve_file_name(f_n)
                return
        else:
            if (f_exists("/home/pi/sndtrk/" + snd_f + ".json") == True):
                f_n = "/home/pi/sndtrk/" + snd_f + ".json"
                self.handle_serve_file_name(f_n)
                return
            else:
                f_n = "/home/pi/t_s_def/timestamp mode.json"
                self.handle_serve_file_name(f_n)
                return

    def get_scripts_post(self, rq_d):
        sounds = []
        sounds.extend(plylst_opt)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = sounds
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def create_playlist_post(self, rq_d):
        global data
        f_n = "/home/pi/plylst/" + rq_d["fn"] + ".json"
        files.write_json_file(f_n, ["0.0|", "1.0|"])
        upd_media()
        gc_col("created playlist")
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = "created " + rq_d["fn"] + " playlist"
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def update_light_string_post(self, rq_d):
        global cfg
        if rq_d["action"] == "save" or rq_d["action"] == "clear" or rq_d["action"] == "defaults":
            cfg["light_string"] = rq_d["text"]
            print("action: " +
                  rq_d["action"] + " data: " + cfg["light_string"])
            files.write_json_file("/home/pi/cfg.json", cfg)
            # upd_l_str()
            play_a_0("/home/pi/mvc/all_changes_complete.wav")
            self.send_response(200)
            # Change the content type to text/plain
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            response = cfg["light_string"]
            # Write the string directly
            self.wfile.write(response.encode('utf-8'))
            return
        if cfg["light_string"] == "":
            cfg["light_string"] = rq_d["text"]
        else:
            cfg["light_string"] = cfg["light_string"] + \
                "," + rq_d["text"]
        print("action: " + rq_d["action"] +
              " data: " + cfg["light_string"])
        files.write_json_file("/home/pi/cfg.json", cfg)
        # upd_l_str()
        play_a_0("/home/pi/mvc//all_changes_complete.wav")
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["light_string"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def mode_post(self, rq_d):
        print(rq_d)
        global cfg, cont_run, ts_mode
        if rq_d["an"] == "cont_mode_on":
            play_a_0("/home/pi/mvc/continuous_mode_activated.wav")
            cont_run = True
        elif rq_d["an"] == "cont_mode_off":
            play_a_0("/home/pi/mvc/continuous_mode_deactivated.wav")
            cont_run = False
        elif rq_d["an"] == "timestamp_mode_on":
            play_a_0("/home/pi/mvc/timestamp_mode_on.wav")
            play_a_0("/home/pi/mvc/timestamp_instructions.wav")
            ts_mode = True
        elif rq_d["an"] == "timestamp_mode_off":
            play_a_0("/home/pi/mvc/timestamp_mode_off.wav")
            ts_mode = False
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"mode processed": rq_d["an"]}
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def animation_post(self, rq_d):
        global cfg, cont_run, ts_mode
        cfg["option_selected"] = rq_d["an"]
        an(cfg["option_selected"])
        files.write_json_file("/home/pi/cfg.json", cfg)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"Ran animation": cfg["option_selected"]}
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def defaults_post(self, rq_d):
        global cfg
        if rq_d["an"] == "reset_to_defaults":
            rst_def()
            files.write_json_file("/home/pi/cfg.json", cfg)
            play_a_0("/home/pi/mvc/all_changes_complete.wav")
            st_mch.go_to('base_state')
        self.wfile.write("Utility: " + rq_d["an"])

    def speaker_post(self, rq_d):
        global cfg
        if rq_d["an"] == "speaker_test":
            cmd_snt = "speaker_test"
            play_a_0("/home/pi/mvc/left_speaker_right_speaker.wav")
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = rq_d["an"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def get_light_string_post(self, rq_d):
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["light_string"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def update_host_name_post(self, rq_d):
        global cfg
        cfg["HOST_NAME"] = rq_d["text"]
        files.write_json_file("/home/pi/cfg.json", cfg)
        spk_web()
        restart_pi_timer()
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["HOST_NAME"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def get_host_name_post(self, rq_d):
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["HOST_NAME"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def update_volume_post(self, rq_d):
        global cfg
        ch_vol(rq_d["action"])
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["volume"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def get_volume_post(self, rq_d):
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["volume"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def get_customers_sound_tracks_post(self, rq_d):
        upd_media()
        response = []
        response.extend(mysndtrk_opt)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def get_built_in_sound_tracks_post(self, rq_d):
        upd_media()
        response = []
        response.extend(sndtrk_opt)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
        print("Response sent:", response)

    def defaults_post(self, rq_d):
        global cfg
        if rq_d["an"] == "reset_animation_timing_to_defaults":
            for time_stamp_file in ts_jsons:
                time_stamps = files.read_json_file(
                    "/home/pi/t_s_def/" + time_stamp_file + ".json")
                files.write_json_file(
                    "/home/pi/sndtrk/"+time_stamp_file+".json", time_stamps)
            play_a_0("/home/pi/mvc/all_changes_complete.wav")
        elif rq_d["an"] == "reset_to_defaults":
            cmd_snt = "reset_to_defaults"
            rst_def()
            files.write_json_file("/home/pi/cfg.json", cfg)
            play_a_0("/home/pi/mvc/all_changes_complete.wav")
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = cfg["volume"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly

    def lights_post(self, rq_d):
        set_hdw(rq_d["an"], 1)
        self.send_response(200)
        # Change the content type to text/plain
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        response = rq_d["an"]
        self.wfile.write(response.encode('utf-8'))  # Write the string directly


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
# Global Methods


def rst_def():
    global cfg
    cfg["HOST_NAME"] = "animator-drive-in"
    cfg["option_selected"] = "random all"
    cfg["volume"] = "20"

################################################################################
# Dialog and sound play methods


def upd_vol(seconds):
    try:
        volume = int(cfg["volume"]) / 100
    except Exception as e:
        files.log_item(e)
        volume = .5
    if volume < 0 or volume > 1:
        volume = .5
    mix.set_volume(volume)
    media_player.audio_set_volume(int(volume*300))
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
    files.write_json_file("/home/pi/cfg.json", cfg)
    play_a_0("/home/pi/mvc/volume.wav")
    spk_str(cfg["volume"], False)


def play_a_0(file_name, wait_untill_done=True):
    print("playing " + file_name)
    if mix.get_busy():
        mix.stop()
        while mix.get_busy():
            upd_vol(0.1)
    mix.load(file_name)
    mix.play(loops=0)
    while mix.get_busy() and wait_untill_done:
        exit_early()
    print("done playing")


def wait_snd():
    while mix.get_busy():
        exit_early()
    print("done playing")


def stop_a_0():
    mix.stop()
    while mix.get_busy():
        pass


def exit_early():
    upd_vol(0.1)
    l_sw.update()
    if l_sw.fell:
        mix.stop()


def rst_an():
    stop_a_0()
    led.fill((0, 0, 0))
    led.show()


def spk_str(str_to_speak, addLocal):
    for character in str_to_speak:
        try:
            if character == " ":
                character = "space"
            if character == "-":
                character = "dash"
            if character == ".":
                character = "dot"
            play_a_0("/home/pi/mvc/" + character + ".wav")
        except Exception as e:
            files.log_item(e)
            print("Invalid character in string to speak")
    if addLocal:
        play_a_0("/home/pi/mvc/dot.wav")
        play_a_0("/home/pi/mvc/local.wav")


def l_r_but():
    play_a_0("/home/pi/mvc/press_left_button_right_button.wav")


def sel_web():
    play_a_0("/home/pi/mvc/web_menu.wav")
    l_r_but()


def opt_sel():
    play_a_0("/home/pi/mvc/option_selected.wav")


def spk_sng_num(song_number):
    play_a_0("/home/pi/mvc/song.wav")
    spk_str(song_number, False)


def no_trk():
    play_a_0("/home/pi/mvc/no_user_soundtrack_found.wav")
    while True:
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            break
        if r_sw.fell:
            play_a_0("/home/pi/mvc/create_sound_track_files.wav")
            break


def spk_web():
    play_a_0("/home/pi/mvc/animator_available_on_network.wav")
    play_a_0("/home/pi/mvc/to_access_type.wav")
    if cfg["HOST_NAME"] == "animator-drive-in":
        play_a_0("/home/pi/mvc/animator_dash_bandstand.wav")
        play_a_0("/home/pi/mvc/dot.wav")
        play_a_0("/home/pi/mvc/local.wav")
    else:
        spk_str(cfg["HOST_NAME"], True)
    play_a_0("/home/pi/mvc/in_your_browser.wav")

################################################################################
# Animation methods


def stop_all_media():
    mix.stop()
    media_player.stop()
    led.fill((0, 0, 0))
    led.show()


def an(f_nm):
    global cfg, lst_opt, an_running
    print("Filename: " + f_nm)
    cur_opt = f_nm
    try:
        if f_nm == "random built in":
            h_i = len(sndtrk_opt) - 1
            cur_opt = sndtrk_opt[random.randint(
                0, h_i)]
            while lst_opt == cur_opt and len(sndtrk_opt) > 1:
                cur_opt = sndtrk_opt[random.randint(
                    0, h_i)]
            lst_opt = cur_opt
            print("Random sound option: " + f_nm)
            print("Sound file: " + cur_opt)
        elif f_nm == "random my":
            h_i = len(mysndtrk_opt) - 1
            cur_opt = mysndtrk_opt[random.randint(
                0, h_i)]
            while lst_opt == cur_opt and len(mysndtrk_opt) > 1:
                cur_opt = mysndtrk_opt[random.randint(
                    0, h_i)]
            lst_opt = cur_opt
            print("Random sound option: " + f_nm)
            print("Sound file: " + cur_opt)
        elif f_nm == "random all":
            h_i = len(all_snd_opt) - 1
            cur_opt = all_snd_opt[random.randint(
                0, h_i)]
            while lst_opt == cur_opt and len(all_snd_opt) > 1:
                cur_opt = all_snd_opt[random.randint(
                    0, h_i)]
            lst_opt = cur_opt
            print("Random sound option: " + f_nm)
            print("Sound file: " + cur_opt)
        if ts_mode:
            an_ts(cur_opt)
            gc_col("animation cleanup")
        else:
            an_light(cur_opt)
            gc_col("animation cleanup")
    except Exception as e:
        files.log_item(e)
        no_trk()
        cfg["option_selected"] = "random built in"
        return
    gc_col("Animation complete.")


def an_light(f_nm):
    global ts_mode, an_running
    an_running = True

    upd_vol(.1)

    cust_f = "customers_owned_music_" in f_nm
    is_video = ".mp4" in f_nm
    json_fn = f_nm.replace(".mp4", "")
    json_fn = json_fn.replace(".wav", "")
    json_fn = json_fn.replace("customers_owned_music_", "")

    flsh_t = []


    if cust_f:
        f_nm = f_nm.replace("customers_owned_music_", "")
        if (f_exists("/home/pi/customers_owned_music/" + json_fn + ".json") == True):
            flsh_t = files.read_json_file(
                "/home/pi/customers_owned_music/" + json_fn + ".json")
        else:
            try:
                flsh_t = files.read_json_file(
                    "/home/pi/customers_owned_music/" + json_fn + ".json")
            except Exception as e:
                files.log_item(e)
                play_a_0("/home/pi/mvc/no_timestamp_file_found.wav")
                while True:
                    l_sw.update()
                    r_sw.update()
                    if l_sw.fell:
                        ts_mode = False
                        an_running = False
                        return
                    if r_sw.fell:
                        ts_mode = True
                        an_running = False
                        play_a_0("/home/pi/mvc/timestamp_instructions.wav")
                        return
    else:
        if (f_exists("/home/pi/sndtrk/" + json_fn + ".json") == True):
            flsh_t = files.read_json_file(
                "/home/pi/sndtrk/" + json_fn + ".json")

    flsh_i = 0

    if cust_f:
        media0 = "/home/pi/customers_owned_music/" + f_nm
    else:
        media0 = "/home/pi/sndtrk/" + f_nm

    if is_video:
        play_movie_file(media0)
    else:
        play_a_0(media0, False)

    srt_t = time.perf_counter()

    ft1 = []
    ft2 = []

    while True:
        t_past = time.perf_counter()-srt_t

        if flsh_i < len(flsh_t)-1:
            ft1 = flsh_t[flsh_i].split("|")
            ft2 = flsh_t[flsh_i+1].split("|")
            dur = float(ft2[0]) - float(ft1[0]) - 0.25
        else:
            dur = 0.25
        if dur < 0:
            dur = 0
        if t_past > float(ft1[0]) - 0.25 and flsh_i < len(flsh_t)-1:
            files.log_item("time elapsed: " + str(t_past) +
                           " Timestamp: " + ft1[0])
            if (len(ft1) == 1 or ft1[1] == ""):
                pos = random.randint(60, 120)
                lgt = random.randint(60, 120)
                # loop.create_task(set_hdw_async("L0" + str(lgt) + ",S0" + str(pos),dur))
            # else:
                # loop.create_task(set_hdw_async(ft1[1],dur))
            flsh_i += 1
        l_sw.update()
        if l_sw.fell and cfg["can_cancel"]:
            mix.stop()
            media_player.stop()
        if not mix.get_busy() and not media_player.is_playing():
            stop_all_media()
            an_running = False
            return
        upd_vol(.1)


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

    f_nm = f_nm.replace("customers_owned_music_", "")

    if cust_f:
        media0 = "/home/pi/customers_owned_music/" + f_nm
    else:
        media0 = "/home/pi/sndtrk/" + f_nm

    if is_video:
        play_movie_file(media0)
    else:
        play_a_0(media0, False)

    startTime = time.perf_counter()
    upd_vol(.1)

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
                    "/home/pi/customers_owned_music/" + json_fn + ".json", t_s)
            else:
                files.write_json_file(
                    "/home/pi/sndtrk/" + json_fn + ".json", t_s)
            break

    ts_mode = False
    stop_all_media()
    play_a_0("/home/pi/mvc/timestamp_saved.wav")
    play_a_0("/home/pi/mvc/timestamp_mode_off.wav")
    play_a_0("/home/pi/mvc/animations_are_now_active.wav")


###############
# Animation helpers

br = 0


def set_hdw(cmd, dur):
    global sp, br
    # Split the input string into segments
    segs = cmd.split(",")

    # Process each segment
    try:
        for seg in segs:
            f_nm = ""
            if seg[0] == 'E':  # end an
                return "STOP"
            if seg[0] == 'M':  # play file
                if seg[1] == "S":
                    stop_a_0()
                elif seg[1] == "W" or seg[1] == "A" or seg[1] == "P":
                    stop_a_0()
                    if seg[2] == "S":
                        w0 = "/home/pi/sndtrk/" + seg[3:] + ".wav"
                        f_nm = seg[3:]
                    elif seg[2] == "M":
                        w0 = "/home/pi/customers_owned_music/" + \
                            seg[3:] + ".wav"
                        f_nm = "customers_owned_music_" + seg[3:]
                    elif seg[2] == "P":
                        f_nm = "plylst_" + seg[3:]
                    if seg[1] == "W" or seg[1] == "P":
                        play_a_0(w0, False)
                    if seg[1] == "A":
                        res = an(f_nm)
                        if res == "STOP":
                            return "STOP"
                    if seg[1] == "W":
                        wait_snd()
            if seg[0] == 'L':  # lights
                mod = (int(seg[1])*10+int(seg[2]))*2
                mod_num = mod - 2
                print(mod_num)
                ind = int(seg[4])-1
                if ind == 0:
                    ind = 1
                elif ind == 1:
                    ind = 0
                elif ind == 3:
                    ind = 4
                elif ind == 4:
                    ind = 3
                v = int(seg[5:])
                print(v)
                if seg[1] == "0" and seg[2] == "0":
                    led.fill((v, v, v))
                else:
                    if seg[4] == "0":
                        led[mod_num] = (v, v, v)
                        led[mod_num+1] = (v, v, v)
                    elif ind < 3:
                        cur = list(led[mod_num])
                        cur[ind] = v
                        led[mod_num] = (cur[0], cur[1], cur[2])
                    else:
                        cur = list(led[mod_num+1])
                        cur[ind-3] = v
                        led[mod_num+1] = (cur[0], cur[1], cur[2])
                led.show()
            if seg[0] == 'B':  # brightness
                br = int(seg[1:])
                led.brightness = float(br/100)
                led.show()
            if seg[0] == 'F':  # fade in or out
                v = int(seg[1])*100+int(seg[2])*10+int(seg[3])
                s = float(seg[4:])
                while not br == v:
                    if br < v:
                        br += 1
                        led.brightness = float(br/100)
                    else:
                        br -= 1
                        led.brightness = float(br/100)
                    led.show()
                    upd_vol(s)
            if seg[0] == 'R':
                v = float(seg[1:])
                rbow(v, dur)
            if seg[0] == 'C':
                print("not implemented")
    except Exception as e:
        files.log_item(e)


def rbow(spd, dur):
    st = time.monotonic()
    te = time.monotonic()-st
    while te < dur:
        for j in range(0, 255, 1):
            for i in range(num_px):
                pixel_index = (i * 256 // num_px) + j
                led[i] = colorwheel(pixel_index & 255)
            led.show()
            upd_vol(spd)
            te = time.monotonic()-st
            if te > dur:
                return
        for j in reversed(range(0, 255, 1)):
            for i in range(num_px):
                pixel_index = (i * 256 // num_px) + j
                led[i] = colorwheel(pixel_index & 255)
            led.show()
            upd_vol(spd)
            te = time.monotonic()-st
            if te > dur:
                return

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
    global an_running

    def __init__(self):
        pass

    @property
    def name(self):
        return 'base_state'

    def enter(self, mch):
        play_a_0("/home/pi/mvc/animations_are_now_active.wav")
        files.log_item("Entered base state")
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        global cont_run
        switch_state = utilities.switch_state(
            l_sw, r_sw, upd_vol, 3.0)
        if switch_state == "left_held":
            if cont_run:
                cont_run = False
                play_a_0("/home/pi/mvc/continuous_mode_deactivated.wav")
            else:
                cont_run = True
                play_a_0("/home/pi/mvc/continuous_mode_activated.wav")
        elif switch_state == "left" or cont_run and not an_running:
            an(cfg["option_selected"])
        elif switch_state == "right":
            mch.go_to('main_menu')


class Main(Ste):

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'main_menu'

    def enter(self, mch):
        files.log_item('Main menu')
        play_a_0("/home/pi/mvc/main_menu.wav")
        l_r_but()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            play_a_0("/home/pi/mvc/" + main_m[self.i] + ".wav")
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
            elif sel_mnu == "volume_settings":
                mch.go_to('volume_settings')
            else:
                play_a_0("/home/pi/mvc/all_changes_complete.wav")
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
        play_a_0("/home/pi/mvc/sound_selection_menu.wav")
        l_r_but()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            try:
                play_a_0("/home/pi/o_snds/" + menu_snd_opt[self.i] + ".wav")
            except Exception as e:
                files.log_item(e)
                spk_sng_num(str(self.i+1))
            self.sel_i = self.i
            self.i += 1
            if self.i > len(menu_snd_opt)-1:
                self.i = 0
        if r_sw.fell:
            cfg["option_selected"] = menu_snd_opt[self.sel_i]
            files.write_json_file("/home/pi/cfg.json", cfg)
            play_a_0("/home/pi/mvc/option_selected.wav", "rb")
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
        play_a_0("/home/pi/mvc/add_sounds_animate.wav")
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
                "/home/pi/mvc/" + add_snd[self.i] + ".wav")
            self.sel_i = self.i
            self.i += 1
            if self.i > len(add_snd)-1:
                self.i = 0
        if r_sw.fell:
            sel_mnu = add_snd[self.sel_i]
            if sel_mnu == "hear_instructions":
                play_a_0("/home/pi/mvc/create_sound_track_files.wav")
            elif sel_mnu == "timestamp_mode_on":
                ts_mode = True
                play_a_0("/home/pi/mvc/timestamp_mode_on.wav")
                play_a_0("/home/pi/mvc/timestamp_instructions.wav")
                mch.go_to('base_state')
            elif sel_mnu == "timestamp_mode_off":
                ts_mode = False
                play_a_0("/home/pi/mvc/timestamp_mode_off.wav")
            else:
                play_a_0("/home/pi/mvc/all_changes_complete.wav")
                mch.go_to('base_state')


class VolSet(Ste):

    def __init__(self):
        self.i = 0
        self.sel_i = 0

    @property
    def name(self):
        return 'volume_settings'

    def enter(self, mch):
        files.log_item('Set Web Options')
        play_a_0("/home/pi/mvc/volume_settings_menu.wav")
        l_r_but()
        Ste.enter(self, mch)

    def exit(self, mch):
        Ste.exit(self, mch)

    def upd(self, mch):
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            play_a_0("/home/pi/mvc/" + vol_set[self.i] + ".wav")
            self.sel_i = self.i
            self.i += 1
            if self.i > len(vol_set)-1:
                self.i = 0
        if r_sw.fell:
            sel_mnu = vol_set[self.sel_i]
            if sel_mnu == "volume_level_adjustment":
                play_a_0("/home/pi/mvc/volume_adjustment_menu.wav")
                done = False
                while not done:
                    switch_state = utilities.switch_state(
                        l_sw, r_sw, upd_vol, 3.0)
                    if switch_state == "left":
                        ch_vol("lower")
                    elif switch_state == "right":
                        ch_vol("raise")
                    elif switch_state == "right_held":
                        files.write_json_file(
                            "/home/pi/cfg.json", cfg)
                        play_a_0("/home/pi/mvc/all_changes_complete.wav")
                        done = True
                        mch.go_to('base_state')
                    upd_vol(0.1)
                    pass
            elif sel_mnu == "volume_pot_off":
                cfg["volume_pot"] = False
                if cfg["volume"] == 0:
                    cfg["volume"] = 10
                files.write_json_file("/home/pi/cfg.json", cfg)
                play_a_0("/home/pi/mvc/all_changes_complete.wav")
                mch.go_to('base_state')
            elif sel_mnu == "volume_pot_on":
                cfg["volume_pot"] = True
                files.write_json_file("/home/pi/cfg.json", cfg)
                play_a_0("/home/pi/mvc/all_changes_complete.wav")
                mch.go_to('base_state')


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
        l_sw.update()
        r_sw.update()
        if l_sw.fell:
            play_a_0("/home/pi/mvc/" + web_m[self.i] + ".wav")
            self.sel_i = self.i
            self.i += 1
            if self.i > len(web_m)-1:
                self.i = 0
        if r_sw.fell:
            selected_menu_item = web_m[self.sel_i]
            if selected_menu_item == "web_on":
                cfg["serve_webpage"] = True
                opt_sel()
                sel_web()
            elif selected_menu_item == "web_off":
                cfg["serve_webpage"] = False
                opt_sel()
                sel_web()
            elif selected_menu_item == "hear_url":
                spk_str(cfg["HOST_NAME"], True)
                sel_web()
            elif selected_menu_item == "hear_instr_web":
                play_a_0("/home/pi/mvc/web_instruct.wav")
                sel_web()
            else:
                files.write_json_file("/home/pi/cfg.json", cfg)
                play_a_0("/home/pi/mvc/all_changes_complete.wav")
                mch.go_to('base_state')

###############################################################################
# Create the state machine


st_mch = StMch()
st_mch.add(BseSt())
st_mch.add(Main())
st_mch.add(Snds())
st_mch.add(AddSnds())
st_mch.add(VolSet())
st_mch.add(WebOpt())


upd_vol(0)
aud_en.value = True
time.sleep(1)

if (web):
    files.log_item("starting server...")
    try:
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


st_mch.go_to('base_state')
files.log_item("animator has started...")
gc_col("animations started.")


def run_state_machine():
    global run_movie_cont
    while True:
        st_mch.upd()
        time.sleep(0.1)  # Add a small delay to prevent excessive CPU usage
        upd_vol(.1)


# Start the state machine in a separate thread
state_machine_thread = threading.Thread(target=run_state_machine)

# Daemonize the thread to end with the main program
state_machine_thread.daemon = True
state_machine_thread.start()

while True:
    try:
        input("Press enter to exit...\n\n")
    finally:
        print("Unregistering mDNS service...")
        zeroconf.unregister_service(info)
        zeroconf.close()
        httpd.shutdown()
        quit()


# type: ignore