"""
Button module.

This module provides the implementation of the `ButtonController` class, which
manages button input, including debouncing, state changes, and optional buzzer feedback.
"""

import time
import random

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
    JITTER = 100

    # Delay to confirm the button is pressed after the first signal
    DELAY = 1500

    # Timestamp when the state was last changed
    _pressed_at = 0
    _released_at = 0
    _cycle_started = False

    # Current state of the button (True for pressed, False for released)
    _state = False

    # Optional buzzer controller
    _buzzer = None

    _long_press_timer = None

    def __init__(
        self,
        listen_pin=LISTEN_PIN,
        trigger_delay=DELAY,
        on_short_press=None,
        on_long_press=None,
        buzzer=None,
        trigger_timer=None,
        inverted=False,
    ):
        """
        Initialize the ButtonController.

        Args:
            listen_pin (int): The pin to listen for button input.
            trigger_delay (int): Delay (in milliseconds) to confirm button press.
            on_short_press (callable): Callback function to execute on short button press.
            on_long_press (callable): Callback function to execute on long button press.
            buzzer (BuzzerController): Optional buzzer controller for feedback.
            trigger_timer (machine.Timer): Timer for handling button press confirmation.
            inverted (bool, optional): Whether the button is inverted (True for released). Defaults to False.:
        """
        self._buzzer = buzzer
        self._inverted = inverted
        self._on_short_press = on_short_press
        self._on_long_press = on_long_press
        self._trigger_timer = trigger_timer
        self._trigger_delay = trigger_delay

        initial_state = machine.Pin.PULL_DOWN
        if self._inverted:
            initial_state = machine.Pin.PULL_UP

        self._listen_pin = machine.Pin(listen_pin, machine.Pin.IN, initial_state)
        self._listen_pin.irq(
            trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING,
            handler=self._check_state,
        )

        self._long_press_timer = machine.Timer(1)
        logger.info(
            f"Button {self._listen_pin} state initialized", self._listen_pin.value()
        )

    def _check_state(self, pin):
        """
        Check the state of the button when it's pushed.

        Args:
            pin (machine.Pin): The pin that triggered the interrupt.
        """
        state = pin.value()

        if (self._inverted and not state) or (not self._inverted and state):
            callback = self.on_pressed_irq

        if (self._inverted and state) or (not self._inverted and not state):
            callback = self.on_released_irq

        self._trigger_timer.init(
            period=1,
            mode=machine.Timer.ONE_SHOT,
            callback=callback,
        )

    def on_pressed_irq(self, timer):

        timer.deinit()

        if self._cycle_started:
            return

        self._cycle_started = True
        current_ms = time.ticks_ms()
        elapsed_ms = current_ms - self._pressed_at
        if elapsed_ms < self.JITTER:
            pass

        self._pressed_at = current_ms
        self._released_at = current_ms

        self._long_press_timer.init(
            period=self._trigger_delay,
            mode=machine.Timer.ONE_SHOT,
            callback=self.trigger,
        )

    def on_released_irq(self, timer):
        timer.deinit()
        if not self._cycle_started:
            return

        current_ms = time.ticks_ms()
        elapsed_ms = current_ms - self._released_at
        if elapsed_ms < self.JITTER:
            pass

        self._released_at = current_ms
        self._cycle_started = False

        if self._on_short_press and elapsed_ms < self._trigger_delay:
            logger.info(f"Button short pressed {self._listen_pin}")
            self._on_short_press()

    def trigger(self, timer):
        """
        Confirm the button is still pressed and execute the callback.

        Args:
            timer (machine.Timer): The timer used for debouncing.
        """
        timer.deinit()
        state = self._listen_pin.value()
        pressed = state
        if self._inverted:
            pressed = not state

        if not pressed:
            return

        if self._on_long_press is not None:
            logger.info(f"Button long pressed {self._listen_pin}")
            self._on_long_press()
            if self._buzzer:
                self._buzzer.powerup()
