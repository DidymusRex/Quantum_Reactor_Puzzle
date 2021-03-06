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
  encoder button on pin 5
  set up listener on encoder button
"""
knob_btn = Pin(5, Pin.IN, Pin.PULL_UP)
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
knob = RotaryIRQ(pin_num_clk=17,
                 pin_num_dt=16,
                 min_val=0,
                 max_val=100,
                 reverse=False,
                 range_mode=RotaryIRQ.RANGE_BOUNDED,
                 pull_up=True,
                 half_step=False)

knob.add_listener(knob_listener)

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
