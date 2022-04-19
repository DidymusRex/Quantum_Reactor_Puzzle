"""
boot_quadcorder.py
Save to device as boot.by
"""

"""
import needed modules
"""
from adafruitGFX import GFX
from basic_ble import *
from KeyPad import KeyPad
from machine import disable_irq, enable_irq, I2C, Pin, reset, Timer, UART
from math import atan2, degrees, ceil, cos, floor, pi, radians, sin, sqrt
from micropyGPS import MicropyGPS
from rotary_irq_esp import RotaryIRQ
import ssd1306
import sys
import time
import ubluetooth

# Device Pin numbers
OLED_SCL=18
OLED_SDA=19
KNOB_BTN=5
KNOB_CLK=17
KNOB_DAT=16
UART_RX=21
UART_TX=22
KP_R1=13
KP_R2=12
KP_R3=14
KP_R4=27
KP_C1=26
KP_C2=25
KP_C3=33
KP_C4=32

# GPS Targets
targets = {"0000#CCCC": (42.040545, -86.435835), # Home
           "A08D#6CDD": (42.039323, -86.435976), # Substation
           "CB69#A409": (42.044174, -86.446875), # EP Clark Elementary
           "D694#734A": (42.048659, -86.473342), # Upton Middle School
           "B2A5#55BD": (42.013209, -86.492442), # Lakeshore High School
           "60C3#6748": (42.094203, -86.391581), # Lake Michigan College
           "5DC3#154D": (42.015690, -86.504157)  # Lincoln Twp Library
}
beacon_key = b'67D7A2D5'

"""
Set up OLED on I2C
  uses default address 0x3C
  I2C 0 uses scl 18 and sda 19 by default
"""
i2c = I2C(0) 
display = ssd1306.SSD1306_I2C(128, 64, i2c)
gfx = GFX(128, 64, display.pixel, display.hline, display.vline)

display.fill(1)
display.show()

"""
Set up rotary encoder
  encoder button on pin 5
  set up listener on encoder button
"""
knob_btn = Pin(KNOB_BTN, Pin.IN, Pin.PULL_UP)
knob_btn_pushed = False
knob_prev = 0
knob_val = 0
knob_dir = "."
knob_change = False

def knob_btn_isr(pin):
    """
    ISR flags a button push
    """
    global knob_btn_pushed
    knob_btn_pushed = True

"""
  attach ISR. Push only, not release
"""
knob_btn.irq(trigger=Pin.IRQ_FALLING, handler=knob_btn_isr)

def knob_listener():
    """
    Sets direction indicator and flags a change in value
      scheduled by knob.process_rotary_pins
    """
    global knob_prev, knob_val, knob_dir, knob_change
    
    knob_val = knob.value()
    knob_dir = "."     # Static, default
    
    if knob_val > knob_prev:
        knob_dir = "+" # CW

    if knob_val < knob_prev:
        knob_dir = "-" # CCW

    knob_prev = knob_val
    knob_change = True

"""
define the knob
  pull_up=True required when no external pullup in circuit
  add a listener function to capture knob change and direction
"""
knob = RotaryIRQ(pin_num_clk=KNOB_CLK,
                 pin_num_dt=KNOB_DAT,
                 min_val=0,
                 max_val=10,
                 reverse=False,
                 range_mode=RotaryIRQ.RANGE_BOUNDED,
                 pull_up=True,
                 half_step=False)

knob.add_listener(knob_listener)

"""
Set up the GPS receiver on UART 1
  set up the gps parser
"""
uart = UART(1,
            rx=UART_RX,
            tx=UART_TX,
            baudrate=9600,
            bits=8,
            parity=None,
            stop=1,
            timeout=5000,
            rxbuf=1024)

gps_message = ""
gps = MicropyGPS()

"""
Set up the keypad
"""
kp = KeyPad(KP_R1, KP_R2, KP_R3, KP_R4, 
            KP_C1, KP_C2, KP_C3, KP_C4, 
            timer_period=50)

"""
Set up a bluetooth object and UUIDs for Nordic UART service
"""
ble = BLE("QuadCorder1")

SVC_UUID = ubluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
TX_UUID  = ubluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
RX_UUID  = ubluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')

"""
set up a timer for oled refresh, period is in ms
    Timer(0) used by basic_ble.py
"""
oled_timer_triggered = False

def oled_timer_isr(t):
    global oled_timer_triggered
    oled_timer_triggered = True
    
oled_timer = Timer(1)

oled_timer.init(period = 5000,
                mode=Timer.PERIODIC,
                callback=oled_timer_isr)

