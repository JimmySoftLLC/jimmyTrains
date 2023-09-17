import gc
import files

def garbage_collect(collection_point):
    gc.collect()
    start_mem = gc.mem_free()
    files.log_item( "Point " + collection_point + " Available memory: {} bytes".format(start_mem) )
    
garbage_collect("Imports gc, files")

import time
import audiocore
import audiomixer
import audiobusio
import sdcardio
import storage
import busio
import pwmio
import digitalio
import board
import neopixel
import random
import rtc
import microcontroller

import audiomp3
from analogio import AnalogIn
from rainbowio import colorwheel
from adafruit_debouncer import Debouncer

import animate_lightning

def reset_pico():
    microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
    microcontroller.reset()
    
garbage_collect("imports")
################################################################################
# Setup hardware

# Setup and analog pin to be used for volume control
# the the volume control is digital by setting mixer voice levels
analog_in = AnalogIn(board.A0)

def get_voltage(pin, wait_for):
    my_increment = wait_for/10
    pin_value = 0
    for _ in range(10):
        time.sleep(my_increment)
        pin_value += 1
        pin_value = pin_value / 10
    return (pin.value) / 65536

audio_enable = digitalio.DigitalInOut(board.GP28)
audio_enable.direction = digitalio.Direction.OUTPUT
audio_enable.value = False

# Setup the switches, there are two the Left and Right or Black and Red
SWITCH_1_PIN = board.GP6 #S1 on animator board
SWITCH_2_PIN = board.GP7 #S2 on animator board

switch_io_1 = digitalio.DigitalInOut(SWITCH_1_PIN)
switch_io_1.direction = digitalio.Direction.INPUT
switch_io_1.pull = digitalio.Pull.UP
left_switch = Debouncer(switch_io_1)

switch_io_2 = digitalio.DigitalInOut(SWITCH_2_PIN)
switch_io_2.direction = digitalio.Direction.INPUT
switch_io_2.pull = digitalio.Pull.UP
right_switch = Debouncer(switch_io_2)

# setup audio on the i2s bus, the animator uses the MAX98357A
# the animator can have one or two MAX98357As. one for mono two for stereo
# both MAX98357As share the same bus
# for mono the MAX98357A defaults to combine channels
# for stereo the MAX98357A SD pin is connected to VCC for right and a resistor to VCC for left
# the audio mixer is used so that volume can be control digitally it is set to stereo
# the sample_rate of the audio mixer is set to 22050 hz.  This is the max the raspberry pi pico can handle
# all files with be in the wave format instead of mp3.  This eliminates the need for decoding
i2s_bclk = board.GP18   # BCLK on MAX98357A
i2s_lrc = board.GP19  # LRC on MAX98357A
i2s_din = board.GP20  # DIN on MAX98357A

audio = audiobusio.I2SOut(bit_clock=i2s_bclk, word_select=i2s_lrc, data=i2s_din)

# Setup sdCard
# the sdCard holds all the media and calibration files
# if the card is missing a voice command is spoken
# the user inserts the card a presses the left button to move forward
audio_enable.value = True
sck = board.GP2
si = board.GP3
so = board.GP4
cs = board.GP5
spi = busio.SPI(sck, si, so)
try:
  sdcard = sdcardio.SDCard(spi, cs)
  vfs = storage.VfsFat(sdcard)
  storage.mount(vfs, "/sd")
except:
  wave0 = audiomp3.MP3Decoder(open("wav/micro_sd_card_not_inserted.mp3", "rb"))
  audio.play(wave0)
  while audio.playing:
    pass
  cardInserted = False
  while not cardInserted:
    left_switch.update()
    if left_switch.fell:
        try:
            sdcard = sdcardio.SDCard(spi, cs)
            vfs = storage.VfsFat(sdcard)
            storage.mount(vfs, "/sd")
            cardInserted = True
            wave0 = audiomp3.MP3Decoder(open("wav/micro_sd_card_success.mp3", "rb"))
            audio.play(wave0)
            while audio.playing:
                pass
        except:
            wave0 = audiomp3.MP3Decoder(open("wav/micro_sd_card_not_inserted.mp3", "rb"))
            audio.play(wave0)
            while audio.playing:
                pass

