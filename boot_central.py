# boot_central.py
from basic_ble import *
from dfplayermini import Player
from machine import Pin, reset, SoftI2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
import time
import ubluetooth

beacon_key = "67D7A2D5"
beacons_found = {#"0000#CCCC": False, # Home
                 "A08D#6CDD": False, # Substation
                 "CB69#A409": False, # EP Clark Elementary
                 "D694#734A": False, # Upton Middle School
                 "B2A5#55BD": False, # Lakeshore High School
                 "60C3#6748": False, # Lake Michigan College
                 "5DC3#154D": False  # Lincoln Twp Library
}
beacon_list=list()
for id in beacons_found.keys():
    beacon_list.append(id)

"""
Setup i2C bus
"""
sclPin=Pin(23)
sdaPin=Pin(22)
I2C_NANO = 0x07
I2C_ADDR = 0x27
i2c = SoftI2C(sclPin, sdaPin, freq=10000)

"""
Setup lcd
"""
totalRows = 2
totalColumns = 16
lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)
lcd.backlight_off()

"""
Setup DFPlayer
"""
music = Player(pin_TX=17, pin_RX=16)

"""
Set up a bluetooth object and UUIDs for Nordic UART service
"""
ble = BLE("CentralComputer")

SVC_UUID = ubluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
TX_UUID  = ubluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
RX_UUID  = ubluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')

"""
Setup lighted button
"""
btnPin = Pin(18, Pin.IN, Pin.PULL_UP)
btnLed = Pin(19, Pin.OUT, Pin.PULL_DOWN)

"""
Ensure we start with btn in off position
"""
if btnPin.value():
    btnLed.off()
else:
    lcd.backlight_on()
    lcd.putstr("err: pwr btn")
    while not btnPin.value():
        pass
    lcd.clear()
    lcd.backlight_off()
    btnLed.off()
    
# ISR for btnPin pin. Toggle btnLed and lcd backlight
def btn_isr(pin):
    btnLed.value(not btnLed.value())
    if lcd.backlight:
        lcd.backlight_off()
    else:
        lcd.backlight_on()

# attach ISR to boot pin
btnPin.irq(trigger=Pin.IRQ_RISING|Pin.IRQ_FALLING, handler=btn_isr)

def lcd_print(msg, clr=False, row=0, col=0):
    if(clr):
        lcd.clear()
    
    lcd.move_to(col, row)
    lcd.putstr(msg)

def request_light_effect(e, m):
    i2c.writeto(I2C_NANO, (e+m).encode('utf-8')) 
    
def boot_msg():
    request_light_effect("3", "0")
    lcd_print("boot", True, 0, 6)
    time.sleep(2)

    lcd.clear()
    for i in range(totalColumns):
        lcd_print("o", False, 0, i)
        time.sleep(.1)

"""
main
"""
lcd.clear()

# wait for power button press
while btnPin.value():
    pass
lcd.backlight_on()

boot_msg()
cfm=True
cft=time.time()
beacon_count=0
beacon_display=0
last_bc=0
light_effect_requested=False

ble.scan()
while True:
    if not beacons_found["A08D#6CDD"]:
        if (time.time() - cft) > 3:
            cft=time.time()
            if cfm:
                lcd_print("CORE FAULT", True, 0, 3)
                lcd_print("FREQUENCY NEEDED", False, 1, 0)
            else:
                lcd_print("LOCATE MODULE", True, 0, 2)
                lcd_print("A08D#6CDD", False, 1, 4)
            cfm = not cfm
    else:
        if (time.time() - cft) > 3:
            cft=time.time()
            beacon_display = beacon_display+1
            if beacon_display > len(beacon_list)-2:
                beacon_display = 0
            lcd_print(beacon_list[beacon_display] + " " + ("+" if beacons_found[beacon_list[beacon_display]] else "-"), True, 0, 3)
            lcd_print(beacon_list[beacon_display+1] + " " + ("+" if beacons_found[beacon_list[beacon_display+1]] else "-"), False, 1, 3)
            
        beacon_count = 0
        for id in beacons_found.keys():
            if beacons_found[id]:
                beacon_count = beacon_count + 1
        if beacon_count != last_bc:
            last_bc=beacon_count
            request_light_effect("5", str(beacon_count))
        if beacon_count >= len(beacon_list):
            break

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
                print('I see a beacon')
                print(adv_data)
                
                for id in beacons_found.keys():
                    if id in adv_data:
                        print("saw " + id)
                        if not beacons_found[id]:
                            lcd_print("NEW FREQUENCY!", True, 0, 0)
                            lcd_print(id, False, 1, 0)
                            time.sleep(3)
                            beacons_found[id]=True

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

# Grand finale!
request_light_effect("2", "0")
lcd_print("REACTOR CORE", True, 0, 2)
lcd_print("ONLINE!", False, 1, 5)
request_light_effect("4", "0")
