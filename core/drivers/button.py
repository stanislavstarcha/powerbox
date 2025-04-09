"""
Button module.

This module provides the implementation of the `ButtonController` class, which
manages button input, including debouncing, state changes, and optional buzzer feedback.
"""

import time

import machine

from logging import logger


class ButtonController:
    """
    Controller for managing button input.

    This class handles button state changes, debouncing, and optional buzzer feedback.

    Attributes:
        LISTEN_PIN (int): Default pin for listening to button input.
        JITTER (int): Minimum delay (in milliseconds) to avoid jitter when pressing the button.
        DELAY (int): Delay (in milliseconds) to confirm button press after the first signal.
    """

    LISTEN_PIN = None

    # Minimum delay between button state changes to avoid jitter
    JITTER = 500

    # Delay to confirm button press after the first signal
    DELAY = 50

    # Timestamp when the state was last changed
    _changed_at = 0

    # Current state of the button (True for pressed, False for released)
    _state = False

    # Optional buzzer controller
    _buzzer = None

    def __init__(
        self,
        listen_pin=LISTEN_PIN,
        trigger_delay=DELAY,
        on_change=None,
        buzzer=None,
        trigger_timer=None,
    ):
        """
        Initialize the ButtonController.

        Args:
            listen_pin (int): The pin number to listen for button input.
            trigger_delay (int): Delay (in milliseconds) to confirm button press.
            on_change (callable): Callback function to execute on button state change.
            buzzer (BuzzerController): Optional buzzer controller for feedback.
            trigger_timer (machine.Timer): Timer for handling button press confirmation.
        """
        self._buzzer = buzzer
        self._on_change = on_change
        self._trigger_timer = trigger_timer
        self._trigger_delay = trigger_delay
        self._listen_pin = machine.Pin(
            listen_pin, machine.Pin.IN, machine.Pin.PULL_DOWN
        )

        self._listen_pin.irq(
            trigger=machine.Pin.IRQ_RISING,
            handler=self._check_state,
        )
        logger.info(
            f"Button {self._listen_pin} state initialized", self._listen_pin.value()
        )

    def _check_state(self, pin):
        """
        Check the state of the button and handle debouncing.

        Args:
            pin (machine.Pin): The pin that triggered the interrupt.
        """
        current_ms = time.ticks_ms()
        # Avoid flickering effect by enforcing a minimum delay (jitter)
        if current_ms - self._changed_at < self.JITTER:
            return

        logger.debug(f"Button {self._listen_pin} pushed")
        self._changed_at = current_ms
        self._trigger_timer.init(
            period=self._trigger_delay,
            mode=machine.Timer.ONE_SHOT,
            callback=self.trigger,
        )

    def trigger(self, timer):
        """
        Confirm the button press and execute the callback.

        Args:
            timer (machine.Timer): The timer used for debouncing.
        """
        timer.deinit()
        if self._listen_pin.value() == 0:
            return
        logger.debug(f"Confirming button {self._listen_pin} state")
        if self._on_change is not None:
            self._on_change()
            if self._buzzer:
                self._buzzer.powerup()
