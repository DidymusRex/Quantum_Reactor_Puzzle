"""
KeyPad example
save as boot.py on client device
"""
from KeyPad import KeyPad
from machine import Pin, PWM, reset, Timer
from time import sleep_ms, ticks_ms

"""
simple function to reboot in REPL
"""
def reboot():
    reset()

kp = KeyPad(13, 12, 14, 27, 26, 25, 33, 32, timer_period=50)
btn = -1

print("begin")

while True:
    if kp.get_btn() >= 0:
        print(kp.btn_chr)

    sleep_ms(20)
