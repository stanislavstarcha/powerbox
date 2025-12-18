"""
Drivers module.

This module provides the base classes and utilities for implementing various drivers
used in the system, such as state management and hardware interaction.
"""

import asyncio
import gc
import time

import machine

from const import (
    BLE_HISTORY_STATE_UUID,
    EVENT_STATE_CHANGE,
    EVENT_STATE_ON,
    EVENT_STATE_OFF,
)
from logging import logger


class UART:
    """
    UART class for managing UART communication.

    This class provides methods for initializing and interacting with UART interfaces.

    Attributes:
        _active (bool): Whether the UART is active.
        _uart (machine.UART): The UART instance.
        _interface (int): The UART interface number.
        _baud_rate (int): The baud rate for UART communication.
        _timeout (int): The timeout for UART operations.
    """

    _active = None
    _uart = None
    _interface = None
    _baud_rate = None
    _timeout = None

    def __init__(self, interface, timeout=None):
        """
        Initializes the UART instance.

        Args:
            interface (int): The UART interface number.
            timeout (int, optional): The timeout for UART operations.
        """
        self._interface = interface
        self._timeout = timeout
        self._uart = machine.UART(self._interface)

    def init(self, rx=None, tx=None, baud_rate=9600):
        """
        Initializes the UART hardware.

        Args:
            rx (int, optional): The RX pin number.
            tx (int, optional): The TX pin number.
            baud_rate (int, optional): The baud rate for UART communication.
        """
        tx = machine.Pin(tx, machine.Pin.OUT, machine.Pin.PULL_UP) if tx else None
        rx = machine.Pin(rx, machine.Pin.IN, machine.Pin.PULL_UP) if rx else None

        if rx and tx:
            self._uart.init(baudrate=baud_rate, rx=rx, tx=tx)
            logger.info("Initialized bidirectional UART", baud_rate, rx, tx)
        elif rx:
            self._uart.init(baudrate=baud_rate, rx=rx)
            logger.info("Initialized read-only UART", baud_rate, rx)

        gc.collect()

    def query(self, frame, delay=0):
        """
        Sends a query frame and reads the response.

        Args:
            frame (bytes): The frame to send.
            delay (int, optional): Delay in milliseconds before reading the response.

        Returns:
            bytes: The response data.
        """
        logger.debug("UART query", self._interface, frame)
        self._uart.write(frame)
        if delay:
            time.sleep_ms(delay)

        return self._uart.read()

    def sample(self, timeout=1000, max_size=512):
        """
        Reads data from the UART interface.

        Args:
            timeout (int, optional): The timeout in milliseconds.
            max_size (int, optional): The maximum size of data to read.

        Returns:
            bytes: The data read from the UART interface.
        """
        logger.debug("UART sample", self._interface, timeout, max_size)
        buffer = bytearray()

        started_at = time.ticks_ms()
        while True:
            data = self._uart.read()
            if data:
                buffer += data
                if len(buffer) > max_size:
                    break

            diff = time.ticks_ms() - started_at
            if diff > timeout:
                break

        return bytes(buffer)


