from kt403A import KT403A
from machine import reset

def reboot():
    reset()

print("-----------------")
print(" Test KT403A MP3 ")
print("-----------------")

mp3 = KT403A(1, 3, 4)
mp3.EnableLoopAll()
