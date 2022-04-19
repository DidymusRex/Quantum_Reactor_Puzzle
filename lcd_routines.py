"""
lcd_routines.py
"""
from machine import Pin
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16

def lcd_setup(i2c):
    lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)

def lcd_print(msg, clr=False, row=0, col=0):
    if(clr):
        lcd.clear()
    
    lcd.move_to(col, row)
    lcd.putstr(msg)

def boot():
    lcd_print("foobar", True, 6, 1)
    sleep(1)

def boot_msg():
    lcd_print("boot", True, 6, 1)
    sleep(2)

    lcd.clear()
    for i in range(totalColumns):
        lcd_print("o", False, 0, i)
        sleep(.1)

    lcd.clear()
    lcd.move_to(0,0)
    lcd_Print("core initialized", True)
