"""
PSU (Power Supply Unit) module.

This module provides the implementation of the `PSUState` and `PowerSupplyController`
classes, which manage the state, control logic, and hardware interaction for the PSU.
"""

import struct

import machine

from const import BLE_PSU_STATE_UUID
from const import (
    HISTORY_PSU_RPM,
    HISTORY_PSU_TEMPERATURE_1,
    HISTORY_PSU_TEMPERATURE_2,
    HISTORY_PSU_POWER_1,
    HISTORY_PSU_POWER_2,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
)
from drivers import BaseState
from drivers.button import ButtonController
from lib.history import HistoricalData
from lib.tachometer import Tachometer
from logging import logger


class PSUState(BaseState):
    """
    Represents the state of the Power Supply Unit (PSU).

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the PSU state.
        ERROR_PIN (int): Error code for pin-related issues.
        active (bool): Whether the PSU is active.
        current (int): Current channel (0-3).
        FRAME_SIZE (int): Size of the data frame.
        rpm (int): Fan RPM.
        power1 (int): Power output 1.
        power2 (int): Power output 2.
        ac (int): AC state.
        t1 (int): Temperature sensor 1.
        t2 (int): Temperature sensor 2.
        t3 (int): Temperature sensor 3.
        state (int): Current state of the PSU.
        unknown (int): Unknown state value.
        history (dict): Historical data for telemetry.
    """

    NAME = "PSU"
    BLE_STATE_UUID = BLE_PSU_STATE_UUID
    ERROR_PIN = 6

    # on/off
    active = False

    # current channel (0-3)
    current = 0

    FRAME_SIZE = 22

    # telemetry
    rpm = None
    power1 = None
    power2 = None
    ac = None
    t1 = None
    t2 = None
    t3 = None
    state = None
    unknown = None

    _power_crc = None
    _data_crc = None

    history = {
        HISTORY_PSU_RPM: HistoricalData(
            chart_type=HISTORY_PSU_RPM,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_PSU_POWER_1: HistoricalData(
            chart_type=HISTORY_PSU_POWER_1,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_PSU_POWER_2: HistoricalData(
            chart_type=HISTORY_PSU_POWER_2,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_PSU_TEMPERATURE_1: HistoricalData(
            chart_type=HISTORY_PSU_TEMPERATURE_1,
            data_type=DATA_TYPE_BYTE,
        ),
        HISTORY_PSU_TEMPERATURE_2: HistoricalData(
            chart_type=HISTORY_PSU_TEMPERATURE_2,
            data_type=DATA_TYPE_BYTE,
        ),
    }

    def clear(self):
        """
        Clears the PSU state.

        Resets all telemetry and state attributes to their default values.
        """
        self.rpm = None
        self.active = False
        self.power1 = None
        self.power2 = None
        self.ac = None
        self.t1 = None
        self.t2 = None
        self.t3 = None
        self.state = None
        self.external_errors = None
        self.notify()

    def get_avg_temperature(self):
        """
        Calculates the average temperature from the two temperature sensors.

        Returns:
            int: The average temperature, or None if one of the sensors is missing.
        """
        if self.t1 and self.t2:
            return int((self.t1 + self.t2) / 2)

    def get_ble_state(self):
        """
        Constructs the BLE state representation of the PSU.

        Returns:
            bytes: A packed representation of the PSU state for BLE communication.
        """
        t1 = self.get_avg_temperature()
        return struct.pack(
            ">HHHBBBBBBB",
            self._pack(self.rpm),
            self._pack(self.power1),
            self._pack(self.power2),
            self._pack(self.ac),
            self._pack(t1),
            self._pack(self.t3),
            self._pack(self.current_channel),
            self._pack_bool(self.active),
            self._pack(self.external_errors),
            self._pack(self.internal_errors),
        )

    def build_history(self):
        """
        Updates the historical telemetry data for the PSU.
        """
        t1 = self.get_avg_temperature()
        self.history[HISTORY_PSU_RPM].push(self._pack(self.rpm))
        self.history[HISTORY_PSU_POWER_1].push(self._pack(self.power1))
        self.history[HISTORY_PSU_POWER_2].push(self._pack(self.power2))
        self.history[HISTORY_PSU_TEMPERATURE_1].push(self._pack(t1))
        self.history[HISTORY_PSU_TEMPERATURE_2].push(self._pack(self.t3))

    def crc(self, data):
        """
        Calculates the CRC checksum for the given data.

        Args:
            data (bytes): The data to calculate the checksum for.

        Returns:
            int: The CRC checksum.
        """
        return sum(b for b in data) % 0x100

    def parse(self, frame):
        """
        Parses a data frame and updates the PSU state.

        Args:
            frame (bytes): The data frame to parse.
        """
        offset = 0
        header = struct.unpack_from(">BB", frame)
        if header != (0x49, 0x34):
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error("PSU bad header")
            return
        offset += 2

        power1 = struct.unpack_from("<H", frame, offset)[0]
        offset += 2

        power2 = struct.unpack_from("<H", frame, offset)[0]
        offset += 2

        actual_power_crc = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        power_crc = self.crc(frame[2:6])
        power_crc_diff = abs(power_crc - actual_power_crc)

        if power_crc != actual_power_crc:
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error(
                "PSU bad power CRC", power_crc, actual_power_crc, power_crc_diff
            )
            return

        data_header = struct.unpack_from(">B", frame, offset)
        offset += 1

        state = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        unknown = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        ac = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        t1 = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        t2 = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        t3 = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        reserved = struct.unpack_from(">BBBBBBB", frame, offset)
        offset += 7

        actual_data_crc = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        data_crc = self.crc(frame[9:21])
        crc_diff = abs(data_crc - actual_data_crc)

        if data_crc != actual_data_crc:
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error("PSU bad CRC", data_crc, actual_data_crc, crc_diff)
            return

        self.reset_error(self.ERROR_BAD_RESPONSE)
        self.power1 = power1
        self.power2 = power2
        self.ac = ac
        self.state = state
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        logger.info(
            f"PSU AC: {self.ac} t1: {self.t1} t2: {self.t2} t3: {self.t3} p1: {self.power1} p2: {self.power2}"
        )

        return True

    def parse_buffer(self, buffer):
        """
        Parses a buffer of data and extracts valid frames.

        Args:
            buffer (bytes): The buffer containing data frames.
        """

        if buffer is None:
            return

        frame_start = buffer.find(b"\x49\x34")
        if frame_start < 0:
            return

        # incomplete buffer
        if (frame_start + self.FRAME_SIZE) > len(buffer):
            return

        frame = buffer[frame_start : frame_start + self.FRAME_SIZE]
        logger.debug("PSU frame", self.as_hex(frame))

        try:
            succeeded = self.parse(frame)
            if not succeeded:
                return
        except Exception as e:
            logger.critical(e)

        return True


class PowerSupplyController:
    """
    Controller for managing the Power Supply Unit (PSU).

    This class handles monitoring, controlling, and interacting with the PSU hardware.

    Attributes:
        POWER_BUTTON_PIN (int): Pin for the power button.
        POWER_GATE_PIN (int): Pin for controlling the PSU power gate.
        CURRENT_A_PIN (int): Pin A for current control.
        CURRENT_B_PIN (int): Pin B for current control.
        TURN_OFF_VOLTAGE (float): Voltage threshold for turning off the PSU.
        TURN_OFF_MAX_CONFIRMATIONS (int): Maximum confirmations for turn-off voltage.
        CURRENT_CHANNEL (int): Default current channel.
    """

    # A pin to listen to
    POWER_BUTTON_PIN = None

    # A pin to turn on/off PSU via MOSFET
    POWER_GATE_PIN = None

    # Current control pins
    # Two pins define 4 channels ranging from 0 (lowest) current to 3.
    CURRENT_A_PIN = None
    CURRENT_B_PIN = None

    _power_gate_pin = None

    # PSU button controller
    _power_button = None

    # current pin instances
    _current_a_pin = None
    _current_b_pin = None

    # fan tachometer
    _tachometer = None

    _state = None

    _error = 0

    CURRENT_CHANNEL = 0
    TURN_OFF_VOLTAGE = 3.5
    TURN_OFF_MAX_CONFIRMATIONS = 3

    _turn_off_voltage = 3.5
    _turn_off_confirmations = 0

    _buffer = None

    def __init__(
        self,
        power_button_pin=POWER_BUTTON_PIN,
        power_button_timer=None,
        power_gate_pin=POWER_GATE_PIN,
        current_a_pin=CURRENT_A_PIN,
        current_b_pin=CURRENT_B_PIN,
        fan_tachometer_pin=None,
        fan_tachometer_timer=-1,
        uart=None,
        uart_rx_pin=None,
        buzzer=None,
        turn_off_voltage=TURN_OFF_VOLTAGE,
        current_channel=CURRENT_CHANNEL,
    ):
        """
        Initializes the PowerSupplyController.

        Args:
            power_button_pin (int): Pin for the power button.
            power_button_timer (int): Timer for the power button.
            power_gate_pin (int): Pin for the power gate.
            current_a_pin (int): Pin A for current control.
            current_b_pin (int): Pin B for current control.
            fan_tachometer_pin (int): Pin for the fan tachometer.
            fan_tachometer_timer (int): Timer for the fan tachometer.
            uart (UART): UART interface for communication.
            uart_rx_pin (int): Pin for UART RX.
            buzzer (Buzzer): Buzzer instance for notifications.
            turn_off_voltage (float): Voltage threshold for turning off the PSU.
            current_channel (int): Default current channel.
        """
        self._state = PSUState()
        self._uart = uart
        self._uart_rx_pin = uart_rx_pin
        self._turn_off_voltage = turn_off_voltage

        if fan_tachometer_pin:
            self._tachometer = Tachometer(
                pin=machine.Pin(fan_tachometer_pin, machine.Pin.IN),
                period_ms=250,
                done_callback=self.on_tachometer,
                timer_id=fan_tachometer_timer,
            )

        try:
            self._power_button = ButtonController(
                listen_pin=power_button_pin,
                on_change=self.on_power_trigger,
                buzzer=buzzer,
                trigger_timer=power_button_timer,
            )
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.error("PSU button pin failed")

        try:
            self._power_gate_pin = machine.Pin(
                power_gate_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN
            )
            self._power_gate_pin.off()
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.error("PSU gate pin failed")

        try:
            self._current_a_pin = machine.Pin(
                current_a_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN
            )
            self._current_b_pin = machine.Pin(
                current_b_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN
            )
            self.set_current(current_channel)
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.critical(e)

        logger.info("Initialized power supply controller")

    def on_tachometer(self, rpm):
        """
        Callback for tachometer updates.

        Args:
            rpm (int): The measured RPM of the fan.
        """
        self._state.rpm = rpm
        logger.debug(f"PSU FAN RPM: {rpm}")

    def on_bms_state(self, bms_state):
        """
        Handles updates from the Battery Management System (BMS).

        Args:
            bms_state (BMSState): The current state of the BMS.
        """
        triggered = False
        for voltage in bms_state.cells:
            if voltage is None:
                continue
            voltage /= 1000
            if voltage > self._turn_off_voltage:
                triggered = True
                break

        if triggered:
            self._turn_off_confirmations += 1
            if self._turn_off_confirmations >= self.TURN_OFF_MAX_CONFIRMATIONS:
                logger.info("PSU reached max voltage threshold")
                self.off()
        else:
            self._turn_off_confirmations = 0

    def set_current(self, channel):
        """
        Sets the current channel for the PSU.

        Args:
            channel (int): The current channel to set (0-3).
        """
        self._state.current_channel = channel
        channel_a = channel & 0x01
        channel_b = (channel >> 1) & 0x01
        self._current_a_pin.value(channel_a)  # LSB (A)
        self._current_b_pin.value(channel_b)  # MSB (B)
        logger.debug(
            f"Set PSU current channel: {channel} A: {channel_a} B: {channel_b} "
        )

    def on(self):
        """
        Turns on the PSU.
        """
        logger.info("Turning on PSU")
        self._uart.init(rx=self._uart_rx_pin, baud_rate=4800)
        self._power_gate_pin.on()
        self._state.on()
        logger.info("PSU is on")

    def off(self):
        """
        Turns off the PSU.
        """
        logger.info("Turning off PSU")
        self._power_gate_pin.off()
        self._state.off()
        self._state.clear()
        logger.info("PSU is off")

    def on_power_trigger(self):
        """
        Handles the power button trigger event.
        """
        logger.info("PSU power trigger")
        if self._state.active:
            self.off()
        else:
            self.on()

    async def run(self):
        """
        Main loop for the PSU controller.

        Continuously monitors and updates the PSU state.
        """
        logger.info("Running PSU...")
        while True:
            if self.state.active:
                self._state.parse_buffer(self._uart.sample(timeout=500))
                self._tachometer.measure()
                self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        """
        Gets the current state of the PSU.

        Returns:
            PSUState: The current PSU state.
        """
        return self._state
