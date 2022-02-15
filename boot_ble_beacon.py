"""
Bluetooth beacon
save as boot.py on beacon device
"""
from basic_ble import *
from machine import Pin, PWM, reset, Timer
from time import sleep_ms

# simple function to reboot device in REPL
def reboot():
    reset()

# set up BLE object
ble = BLE('key_can_one')

# set up leds
led=Pin(2,Pin.OUT)
flasher=Pin(13,Pin.OUT)

# set up boot pin
btn=Pin(0,Pin.IN)

# ISR for boot pin
def btn_isr(pin):
    if flashing:
        timerF.deinit()
        timerX.deinit()
        flasher(0)

# attache ISR to boot pin
btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_isr)

# initialize flashing state
flashing=False

# Timer(0) used by basic_ble.py
timerF=Timer(1)
timerX=Timer(2)

# timerX callback
def stop_flashing(t):
    print('stop flashing')
    flashing=False
    timerF.deinit()
    flasher(0)
    ble.send('not lit')
    
print('ready.')
flasher(1)
sleep_ms(500)
flasher(0)

# begin main loop
while True:
    # monitor events
    if ble.event_flag:
        ble.event_flag = False
        print('Event ID....' + str(ble.event_id))

    # look for message from client
    if ble.event_msg == 'find me':
        flashing=True
        ble.event_msg = 'bar'
        print('begin flashing')
        # flash the beacon
        timerF.init(period=200, mode=Timer.PERIODIC, callback=lambda t: flasher(not flasher.value()))
        # for 5 minutes: 300000. 5000 (5 sec. for testing)
        timerX.init(period=5000, mode=Timer.ONE_SHOT, callback=stop_flashing)
        ble.send('lit up!')
        
    elif ble.event_msg == 'foo':
        print('init event message')
        ble.event_msg = 'bar'
        
    elif ble.event_msg == 'bar':
        pass

    else:
        print('invalid message ' + ble.event_msg)
        ble.event_msg = 'bar'
        ble.send('try again, hombre')

    sleep_ms(100)