# Setup the mixer it can play higher quality audio wav using larger wave files
# wave files are less cpu intensive since they are not compressed
num_voices = 1
mixer = audiomixer.Mixer(voice_count=num_voices, sample_rate=22050, channel_count=2,
                         bits_per_sample=16, samples_signed=True, buffer_size=8192)
audio.play(mixer)

audio_enable.value = False

# Setup time
r = rtc.RTC()
r.datetime = time.struct_time((2019, 5, 29, 15, 14, 15, 0, -1, -1))

#setup neo pixels
num_pixels = 60
ledStrip = neopixel.NeoPixel(board.GP10, num_pixels)
ledStrip.auto_write = False
ledStrip.brightness = 1.0

################################################################################
# Global Variables

config = files.read_json_file("/sd/config_lightning.json")

sound_options = config["options"]

serve_webpage = config["serve_webpage"]

garbage_collect("config setup")

################################################################################
# Setup wifi and web server

if (serve_webpage):
    import socketpool
    import mdns
    garbage_collect("config wifi imports")
    import wifi
    garbage_collect("config wifi imports")
    from adafruit_httpserver import Server, Request, FileResponse, Response, POST
    garbage_collect("config wifi imports")

    files.log_item("Connecting to WiFi")

    #default for manufacturing and shows
    WIFI_SSID="jimmytrainsguest"
    WIFI_PASSWORD=""

    try:
        env = files.read_json_file("/sd/env.json")
        WIFI_SSID = env["WIFI_SSID"]
        WIFI_PASSWORD = env["WIFI_PASSWORD"]
        garbage_collect("wifi env")
        print("Using env ssid and password")
    except:
        print("Using default ssid and password")

    try:
        # connect to your SSID
        wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
        garbage_collect("wifi connect")
        
        # setup mdns server
        mdns_server = mdns.Server(wifi.radio)
        mdns_server.hostname = config["HOST_NAME"]
        mdns_server.advertise_service(service_type="_http", protocol="_tcp", port=80)
        
        # files.log_items MAC address to REPL
        mystring = [hex(i) for i in wifi.radio.mac_address]
        files.log_item("My MAC addr:" + str(mystring))

        ip_address = str(wifi.radio.ipv4_address)

        # files.log_items IP address to REPL
        files.log_item("My IP address is" + ip_address)
        files.log_item("Connected to WiFi")
        
        # set up server
        pool = socketpool.SocketPool(wifi.radio)
        server = Server(pool, "/static", debug=True)
        garbage_collect("wifi server")
        
        ################################################################################
        # Setup routes

        @server.route("/")
        def base(request: HTTPRequest):
            garbage_collect("Home page.")
            return FileResponse(request, "index.html", "/")
        
        @server.route("/mui.min.css")
        def base(request: HTTPRequest):
            return FileResponse(request, "mui.min.css", "/")
        
        @server.route("/mui.min.js")
        def base(request: HTTPRequest):
            return FileResponse(request, "mui.min.js", "/")

        @server.route("/animation", [POST])
        def buttonpress(request: Request):
            global config
            global continuous_run
            raw_text = request.raw_request.decode("utf8")
            if "random" in raw_text: 
                config["option_selected"] = "random"
                start_animation(config["option_selected"])
            elif "thunder_birds_rain" in raw_text: 
                config["option_selected"] = "thunder_birds_rain"
                start_animation("thunder_birds_rain")
            elif "cont_mode_on" in raw_text: 
                continuous_run = True
                play_audio_0("/sd/menu_voice_commands/continuous_mode_activated.wav")
            elif "cont_mode_off" in raw_text: 
                continuous_run = False
                play_audio_0("/sd/menu_voice_commands/continuous_mode_deactivated.wav")
            return Response(request, "Animation " + config["option_selected"] + " started.")
        
        @server.route("/feller", [POST])        
        def buttonpress(request: Request):
            global config
            global feller_movement_type
            raw_text = request.raw_request.decode("utf8")    
            if "feller_rest_pos" in raw_text:
                feller_movement_type = "feller_rest_pos"
                moveFellerToPositionGently(config[feller_movement_type], 0.01)
                return Response(request, "Moved feller to rest position.")
            elif "feller_chop_pos" in raw_text:
                feller_movement_type = "feller_chop_pos"
                moveFellerToPositionGently(config[feller_movement_type], 0.01)
                return Response(request, "Moved feller to chop position.")
            elif "feller_adjust" in raw_text:
                feller_movement_type = "feller_rest_pos"
                moveFellerToPositionGently(config[feller_movement_type],0.01)
                return Response(request, "Redirected to feller-adjust page.")
            elif "feller_home" in raw_text:
                return Response(request, "Redirected to home page.")
            elif "feller_clockwise" in raw_text:
                calibrationLeftButtonPressed(feller_servo, feller_movement_type, 1, feller_min, feller_max)
                return Response(request, "Moved feller clockwise.")
            elif "feller_counter_clockwise" in raw_text:
                calibrationRightButtonPressed(feller_servo, feller_movement_type, 1, feller_min, feller_max)
                return Response(request, "Moved feller counter clockwise.")
            elif "feller_cal_saved" in raw_text:
                write_calibrations_to_config_file()
                pretty_state_machine.go_to_state('base_state')
                return Response(request, "Feller " + feller_movement_type + " cal saved.")
                
        @server.route("/tree", [POST])        
        def buttonpress(request: Request):
            global config
            global tree_movement_type
            raw_text = request.raw_request.decode("utf8")    
            if "tree_up_pos" in raw_text:
                tree_movement_type = "tree_up_pos"
                moveTreeToPositionGently(config[tree_movement_type], 0.01)
                return Response(request, "Moved tree to up position.")
            elif "tree_down_pos" in raw_text:
                tree_movement_type = "tree_down_pos"
                moveTreeToPositionGently(config[tree_movement_type], 0.01)
                return Response(request, "Moved tree to fallen position.")
            elif "tree_adjust" in raw_text:
                tree_movement_type = "tree_up_pos"
                moveTreeToPositionGently(config[tree_movement_type], 0.01)
                return Response(request, "Redirected to tree-adjust page.")
            elif "tree_home" in raw_text:
                return Response(request, "Redirected to home page.")
            elif "tree_up" in raw_text:
                calibrationLeftButtonPressed(tree_servo, tree_movement_type, -1, tree_min, tree_max)
                return Response(request, "Moved tree up.")
            elif "tree_down" in raw_text:
                calibrationRightButtonPressed(tree_servo, tree_movement_type, -1, tree_min, tree_max)
                return Response(request, "Moved tree down.")
            elif "tree_cal_saved" in raw_text:
                write_calibrations_to_config_file()
                pretty_state_machine.go_to_state('base_state')
                return Response(request, "Tree " + tree_movement_type + " cal saved.")
            
        @server.route("/dialog", [POST])
        def buttonpress(request: Request):
            global config
            raw_text = request.raw_request.decode("utf8")
            if "opening_dialog_on" in raw_text: 
                config["opening_dialog"] = True

            elif "opening_dialog_off" in raw_text: 
                config["opening_dialog"] = False

            elif "feller_advice_on" in raw_text: 
                config["feller_advice"] = True
                
            elif "feller_advice_off" in raw_text: 
                config["feller_advice"] = False
                
            files.write_json_file("/sd/config_feller.json",config)
            play_audio_0("/sd/menu_voice_commands/all_changes_complete.wav")

            return Response(request, "Dialog option cal saved.")
        
        @server.route("/utilities", [POST])
        def buttonpress(request: Request):
            global config
            raw_text = request.raw_request.decode("utf8")
            if "speaker_test" in raw_text: 
                play_audio_0("/sd/menu_voice_commands/left_speaker_right_speaker.wav") 
            elif "reset_to_defaults" in raw_text:
                reset_to_defaults()      
                files.write_json_file("/sd/config_feller.json",config)
                play_audio_0("/sd/menu_voice_commands/all_changes_complete.wav")
                pretty_state_machine.go_to_state('base_state')

            return Response(request, "Dialog option cal saved.")

        @server.route("/update-host-name", [POST])
        def buttonpress(request: Request):
            global config
            data_object = request.json()
            config["HOST_NAME"] = data_object["text"]
            
            files.write_json_file("/sd/config_feller.json",config)       
            mdns_server.hostname = config["HOST_NAME"]
            speak_webpage()

            return Response(request, config["HOST_NAME"])
        
        @server.route("/get-host-name", [POST])
        def buttonpress(request: Request):
            return Response(request, config["HOST_NAME"])
           
    except Exception as e:
        serve_webpage = False
        files.log_item(e)

    
