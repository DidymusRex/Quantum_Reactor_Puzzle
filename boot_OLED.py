"""
boot_OLED.py
"""
from machine import I2C, Pin, reset
import ssd1306

"""
Set up OLED on I2C
  use default address 0x3C
  I2C 0 is scl 18 and sda 19
"""
i2c = I2C(0)
display = ssd1306.SSD1306_I2C(128, 64, i2c)

display.fill(1)
display.text("Hello World", 0, 0)
display.show()
