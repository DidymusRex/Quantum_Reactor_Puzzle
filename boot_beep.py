from machine import Pin, PWM, reset, Timer
from time import sleep_ms

# set command and state
beep = False
beeping = False
silence = False
btn_push = False

# simple function to reboot device in REPL
def reboot():
    reset()
    
# The pin ISR flagged a change. Turn off interrupt for 50ms to debounce the button
def debounce_pin(pin):
    pin.irq(handler=None)
    sleep_ms(50)
    pin.irq(trigger=Pin.IRQ_FALLING, handler=btn_isr)

# ISR for boot pin - stop beep
def btn_isr(p):
    global btn_push
    btn_push = True

# ISR for timer - alternate beep state
def timer_isr(t):
    global beep
    beep = not beep

# set up boot pin with isr
btn = Pin(0, Pin.IN, Pin.PULL_UP)
btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_isr)

# beep freq every 500ms
timerBeep=Timer(1)
timerBeep.init(period=500, mode=Timer.PERIODIC, callback= timer_isr)

# create beeper
beeper=PWM(Pin(14, Pin.OUT), freq=880, duty=512)

# main loop
while True :
    if btn_push:
        debounce_pin(btn)
        btn_push = False
        silence = not silence

    if silence:
        beep = False

    if beep:
        if beeping:
            pass
        else:
            beeper.init()
            beeping = True
    else:
        if beeping:
            beeper.deinit()
            beeping = False

