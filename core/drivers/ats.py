"""
ATS (Automatic Transfer Switch) module.

This module provides the implementation of the ATSState and ATSController
classes, which manage the state and control logic for the automatic transfer
switch functionality.
"""

import struct

import machine

from const import BLE_ATS_STATE_UUID, ATS_MODE_NONE, ATS_MODE_CITY, ATS_MODE_BATTERY
from drivers import BaseState
from logging import logger


class ATSState(BaseState):
    """
    Represents the state of the Automatic Transfer Switch (ATS).

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the ATS state.
        mode (int): The current mode of the ATS (e.g., NONE, CITY, BATTERY).
    """

    NAME = "ATS"
    BLE_STATE_UUID = BLE_ATS_STATE_UUID

    mode = ATS_MODE_NONE

    def get_ble_state(self):
        """
        Get the BLE representation of the ATS state.

        Returns:
            bytes: The packed BLE state of the ATS.
        """
        logger.debug("Getting ATS BLE state")
        return struct.pack(
            ">BB",
            self._pack(self.mode),
            self._pack(self.internal_errors),
        )


class ATSController:
    """
    Controller for the Automatic Transfer Switch (ATS).

    This class manages the logic for detecting and switching between different
    ATS modes (e.g., NONE, CITY, BATTERY).

    Attributes:
        ENABLED (bool): Indicates whether the ATS is enabled.
        NC_PIN (int): Normally closed pin for the ATS.
        NO_PIN (int): Normally open pin for the ATS.
    """

    ENABLED = False
    NC_PIN = None
    NO_PIN = None

    _nc_pin = None
    _no_pin = None
    _state = None

    def __init__(self, nc_pin=NC_PIN, no_pin=NO_PIN, enabled=False):
        """
        Initialize the ATSController.

        Args:
            nc_pin (int): The pin number for the normally closed connection.
            no_pin (int): The pin number for the normally open connection.
            enabled (bool): Whether the ATS is enabled on initialization.
        """
        self._state = ATSState()
        self._nc_pin = machine.Pin(nc_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self._no_pin = machine.Pin(no_pin, machine.Pin.IN, machine.Pin.PULL_DOWN)
        if enabled:
            self.enable()

    def on_profile_state(self, state):
        """
        Handle changes to the profile state.

        Args:
            state: The new profile state.
        """
        pass

    def enable(self):
        """
        Enable the ATS controller.

        This method sets up IRQ handlers for the NC and NO pins and initializes
        the ATS state.
        """
        try:
            self._nc_pin.irq(
                trigger=machine.Pin.IRQ_RISING,
                handler=self._check_state,
            )

            self._no_pin.irq(
                trigger=machine.Pin.IRQ_RISING,
                handler=self._check_state,
            )

            # TODO: Get initial state, e.g., when it's already connected
            logger.info(
                f"Initialized ATS controller nc: {self._nc_pin} no: {self._no_pin}"
            )
        except Exception as e:
            logger.info(
                f"Failed initializing ATS controller nc: {self._nc_pin} no: {self._no_pin}"
            )
            self._state.fail(e)

    def disable(self):
        """
        Disable the ATS controller.

        This method removes IRQ handlers and resets the ATS mode to NONE.
        """
        self._nc_pin.irq(handler=None)
        self._no_pin.irq(handler=None)
        self._state.mode = ATS_MODE_NONE

    def _check_state(self, pin):
        """
        Check and update the ATS state based on the NC and NO pin values.

        Args:
            pin (machine.Pin): The pin that triggered the IRQ.
        """
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
        """
        Run the ATS controller.

        This method continuously monitors the ATS state and sleeps between
        updates.
        """
        logger.info("Running ATS controller")
        while True:
            self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        """
        Get the current state of the ATS.

        Returns:
            ATSState: The current ATS state.
        """
        return self._state
