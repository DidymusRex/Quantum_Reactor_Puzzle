"""
boot_quadcorder.py
Save to device as boot.by
"""

"""
import needed modules
"""
from adafruitGFX import GFX
from basic_ble import *
from machine import disable_irq, enable_irq, I2C, Pin, reset, Timer, UART
from math import atan2, degrees, ceil, cos, floor, pi, radians, sin, sqrt
from micropyGPS import MicropyGPS
from rotary_irq_esp import RotaryIRQ
import ssd1306
import sys
import time
import ubluetooth

"""
simple function to reboot in REPL
"""
def reboot():
    reset()
    
"""
Set up OLED on I2C
  use default address 0x3C
  I2C 0 is scl 18 and sda 19
"""
i2c = i2c = I2C(0) 
display = ssd1306.SSD1306_I2C(128, 64, i2c)
gfx = GFX(128, 64, display.pixel, display.hline, display.vline)

display.fill(1)
display.show()

"""
Set up rotary encoder
  encoder button on pin 25
  set up listener on encoder button
"""
knob_btn = Pin(25, Pin.IN, Pin.PULL_UP)
knob_btn_pushed = False
knob_prev = 0
knob_val = 0
knob_dir = "."
knob_change = False

def knob_btn_isr(pin):
    """
    button push ISR flags a button push
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
knob = RotaryIRQ(pin_num_clk=27,
                 pin_num_dt=26,
                 min_val=0,
                 max_val=100,
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
            rx=35,
            tx=32,
            baudrate=9600,
            bits=8,
            parity=None,
            stop=1,
            timeout=5000,
            rxbuf=1024)

gps_message = ""
gps = MicropyGPS()

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
    #radius of Earth in metres
    R = 6371000

    #convert lat/lon to radians
    lat1r = radians(lat1)
    lat2r = radians(lat2)
    deltaLat = radians(lat2-lat1)
    deltaLon = radians(lon2-lon1)

    #haversine formula
    a = sin(deltaLat/2) * sin(deltaLat/2) + cos(lat1r) * cos(lat2r) * sin(deltaLon/2) * sin(deltaLon/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def calc_bearing(lat1, lon1, lat2, lon2):
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
    display.fill(0)

    display.text('N', cx-4, 0, 1)
    l = len(str(degrees(angleR)))*4
    display.text(str(degrees(angleR)), cx - l, 50, 1)

    #move from x to y axis
    angleR = angleR - radians(90)
    rx = cx + ceil(radius * cos(angleR))
    ry = cy + ceil(radius * sin(angleR))

    gfx.circle(cx, cy, radius, 1)
    display.line(cx, cy, rx, ry, 1)
    display.show()

def update_oled(s):
    """
    Get new data from GPS module and format it on the oled display
    """
    global knob_dir

    display.fill(0)

    # Line 1 BLE info
    display.text("BLE", 0, 0, 1)
    display.text(ble.scan_indicator[ble.scan_count%4], 64, 0)
    display.text(str(ble.scan_count), 80, 0)
    
    if ble.connect_status == True:
        display.fill_rect(32, 1, 6, 6, 1)
    else:
        display.rect(32, 1, 6, 6, 1)

    if ble.scanning == True:
        display.fill_rect(48, 1, 6, 6, 1)
    else:
        display.rect(48, 1, 6, 6, 1)

    # Lines 2-4 GPS info
    if update_gps_info():
        display.text("Lat ", 0, 10)
        display.text(str(gps.latitude[2]), 32, 10)
        display.text(str(gps.latitude[0]), 48, 10)
        display.text(str(gps.latitude[1]), 72, 10)
        
        display.text("Lon ", 0, 20)
        display.text(str(gps.longitude[2]), 32, 20)
        display.text(str(gps.longitude[0]), 48, 20)
        display.text(str(gps.longitude[1]), 72, 20)

        display.text("Sat " + str(gps.satellites_in_use), 0, 30)
    else:
        display.text("Lat ---", 0, 10)
        display.text("Lon ---", 0, 20)
        display.text("Sat ---", 0, 30)


    # Line 5 update event
    display.text(s, 0, 50)
    display.show()

"""
main loop
"""
update_oled("main")

while True:
    """
    button interrupt was triggered.
      debounce, reset, and then do whatever
    """
    if knob_btn_pushed:
        debounce_pin(knob_btn)
        knob_btn_pushed = False

        """ do whatever """
        if ble.scanning:
            ble.stop_scan()
        else:
            ble.scan()

        update_oled("button")

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
            update_oled('scan')

            """
            advertising data contains the name of the device
            """
            if b'key_can' in adv_data:
                print('found a key can, connecting')
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
