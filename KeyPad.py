# esp32 version in Micropython
from machine import disable_irq, enable_irq, Pin, PWM, reset, Timer
from micropython import const, schedule
from time import sleep_ms, ticks_ms

class KeyPad():
    def __init__(self, r1, r2, r3, r4, c1, c2, c3, c4, timer_period = 200):
        self._led = Pin(2, Pin.OUT)             # LED on pin 2 (onboard led)

        self._rows = []                         # Rows: pins are OUTPUT pulled HIGH
        for p in (r1, r2, r3, r4):
            row = Pin(p, Pin.OUT, Pin.PULL_UP, value = 1)
            self._rows.append(row)

        self._cols = []                         # Cols: pins are INPUT pulled low
        for p in (c1, c2, c3, c4):
            col = Pin(p, Pin.IN, Pin.PULL_DOWN, value = 0)
            self._cols.append(col)

        self._enable_col_isr()
        
        self._timerKP = Timer(3)                # Create a timer for debounce
        self._period = timer_period

        self._chars = ["1","2","3","A",         # Characters for buttons
                       "4","5","6","B",
                       "7","8","9","C",
                       "*","0","#","D"]

        self._btn_pressed = False               # No button pressed yet
        self._btn_val = 0
        self._btn_hold = 0
        self.btn_chr = ""

    def _enable_col_isr(self):
        for c in range(4):
            self._cols[c].irq(trigger=Pin.IRQ_RISING, handler=self._isr)
    
    def _disable_col_isr(self):
        for c in range(4):
            self._cols[c].irq(trigger=Pin.IRQ_RISING, handler=None)
        
    def _debounce(self, t):                     # Button pressed and debounced
        self._btn_pressed = True
        self._led.on()

        self._btn_val = self._scan()            # Scan for which button
        if self._btn_val >= 0:                  # Keep old value on -1
            self.btn_chr = self._chars[self._btn_val]

        self._enable_col_isr()                   # Re-enable interrupts

    def _isr_sched(self, p):
        self._disable_col_isr()                  # Disable interrupts
        self._timerKP.init(period=self._period,  # Debounce the pin
                           mode=Timer.ONE_SHOT, 
                           callback=self._debounce)

    def _isr(self, pin):
        schedule(self._isr_sched, pin)

    def _scan(self):                            # Returns -1 or button index
        i = -1                                  # Error value for no button press
        for r in range(4):                      # Turn OFF all the rows for scanning
            self._rows[r].off()

        for r in range(4):                      # Rows, one at a time
            self._rows[r].on()                  # Set row ON

            for c in range(4):                  # Test columns, one at a time
                if self._cols[c].value() == 1:  # Is column ON?
                    i = r * 4 + c               # Calculate index to character list

            self._rows[r].off()                 # Set row back OFF

        for r in range(4):                      # Turn all the rows back ON
            self._rows[r].on()

        return i

    def get_btn(self):
        if self._btn_pressed:
            self._btn_pressed = False           # Only return the button once
            self._led.off()
            return self._btn_val
        else:
            return -1                           # No button pressed
