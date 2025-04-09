"""
Buzzer module.

This module provides the implementation of the `BuzzerController` class, which
manages the buzzer's behavior, including boot, power-up, and stopping operations.
"""

import asyncio

import machine

from logging import logger


class BuzzerController:
    """
    Controller for managing the buzzer.

    This class handles the buzzer's operations, such as boot signals, power-up signals,
    and stopping the buzzer.

    Attributes:
        SIGNAL_PIN (int): Default pin for the buzzer signal.
        _event (asyncio.Event): Event object for asynchronous operations.
        _timer (machine.Timer): Timer for managing buzzer timing.
        _pwm (machine.PWM): PWM instance for controlling the buzzer.
    """

    SIGNAL_PIN = None

    _event = None

    def __init__(self, signal_pin=SIGNAL_PIN):
        """
        Initialize the BuzzerController.

        Args:
            signal_pin (int): The pin number for the buzzer signal.
        """
        self._event = asyncio.Event()
        self._timer = machine.Timer(0)

        buzzer_pin = machine.Pin(signal_pin, machine.Pin.OUT)
        self._pwm = machine.PWM(buzzer_pin)
        self._pwm.duty(0)

    def boot(self):
        """
        Emit a boot signal using the buzzer.

        This method sets the buzzer frequency and duty cycle, then stops the buzzer
        after a short delay using a timer.
        """
        logger.debug("Buzzer boot")
        self._pwm.freq(400)
        self._pwm.duty(500)
        self._timer.init(period=200, mode=machine.Timer.ONE_SHOT, callback=self.stop)

    def powerup(self):
        """
        Emit a power-up signal using the buzzer.

        This method sets the buzzer frequency and duty cycle, then stops the buzzer
        after a short delay using a timer.
        """
        logger.debug("Buzzer power up")
        self._pwm.freq(600)  # Set frequency
        self._pwm.duty(500)
        self._timer.init(period=200, mode=machine.Timer.ONE_SHOT, callback=self.stop)

    def stop(self, timer=None):
        """
        Stop the buzzer.

        This method deinitializes the timer and sets the buzzer duty cycle to zero.

        Args:
            timer (machine.Timer, optional): The timer instance used to stop the buzzer.
        """
        self._timer.deinit()
        self._pwm.duty(0)
        logger.debug("Stopping buzzer")
