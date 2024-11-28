import asyncio
import machine


from logging import logger


class BuzzerController:

    SIGNAL_PIN = None

    _event = None

    def __init__(self, signal_pin=SIGNAL_PIN):
        self._event = asyncio.Event()
        self._timer = machine.Timer(0)

        buzzer_pin = machine.Pin(signal_pin, machine.Pin.OUT)
        self._pwm = machine.PWM(buzzer_pin)
        self._pwm.duty(0)

    def boot(self):
        logger.debug("Buzzer boot")
        self._pwm.freq(400)
        self._pwm.duty(500)
        self._timer.init(period=200, mode=machine.Timer.ONE_SHOT, callback=self.stop)

    def powerup(self):
        logger.debug("Buzzer power up")
        self._pwm.freq(600)  # Set frequency
        self._pwm.duty(500)
        self._timer.init(period=200, mode=machine.Timer.ONE_SHOT, callback=self.stop)

    def stop(self, timer=None):
        self._timer.deinit()
        self._pwm.duty(0)
        logger.debug("Stopping buzzer")