garbage_collect("web server")

################################################################################
# Global Methods

def sleepAndUpdateVolume(seconds):
    volume = get_voltage(analog_in, seconds)
    mixer.voice[0].level = volume

################################################################################
# Dialog and sound play methods

def play_audio_0(file_name):
    if mixer.voice[0].playing:
        mixer.voice[0].stop()
        while mixer.voice[0].playing:
            sleepAndUpdateVolume(0.02)
    wave0 = audiocore.WaveFile(open(file_name, "rb"))
    mixer.voice[0].play( wave0, loop=False )
    while mixer.voice[0].playing:
        shortCircuitDialog()

def stop_audio_0():
    mixer.voice[0].stop()
    while mixer.voice[0].playing:
        pass

def shortCircuitDialog():
    sleepAndUpdateVolume(0.02)
    left_switch.update()
    if left_switch.fell:
        mixer.voice[0].stop()
        
def speak_this_string(str_to_speak, addLocal):
    for character in str_to_speak:
        if character == "-":
            character = "dash"
        if character == ".":
            character = "dot"
        play_audio_0("/sd/menu_voice_commands/" + character + ".wav")
    if addLocal:
        play_audio_0("/sd/menu_voice_commands/dot.wav")
        play_audio_0("/sd/menu_voice_commands/local.wav")
        
