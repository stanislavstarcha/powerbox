"""
PSU (Power Supply Unit) module.

This module provides the implementation of the `PSUState` and `PowerSupplyController`
classes, which manage the state, control logic, and hardware interaction for the PSU.
"""

import struct

import machine

from const import BLE_PSU_STATE_UUID
from const import (
    PROFILE_KEY_PSU_TURBO,
    HISTORY_PSU_RPM,
    HISTORY_PSU_TEMPERATURE_1,
    HISTORY_PSU_TEMPERATURE_2,
    HISTORY_PSU_POWER_1,
    HISTORY_PSU_POWER_2,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
    PSU_CURRENT_100,
    PSU_CURRENT_75,
    PSU_REDUCE_CURRENT_VOLTAGE,
)
from drivers import BaseState
from drivers.button import ButtonController
from lib.history import HistoricalData
from lib.tachometer import Tachometer
from logging import logger


class PSUState(BaseState):
    """
    Represents the state of the Power Supply Unit (PSU).

    This class manages the telemetry data, state information, and historical data
    for the PSU. It handles data parsing, state transitions, and BLE communication.

    The state tracks:
    - Power status (active/inactive)
    - Current channel selection
    - Fan RPM
    - Power output levels
    - Temperature readings
    - Error conditions

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

    # turbo mode
    turbo_mode = False

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
        Reset the PSU state to default values.

        Clears all telemetry data and state attributes, then notifies
        any observers of the state change.
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
        Calculate the average temperature from the two primary temperature sensors.

        Returns:
            int: The average temperature in the same units as the sensors,
                 or None if either sensor is missing.
        """
        if self.t1 and self.t2:
            return int((self.t1 + self.t2) / 2)

    def get_ble_state(self):
        """
        Construct the BLE state representation of the PSU.

        Packs the current state data into a binary format for BLE transmission.

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
            self._pack_bool(self.turbo_mode),
            self._pack_bool(self.active),
            self._pack(self.external_errors),
            self._pack(self.internal_errors),
        )

    def build_history(self):
        """
        Update the historical telemetry data for the PSU.

        Pushes the current telemetry values to their respective historical data
        collections for trend analysis and visualization.
        """
        t1 = self.get_avg_temperature()
        self.history[HISTORY_PSU_RPM].push(self._pack(self.rpm))
        self.history[HISTORY_PSU_POWER_1].push(self._pack(self.power1))
        self.history[HISTORY_PSU_POWER_2].push(self._pack(self.power2))
        self.history[HISTORY_PSU_TEMPERATURE_1].push(self._pack(t1))
        self.history[HISTORY_PSU_TEMPERATURE_2].push(self._pack(self.t3))

    def crc(self, data):
        """
        Calculate the CRC checksum for the given data.

        Args:
            data (bytes): The data to calculate the checksum for.

        Returns:
            int: The CRC checksum value (0-255).
        """
        return sum(b for b in data) % 0x100

    def parse(self, frame):
        """
        Parse a data frame and update the PSU state.

        Extracts telemetry data from a binary frame, validates checksums,
        and updates the state attributes.

        Args:
            frame (bytes): The data frame to parse.

        Returns:
            bool: True if parsing was successful, False otherwise.
        """
        if not frame or len(frame) < self.FRAME_SIZE:
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error(
                f"PSU frame too short: {len(frame) if frame else 0} < {self.FRAME_SIZE}"
            )
            return False

        offset = 0

        # Validate header
        try:
            header = struct.unpack_from(">BB", frame)
            if header != (0x49, 0x34):
                self.set_error(self.ERROR_BAD_RESPONSE)
                logger.error(f"PSU bad header: {header}")
                return False
            offset += 2
        except struct.error as e:
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error(f"PSU header parse error: {e}")
            return False

        # Parse power values
        try:
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
                    f"PSU bad power CRC: calculated={power_crc}, received={actual_power_crc}, diff={power_crc_diff}"
                )
                return False
        except struct.error as e:
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error(f"PSU power data parse error: {e}")
            return False

        # Parse data header
        try:
            data_header = struct.unpack_from(">B", frame, offset)
            offset += 1
        except struct.error as e:
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error(f"PSU data header parse error: {e}")
            return False

        # Parse state and telemetry data
        try:
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
                logger.error(
                    f"PSU bad data CRC: calculated={data_crc}, received={actual_data_crc}, diff={crc_diff}"
                )
                return False
        except struct.error as e:
            self.set_error(self.ERROR_BAD_RESPONSE)
            logger.error(f"PSU telemetry data parse error: {e}")
            return False

        # Update state with parsed data
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
        Parse a buffer of data and extract valid frames.

        Searches for a valid frame in the buffer, extracts it, and parses it.
        Handles incomplete buffers and invalid frames gracefully.

        Args:
            buffer (bytes): The buffer containing data frames.

        Returns:
            bool: True if a valid frame was parsed, False otherwise.
        """
        if buffer is None:
            logger.debug("PSU parse_buffer: received None buffer")
            return False

        # Find the start of a frame (header bytes)
        frame_start = buffer.find(b"\x49\x34")
        if frame_start < 0:
            logger.debug(
                f"PSU parse_buffer: no valid frame header found (size: {len(buffer)}) {self.as_hex(buffer)}"
            )
            return False

        # Check if we have a complete frame
        if (frame_start + self.FRAME_SIZE) > len(buffer):
            logger.debug(
                f"PSU parse_buffer: incomplete frame at position {frame_start}"
            )
            return False

        # Extract the frame
        frame = buffer[frame_start : frame_start + self.FRAME_SIZE]
        logger.debug(f"PSU frame at position {frame_start}: {self.as_hex(frame)}")

        # Parse the frame
        try:
            succeeded = self.parse(frame)
            if not succeeded:
                logger.debug("PSU parse_buffer: frame parsing failed")
                return False
            return True
        except Exception as e:
            logger.critical(f"PSU parse_buffer: unexpected error: {e}")
            return False


