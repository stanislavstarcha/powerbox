"""
MCU (Microcontroller Unit) module.

This module provides the implementation of the `MCUState` and `MCUController`
classes, which manage the state and control logic for the microcontroller,
including memory usage, temperature monitoring, and heartbeat functionality.
"""

import gc
import struct
import time

import esp32

import version
from const import BLE_MCU_STATE_UUID
from drivers import BaseState
from logging import logger


class MCUState(BaseState):
    """
    Represents the state of the MCU (Microcontroller Unit).

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the MCU state.
        GC_FREQUENCY (int): Frequency (in cycles) for garbage collection.
        version (str): Firmware version of the MCU.
        memory (int): Percentage of memory used.
        temperature (float): Temperature of the MCU in degrees Celsius.
        heartbeat (bool): Heartbeat signal to indicate activity.
    """

    NAME = "MCU"
    BLE_STATE_UUID = BLE_MCU_STATE_UUID

    GC_FREQUENCY = 5

    version = None
    memory = 0
    temperature = 0
    heartbeat = True

    def clear(self):
        """
        Clear the MCU state.

        Resets memory and temperature attributes to their default values.
        """
        self.memory = None
        self.temperature = None

    def get_ble_state(self):
        """
        Get the BLE representation of the MCU state.

        Returns:
            bytes: The packed BLE state of the MCU, including uptime, version,
                   temperature, memory usage, and internal errors.
        """
        uptime = int(time.time())
        return struct.pack(
            ">IBBBB",
            self._pack(uptime),
            self._pack_version(version.FIRMWARE),
            self._pack(self.temperature),
            self._pack(self.memory),
            self._pack(self.internal_errors),
        )


class MCUController:
    """
    Controller for managing the MCU (Microcontroller Unit).

    This class handles monitoring the MCU's memory usage, temperature, and
    heartbeat functionality. It also manages LED pulsing for visual feedback.

    Attributes:
        _state (MCUState): The current state of the MCU.
        _led (LedController): Optional LED controller for visual feedback.
    """

    _state = None

    def __init__(self, led=None):
        """
        Initialize the MCUController.

        Args:
            led (LedController): Optional LED controller for visual feedback.
        """
        self._state = MCUState()
        self._led = led

    async def run(self):
        """
        Run the MCU controller.

        This method continuously updates the MCU state, including memory usage,
        temperature, and heartbeat. It also performs garbage collection at
        regular intervals.
        """
        gc_counter = 0
        while True:
            self._state.heartbeat = not self._state.heartbeat
            free_mem = gc.mem_free()
            used_mem = gc.mem_alloc()
            total_mem = free_mem + used_mem
            self._state.memory = int((used_mem / total_mem) * 100)
            self._state.temperature = esp32.mcu_temperature()

            if self._led:
                self._led.pulse((0, 0, 100), 50)

            gc_counter += 1
            if gc_counter >= self._state.GC_FREQUENCY:
                gc.collect()
                gc_counter = 0
                logger.debug(
                    "ESP stats memory",
                    self._state.memory,
                    "temperature",
                    self._state.temperature,
                )

            self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        """
        Get the current state of the MCU.

        Returns:
            MCUState: The current MCU state.
        """
        return self._state
