"""
BMS (Battery Management System) module.

This module provides a comprehensive implementation for managing battery systems, including
error handling, state tracking, and control functionality. It consists of three main classes:

1. BMSErrors: Defines error codes and their meanings for battery management issues
2. BMSState: Tracks and manages the current state of the battery system
3. BMSController: Handles communication with the physical BMS hardware via UART

The module supports monitoring battery parameters such as cell voltages, temperature,
state of charge, and current, while also providing control functions for charging and
discharging operations.
"""

import struct

import math

import const
from drivers import BaseState, UART
from lib.history import HistoricalData
from logging import logger

from const import (
    HISTORY_BMS_SOC,
    HISTORY_BMS_CURRENT,
    HISTORY_BMS_CELL1_VOLTAGE,
    HISTORY_BMS_CELL2_VOLTAGE,
    HISTORY_BMS_CELL3_VOLTAGE,
    HISTORY_BMS_CELL4_VOLTAGE,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
    BLE_BMS_STATE_UUID,
    PROFILE_KEY_MCU_POWER,
)


class BMSErrors:
    """
    Represents the error codes for the Battery Management System.

    This class defines a comprehensive set of error codes that can be detected by the BMS.
    Each error is represented by a specific bit in a two-byte value, allowing multiple
    errors to be reported simultaneously.

    Attributes:
        ERROR_LOW_CAPACITY (int): Low capacity error (bit 0).
        ERROR_MOS_OVER_TEMPERATURE (int): MOS over-temperature error (bit 1).
        ERROR_CHARGE_OVER_VOLTAGE (int): Charge over-voltage error (bit 2).
        ERROR_DISCHARGE_UNDER_VOLTAGE (int): Discharge under-voltage error (bit 3).
        ERROR_BATTERY_OVER_TEMPERATURE (int): Battery over-temperature error (bit 4).
        ERROR_CHARGE_OVER_CURRENT (int): Charge over-current error (bit 5).
        ERROR_DISCHARGE_OVER_CURRENT (int): Discharge over-current error (bit 6).
        ERROR_CORE_DIFFERENTIAL_PRESSURE (int): Core differential pressure error (bit 7).
        ERROR_BATTERY_BOX_OVER_TEMPERATURE (int): Over-temperature alarm in the battery box (bit 8).
        ERROR_BATTERY_LOW_TEMPERATURE (int): Battery low-temperature error (bit 9).
        ERROR_UNIT_OVER_VOLTAGE (int): Unit over-voltage error (bit 10).
        ERROR_UNIT_UNDER_VOLTAGE (int): Unit under-voltage error (bit 11).
        ERROR_309_A_PROTECTION (int): 309_A protection error (bit 12).
        ERROR_309_B_PROTECTION (int): 309_B protection error (bit 13).
    """

    ERROR_LOW_CAPACITY = 0x0001  # Bit 0
    ERROR_MOS_OVER_TEMPERATURE = 0x0002  # Bit 1
    ERROR_CHARGE_OVER_VOLTAGE = 0x0004  # Bit 2
    ERROR_DISCHARGE_UNDER_VOLTAGE = 0x0008  # Bit 3
    ERROR_BATTERY_OVER_TEMPERATURE = 0x0010  # Bit 4
    ERROR_CHARGE_OVER_CURRENT = 0x0020  # Bit 5
    ERROR_DISCHARGE_OVER_CURRENT = 0x0040  # Bit 6
    ERROR_CORE_DIFFERENTIAL_PRESSURE = 0x0080  # Bit 7
    ERROR_BATTERY_BOX_OVER_TEMPERATURE = 0x0100  # Bit 8
    ERROR_BATTERY_LOW_TEMPERATURE = 0x0200  # Bit 9
    ERROR_UNIT_OVER_VOLTAGE = 0x0400  # Bit 10
    ERROR_UNIT_UNDER_VOLTAGE = 0x0800  # Bit 11
    ERROR_309_A_PROTECTION = 0x1000  # Bit 12
    ERROR_309_B_PROTECTION = 0x2000  # Bit 13


