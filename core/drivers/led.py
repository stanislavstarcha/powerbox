import machine, neopixel
import time


class LedController:
    def __init__(self, pin):
        self._np = neopixel.NeoPixel(machine.Pin(pin, machine.Pin.OUT), 1)

    def on(self, color=(1, 1, 1)):
        self._np[0] = color
        self._np.write()

    def off(self):
        self.on((0, 0, 0))

    def pulse(self, color=(0, 0, 0), duration=50, n=1):
        while n >= 1:
            self.on(color)
            time.sleep_ms(duration)
            self.off()
            time.sleep_ms(duration)
            n -= 1