class BaseState:
    """
    Base class for managing the state of a driver.

    This class provides common functionality for state management, including error
    handling, notifications, and state updates.

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the state.
        ERROR_TIMEOUT (int): Error code for timeout errors.
        ERROR_EXCEPTION (int): Error code for exceptions.
        ERROR_NO_RESPONSE (int): Error code for no response.
        ERROR_BAD_RESPONSE (int): Error code for bad responses.
        ERROR_EXTERNAL (int): Error code for external errors.
        active (bool): Whether the state is active.
        internal_errors (int): Internal error flags.
        external_errors (int): External error flags.
        exception (Exception): The last exception encountered.
        history (dict): Historical data for telemetry.
        STATE_FREQUENCY (int): Frequency of state updates.
        HISTORY_FREQUENCY (int): Frequency of historical updates.
    """

    NAME = "BASE"

    BLE_STATE_UUID = None

    # internal loop stuck
    ERROR_TIMEOUT = 0

    # exception registered
    ERROR_EXCEPTION = 1

    # no response from external device
    ERROR_NO_RESPONSE = 2

    # invalid response from external device
    ERROR_BAD_RESPONSE = 3

    # error from the external device
    ERROR_EXTERNAL = 4

    _ble = None

    # is external device active
    active = False

    # software error code
    internal_errors = 0

    # device error code
    external_errors = 0

    # last exception
    exception = None

    # last time snapshot function was called
    _state_modified = 0

    # last time history function was called
    _history_modified = 0

    history = None

    # how often to update display and BLE state
    STATE_FREQUENCY = 2

    # how often to record and update historical BLE state
    HISTORY_FREQUENCY = 5

    _callbacks = None

    def __init__(self):
        """
        Initializes the BaseState instance.
        """
        self._callbacks = {
            EVENT_STATE_CHANGE: [],
            EVENT_STATE_ON: [],
            EVENT_STATE_OFF: [],
        }

    def add_callback(self, event, callback):
        """
        Adds a callback for a specific event.

        Args:
            event (str): The event type.
            callback (callable): The callback function.
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def on(self):
        """
        Activates the state and triggers the ON event.
        """
        self.active = True
        if self._callbacks[EVENT_STATE_ON]:
            for cb in self._callbacks[EVENT_STATE_ON]:
                cb()

        self.notify()

    def off(self):
        """
        Deactivates the state and triggers the OFF event.
        """
        self.active = False
        if self._callbacks[EVENT_STATE_OFF]:
            for cb in self._callbacks[EVENT_STATE_OFF]:
                cb()
        self.notify()

    def trigger(self, event):
        if self._callbacks[event]:
            for cb in self._callbacks[event]:
                cb()

    def fail(self, e=None):
        """
        Sets the state to failed and logs the exception.

        Args:
            e (Exception, optional): The exception that caused the failure.
        """
        self.set_error(self.ERROR_EXCEPTION)
        self.exception = e

    async def sleep(self):
        """
        Puts the state into a sleep mode for a predefined duration.
        """
        await asyncio.sleep(self.STATE_FREQUENCY)

    def set_error(self, b):
        """
        Sets an error flag.

        Args:
            b (int): The error bit to set.
        """
        new_state = self.internal_errors | (1 << b)
        if new_state != self.internal_errors:
            self.internal_errors = new_state
            self.notify()
            logger.error(f"{self.NAME} SET ERROR {b}")

    def reset_error(self, b):
        """
        Resets an error flag.

        Args:
            b (int): The error bit to reset.
        """
        new_state = self.internal_errors & ~(1 << b)
        if new_state != self.internal_errors:
            self.internal_errors = new_state
            self.notify()
            logger.info(f"{self.NAME} RESET ERROR {b}")

    def clear_internal_errors(self):
        """
        Clears all internal error flags.
        """
        if self.internal_errors == 0:
            return

        self.internal_errors = 0
        self.notify()

    def check_health(self):
        """
        Checks whether the loop runs normally.
        """
        diff = time.time() - self._state_modified
        if diff - 5 > self.STATE_FREQUENCY:
            self.set_error(self.ERROR_TIMEOUT)
        else:
            self.reset_error(self.ERROR_TIMEOUT)

    def snapshot(self):
        """
        Captures a snapshot of the current state.
        """
        self._state_modified = time.time()
        self.check_health()

        if self._state_modified - self._history_modified >= self.HISTORY_FREQUENCY:
            self.build_history()
            self._notify_history_update()
            self._history_modified = time.time()

        self.notify()

    @staticmethod
    def _pack(value):
        """
        Converts a value into a numeric type where 0x00 represents NULL.

        Args:
            value (Any): The value to pack.

        Returns:
            int: The packed value.
        """
        if value is None:
            return 0x00
        return int(value) + 1

    @staticmethod
    def _unpack(value):
        """
        Unpacks a numeric value where 0x00 represents NULL.

        Args:
            value (int): The packed value.

        Returns:
            Any: The unpacked value.
        """
        if value == 0:
            return None
        return value - 1

    @staticmethod
    def _pack_bool(value):
        """
        Packs a boolean value.

        Args:
            value (bool): The boolean value to pack.

        Returns:
            int: The packed value.
        """
        if value is None:
            return 0x00

        if value:
            return 0x02

        return 0x01

    @staticmethod
    def _pack_version(value: str) -> int:
        """
        Packs a version string into an 8-bit integer representation.
        Layout: 1 bit for major, 4 bits for minor, 3 bits for patch.

        Args:
            value (str): The version string (e.g., "1.15.7").

        Returns:
            int: The packed 8-bit integer.
        """
        major, minor, patch = map(int, value.split("."))
        # major: 1 bit (msb), minor: 4 bits, patch: 3 bits (lsb)
        return ((major & 0b1) << 7) | ((minor & 0b1111) << 3) | (patch & 0b111)

    @staticmethod
    def _pack_bms_temperature(value):
        """
        Packs a BMS temperature value.

        Args:
            value (int): The temperature value.

        Returns:
            int: The packed temperature value.
        """
        if value is None:
            return 0

        # when disabled
        if value == 140:
            return 0

        return value + 1

    @staticmethod
    def _pack_cell_voltage(voltage):
        """
        Packs a cell voltage value.

        Args:
            voltage (int): The cell voltage.

        Returns:
            int: The packed voltage value.
        """
        if voltage is None:
            return 0

        return 1 + int(voltage / 10) - 250

    @staticmethod
    def _pack_voltage(voltage):
        """
        Packs a voltage value.

        Args:
            voltage (float): The voltage value.

        Returns:
            int: The packed voltage value.
        """
        if voltage is None:
            return 0
        return voltage + 1

    @staticmethod
    def _pack_float(value, factor=100):
        """
        Packs a float value.

        Args:
            value (float): The value.

        Returns:
            int: The packed value.
        """
        if value is None:
            return 0
        return int(value * factor) + 1

    def get_ble_state(self):
        """
        Creates a snapshot for BLE current and historical state.
        """
        pass

    def _notify_history_update(self):
        """
        Builds incremental historical state.
        """
        if not self.history or not self._ble:
            return

        for chart_type, historical_data in self.history.items():
            self._ble.notify(BLE_HISTORY_STATE_UUID, historical_data.ble_update())

    def build_history(self):
        """
        Creates a snapshot for BLE current and historical state.
        """
        pass

    def attach_ble(self, instance):
        """
        Attaches a BLE instance to the state.

        Args:
            instance: The BLE instance to attach.
        """
        self._ble = instance

    def notify(self):
        """
        Notifies listeners about a state change.
        """
        if self.BLE_STATE_UUID and self._ble:
            self._ble.notify(self.BLE_STATE_UUID, self.get_ble_state())

        if self._callbacks[EVENT_STATE_CHANGE]:
            for cb in self._callbacks[EVENT_STATE_CHANGE]:
                cb(self)

    def pull_history(self):
        """
        Pulls historical data for BLE notifications.
        """
        if not self.history:
            return

        for metric_name, data in self.history.items():
            chunks = data.ble_chunks()
            if not chunks:
                continue
            for chunk in chunks:
                self._ble.notify(BLE_HISTORY_STATE_UUID, chunk)
                time.sleep_ms(10)

    @staticmethod
    def as_hex(data):
        """
        Converts binary data to a hexadecimal string.

        Args:
            data (bytes): The binary data.

        Returns:
            str: The hexadecimal representation of the data.
        """
        if not data:
            return ""

        return " ".join(f"{byte:02X}" for byte in data)