class BMSState(BaseState):
    """
    Represents the state of the Battery Management System (BMS).

    This class tracks all aspects of the battery system's current state, including
    cell voltages, temperatures, charge levels, and protection parameters. It also
    maintains historical data for key metrics and provides methods for parsing
    responses from the BMS hardware.

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the BMS state.
        cells (list): Per-cell voltage values in millivolts.
        mos_temperature (int): MOSFET temperature in tenths of a degree Celsius.
        sensor1_temperature (int): Temperature from sensor 1 in tenths of a degree Celsius.
        sensor2_temperature (int): Temperature from sensor 2 in tenths of a degree Celsius.
        voltage (int): Total battery voltage in millivolts.
        current (int): Current flowing through the battery in milliamperes.
        soc (int): State of charge as a percentage (0-100).
        charging_allowed (bool): Whether charging is currently allowed.
        discharging_allowed (bool): Whether discharging is currently allowed.
        temperature_sensors (int): Number of temperature sensors.
        cycles (int): Number of charge/discharge cycles.
        cycle_capacity (int): Capacity in ampere-hours.
        battery_strings (int): Number of battery strings.
        state (int): Current state flags.
        total_over_voltage_protection (int): Total over-voltage protection threshold.
        total_under_voltage_protection (int): Total under-voltage protection threshold.
        cell_over_voltage_protection (int): Cell over-voltage protection threshold.
        cell_over_voltage_recovery (int): Cell over-voltage recovery threshold.
        cell_over_voltage_delay (int): Cell over-voltage delay in milliseconds.
        cell_under_voltage_protection (int): Cell under-voltage protection threshold.
        cell_under_voltage_recovery (int): Cell under-voltage recovery threshold.
        cell_under_voltage_delay (int): Cell under-voltage delay in milliseconds.
        cell_pressure_difference (int): Cell pressure difference threshold.
        discharge_over_current (int): Discharge over-current threshold.
        discharge_over_current_delay (int): Discharge over-current delay in milliseconds.
        charge_over_current (int): Charge over-current threshold.
        charge_over_current_delay (int): Charge over-current delay in milliseconds.
        balancing_voltage (int): Balancing voltage threshold.
        balancing_pressure_difference (int): Balancing pressure difference threshold.
        history (dict): Historical data for various metrics.
    """

    NAME = "BMS"
    BLE_STATE_UUID = BLE_BMS_STATE_UUID

    ERROR_NO_MODIFY_RESPONSE = 2

    # Self-consumption power
    MCU_POWER = 1.5
    BMS_POWER = 0.9
    USB_POWER = 0.17
    mcu_consumed = 0

    # per cell voltage
    cells = [None, None, None, None]

    mos_temperature = None
    sensor1_temperature = None
    sensor2_temperature = None

    voltage = None
    current = None
    soc = None
    soc_drift = None

    temperature_sensors = None
    cycles = None
    cycle_capacity = None
    battery_strings = None

    state = None
    charging_allowed = None
    discharging_allowed = None

    total_over_voltage_protection = None
    total_under_voltage_protection = None

    cell_over_voltage_protection = None
    cell_over_voltage_recovery = None
    cell_over_voltage_delay = None
    cell_under_voltage_protection = None
    cell_under_voltage_recovery = None
    cell_under_voltage_delay = None
    cell_pressure_difference = None

    discharge_over_current = None
    discharge_over_current_delay = None

    charge_over_current = None
    charge_over_current_delay = None

    balancing_voltage = None
    balancing_pressure_difference = None

    battery_capacity = None

    history = {
        HISTORY_BMS_SOC: HistoricalData(
            chart_type=HISTORY_BMS_SOC,
            data_type=DATA_TYPE_BYTE,
        ),
        HISTORY_BMS_CURRENT: HistoricalData(
            chart_type=HISTORY_BMS_CURRENT,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_BMS_CELL1_VOLTAGE: HistoricalData(
            chart_type=HISTORY_BMS_CELL1_VOLTAGE,
            data_type=DATA_TYPE_BYTE,
        ),
        HISTORY_BMS_CELL2_VOLTAGE: HistoricalData(
            chart_type=HISTORY_BMS_CELL2_VOLTAGE,
            data_type=DATA_TYPE_BYTE,
        ),
        HISTORY_BMS_CELL3_VOLTAGE: HistoricalData(
            chart_type=HISTORY_BMS_CELL3_VOLTAGE,
            data_type=DATA_TYPE_BYTE,
        ),
        HISTORY_BMS_CELL4_VOLTAGE: HistoricalData(
            chart_type=HISTORY_BMS_CELL4_VOLTAGE,
            data_type=DATA_TYPE_BYTE,
        ),
    }

    def clear(self):
        """
        Clear the BMS state by resetting all attributes to their default values.

        This method is typically called when a communication error occurs or when
        initializing a new state. It resets all state variables to None or their
        appropriate default values.
        """
        self.cells = [None, None, None, None]

        self.mos_temperature = None
        self.sensor1_temperature = None
        self.sensor2_temperature = None

        self.voltage = None
        self.current = None
        self.soc = None
        self.soc_drift = None

        self.temperature_sensors = None
        self.cycles = None
        self.cycle_capacity = None
        self.battery_strings = None

        self.state = 0
        self.charging_allowed = None
        self.discharging_allowed = None

        self.total_over_voltage_protection = None
        self.total_under_voltage_protection = None

        self.cell_over_voltage_protection = None
        self.cell_over_voltage_recovery = None
        self.cell_over_voltage_delay = None
        self.cell_under_voltage_protection = None
        self.cell_under_voltage_recovery = None
        self.cell_under_voltage_delay = None
        self.cell_pressure_difference = None

        self.discharge_over_current = None
        self.discharge_over_current_delay = None

        self.charge_over_current = None
        self.charge_over_current_delay = None

        self.balancing_voltage = None
        self.balancing_pressure_difference = None

        self.battery_capacity = None

    def parse(self, response):
        """
        Parse a response from the BMS hardware.

        This method decodes the binary response from the BMS hardware, extracting
        all relevant state information including cell voltages, temperatures,
        current, voltage, and protection parameters.

        Args:
            response (bytes): The binary response data to parse from the BMS hardware.

        Raises:
            AssertionError: If the response format is invalid or descriptors don't match.
        """
        _, size = struct.unpack_from(">HH", response)

        offset = response.find(b"\x79")
        descriptor, cell_charge_size = struct.unpack_from(">BB", response, offset)
        assert descriptor == 0x79
        offset += 2

        for i in range(cell_charge_size // 3):
            cell_index, cell_charge = struct.unpack_from(
                ">BH", response, offset + i * 3
            )
            self.cells[i] = cell_charge
        offset += cell_charge_size

        descriptor, self.mos_temperature = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x80
        offset += 3

        descriptor, self.sensor1_temperature = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x81
        offset += 3

        descriptor, self.sensor2_temperature = struct.unpack_from(
            ">Bh", response, offset
        )
        assert descriptor == 0x82
        offset += 3

        descriptor, self.voltage = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x83
        offset += 3

        descriptor, self.current = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x84
        offset += 3

        descriptor, self.soc = struct.unpack_from(">BB", response, offset)
        assert descriptor == 0x85
        offset += 2

        descriptor, self.temperature_sensors = struct.unpack_from(
            ">BB", response, offset
        )
        assert descriptor == 0x86
        offset += 2

        descriptor, self.cycles = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x87
        offset += 3

        descriptor, self.cycle_capacity = struct.unpack_from(">BI", response, offset)
        assert descriptor == 0x89
        offset += 5

        descriptor, self.battery_strings = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x8A
        offset += 3

        descriptor, self.external_errors = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x8B
        offset += 3

        descriptor, self.state = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x8C
        self.charging_allowed = bool(self.state & 0x01)
        self.discharging_allowed = bool(self.state & 0x02)
        offset += 3

        descriptor, self.total_over_voltage_protection = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x8E
        offset += 3

        descriptor, self.total_under_voltage_protection = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x8F
        offset += 3

        descriptor, self.cell_over_voltage_protection = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x90
        offset += 3

        descriptor, self.cell_over_voltage_recovery = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x91
        offset += 3

        descriptor, self.cell_over_voltage_delay = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x92
        offset += 3

        descriptor, self.cell_under_voltage_protection = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x93
        offset += 3

        descriptor, self.cell_under_voltage_recovery = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x94
        offset += 3

        descriptor, self.cell_under_voltage_delay = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x95
        offset += 3

        descriptor, self.cell_pressure_difference = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x96
        offset += 3

        descriptor, self.discharge_over_current = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x97
        offset += 3

        descriptor, self.discharge_over_current_delay = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x98
        offset += 3

        descriptor, self.charge_over_current = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x99
        offset += 3

        descriptor, self.charge_over_current_delay = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x9A
        offset += 3

        descriptor, self.balancing_voltage = struct.unpack_from(">BH", response, offset)
        assert descriptor == 0x9B
        offset += 3

        descriptor, self.balancing_pressure_difference = struct.unpack_from(
            ">BH", response, offset
        )
        assert descriptor == 0x9C
        offset += 40

        # ... skip temperature sensors ...

        descriptor, self.battery_capacity = struct.unpack_from(">BI", response, offset)
        assert descriptor == 0xAA
        offset += 4

        if self.external_errors:
            self.set_error(self.ERROR_EXTERNAL)
        else:
            self.reset_error(self.ERROR_EXTERNAL)

    def build_history(self):
        """
        Build historical data for the BMS metrics.

        Updates the historical data for key metrics including state of charge (SOC),
        current, and per-cell voltages. This data is used for tracking battery
        performance over time and can be used for analysis and diagnostics.
        """
        self.history[HISTORY_BMS_SOC].push(self._pack(self.get_soc()))
        self.history[HISTORY_BMS_CURRENT].push(self._pack(self.current))

        self.history[HISTORY_BMS_CELL1_VOLTAGE].push(
            self._pack(self._pack_cell_voltage(self.cells[0]))
        )
        self.history[HISTORY_BMS_CELL2_VOLTAGE].push(
            self._pack(self._pack_cell_voltage(self.cells[1]))
        )
        self.history[HISTORY_BMS_CELL3_VOLTAGE].push(
            self._pack(self._pack_cell_voltage(self.cells[2]))
        )
        self.history[HISTORY_BMS_CELL4_VOLTAGE].push(
            self._pack(self._pack_cell_voltage(self.cells[3]))
        )

    @staticmethod
    def crc(frame):
        """
        Calculate the CRC (Cyclic Redundancy Check) for a given frame.

        This method computes a simple checksum by summing all bytes in the frame
        and returning the high and low bytes of the result.

        Args:
            frame (bytes): The binary frame to calculate the CRC for.

        Returns:
            list: A two-element list containing the high and low bytes of the CRC.
        """
        result = 0
        for b in frame:
            result += b
        return [(result >> 8) & 0xFF, result & 0xFF]

    def get_ble_state(self):
        """
        Get the BLE (Bluetooth Low Energy) representation of the BMS state.

        This method packs the current BMS state into a binary format suitable
        for transmission over BLE, including voltage, current, SOC, charging
        status, temperatures, and cell voltages.

        Returns:
            bytes: The packed BLE state data of the BMS.
        """
        return struct.pack(
            ">HHHBBBBBBBBBBHB",
            self._pack_voltage(self.voltage),
            self._pack(self.current),
            self._pack_voltage(self.mcu_consumed),
            self._pack(self.get_soc()),
            self._pack_bool(self.charging_allowed),
            self._pack_bool(self.discharging_allowed),
            self._pack_bms_temperature(self.mos_temperature),
            self._pack_bms_temperature(self.sensor1_temperature),
            self._pack_bms_temperature(self.sensor2_temperature),
            self._pack_cell_voltage(self.cells[0]),
            self._pack_cell_voltage(self.cells[1]),
            self._pack_cell_voltage(self.cells[2]),
            self._pack_cell_voltage(self.cells[3]),
            self._pack(self.external_errors),
            self._pack(self.internal_errors),
        )

    def get_soc(self):
        if (
            self.soc is None
            or self.battery_capacity is None
            or self.mcu_consumed is None
        ):
            return

        mcu_consumption_percentage = math.floor(
            100 * self.mcu_consumed / self.battery_capacity
        )
        return self.soc - mcu_consumption_percentage

    def get_direction(self):
        """
        Determine the current flow direction in the battery.

        Returns:
            int: A value indicating the direction of the current flow (0 for discharge,
                 non-zero for charge).
        """
        return self.current & (1 << 15)

    def get_power(self):
        """
        Calculate the instantaneous power of the battery.

        This method computes the power in watts based on the current voltage and
        current values. The calculation accounts for the sign of the current to
        determine if power is being consumed (positive) or generated (negative).

        Returns:
            int: The calculated power in watts, or 0 if current or voltage is None.
        """
        if not self.current or not self.voltage:
            return 0

        current = (self.current & (0xFFFF >> 1)) / 100
        return int(current * self.voltage / 100)

    def increase_mcu_consumption(self, period, power, voltage):
        ah = ((period / 3600) * power) / (voltage / 100)
        self.mcu_consumed += ah
        logger.debug("mcu inc consumption", ah, self.mcu_consumed)

    def decrease_mcu_consumption(self, period, power, voltage):
        ah = ((period / 3600) * power) / (voltage / 100)
        self.mcu_consumed -= ah
        if self.mcu_consumed < 0:
            self.mcu_consumed = 0
        logger.debug("mcu dec consumption", ah, self.mcu_consumed)

    def reset_mcu_consumption(self):
        logger.debug("reset mcu consumption")
        self.mcu_consumed = 0

    def set_mcu_consumption(self, ah):
        logger.debug("set mcu consumption", ah)
        self.mcu_consumed = ah


class BMSController:
    """
    Controller for the Battery Management System (BMS).

    This class manages communication with the physical BMS hardware via UART,
    providing methods to query the current state and send control commands.
    It handles the low-level protocol details and provides a high-level interface
    for interacting with the BMS.

    The controller supports enabling/disabling charging and discharging operations,
    as well as continuous monitoring of the battery state.

    Attributes:
        HEADER (bytes): The header bytes for BMS communication.
        STATUS_REQUEST (bytes): Command to request current BMS status.
        ENABLE_CHARGE (bytes): Command to enable charging.
        DISABLE_CHARGE (bytes): Command to disable charging.
        ENABLE_DISCHARGE (bytes): Command to enable discharging.
        DISABLE_DISCHARGE (bytes): Command to disable discharging.
        BAUD_RATE (int): Default UART baud rate (115200).
        UART_IF (int): Default UART interface number (1).
        UART_TX_PIN (int): Default UART TX pin number (18).
        UART_RX_PIN (int): Default UART RX pin number (16).
    """

    HEADER = b"\x4e\x57"

    # Jikong BMS request signature
    STATUS_REQUEST = b"\x4e\x57\x00\x13\x00\x00\x00\x00\x06\x03\x00\x00\x00\x00\x00\x00\x68\x00\x00\x01\x29"

    ENABLE_CHARGE = b"\x4e\x57\x00\x14\x00\x00\x00\x00\x02\x03\x02\xab\x01\x00\x00\x00\x00\x68\x00\x00\x01\xd4"
    DISABLE_CHARGE = b"\x4e\x57\x00\x14\x00\x00\x00\x00\x02\x03\x02\xab\x00\x00\x00\x00\x00\x68\x00\x00\x01\xd3"

    ENABLE_DISCHARGE = b"\x4e\x57\x00\x14\x00\x00\x00\x00\x02\x03\x02\xac\x01\x00\x00\x00\x00\x68\x00\x00\x01\xd5"
    DISABLE_DISCHARGE = b"\x4e\x57\x00\x14\x00\x00\x00\x00\x02\x03\x02\xac\x00\x00\x00\x00\x00\x68\x00\x00\x01\xd4"

    BAUD_RATE = 115200
    UART_IF = 1
    UART_TX_PIN = 18
    UART_RX_PIN = 16

    # track mcu consumption every n seconds
    MCU_POWER_FREQUENCY = 5

    # time elapsed since the last update
    mcu_power_ticks = 0

    TURN_OFF_MAX_CONFIRMATIONS = 3
    _turn_off_confirmations = 0
    _turn_off_min_voltage = None
    _turn_off_max_voltage = None

    _uart = None
    _state: BMSState = None

    def __init__(
        self,
        baud_rate=BAUD_RATE,
        uart_if=UART_IF,
        uart_rx_pin=UART_RX_PIN,
        uart_tx_pin=UART_TX_PIN,
        profile=None,
        turn_off_min_voltage=None,
        turn_off_max_voltage=None,
    ):
        """
        Initialize the BMSController with UART communication parameters.

        This method sets up the UART communication channel for interacting with
        the BMS hardware and initializes the state tracking object.

        Args:
            baud_rate (int, optional): The baud rate for UART communication. Defaults to 115200.
            uart_if (int, optional): The UART interface number. Defaults to 1.
            uart_rx_pin (int, optional): The UART RX pin. Defaults to 16.
            uart_tx_pin (int, optional): The UART TX pin. Defaults to 18.
            profile (object, optional): The profile object to use for battery metrics. Defaults to None.
        """
        self._state = BMSState()
        self._uart = UART(
            interface=uart_if,
        )
        self._uart.init(
            tx=uart_tx_pin,
            rx=uart_rx_pin,
            baud_rate=baud_rate,
        )

        self._profile = profile
        self.mcu_power_ticks = 0
        if self._profile:
            self.state.set_mcu_consumption(profile.get(PROFILE_KEY_MCU_POWER, 0))

        if turn_off_min_voltage:
            self._turn_off_min_voltage = turn_off_min_voltage

        if turn_off_max_voltage:
            self._turn_off_max_voltage = turn_off_max_voltage

    async def run(self):
        """
        Run the BMS controller in continuous monitoring mode.

        This asynchronous method continuously queries the BMS state and updates
        the internal state tracking. It runs indefinitely until interrupted,
        with a configurable delay between queries.

        The method also takes snapshots of the state for historical tracking
        and handles any communication errors that may occur.
        """
        logger.info("Running BMS controller")
        self.request_status(delay=50)

        while True:
            self.request_status()
            self.state.snapshot()
            await self.state.sleep()

    def update_mcu_consumption(self):
        """Manage unrecorded power consumption by BMS itself and ESP32 ICs"""

        direction = 0  # discharging
        voltage = 3.2 * 4 * 100  # nominal voltage
        power = self.state.MCU_POWER + self.state.USB_POWER  # always on

        self.mcu_power_ticks += 1

        if self.state.get_soc():
            direction = self.state.get_direction()
            power += self.state.BMS_POWER
            voltage = self.state.voltage

        if self.mcu_power_ticks < self.MCU_POWER_FREQUENCY:
            return

        period = self.mcu_power_ticks * self.state.STATE_FREQUENCY
        self.mcu_power_ticks = 0

        if direction:
            self.state.decrease_mcu_consumption(
                period, self.state.get_power() - power, voltage
            )
        else:
            self.state.increase_mcu_consumption(period, power, voltage)

        if self._profile:
            self._profile.set(PROFILE_KEY_MCU_POWER, self.state.mcu_consumed, False)

    def request_status(self, delay=100):
        """
        Request the current status from the BMS hardware.

        This method sends a status request command to the BMS and processes the
        response to update the internal state. It handles communication errors
        and logs relevant information.

        Args:
            delay (int, optional): The delay in milliseconds between sending the request
                                 and reading the response. Defaults to 100.

        Returns:
            bool: True if the status was successfully retrieved and parsed,
                 False if a communication error occurred.
        """
        self.update_mcu_consumption()
        data = self._uart.query(self.STATUS_REQUEST, delay=delay)
        if data:
            try:
                logger.debug("BMS response", data)
                self.state.parse(data)
                self.check_voltage_thresholds()
                self.state.reset_error(self._state.ERROR_NO_RESPONSE)
                logger.info(
                    "BMS Voltage",
                    self.state.voltage,
                    "Temperature: ",
                    self.state.mos_temperature,
                    "Power: ",
                    self.state.get_power(),
                    "SOC: ",
                    self.state.get_soc(),
                )
                return True
            except Exception as e:
                logger.critical(e)

        self.state.clear()
        self.state.set_error(self._state.ERROR_NO_RESPONSE)
        return False

    def enable_charge(self, delay=50):
        """
        Enable charging on the BMS.

        This method sends a command to the BMS to enable the charging function.
        It verifies the response and updates the error state accordingly.

        Args:
            delay (int, optional): The delay in milliseconds between sending the command
                                 and reading the response. Defaults to 50.

        Returns:
            bool: True if charging was successfully enabled, False otherwise.
        """
        logger.debug("Enabling BMS charging...")
        data = self._uart.query(self.ENABLE_CHARGE, delay=delay)
        if data:
            logger.info("Enabled BMS charging")
            self._state.reset_error(self._state.ERROR_NO_RESPONSE)
            return True

        logger.error("Failed to enable BMS charging")
        self._state.set_error(self._state.ERROR_NO_RESPONSE)
        return False

    def disable_charge(self, delay=50):
        """
        Disable charging on the BMS.

        This method sends a command to the BMS to disable the charging function.
        It verifies the response and updates the error state accordingly.

        Args:
            delay (int, optional): The delay in milliseconds between sending the command
                                 and reading the response. Defaults to 50.

        Returns:
            bool: True if charging was successfully disabled, False otherwise.
        """
        logger.debug("Disabling BMS charging")
        data = self._uart.query(self.DISABLE_CHARGE, delay=delay)
        if data:
            logger.info("Disabled BMS charging")
            self._state.reset_error(self._state.ERROR_NO_MODIFY_RESPONSE)
            return True

        logger.error("Failed to disable BMS charging")
        self._state.set_error(self._state.ERROR_NO_MODIFY_RESPONSE)
        return False

    def enable_discharge(self, delay=50):
        """
        Enable discharging on the BMS.

        This method sends a command to the BMS to enable the discharging function.
        It verifies the response and updates the error state accordingly.

        Args:
            delay (int, optional): The delay in milliseconds between sending the command
                                 and reading the response. Defaults to 50.

        Returns:
            bool: True if discharging was successfully enabled, False otherwise.
        """
        logger.debug("Enabling BMS discharging")
        data = self._uart.query(self.ENABLE_DISCHARGE, delay=delay)
        if data:
            logger.info("Enabled BMS discharging")
            self._state.reset_error(self._state.ERROR_NO_MODIFY_RESPONSE)
            return True

        logger.error("Failed to enable BMS discharging")
        self._state.set_error(self._state.ERROR_NO_MODIFY_RESPONSE)
        return False

    def disable_discharge(self, delay=50):
        """
        Disable discharging on the BMS.

        This method sends a command to the BMS to disable the discharging function.
        It verifies the response and updates the error state accordingly.

        Args:
            delay (int, optional): The delay in milliseconds between sending the command
                                 and reading the response. Defaults to 50.

        Returns:
            bool: True if discharging was successfully disabled, False otherwise.
        """
        data = self._uart.query(self.DISABLE_DISCHARGE, delay=delay)
        if data:
            logger.info("Disabled BMS discharging")
            self._state.reset_error(self._state.ERROR_NO_MODIFY_RESPONSE)
            return True

        logger.error("Failed to disable BMS discharging")
        self._state.set_error(self._state.ERROR_NO_MODIFY_RESPONSE)
        return False

    def check_voltage_thresholds(self):
        """
        Process updates from the Battery Management System (BMS).

        Monitors battery cell voltages and triggers PSU shutdown if voltage
        exceeds the safety threshold for a sufficient number of confirmations.
        """
        # Check if any cell voltage exceeds the threshold
        min_voltage_exceeded = False
        max_voltage_exceeded = False

        for cell_index, voltage in enumerate(self.state.cells):
            if voltage is None:
                continue

            # Convert from mV to V
            voltage_v = voltage / 1000

            if self._turn_off_min_voltage and voltage_v < self._turn_off_min_voltage:
                min_voltage_exceeded = True
                logger.debug(
                    f"Min cell {cell_index} voltage {voltage_v}V exceeds threshold {self._turn_off_min_voltage}V"
                )
                break

            if self._turn_off_max_voltage and voltage_v > self._turn_off_max_voltage:
                max_voltage_exceeded = True
                logger.debug(
                    f"Max cell {cell_index} voltage {voltage_v}V exceeds threshold {self._turn_off_max_voltage}V"
                )
                break

        # Update confirmation counter based on voltage status
        if any([min_voltage_exceeded, max_voltage_exceeded]):
            self._turn_off_confirmations += 1
            logger.debug(
                f"Voltage threshold exceeded: {self.TURN_OFF_MAX_CONFIRMATIONS} confirmations"
            )
        else:
            self._turn_off_confirmations = 0

        threshold_triggerred = (
            self._turn_off_confirmations >= self.TURN_OFF_MAX_CONFIRMATIONS
        )

        if max_voltage_exceeded and threshold_triggerred:
            logger.info(
                f"Battery cell reached max voltage threshold ({self._turn_off_max_voltage}V)"
            )
            self.state.trigger(const.EVENT_BATTERY_CHARGED)
            self.state.reset_mcu_consumption()

        if min_voltage_exceeded and threshold_triggerred:
            logger.info(
                f"Battery cell reached min voltage threshold ({self._turn_off_min_voltage}V)"
            )
            self.state.trigger(const.EVENT_BATTERY_DISCHARGED)

    @property
    def state(self):
        """
        Get the current state of the BMS.

        This property provides access to the internal BMSState object that
        tracks all aspects of the battery system's current state.

        Returns:
            BMSState: The current BMS state object containing all state information.
        """
        return self._state
