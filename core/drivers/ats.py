import struct
from logging import logger
import machine

from drivers import BaseState
from const import BLE_ATS_STATE_UUID, ATS_MODE_NONE, ATS_MODE_CITY, ATS_MODE_BATTERY


class ATSState(BaseState):
    NAME = "ATS"
    BLE_STATE_UUID = BLE_ATS_STATE_UUID

    mode = ATS_MODE_NONE

    def get_ble_state(self):
        logger.debug("Getting ATS BLE state")
        return struct.pack(
            ">BB",
            self._pack(self.mode),
            self._pack(self.internal_errors),
        )


class ATSController:

    ENABLED = False
    NC_PIN = None
    NO_PIN = None

    _nc_pin = None
    _no_pin = None
    _state = None

    def __init__(self, nc_pin=NC_PIN, no_pin=NO_PIN, enabled=False):
        self._state = ATSState()
        self._nc_pin = machine.Pin(nc_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self._no_pin = machine.Pin(no_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        if enabled:
            self.enable()

    def on_profile_state(self, state):
        pass

    def enable(self):
        try:
            self._nc_pin.irq(
                trigger=machine.Pin.IRQ_RISING,
                handler=self._check_state,
            )

            self._no_pin.irq(
                trigger=machine.Pin.IRQ_RISING,
                handler=self._check_state,
            )

            # TODO get initial state, e.g. when it's already connected
            logger.info(
                f"Initialized ATS controller nc: {self._nc_pin} no: {self._no_pin}"
            )
        except Exception as e:
            logger.info(
                f"Failed initializing ATS controller nc: {self._nc_pin} no: {self._no_pin}"
            )
            self._state.fail(e)

    def disable(self):
        self._nc_pin.irq(handler=None)
        self._no_pin.irq(handler=None)
        self._state.mode = ATS_MODE_NONE

    def _check_state(self, pin):

        nc_state = self._nc_pin.value()
        no_state = self._no_pin.value()

        mode = ATS_MODE_NONE

        if nc_state == 1 and no_state == 0:
            mode = ATS_MODE_CITY

        if nc_state == 0 and no_state == 1:
            mode = ATS_MODE_BATTERY

        if mode != self._state.mode:
            logger.info(f"Changed ATS state to {self._state.mode}")
            self._state.mode = mode
            self._state.notify()

    async def run(self):
        logger.info("Running ATS controller")
        while True:
            self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        return self._state
