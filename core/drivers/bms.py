"""
BMS (Battery Management System) module.

This module provides the implementation of BMSErrors, BMSState, and BMSController
classes, which manage the state, errors, and control logic for the battery
management system.
"""

import struct

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
)


class BMSErrors:
    """
    Represents the error codes for the BMS.

    A two-byte value represents one or more errors specified in the following bits:

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

    Attributes:
        NAME (str): The name of the state.
        BLE_STATE_UUID (UUID): The BLE UUID for the BMS state.
        cells (list): Per-cell voltage values.
        mos_temperature (int): MOSFET temperature.
        sensor1_temperature (int): Temperature from sensor 1.
        sensor2_temperature (int): Temperature from sensor 2.
        voltage (int): Total battery voltage.
        current (int): Current flowing through the battery.
        soc (int): State of charge (percentage).
        charging_allowed (bool): Whether charging is allowed.
        discharging_allowed (bool): Whether discharging is allowed.
    """

    NAME = "BMS"
    BLE_STATE_UUID = BLE_BMS_STATE_UUID

    ERROR_NO_MODIFY_RESPONSE = 2

    # per cell voltage
    cells = [None, None, None, None]

    mos_temperature = None
    sensor1_temperature = None
    sensor2_temperature = None

    voltage = None
    current = None
    soc = None

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
        Clear the BMS state.

        Resets all state attributes to their default values.
        """
        self.cells = [None, None, None, None]

        self.mos_temperature = None
        self.sensor1_temperature = None
        self.sensor2_temperature = None

        self.voltage = None
        self.current = None
        self.soc = None

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

    def parse(self, response):
        """
        Parse a response from the BMS.

        Args:
            response (bytes): The response data to parse.
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
        offset += 3

        if self.external_errors:
            self.set_error(self.ERROR_EXTERNAL)
        else:
            self.reset_error(self.ERROR_EXTERNAL)

    def build_history(self):
        """
        Build historical data for the BMS.

        Updates the historical data for SOC, current, and per-cell voltages.
        """
        self.history[HISTORY_BMS_SOC].push(self._pack(self.soc))
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
        Calculate the CRC for a given frame.

        Args:
            frame (bytes): The frame to calculate the CRC for.

        Returns:
            list: A list containing the two-byte CRC.
        """
        result = 0
        for b in frame:
            result += b
        return [(result >> 8) & 0xFF, result & 0xFF]

    def get_ble_state(self):
        """
        Get the BLE representation of the BMS state.

        Returns:
            bytes: The packed BLE state of the BMS.
        """
        return struct.pack(
            ">HHBBBBBBBBBBHB",
            self._pack(self.voltage),
            self._pack(self.current),
            self._pack(self.soc),
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

    def get_direction(self):
        return self.current & (1 << 15)

    def get_power(self):
        """
        Calculate the power based on current and voltage.

        Returns:
            int: The calculated power in watts.
        """
        if not self.current or not self.voltage:
            return 0

        current = (self.current & (0xFFFF >> 1)) / 100
        return int(current * self.voltage / 100)


class BMSController:
    """
    Controller for the Battery Management System (BMS).

    This class manages communication with the BMS, including querying its state
    and sending commands.

    Attributes:
        ENABLE_CHARGE (bytes): Command to enable charging.
        DISABLE_CHARGE (bytes): Command to disable charging.
        ENABLE_DISCHARGE (bytes): Command to enable discharging.
        DISABLE_DISCHARGE (bytes): Command to disable discharging.
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

    _uart = None
    _state: BMSState = None

    def __init__(
        self,
        baud_rate=BAUD_RATE,
        uart_if=UART_IF,
        uart_rx_pin=UART_RX_PIN,
        uart_tx_pin=UART_TX_PIN,
    ):
        """
        Initialize the BMSController.

        Args:
            baud_rate (int): The baud rate for UART communication.
            uart_if (int): The UART interface number.
            uart_rx_pin (int): The UART RX pin number.
            uart_tx_pin (int): The UART TX pin number.
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

    async def run(self):
        """
        Run the BMS controller.

        This method continuously queries the BMS state and updates it.
        """
        logger.info("Running BMS controller")
        self.request_status(delay=50)

        while True:
            self.request_status()
            self._state.snapshot()
            await self._state.sleep()

    def request_status(self, delay=100):
        """
        Request the current status from the BMS.

        Args:
            delay (int): The delay between sending the request and reading the response.

        Returns:
            bool: True if the status was successfully retrieved, False otherwise.
        """
        data = self._uart.query(self.STATUS_REQUEST, delay=delay)
        if data:
            try:
                logger.debug("BMS response", data)
                self.state.parse(data)
                self.state.reset_error(self._state.ERROR_NO_RESPONSE)
                logger.info(
                    "BMS Voltage",
                    self.state.voltage,
                    "Temperature: ",
                    self.state.mos_temperature,
                    "Power: ",
                    self.state.get_power(),
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

        Args:
            delay (int): The delay between sending the command and reading the response.

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

        Args:
            delay (int): The delay between sending the command and reading the response.

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

        Args:
            delay (int): The delay between sending the command and reading the response.

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

        Args:
            delay (int): The delay between sending the command and reading the response.

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

    @property
    def state(self):
        """
        Get the current state of the BMS.

        Returns:
            BMSState: The current BMS state.
        """
        return self._state
