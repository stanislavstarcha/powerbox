"""
Inverter module.

This module provides the implementation of the `InverterState` and `InverterController`
classes, which manage the state and control logic for the inverter, including
communication, fan tachometer monitoring, and power state management.
"""

import asyncio
import machine
import struct

from drivers import BaseState
from drivers.button import ButtonController
from lib.history import HistoricalData
from lib.tachometer import Tachometer

from logging import logger
from const import BLE_INVERTER_STATE_UUID

from const import (
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
    HISTORY_INVERTER_RPM,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
)


class InverterState(BaseState):
    """
    Represents the state of the inverter.

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the inverter state.
        active (bool): Indicates whether the inverter is active.
        ac (int): AC output voltage.
        power (int): Output power.
        dc (float): Input voltage.
        temperature (int): Device temperature.
        level (int): Battery level (1-10).
        rpm_a (int): Fan A speed in RPM.
        rpm_b (int): Fan B speed in RPM.
        _valid (bool): Indicates whether the state is valid.
        history (dict): Historical data for power, temperature, and RPM.
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

        Resets all state attributes to their default values.
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

        Args:
            frame (bytes): The frame to parse.
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

        Args:
            buffer (bytes): The buffer to parse.
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

        Returns:
            bool: True if the state is valid, False otherwise.
        """
        return self._valid

    def get_avg_rpm(self):
        """
        Calculate the average RPM of the fans.

        Returns:
            int: The average RPM of the fans.
        """
        if self.rpm_a and self.rpm_b:
            return int((self.rpm_a + self.rpm_b) / 2)

    def build_history(self):
        """
        Build historical data for the inverter.

        Updates the historical data for power, temperature, and RPM.
        """
        self.history[HISTORY_INVERTER_POWER].push(self._pack(self.power))
        self.history[HISTORY_INVERTER_TEMPERATURE].push(self._pack(self.temperature))
        self.history[HISTORY_INVERTER_RPM].push(self._pack(self.get_avg_rpm()))

    def get_ble_state(self):
        """
        Get the BLE representation of the inverter state.

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
    and managing the power state.

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
        TURN_OFF_VOLTAGE (float): Voltage threshold for turning off the inverter.
        TURN_OFF_MAX_CONFIRMATIONS (int): Maximum confirmations before turning off.
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

    TURN_OFF_VOLTAGE = 2.7
    TURN_OFF_MAX_CONFIRMATIONS = 3
    _turn_off_voltage = 2.7
    _turn_off_confirmations = 0

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
        turn_off_voltage=TURN_OFF_VOLTAGE,
        fan_tachometer_a_pin=None,
        fan_tachometer_b_pin=None,
        fan_tachometer_a_timer=None,
        fan_tachometer_b_timer=None,
    ):
        """
        Initialize the InverterController.

        Args:
            power_button_pin (int): Pin for the power button.
            power_button_timer (int): Timer for the power button.
            power_gate_pin (int): Pin for the power gate.
            uart (UART): UART instance for communication.
            baud_rate (int): Baud rate for UART communication.
            uart_tx_pin (int): UART TX pin number.
            uart_rx_pin (int): UART RX pin number.
            buzzer (BuzzerController): Buzzer controller for feedback.
            turn_off_voltage (float): Voltage threshold for turning off the inverter.
            fan_tachometer_a_pin (int): Pin for fan A tachometer.
            fan_tachometer_b_pin (int): Pin for fan B tachometer.
            fan_tachometer_a_timer (int): Timer for fan A tachometer.
            fan_tachometer_b_timer (int): Timer for fan B tachometer.
        """
        self._state = InverterState()
        self._turn_off_voltage = turn_off_voltage

        self._uart = uart
        self._tx_pin = uart_tx_pin
        self._rx_pin = uart_rx_pin
        self._baud_rate = baud_rate

        self._power_button = ButtonController(
            listen_pin=power_button_pin,
            on_change=self.on_power_trigger,
            buzzer=buzzer,
            trigger_timer=power_button_timer,
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

        logger.info(f"Initialized inverter turn off voltage: {turn_off_voltage}")

    def on_tachometer_a(self, rpm):
        """
        Handle RPM updates from fan A tachometer.

        Args:
            rpm (int): RPM value from fan A.
        """
        self._state.rpm_a = rpm
        logger.debug(f"INVERTER FAN A RPM: {rpm}")

    def on_tachometer_b(self, rpm):
        """
        Handle RPM updates from fan B tachometer.

        Args:
            rpm (int): RPM value from fan B.
        """
        self._state.rpm_b = rpm
        logger.debug(f"INVERTER FAN B RPM: {rpm}")

    def on_bms_state(self, bms_state):
        """
        Handle updates from the BMS state.

        Args:
            bms_state (BMSState): The current state of the BMS.
        """
        triggered = False
        for voltage in bms_state.cells:
            if voltage is None or voltage == 0:
                continue
            voltage /= 1000
            if voltage < self._turn_off_voltage:
                triggered = True
                break

        if triggered:
            self._turn_off_confirmations += 1
            if self._turn_off_confirmations >= self.TURN_OFF_MAX_CONFIRMATIONS:
                logger.info(f"Inverter reached min voltage threshold")
                self.off()
                self._turn_off_confirmations = 0
        else:
            self._turn_off_confirmations = 0

    def on(self):
        """
        Turn on the inverter.
        """
        self._bootstrapping = True
        self._uart.init(rx=self._rx_pin, tx=self._tx_pin, baud_rate=self._baud_rate)
        self._power_gate_pin.on()
        self._state.on()
        logger.info("Inverter is on")

    def off(self):
        """
        Turn off the inverter.
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
        """
        if self._state.active:
            self.off()
        else:
            self.on()

    async def run(self):
        """
        Run the inverter controller.

        This method continuously monitors the inverter state and updates it.
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

        Sends a status request command and parses the response.
        """
        data = self._uart.query(self.STATUS_REQUEST, delay=50)
        logger.debug("Inverter response", self.state.as_hex(data))
        self._state.parse_buffer(data)

    @property
    def state(self):
        """
        Get the current state of the inverter.

        Returns:
            InverterState: The current inverter state.
        """
        return self._state
