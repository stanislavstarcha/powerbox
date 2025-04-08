"""
LED module.

This module provides the implementation of the `LedController` class, which
manages the behavior of an LED, including turning it on, off, and pulsing.
"""

import machine
import neopixel
import time


class LedController:
    """
    Controller for managing an LED.

    This class provides methods to control an LED, including turning it on, off,
    and creating a pulsing effect.

    Attributes:
        _np (neopixel.NeoPixel): NeoPixel instance for controlling the LED.
    """

    def __init__(self, pin):
        """
        Initialize the LedController.

        Args:
            pin (int): The pin number to which the LED is connected.
        """
        self._np = neopixel.NeoPixel(machine.Pin(pin, machine.Pin.OUT), 1)

    def on(self, color=(1, 1, 1)):
        """
        Turn the LED on with the specified color.

        Args:
            color (tuple): A tuple representing the RGB color of the LED. Default is (1, 1, 1).
        """
        self._np[0] = color
        self._np.write()

    def off(self):
        """
        Turn the LED off.

        This method sets the LED color to (0, 0, 0), effectively turning it off.
        """
        self.on((0, 0, 0))

    def pulse(self, color=(0, 0, 0), duration=50, n=1):
        """
        Create a pulsing effect on the LED.

        Args:
            color (tuple): A tuple representing the RGB color of the LED during the pulse.
            duration (int): The duration (in milliseconds) of each pulse.
            n (int): The number of pulses to create.
        """
        while n >= 1:
            self.on(color)
            time.sleep_ms(duration)
            self.off()
            time.sleep_ms(duration)
            n -= 1
