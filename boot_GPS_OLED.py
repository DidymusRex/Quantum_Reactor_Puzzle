from adafruitGFX import GFX
from machine import disable_irq, enable_irq, I2C, Pin, reset, Timer, UART
from math import atan2, degrees, ceil, cos, floor, pi, radians, sin, sqrt
from micropyGPS import MicropyGPS

import ssd1306
import sys
import time

"""
Set up OLED on I2C
  use default address 0x3C
  I2C 0 is scl 18 and sda 19
"""
i2c = I2C(0)
display = ssd1306.SSD1306_I2C(128, 64, i2c)
gfx = GFX(128, 64, display.pixel, display.hline, display.vline)

display.fill(1)
display.show()

"""
Set up the GPS receiver on UART 1
  set up the gps parser
"""
uart = UART(1,
            rx=21,
            tx=22,
            baudrate=9600,
            bits=8,
            parity=None,
            stop=1,
            timeout=5000,
            rxbuf=1024)

gps_message = ""
gps = MicropyGPS()


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
    # global knob_dir

    display.fill(0)

    # # Line 1 BLE info
    # display.text("BLE", 0, 0, 1)
    # display.text(ble.scan_indicator[ble.scan_count%4], 64, 0)
    # display.text(str(ble.scan_count), 80, 0)
    
    # if ble.connect_status == True:
    #     display.fill_rect(32, 1, 6, 6, 1)
    # else:
    #     display.rect(32, 1, 6, 6, 1)

    # if ble.scanning == True:
    #     display.fill_rect(48, 1, 6, 6, 1)
    # else:
    #     display.rect(48, 1, 6, 6, 1)

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

"""
Water Tower location data
"""
tgtLat=42.04214844650904
tgtLon=-86.43326731606975

while True:
    update_oled("main")
    time.sleep(10)
