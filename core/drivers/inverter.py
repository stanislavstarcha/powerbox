"""
Inverter module.

This module provides the implementation of the `InverterState` and `InverterController`
classes, which manage the state and control logic for the inverter, including
communication, fan tachometer monitoring, and power state management.

The module handles:
- Communication with the inverter via UART
- Monitoring fan tachometers for RPM readings
- Managing power state (on/off)
- Tracking inverter metrics (voltage, power, temperature)
- Error detection and handling
- Historical data collection
"""

import asyncio
import struct

import machine

from const import BLE_INVERTER_STATE_UUID
from const import (
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
    HISTORY_INVERTER_RPM,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
)
from drivers import BaseState
from drivers.button import ButtonController
from lib.history import HistoricalData
from lib.tachometer import Tachometer
from logging import logger


class InverterState(BaseState):
    """
    Represents the state of the inverter.

    This class manages the current state of the inverter, including its operational
    status, electrical measurements, and error conditions. It also handles parsing
    of communication frames from the inverter and maintains historical data.

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the inverter state.
        active (bool): Indicates whether the inverter is active.
        ac (int): AC output voltage in volts.
        power (int): Output power in watts.
        dc (float): Input voltage in volts.
        temperature (int): Device temperature in degrees Celsius.
        level (int): Battery level (1-10).
        rpm_a (int): Fan A speed in RPM.
        rpm_b (int): Fan B speed in RPM.
        _valid (bool): Indicates whether the state is valid.
        history (dict): Historical data for power, temperature, and RPM.
        external_errors (int): Bitmap of external error conditions.
        internal_errors (int): Bitmap of internal error conditions.
    """

    NAME = "INVERTER"
    BLE_STATE_UUID = BLE_INVERTER_STATE_UUID

    active = False
    ac = None
    power = None
    dc = None
    temperature = None
    level = None
    rpm_a = None
    rpm_b = None
    _valid = False

    history = {
        HISTORY_INVERTER_POWER: HistoricalData(
            chart_type=HISTORY_INVERTER_POWER,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_INVERTER_RPM: HistoricalData(
            chart_type=HISTORY_INVERTER_RPM,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_INVERTER_TEMPERATURE: HistoricalData(
            chart_type=HISTORY_INVERTER_TEMPERATURE,
            data_type=DATA_TYPE_BYTE,
        ),
    }

    def clear(self):
        """
        Clear the inverter state.

        Resets all state attributes to their default values and notifies
        any observers of the state change.

        Returns:
            None
        """
        self.active = False
        self.ac = None
        self.power = None
        self.dc = None
        self.temperature = None
        self.level = None
        self.rpm_a = None
        self.rpm_b = None
        self.external_errors = 0
        self.notify()

    def parse(self, frame):
        """
        Parse a frame received from the inverter.

        Extracts and validates data from a communication frame, including
        voltage, power, temperature, and error conditions. Performs checksum
        validation to ensure data integrity.

        Args:
            frame (bytes): The raw communication frame to parse.

        Returns:
            None
        """
        # TODO: use frame size
        if len(frame) != 17:
            return

        (
            frame_start,
            address,
            length,
            cmd,
            ac1,
            ac2,
            power1,
            power2,
            dc1,
            dc2,
            temperature1,
            temperature2,
            _,
            device_error,
            level,
            checksum,
            frame_end,
        ) = struct.unpack_from("B" * 17, frame)

        self.ac = int(f"{ac1:x}") * 100 + int(f"{ac2:x}")
        self.power = int(f"{power1:x}") * 100 + int(f"{power2:x}")
        self.dc = int(f"{dc1:x}") * 10 + int(f"{dc2:x}") / 10
        self.temperature = int(f"{temperature1:x}") * 100 + int(f"{temperature2:x}")
        """
        # inverter device errors
        0x02 Overload timing
        0x04 Overload protection
        0x08 Overtemperature protection
        0x10 Undervoltage protection
        0x20 Overvoltage protection
        0x40 Fan rotation flag
        """
        self.external_errors = int(device_error)
        self.level = int(level)

        # clear fan rotation error due to custom fan model
        self.external_errors &= ~(1 << 6)

        checksum = int(f"{checksum:x}")
        actual_checksum = (
            address
            + length
            + cmd
            + ac1
            + ac2
            + power1
            + power2
            + dc1
            + dc2
            + temperature1
            + temperature2
            + device_error
            + level
        ) % 256

        actual_checksum = actual_checksum % 100
        self._valid = actual_checksum == checksum

    def parse_buffer(self, buffer):
        """
        Parse a buffer received from the inverter.

        Processes a communication buffer, extracts valid frames, and updates
        the inverter state. Handles error conditions and sets appropriate
        error flags.

        Args:
            buffer (bytes): The communication buffer to parse.

        Returns:
            bool: True if parsing was successful, False otherwise.
        """
        if not buffer:
            self.set_error(self.ERROR_NO_RESPONSE)
            self.reset_error(self.ERROR_BAD_RESPONSE)
            return False

        self.reset_error(self.ERROR_NO_RESPONSE)

        if 0xAE in buffer and 0xEE in buffer:
            frame_start = buffer.find(b"\xae")
            frame_end = buffer.find(b"\xee") + 1
            self.parse(buffer[frame_start:frame_end])

        if self.is_valid():
            self.reset_error(self.ERROR_BAD_RESPONSE)
            if self.external_errors:
                self.set_error(self.ERROR_EXTERNAL)
            else:
                self.reset_error(self.ERROR_EXTERNAL)
        else:
            self.set_error(self.ERROR_BAD_RESPONSE)

    def is_valid(self):
        """
        Check if the inverter state is valid.

        Validates the current state based on checksum verification
        and other error conditions.

        Returns:
            bool: True if the state is valid, False otherwise.
        """
        return self._valid

    def get_avg_rpm(self):
        """
        Calculate the average RPM of the fans.

        Computes the arithmetic mean of both fan speeds if both
        are available.

        Returns:
            int: The average RPM of the fans, or None if either fan
                 speed is unavailable.
        """
        if self.rpm_a and self.rpm_b:
            return int((self.rpm_a + self.rpm_b) / 2)
        return None

    def build_history(self):
        """
        Build historical data for the inverter.

        Updates the historical data collections with current power,
        temperature, and RPM values. This data is used for trending
        and analysis.

        Returns:
            None
        """
        self.history[HISTORY_INVERTER_POWER].push(self._pack(self.power))
        self.history[HISTORY_INVERTER_TEMPERATURE].push(self._pack(self.temperature))
        self.history[HISTORY_INVERTER_RPM].push(self._pack(self.get_avg_rpm()))

    def get_ble_state(self):
        """
        Get the BLE representation of the inverter state.

        Creates a binary representation of the current state for
        transmission over Bluetooth Low Energy.

        Returns:
            bytes: The packed BLE state of the inverter.
        """
        return struct.pack(
            ">HHBBBBB",
            self._pack(self.power),
            self._pack(self.get_avg_rpm()),
            self._pack_bool(self.active),
            self._pack(self.ac),
            self._pack(self.temperature),
            self._pack(self.external_errors),
            self._pack(self.internal_errors),
        )


class InverterController:
    """
    Controller for managing the inverter.

    This class handles communication with the inverter, monitoring fan tachometers,
    and managing the power state. It provides a high-level interface for controlling
    the inverter and monitoring its operational status.

    The controller manages:
    - Power state transitions (on/off)
    - UART communication with the inverter
    - Fan tachometer monitoring
    - Battery voltage monitoring
    - Error detection and handling

    Attributes:
        POWER_BUTTON_PIN (int): Default pin for the power button.
        POWER_GATE_PIN (int): Default pin for the power gate.
        BAUD_RATE (int): Default baud rate for UART communication.
        UART_IF (int): UART interface number.
        UART_RX_PIN (int): UART RX pin number.
        UART_TX_PIN (int): UART TX pin number.
        STATUS_REQUEST (bytes): Command to request inverter status.
        SHUTDOWN_REQUEST (bytes): Command to shut down the inverter.
        TURN_ON_REQUEST (bytes): Command to turn on the inverter.
    """

    POWER_BUTTON_PIN = None
    POWER_GATE_PIN = None

    BAUD_RATE = 9600
    UART_IF = None
    UART_RX_PIN = None
    UART_TX_PIN = None

    STATUS_REQUEST = b"\xae\x01\x01\x03\x05\xee"
    SHUTDOWN_REQUEST = b"\xae\x01\x02\x04\x01\x00\x08\xee"
    TURN_ON_REQUEST = b"\xae\x01\x02\x04\x00\x00\x07\xee"

    _bootstrapping = False
    _bootstrapping_delay = 3
    _uart = None
    _power_button = None
    _power_gate_pin = None
    _state = None
    _tachometer_a = None
    _tachometer_b = None

    def __init__(
        self,
        power_button_pin=POWER_BUTTON_PIN,
        power_button_timer=-1,
        power_gate_pin=POWER_GATE_PIN,
        uart=None,
        baud_rate=BAUD_RATE,
        uart_tx_pin=UART_TX_PIN,
        uart_rx_pin=UART_RX_PIN,
        buzzer=None,
        fan_tachometer_a_pin=None,
        fan_tachometer_b_pin=None,
        fan_tachometer_a_timer=None,
        fan_tachometer_b_timer=None,
    ):
        """
        Initialize the InverterController.

        Sets up the controller with the specified hardware configuration,
        including power button, UART communication, and fan tachometers.
        Initializes the inverter state and configures the power gate.

        Args:
            power_button_pin (int): Pin for the power button.
            power_button_timer (int): Timer for the power button debouncing.
            power_gate_pin (int): Pin for the power gate control.
            uart (UART): UART instance for communication with the inverter.
            baud_rate (int): Baud rate for UART communication.
            uart_tx_pin (int): UART TX pin number.
            uart_rx_pin (int): UART RX pin number.
            buzzer (BuzzerController): Buzzer controller for user feedback.
            fan_tachometer_a_pin (int): Pin for fan A tachometer.
            fan_tachometer_b_pin (int): Pin for fan B tachometer.
            fan_tachometer_a_timer (int): Timer for fan A tachometer.
            fan_tachometer_b_timer (int): Timer for fan B tachometer.

        Returns:
            None
        """
        self._state = InverterState()

        self._uart = uart
        self._tx_pin = uart_tx_pin
        self._rx_pin = uart_rx_pin
        self._baud_rate = baud_rate

        self._power_button = ButtonController(
            listen_pin=power_button_pin,
            on_long_press=self.on_power_trigger,
            buzzer=buzzer,
            trigger_timer=power_button_timer,
            inverted=True,
        )

        self._power_gate_pin = machine.Pin(
            power_gate_pin,
            machine.Pin.OUT,
            machine.Pin.PULL_DOWN,
        )
        self._power_gate_pin.off()

        if fan_tachometer_a_pin and fan_tachometer_a_timer:
            self._tachometer_a = Tachometer(
                name="A",
                pin=machine.Pin(fan_tachometer_a_pin, machine.Pin.IN),
                period_ms=200,
                done_callback=self.on_tachometer_a,
                timer_id=fan_tachometer_a_timer,
            )

        if fan_tachometer_b_pin and fan_tachometer_b_timer:
            self._tachometer_b = Tachometer(
                name="B",
                pin=machine.Pin(fan_tachometer_b_pin, machine.Pin.IN),
                period_ms=200,
                done_callback=self.on_tachometer_b,
                timer_id=fan_tachometer_b_timer,
            )

        logger.info(f"Initialized inverter")

    def on_tachometer_a(self, rpm):
        """
        Handle RPM updates from fan A tachometer.

        Updates the state with the current RPM reading from fan A
        and logs the value for debugging.

        Args:
            rpm (int): RPM value from fan A.

        Returns:
            None
        """
        self._state.rpm_a = rpm
        logger.debug(f"INVERTER FAN A RPM: {rpm}")

    def on_tachometer_b(self, rpm):
        """
        Handle RPM updates from fan B tachometer.

        Updates the state with the current RPM reading from fan B
        and logs the value for debugging.

        Args:
            rpm (int): RPM value from fan B.

        Returns:
            None
        """
        self._state.rpm_b = rpm
        logger.debug(f"INVERTER FAN B RPM: {rpm}")

    def on(self):
        """
        Turn on the inverter.

        Initializes UART communication, activates the power gate,
        and sets the inverter state to active. Includes a bootstrapping
        delay to allow the inverter to stabilize.

        Returns:
            None
        """
        self._bootstrapping = True
        self._uart.init(rx=self._rx_pin, tx=self._tx_pin, baud_rate=self._baud_rate)
        self._power_gate_pin.on()
        self._state.on()
        logger.info("Inverter is on")

    def off(self):
        """
        Turn off the inverter.

        Deactivates the power gate, clears the inverter state,
        and resets error conditions.

        Returns:
            None
        """
        self._bootstrapping = False
        self._power_gate_pin.off()
        self._state.off()
        self.state.clear_internal_errors()
        self.state.clear()
        logger.info("Inverter is off")

    def on_power_trigger(self):
        """
        Handle power button triggers to toggle the inverter state.

        Toggles the inverter between on and off states based on
        the current state when the power button is pressed.

        Returns:
            None
        """
        if self._state.active:
            self.off()
        else:
            self.on()

    async def run(self):
        """
        Run the inverter controller.

        This method continuously monitors the inverter state and updates it.
        It handles communication with the inverter, fan tachometer readings,
        and error detection. The method runs indefinitely in an asynchronous loop.

        The controller performs the following tasks:
        - Reads inverter status via UART
        - Measures fan tachometer readings
        - Updates historical data
        - Logs operational status and errors

        Returns:
            None
        """
        logger.info("Running inverter controller...")
        while True:
            if self._state.active:

                # one-off sleep before reading inverter status
                if self._bootstrapping:
                    await asyncio.sleep(self._bootstrapping_delay)
                    self._bootstrapping = False

                try:
                    self.read_status()
                except Exception as e:
                    logger.error("Failed request to inverter")
                    logger.critical(e)

                if self._tachometer_a:
                    self._tachometer_a.measure()

                if self._tachometer_b:
                    self._tachometer_b.measure()

                self._state.snapshot()

                if self._state.is_valid():
                    logger.debug(
                        f"Inverter AC: {self._state.ac}, Temperature: {self._state.temperature} DC: {self._state.dc} POWER: {self._state.power} ERR: {self._state.internal_errors} ({self._state.external_errors})"
                    )
                else:
                    logger.error(
                        f"Inverter ERR: {self._state.internal_errors} ({self._state.external_errors})"
                    )

            await self._state.sleep()

    def read_status(self):
        """
        Read the current status from the inverter.

        Sends a status request command to the inverter via UART,
        receives the response, and parses it to update the inverter state.
        Logs the raw response for debugging purposes.

        Returns:
            None
        """
        data = self._uart.query(self.STATUS_REQUEST, delay=50)
        logger.debug("Inverter response", self.state.as_hex(data))
        self._state.parse_buffer(data)

    @property
    def state(self):
        """
        Get the current state of the inverter.

        Provides access to the InverterState object that contains
        all current operational data and error conditions.

        Returns:
            InverterState: The current inverter state.
        """
        return self._state
