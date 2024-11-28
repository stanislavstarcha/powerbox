import asyncio

from logging import logger
import machine

from drivers import BaseState


class ATSState(BaseState):
    NAME = "ATS"
    active = False

    def set_display_metric(self, metric):
        self.display_metric_glyph = "offgrid" if self.active else "ongrid"


class ATSController:

    NC_PIN = None
    NO_PIN = None

    _nc_pin = None
    _no_pin = None

    _state = False

    def __init__(self, nc_pin=NC_PIN, no_pin=NO_PIN, on_change=None):
        self._state = ATSState()
        return
        self._on_change = on_change
        self._nc_pin = machine.Pin(nc_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self._no_pin = machine.Pin(no_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)

    def _check_state(self, pin):

        is_active = None
        nc_state = self._nc_pin.value()
        no_state = self._no_pin.value()

        if nc_state == 0 and no_state == 1:
            is_active = True

        if nc_state == 1 and no_state == 0:
            is_active = False

        logger.debug(f"AST new state {is_active} nc: {nc_state} no: {no_state}")
        if is_active is not None and self._state.active != is_active:
            self._state.active = is_active
            logger.info(f"Changed AST state to {self._state.active}")
            if self._on_change:
                self._on_change(is_active)

    async def run(self):
        logger.info("Running AST controller")
        self.initialise()
        while True:
            self._state.snapshot()
            await self._state.sleep()

    def initialise(self):
        try:
            self._nc_pin.irq(
                trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING,
                handler=self._check_state,
            )

            self._no_pin.irq(
                trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING,
                handler=self._check_state,
            )

            logger.info(
                f"Initialized AST controller nc: {self._nc_pin} no: {self._no_pin}"
            )
        except Exception as e:
            logger.info(
                f"Failed initializing AST controller nc: {self._nc_pin} no: {self._no_pin}"
            )
            self._state.fail(e)

    @property
    def state(self):
        return self._state