def debounce_pin(pin):
    """
    The pin ISR flagged a change. Turn off interrupt for 50ms
    to debounce the button
    """
    pin.irq(handler=None)
    time.sleep_ms(50)
    pin.irq(trigger=Pin.IRQ_FALLING, handler=knob_btn_isr)

def update_gps_info():
    """
    Query gps module for data and pass it to the gps parser
      read from the serial port
      convert int to char and feed to parser one char at a time
      retval is True when a message is read from uart, False if not
    """
    global gps_message
    retval = False

    buf = uart.readline()
    if buf is None:
        gps_message = "empty"
        
    else:
        for char in buf:
            gps.update(chr(char))
            gps_message += chr(char)
            
        retval = True

    return retval

def calc_distance(lat1, lon1, lat2, lon2):
    if lat1 == 0 or lon1 == 0 or lat2 == 0 or lon2 == 0:
        return -1

    #radius of Earth in metres
    R = 6371000

    #convert lat/lon to radians
    lat1r = radians(lat1)
    lat2r = radians(lat2)
    deltaLat = radians(lat2-lat1)
    deltaLon = radians(lon2-lon1)

    #haversine formula
    a = (sin(deltaLat/2) * sin(deltaLat/2)) + (cos(lat1r) * cos(lat2r) * (sin(deltaLon/2) * sin(deltaLon/2)))
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def calc_bearing(lat1, lon1, lat2, lon2):
    if lat1 == 0 or lon1 == 0 or lat2 == 0 or lon2 == 0:
        return -1

    #convert lat/lon to radians
    lat1r = radians(lat1)
    lat2r = radians(lat2)
    deltaLat = radians(lat2-lat1)
    deltaLon = radians(lon2-lon1)

    a = cos(lat2r) * sin(deltaLon)
    b = cos(lat1r) * sin(lat2r) - sin(lat1r) * cos(lat2r) * cos(deltaLon)
    return (degrees(atan2(a,b)) + 360) % 360

def display_bearing(cx, cy, radius, angleR):
    global gfx

    display.text('N', cx-4, 0, 1)
    gfx.circle(cx, cy, radius, 1)
    
    if angleR < 0:
        display.text("No", cx-8, cy-8)
        display.text("GPS", cx-12, cy+8)
    else:
        #move from x to y axis
        angleR = angleR - radians(90)
        rx = cx - ceil(radius * cos(angleR))
        ry = cy - ceil(radius * sin(angleR))

        display.line(cx, cy, rx, ry, 1)

    display.show()

def update_oled(s):
    """
    Get new data from GPS module and format it on the oled display
    """
    global tgt_found, tgt_code, tgt_lat, tgt_lon

    display.fill(0)

    if tgt_found:
        display.text("*BLINKING*", 0, 0, 1)
    else:
        if ble.scanning == True:
            display.text("Scan for", 0, 0, 1)
        else:
            display.text("Scan OFF", 0, 0, 1)

    gps.coord_format = "dd"
    if update_gps_info():
        gps.coord_format = "dd"
        my_lat=gps.latitude[0]
        if gps.latitude[1] == "S":
            my_lat = my_lat * -1
        my_lon=gps.longitude[0]
        if gps.longitude[1] == "W":
            my_lon = my_lon * -1

    if tgt_code > "":
        display.text(tgt_code, 0, 10, 1)

        display.text("^" + str(tgt_lat), 0, 20)
        display.text(">" + str(tgt_lon), 0, 30)
    else:
        display.text("   No", 0, 10, 1)
        display.text(" Target", 0, 20)
        display.text("Selected", 0, 30)

    b = calc_bearing(my_lat, my_lon, tgt_lat, tgt_lon)
    display_bearing(106, 30, 20, b)
    
    d = calc_distance(my_lat, my_lon, tgt_lat, tgt_lon)
    display.text("dist (km)", 0, 40, 1)
    if d>0:
        display.text(str(d/1000), 0, 50, 1)
    else:
        display.text("--.----", 0, 50, 1)
    
    display.show()

def qc_menu(menu_items):
    global knob_dir, knob_change, knob_btn_pushed

    curr_item = 0
    prev_item = 1
    display.fill(0)
    display.show()

    while True:
        if knob_btn_pushed:
            knob_btn_pushed = False
            break

        if knob_change:
            knob_change = False
            if knob_dir == "+":
                curr_item = curr_item + 1
                if curr_item > len(menu_items):
                    curr_item = len(menu_items)
            else:
                curr_item = curr_item - 1
                if curr_item < 0:
                    curr_item = 0

        if curr_item != prev_item:
            prev_item = curr_item
            display.fill(0)

            for menu_item in menu_items:
                i = menu_items.index(menu_item)
                if i == curr_item:
                    gfx.fill_rect(0, curr_item*10, 128, 10, 1)
                    display.text(menu_item, 0, i*10, 0)
                else:
                    display.text(menu_item, 0, i*10, 1)

            display.show()
                
    return(curr_item)

