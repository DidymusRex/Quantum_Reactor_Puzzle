# boot_i2c_lcd.py
from machine import Pin, SoftI2C
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
from time import sleep

I2C_ADDR = 0x27
totalRows = 2
totalColumns = 16

i2c = SoftI2C(scl=Pin(23), sda=Pin(22), freq=10000)
lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)


"""
main
"""
print("begin")
sleep(5)

lcd.clear()
lcd.putstr(".....")
sleep(1)

boot()
boot_msg()
print("done")
