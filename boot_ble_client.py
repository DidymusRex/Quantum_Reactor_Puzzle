"""
Bluetooth client Test
save as boot.py on client device
"""
from basic_ble import *
from machine import I2C, Pin, reset, Timer
import ssd1306
from time import sleep_ms

# simple function to reboot device in REPL
def reboot():
    reset()

"""
Set up OLED on I2C
  use default address 0x3C
  I2C 0 is scl 18 and sda 19
"""
i2c = I2C(0) 
display = ssd1306.SSD1306_I2C(128, 64, i2c)

display.fill(0)
display.text("Boot",0,0)
display.show()

"""
Set up rotary encoder button on pin 25
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

"""
Set up a bluetooth object and UUIDs for Nordic UART service
"""
ble = BLE("QuadCorder1")

SVC_UUID = ubluetooth.UUID('6E400001-B5A3-F393-E0A9-E50E24DCCA9E')
TX_UUID  = ubluetooth.UUID('6E400003-B5A3-F393-E0A9-E50E24DCCA9E')
RX_UUID  = ubluetooth.UUID('6E400002-B5A3-F393-E0A9-E50E24DCCA9E')

"""
set up a timer for oled refresh, period is in ms
"""
oled_timer_triggered = False

def oled_timer_isr(t):
    global oled_timer_triggered
    oled_timer_triggered = True

oled_timer = Timer(0)

oled_timer.init(period = 60000,
                mode=Timer.PERIODIC,
                callback=oled_timer_isr)

def debounce_pin(pin):
    """
    The pin ISR flagged a change. Turn off interrupts for 50ms
    to debounce the button
    """
    pin.irq(handler=None)
    sleep_ms(50)
    pin.irq(trigger=Pin.IRQ_FALLING, handler=knob_btn_isr)

def update_oled(s):
    """
    Get new data and format it on the oled display
    """
    display.fill(0)
    if ble.scanning:
        display.text('scanning', 0, 0)
    else:
        display.text('scan idle', 0, 0)

    if ble.connect_status:
        display.text('connected', 0, 10)
    else:
        display.text('disconnected', 0, 10)
        
    display.text('role ' + ble.ble_role, 0, 20)
    display.text('name ' + ble.name, 0, 30)
    display.text(s, 0, 50)
    
    display.show()

print('ready.')

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
    monitor ble events
    """
    if ble.event_flag:
        ble.event_flag = False
        print('Event: ' + str(ble.event_type[ble.event_id]))

        if ble.event_id == ble.IRQ_SCAN_RESULT:
            """
            scan result:
            addr       b'$o(\xc0\xf6\xe2'
            adv data   b'\x02\x01\x02\x0c\tkey_can_one'
            """
            addr_type, addr, adv_type, rssi, adv_data = ble.scan_result
            
            if b'key_can' in adv_data:
                print('found a key_can, connecting')
                ble.connect(addr_type, addr)
                sleep_ms(250)
                ble.stop_scan()

        if ble.event_id == ble.IRQ_SCAN_DONE:
            ble.scanning = False
            print('scan complete.')

        if ble.event_id == ble.IRQ_PERIPHERAL_CONNECT:
            # connected. get services, get characteristics, get descriptors, write to something
            ble.stop_scan()
            sleep_ms(250)
            # searching for a specific service
            ble.discover_service(ble.conn_info['conn_handle'], SVC_UUID)
            
        if ble.event_id == ble.IRQ_GATTC_SERVICE_DONE:
            # searching for a specific characteristic
            ble.discover_characteristic(ble.conn_info['conn_handle'], RX_UUID)

        if ble.event_id == ble.IRQ_GATTC_CHARACTERISTIC_RESULT:
            pass
                
        if ble.event_id == ble.IRQ_GATTC_CHARACTERISTIC_DONE:
            # could also be in IRQ_GATTC_CHARACTERISTIC_RESULT but this makes more sense
            ble.write(ble.conn_info['char_conn_handle'],
                      ble.conn_info['char_value_handle'],
                      bytearray('find me'))

            # pause and disconnect
            sleep_ms(250)
            ble.disconnect(ble.conn_info['conn_handle'])

        if ble.event_id == ble.IRQ_GATTC_DESCRIPTOR_DONE:
            pass

        if ble.event_id == ble.IRQ_PERIPHERAL_DISCONNECT:
            ble.disconnected()

    sleep_ms(100)
