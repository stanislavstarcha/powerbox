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
    A two byte value represents one or more errors
    specified in the following bits

    0: Low capacity
    1: MOS over temperature
    2: Charge over voltage
    3: Discharge under voltage
    4: Battery over temperature
    5: Charge over current
    6: Discharge over current
    7: Core differential pressure (WTF)
    8: over temperature alarm in the battery box (???)
    9: Battery low temperature
    10: Unit over voltage
    11: Unit under voltage
    12: 309_A protection
    13: 309_B protection



    """

    pass


class BMSState(BaseState):

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

    def __init__(self):
        for a in range(100):
            self.history[HISTORY_BMS_SOC].push(self._pack(a))

        super(BMSState, self).__init__()

    def clear(self):
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

    @staticmethod
    def crc(frame):
        result = 0
        for b in frame:
            result += b
        return [(result >> 8) & 0xFF, result & 0xFF]

    def build_history(self):

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

    def get_ble_state(self):
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
        if not self.current or not self.voltage:
            return 0

        current = (self.current & (0xFFFF >> 1)) / 100
        return int(current * self.voltage / 100)


class BMSController:

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
        logger.info("Running BMS controller")
        self.request_status(delay=50)

        while True:
            self.request_status()
            self._state.snapshot()
            await self._state.sleep()

    def request_status(self, delay=100):
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
        return self._state
