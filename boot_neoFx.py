# boot_neoFx.py
from machine import Pin, reset
from neopixel import NeoPixel
from time import sleep_ms

npxPin = 13
npxHeight = 12
npxWidth = 6
npxLength = npxHeight * npxWidth

np = NeoPixel(Pin(npxPin, Pin.OUT), npxLength)

def npInit():
    np.fill((0,0,0))
    np.write()

def npVert():
    for h in range(npxHeight):
        for w in range(npxWidth):
            np[w * npxHeight + h] = (255,0,0)
            np.write()
            sleep_ms(50)
            npInit()

def npRunOne():
    for p in range(npxLength):
        npInit()
        sleep_ms(25)
        np[p] = (0,128,0)
        np.write()

"""
https://randomnerdtutorials.com/micropython-ws2812b-addressable-rgb-leds-neopixel-esp32-esp8266/
"""
def bounce(r, g, b, wait):
    n = np.n

    for i in range(4 * n):
        for j in range(n):
            np[j] = (r, g, b)

        if (i // n) % 2 == 0:
            np[i % n] = (0, 0, 0)
        else:
            np[n - 1 - (i % n)] = (0, 0, 0)
            
        np.write()
        sleep_ms(wait)
    
def cycle(r, g, b, wait):
    n = np.n
    
    for i in range(4 * n):
        for j in range(n):
            np[j] = (0, 0, 0)

        np[i % n] = (r, g, b)
        np.write()
        sleep_ms(wait)

def wheel(pos):
    """
    Input a value 0 to 255 to get a color value.
    The colors are a transition r - g - b - back to r.
    """
    if pos < 0 or pos > 255:
        return (0, 0, 0)

    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)

    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)

    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

def rainbow_cycle(wait):
    n = np.n

    for j in range(255):
        for i in range(n):
            rc_index = (i * 256 // n) + j
            np[i] = wheel(rc_index & 255)
            
        np.write()
        sleep_ms(wait)
