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
    """FCHAO state specification.

    0xAE Frame header
    0x01 Address
    0x12 Message length
    0x83 CMD ( Command: Get module output voltage, current, alarm amount )
    0x02 Thousands and hundreds digits of AC output voltage
    0x22 Tens and ones digits of AC output voltage
    0x00 Thousands and hundreds of BAT current
    0x00 Tens and ones digits of BAT current
    0x01 Thousands and hundreds of BAT voltage
    0x34 Tens and ones digits of BAT voltage
    0x00 Thousands and hundreds digits of device temperature
    0x24 Tens and ones digits of device temperature
    0x00 Reserved bytes
    0x00 Module alarm status
    0x09 Battery power level ( level 1-10 )
    0x28 Check word ( accumulated sum of address, length, command , and information fields )
    0xEE End of frame
    """

    NAME = "INVERTER"
    BLE_STATE_UUID = BLE_INVERTER_STATE_UUID

    # whether inverter is turned on
    active = False

    # AC output voltage
    ac = None

    # output power
    power = None

    # input voltage
    dc = None

    # temperature
    temperature = None

    # battery level
    level = None

    # fan A speed
    rpm_a = None

    # fan B speed
    rpm_b = None

    # if state is valid
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
        return self._valid

    def get_avg_rpm(self):
        if self.rpm_a and self.rpm_b:
            return int((self.rpm_a + self.rpm_b) / 2)

    def build_history(self):
        self.history[HISTORY_INVERTER_POWER].push(self._pack(self.power))
        self.history[HISTORY_INVERTER_TEMPERATURE].push(self._pack(self.temperature))
        self.history[HISTORY_INVERTER_RPM].push(self._pack(self.get_avg_rpm()))

    def get_ble_state(self):
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

    # whether inverter is in bootstrapping mode
    _bootstrapping = False
    # time in seconds before reading inverter status
    _bootstrapping_delay = 3
    _uart = None

    # state of the power
    _power_button = None
    _power_gate_pin = None

    # last inverter state
    _state = None

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
        fan_tachometer_timer=None,
    ):
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
            timer_id=power_button_timer,
        )

        self._power_gate_pin = machine.Pin(
            power_gate_pin,
            machine.Pin.OUT,
            machine.Pin.PULL_DOWN,
        )
        self._power_gate_pin.off()

        if fan_tachometer_a_pin:
            self._tachometer_a = Tachometer(
                pin=machine.Pin(fan_tachometer_a_pin, machine.Pin.IN),
                period_ms=200,
                done_callback=self.on_tachometer_a,
                timer_id=fan_tachometer_timer,
            )

        if fan_tachometer_b_pin:
            self._tachometer_b = Tachometer(
                pin=machine.Pin(fan_tachometer_b_pin, machine.Pin.IN),
                period_ms=200,
                done_callback=self.on_tachometer_b,
                timer_id=fan_tachometer_timer,
            )

        logger.info(f"Initialized inverter turn off voltage: {turn_off_voltage}")

    def on_tachometer_a(self, rpm):
        self._state.rpm_a = rpm
        logger.debug(f"INVERTER FAN A RPM: {rpm}")

    def on_tachometer_b(self, rpm):
        self._state.rpm_b = rpm
        logger.debug(f"INVERTER FAN B RPM: {rpm}")

    def on_bms_state(self, bms_state):
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
        self._bootstrapping = True
        self._uart.init(rx=self._rx_pin, tx=self._tx_pin, baud_rate=self._baud_rate)
        self._power_gate_pin.on()
        self._state.on()
        logger.info("Inverter is on")

    def off(self):
        self._bootstrapping = False
        self._power_gate_pin.off()
        self._state.off()
        self.state.clear_internal_errors()
        self.state.clear()
        logger.info("Inverter is off")

    def on_power_trigger(self):
        if self._state.active:
            self.off()
        else:
            self.on()

    async def run(self):
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
                self._tachometer_a.measure()
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
        data = self._uart.query(self.STATUS_REQUEST, delay=50)
        logger.debug("Inverter response", self.state.as_hex(data))
        self._state.parse_buffer(data)

    @property
    def state(self):
        return self._state