def qc_enter_code():
    global knob_change, knob_dir, knob_btn_pushed
    c=0
    t=""
    
    display.fill(0)
    display.text("Enter Code:", 0, 0, 1)
    gfx.fill_rect(len(t)*8, 20, 8, 8, 1)
    display.show()
    
    while True:
        if knob_btn_pushed:
            debounce_pin(knob_btn)
            knob_btn_pushed = False
            break

        if kp.get_btn() >= 0:
            c=c+1
            t=t+kp.btn_chr
            gfx.fill_rect(0, 20, 128, 10, 0)
            display.text(t, 0, 20, 1)
            gfx.fill_rect(c*8, 20, 8, 8, 1)
            display.show()
            
        if c>8:
            break

    return(t)

#-------------------------------------------------------------------------------
display.fill(0)
display.text("Quadcorder v1.00",0 ,0, 1)
display.text("  press knob to ", 0, 20, 1)
display.text("   initialize   ", 0, 30, 1)
display.show()

while True:
    if knob_btn_pushed:
        debounce_pin(knob_btn)
        knob_btn_pushed = False
        break

tgt_found=False
tgt_code=""
tgt_lat=0
tgt_lon=0

while True:
    """
    button interrupt was triggered.
      debounce, reset, and then do whatever
    """
    if knob_btn_pushed:
        debounce_pin(knob_btn)
        knob_btn_pushed = False

        """ do whatever """
        tgt_code = qc_enter_code()

        if tgt_code in targets.keys():
            tgt_lat = targets[tgt_code][0]
            tgt_lon = targets[tgt_code][1]
            tgt_found = False
            ble.scan()
            update_oled("button")
        else:
            tgt_lat = 0
            tgt_lon = 0
            display.fill(0)
            display.text("Invalid Code", 5*4, 20, 1)
            display.text(tgt_code, int(16-(len(tgt_code))/2)*4, 30, 1)
            display.show()
            tgt_found = False
            ble.stop_scan()
            tgt_code=""

            while True:
                if knob_btn_pushed:
                    debounce_pin(knob_btn)
                    knob_btn_pushed = False
                    break

    """
    timer interrupt was triggered
      reset, then do whatever
    """
    if oled_timer_triggered:
        oled_timer_triggered = False
        """ do whatever """
        update_oled("timer")

    """
    knob listener was triggered
      reset, then do whatever
    """
    if knob_change:
        knob_change = False
        """ do whatever """
        update_oled("knob")

    """
    process BLE events
    """
    if ble.event_flag:
        ble.event_flag = False
        print('Event: ' + str(ble.event_type[ble.event_id]))

        if ble.event_id == ble.IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = ble.scan_result
            ble.scan_count += 1

            """
            advertising data contains the name of the device
            """
            if beacon_key in adv_data:
                print('found a beacon, connecting')
                print(adv_data)
                tgt_found = True
                ble.connect(addr_type, addr)

        if ble.event_id == ble.IRQ_SCAN_DONE:
            ble.scanning = False
            print('scan complete.')

        if ble.event_id == ble.IRQ_PERIPHERAL_CONNECT:
            # connected. get handle for uart service
            # searching for a specific service
            ble.discover_service(ble.conn_info['conn_handle'], SVC_UUID)
            
        if ble.event_id == ble.IRQ_GATTC_SERVICE_DONE:
            # searching for a RX characteristic of uart service
            print('Begin disc char')
            ble.discover_characteristic(ble.conn_info['conn_handle'], RX_UUID)
            print('End desc char')
                
        if ble.event_id == ble.IRQ_GATTC_CHARACTERISTIC_DONE:
            # write the trigger string to the RX characteristic of the uart service
            print('begin write')
            ble.write(ble.conn_info['char_conn_handle'],
                      ble.conn_info['char_value_handle'],
                      bytearray('find me'))
            print('end write')
            # pause and disconnect
            sleep_ms(250)
            ble.disconnect(ble.conn_info['conn_handle'])

        if ble.event_id == ble.IRQ_PERIPHERAL_DISCONNECT:
            ble.disconnected()

    time.sleep_ms(10)