def start_animation(file_name):
    animate_lightning.animation(sleepAndUpdateVolume, audiocore, mixer, ledStrip, left_switch, right_switch, file_name, num_pixels)
    
################################################################################
# State Machine

class StateMachine(object):

    def __init__(self):
        self.state = None
        self.states = {}
        self.paused_state = None

    def add_state(self, state):
        self.states[state.name] = state

    def go_to_state(self, state_name):
        if self.state:
            self.state.exit(self)
        self.state = self.states[state_name]
        self.state.enter(self)

    def update(self):
        if self.state:
            self.state.update(self)

    # When pausing, don't exit the state
    def pause(self):
        self.state = self.states['paused']
        self.state.enter(self)

    # When resuming, don't re-enter the state
    def resume_state(self, state_name):
        if self.state:
            self.state.exit(self)
        self.state = self.states[state_name]

    def reset(self):
        """As indicated, reset"""
        self.firework_color = random_color()
        self.burst_count = 0
        self.shower_count = 0
        self.firework_step_time = time.monotonic() + 0.05

################################################################################
# States

# Abstract parent state class.
class State(object):

    def __init__(self):
        pass

    @property
    def name(self):
        return ''

    def enter(self, machine):
        pass

    def exit(self, machine):
        pass

    def update(self, machine):
        if left_switch.fell:
            machine.paused_state = machine.state.name
            machine.pause()
            return False
        return True

