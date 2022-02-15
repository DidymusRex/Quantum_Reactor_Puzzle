"""
Rotary Encoder Test
save as boot.py on client device
"""
from machine import disable_irq, enable_irq, I2C, Pin, Timer
import rotary
from rotary_irq_esp import RotaryIRQ
import ssd1306
import sys
import time

"""
Set up OLED on I2C
use default address 0x3C
I2C 0 is scl 18 and sda 19
"""
i2c = i2c = I2C(0) 
display = ssd1306.SSD1306_I2C(128, 64, i2c)

display.fill(0)
display.text("Boot",0,0)
display.show()

"""
Set up rotary encoder
encoder button on pin 25
set up ISR on encoder button
get proper version of rotary_irq based on platform
"""
knob_btn = Pin(25, Pin.IN, Pin.PULL_UP)
knob_btn_pushed = False
knob_prev = 0
knob_dir = "--"
knob_change = False

"""
button pushed
"""
def knob_btn_isr(pin):
    global knob_btn_pushed
    knob_btn_pushed = True

"""
push only, not release
"""
knob_btn.irq(trigger=Pin.IRQ_FALLING, 
               handler=knob_btn_isr)

knob = RotaryIRQ(pin_num_clk=26,
                 pin_num_dt=27,
                 min_val=0,
                 max_val=10,
                 reverse=False,
                 range_mode=RotaryIRQ.RANGE_BOUNDED)

"""
set up a timer for oled refresh
"""
oled_timer_triggered = False
def oled_timer_isr(t):
    global oled_timer_triggered
    oled_timer_triggered = True
    
oled_timer = Timer(0)
# period is milliseconds
oled_timer.init(period = 30000, mode=Timer.PERIODIC, callback=oled_timer_isr)

def debounce():
    # ISR tiggered, disable IRQs and wait 20ms
    irq_state = disable_irq()
    time.sleep_ms(20)
    enable_irq(irq_state)

def update_oled(s):

    display.fill(0)
    display.text("Knob pos " + knob_dir + " " + str(knob.value()), 0, 0)
    display.text(s, 0, 50)
    display.show()

"""
main loop
"""
update_oled("boot")

val_old = knob.value()
while True:
    # pin interrupt was triggered.
    # Debounce, reset, and then whatever
    if knob_btn_pushed == True:
        debounce()
        knob_btn_pushed = False
        update_oled("button")

    val_new = knob.value()
    if val_old != val_new:
        val_old = val_new
        update_oled("knob")

    time.sleep_ms(50)
