import asyncio
import machine
import neopixel

from logging import logger


class BoardLed:

    LED_PIN = 2

    _led = None

    def __init__(self, led_pin=LED_PIN):
        # self._led = machine.Pin(led_pin, machine.Pin.OUT)
        self._led = machine.PWM(machine.Pin(led_pin, machine.Pin.OUT), freq=1000)
        logger.info(f"Initialized board led controller at GPIO {led_pin}")

    def on(self):
        self._led.duty(64)

    def off(self):
        self._led.duty(0)


class BoardRGBLed(BoardLed):

    PIXEL_PIN = 16

    def __init__(self, pixel_pin=PIXEL_PIN):
        self._led = neopixel.NeoPixel(machine.Pin(pixel_pin), 1)
        logger.info(f"Initialized RGB led controller at GPIO {pixel_pin}")

    def set(self, color=(255, 0, 0)):
        self._pixel[0] = color
        self._pixel.write()

    def on(self):
        self.set((255, 255, 255))

    def off(self):
        self.set((0, 0, 0))


class BoardLedController:

    # specific to core
    LED_PIN = 38

    _led = None

    def __init__(self, led_pin=LED_PIN, led_type=0):

        if led_type == 0:
            self._led = BoardLed(led_pin)
        if led_type == 1:
            self._led = BoardRGBLed(led_pin)

    def on(self):
        self._led.on()

    def off(self):
        self._led.off()

    async def run(self, period_ms):
        logger.info("Running Board LED controller...")
        while True:
            self.on()
            await asyncio.sleep_ms(period_ms)
            self.off()
            await asyncio.sleep_ms(period_ms)

    def shutdown(self):
        self.off()
