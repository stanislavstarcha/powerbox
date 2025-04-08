import machine
import time

from logging import logger


class ButtonController:
    LISTEN_PIN = None

    # minimum delay between a button can be turned on/off
    # it is to avoid jitter when pressing
    JITTER = 500

    # confirm button pressed after DELAY ms since the first signal came in
    DELAY = 50

    # timestamp when the state is set on
    _changed_at = 0

    _state = False

    # optional buzzer controller
    _buzzer = None

    def __init__(
        self,
        listen_pin=LISTEN_PIN,
        trigger_delay=DELAY,
        on_change=None,
        buzzer=None,
        trigger_timer=None,
    ):
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
        logger.info(f"Button {self._listen_pin} state", self._listen_pin.value())

    def _check_state(self, pin):
        current_ms = time.ticks_ms()
        # jitter is needed to avoid flickering effect
        # when a button state generates dozens of on/off
        # states in short period of time
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
        timer.deinit()
        if self._listen_pin.value() == 0:
            return
        logger.debug(f"Confirming button {self._listen_pin} state")
        if self._on_change is not None:
            self._on_change()
            if self._buzzer:
                self._buzzer.powerup()