class BaseState(State):

    def __init__(self):      
        pass

    @property
    def name(self):
        return 'base_state'

    def enter(self, machine):
        play_audio_0("/sd/menu_voice_commands/animations_are_now_active.wav")
        files.log_item("Entered base state")
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        left_switch.update()
        right_switch.update()
        if left_switch.fell:
            start_animation(config["option_selected"])
        if right_switch.fell:
            print('Just pressed option mode')
            machine.go_to_state('program')

class ProgramState(State):

    def __init__(self):
        self.optionIndex = 0
        self.currentOption = 0

    @property
    def name(self):
        return 'program'

    def enter(self, machine):
        print('Select a program option')
        if mixer.voice[0].playing:
            mixer.voice[0].stop()
            while mixer.voice[0].playing:
                pass
        else:
            play_audio_0("/sd/menu_voice_commands/option_mode_entered_left_right.wav")
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        left_switch.update()
        right_switch.update()
        if left_switch.fell:
            if mixer.voice[0].playing:
                mixer.voice[0].stop()
                while mixer.voice[0].playing:
                    pass
            else:
                wave0 = audiocore.WaveFile(open("/sd/lightning_options_voice_commands/option_" + sound_options[self.optionIndex] + ".wav" , "rb"))
                mixer.voice[0].play( wave0, loop=False )
                self.currentOption = self.optionIndex
                self.optionIndex +=1
                if self.optionIndex > len(sound_options)-1:
                    self.optionIndex = 0
                while mixer.voice[0].playing:
                    pass
        if right_switch.fell:
            if mixer.voice[0].playing:
                mixer.voice[0].stop()
                while mixer.voice[0].playing:
                    pass
            else:
                config["option_selected"] = sound_options[self.currentOption]
                files.write_json_file("/sd/config_lightning.json",config)
                wave0 = audiocore.WaveFile(open("/sd/menu_voice_commands/option_selected.wav", "rb"))
                mixer.voice[0].play( wave0, loop=False )
                while mixer.voice[0].playing:
                    pass
            machine.go_to_state('base_state')

# StateTemplate copy and add functionality
class StateTemplate(State):

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'example'

    def enter(self, machine):
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        State.update(self, machine)

###############################################################################
# Create the state machine

pretty_state_machine = StateMachine()
pretty_state_machine.add_state(BaseState())
pretty_state_machine.add_state(ProgramState())
        
audio_enable.value = True

def speak_webpage():
    play_audio_0("/sd/menu_voice_commands/animator_available_on_network.wav")
    play_audio_0("/sd/menu_voice_commands/to_access_type.wav")
    if config["HOST_NAME"]== "animator-lightning-old":
        play_audio_0("/sd/menu_voice_commands/animator_lightning_local.wav")
    else:
        speak_this_string(config["HOST_NAME"], True)
    play_audio_0("/sd/menu_voice_commands/in_your_browser.wav")    

if (serve_webpage):
    files.log_item("starting server...")
    try:
        server.start(str(wifi.radio.ipv4_address))
        files.log_item("Listening on http://%s:80" % wifi.radio.ipv4_address)
        speak_webpage()
    except OSError:
        time.sleep(5)
        files.log_item("restarting...")
        reset_pico()

ledStrip.fill((255, 0, 0))
#ledStrip.show()
sleepAndUpdateVolume(1)
ledStrip.fill((0, 255, 0))
#ledStrip.show()
sleepAndUpdateVolume(1)
ledStrip.fill((0, 0, 255))
#ledStrip.show()
sleepAndUpdateVolume(1)
ledStrip.fill((255, 255, 255))
ledStrip.show()

pretty_state_machine.go_to_state('base_state')   
files.log_item("animator has started...")
garbage_collect("animations started.")

while True:
    pretty_state_machine.update()
    sleepAndUpdateVolume(.02)
    if (serve_webpage):
        try:
            server.poll()
        except Exception as e:
            files.log_item(e)
            continue