class PowerSupplyController:
    """
    Controller for managing the Power Supply Unit (PSU).

    This class provides a comprehensive interface for controlling and monitoring a power supply unit.
    It handles hardware interactions, state management, and telemetry collection for the PSU.

    The controller manages:
    - Power state (on/off) via a MOSFET gate
    - Current channel selection (0-3) via two control pins
    - Fan speed monitoring via tachometer
    - UART communication for telemetry data
    - Battery voltage monitoring for safety shutdown

    Attributes:
        POWER_BUTTON_PIN (int): Pin for the power button.
        POWER_GATE_PIN (int): Pin for controlling the PSU power gate.
        CURRENT_A_PIN (int): Pin A for current control.
        CURRENT_B_PIN (int): Pin B for current control.
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
        profile=None,
    ):
        """
        Initialize the Power Supply Unit controller.

        Sets up all hardware interfaces and initializes the controller state.
        Configures pins for power control, current selection, and monitoring.

        Args:
            power_button_pin (int): GPIO pin for the power button input.
            power_button_timer (int, optional): Timer ID for button debouncing.
            power_gate_pin (int): GPIO pin for controlling the PSU power MOSFET.
            current_a_pin (int): GPIO pin A for current channel selection (LSB).
            current_b_pin (int): GPIO pin B for current channel selection (MSB).
            fan_tachometer_pin (int, optional): GPIO pin for fan tachometer input.
            fan_tachometer_timer (int, optional): Timer ID for tachometer measurements.
            uart (UART, optional): UART interface for PSU communication.
            uart_rx_pin (int, optional): GPIO pin for UART RX.
            buzzer (Buzzer, optional): Buzzer instance for audio feedback.
            profile (object): Profile storage.

        Raises:
            Exception: If pin initialization fails.
        """
        # Initialize state and basic attributes
        self._state = PSUState()
        self._uart = uart
        self._uart_rx_pin = uart_rx_pin
        self._buffer = None
        self._profile = profile

        self._state.turbo_mode = self._profile.get(
            PROFILE_KEY_PSU_TURBO,
            False,
        )

        # Initialize hardware components
        self._uart.init(rx=self._uart_rx_pin, baud_rate=4800)
        self._initialize_tachometer(fan_tachometer_pin, fan_tachometer_timer)
        self._initialize_power_button(power_button_pin, power_button_timer, buzzer)
        self._initialize_power_gate(power_gate_pin)
        self._initialize_current_control(current_a_pin, current_b_pin)

        logger.info("Initialized power supply controller")

    def _initialize_tachometer(self, pin, timer_id):
        """Initialize the fan tachometer if a pin is provided."""
        if pin:
            self._tachometer = Tachometer(
                pin=machine.Pin(pin, machine.Pin.IN),
                period_ms=250,
                done_callback=self.on_tachometer,
                timer_id=timer_id,
            )

    def _initialize_power_button(self, pin, timer_id, buzzer):
        """Initialize the power button controller."""
        logger.info(f"Initializing PSU power button on pin {pin} timer {timer_id}")
        try:
            self._power_button = ButtonController(
                listen_pin=pin,
                on_long_press=self.on_power_trigger,
                on_short_press=self.toggle_turbo_mode,
                buzzer=buzzer,
                trigger_timer=timer_id,
            )
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.error(f"PSU button pin failed: {e}")

    def _initialize_power_gate(self, pin):
        """Initialize the power gate MOSFET control pin."""
        try:
            self._power_gate_pin = machine.Pin(
                pin, machine.Pin.OUT, machine.Pin.PULL_DOWN
            )
            self._power_gate_pin.off()  # Ensure PSU starts in off state
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.error(f"PSU gate pin failed: {e}")

    def _initialize_current_control(self, pin_a, pin_b):
        """Initialize the current control pins and set an initial channel."""
        try:
            self._current_a_pin = machine.Pin(
                pin_a, machine.Pin.OUT, machine.Pin.PULL_DOWN, value=0
            )
            self._current_b_pin = machine.Pin(
                pin_b, machine.Pin.OUT, machine.Pin.PULL_DOWN, value=0
            )
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.critical(f"PSU current control pins failed: {e}")

    def on_tachometer(self, rpm):
        """
        Process tachometer measurements for fan speed monitoring.

        Updates the state with the current fan RPM and logs the measurement.

        Args:
            rpm (int): The measured RPM of the fan.
        """
        self._state.rpm = rpm
        logger.debug(f"PSU FAN RPM: {rpm}")

    def toggle_turbo_mode(self):
        self.set_turbo_mode(not self._state.turbo_mode)

    def set_turbo_mode(self, mode):
        self._state.turbo_mode = mode
        self.set_current(self.get_max_current())
        self._profile.set(PROFILE_KEY_PSU_TURBO, self._state.turbo_mode, as_bytes=False)
        self.state.notify()

    def get_max_current(self):
        return PSU_CURRENT_100 if self._state.turbo_mode else PSU_CURRENT_75

    def set_current(self, channel):
        """
        Set the current channel for the PSU.

        Configures the current control pins to select the desired current channel.
        The channel is encoded using two pins: A (LSB) and B (MSB).

        Args:
            channel (int): The current channel to set (0-3).
            config (bool, optional): Whether to save the channel to persistent storage. Defaults to True.
        """
        self._state.current_channel = channel
        channel_a = channel & 0x01
        channel_b = (channel >> 1) & 0x01
        self._current_a_pin.value(channel_a)  # LSB (A)
        self._current_b_pin.value(channel_b)  # MSB (B)
        logger.info(
            f"Set PSU current channel: {channel} A: {channel_a} B: {channel_b} "
        )

    def on(self):
        """
        Turn on the PSU.

        Initializes the UART interface, activates the power gate MOSFET,
        and updates the state to reflect the active status.
        """
        logger.info("Turning on PSU")
        self.set_current(self.get_max_current())
        self._power_gate_pin.on()
        self._state.on()
        logger.info("PSU is on")

    def off(self):
        """
        Turn off the PSU.

        Deactivates the power gate MOSFET, clears the state data,
        and updates the state to reflect the inactive status.
        """
        logger.info("Turning off PSU")
        self._power_gate_pin.off()
        self._state.off()
        self._state.clear()
        logger.info("PSU is off")

    def on_power_trigger(self):
        """
        Handle the power button trigger event.

        Toggles the PSU state between on and off based on the current state.
        """
        logger.info("PSU power trigger")
        if self._state.active:
            self.off()
        else:
            self.on()

    def check_threshold(self, bms_state):
        max_cell_voltage = 0
        for cell_index, voltage in enumerate(bms_state.cells):
            if voltage > max_cell_voltage:
                max_cell_voltage = voltage

        max_cell_voltage = max_cell_voltage / 1000

        if (
            max_cell_voltage >= PSU_REDUCE_CURRENT_VOLTAGE
            and self._state.current_channel > 0
        ):
            logger.info(
                f"PSU battery voltage too high {max_cell_voltage}, reducing current to",
                self._state.current_channel - 1,
            )

            self.set_current(self._state.current_channel - 1)

    async def run(self):
        """
        Main control loop for the PSU controller.

        Continuously monitors the PSU state and updates telemetry data.
        When active, it samples UART data, measures fan speed, and updates
        the state snapshot.
        """
        logger.info("Running PSU...")
        while True:
            if self.state.active:
                self._state.parse_buffer(self._uart.sample(timeout=500))
                if self._tachometer:
                    self._tachometer.measure()
                self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        """
        Get the current state of the PSU.

        Returns:
            PSUState: The current PSU state object.
        """
        return self._state
