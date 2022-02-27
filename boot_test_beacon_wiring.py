#
# Test ble beacon wiring
#
from machine import Pin, PWM, reset, Timer

led=Pin(2,Pin.OUT)
flasher=Pin(13,Pin.OUT)

def reboot():
    reset()

timerF=Timer(1)

timerF.init(period=200, mode=Timer.PERIODIC, callback=lambda t: flasher(not flasher.value()))

