import machine
import struct

from drivers import BaseState
from drivers.button import ButtonController
from lib.history import HistoricalData

from const import BLE_PSU_STATE_UUID

from lib.tachometer import Tachometer


from const import (
    HISTORY_PSU_RPM,
    HISTORY_PSU_TEMPERATURE_1,
    HISTORY_PSU_TEMPERATURE_2,
    HISTORY_PSU_POWER_1,
    HISTORY_PSU_POWER_2,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
)

from logging import logger


class PSUState(BaseState):

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
        if self.t1 and self.t2:
            return int((self.t1 + self.t2) / 2)

    def get_ble_state(self):
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
        t1 = self.get_avg_temperature()
        self.history[HISTORY_PSU_RPM].push(self._pack(self.rpm))
        self.history[HISTORY_PSU_POWER_1].push(self._pack(self.power1))
        self.history[HISTORY_PSU_POWER_2].push(self._pack(self.power2))
        self.history[HISTORY_PSU_TEMPERATURE_1].push(self._pack(t1))
        self.history[HISTORY_PSU_TEMPERATURE_2].push(self._pack(self.t3))

    def crc(self, data):
        return sum(b for b in data) % 0x100

    def parse(self, frame):
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

    def parse_buffer(self, buffer):

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
            error = self.parse(frame)
            if not error:
                return True

            buffer = buffer[frame_start + self.FRAME_SIZE :]
        except Exception as e:
            print(e)


class PowerSupplyController:
    """
    Controller listens for button pin pressed and turns on/off PSU
    via a MOSFET. The button pin is when connected gets 3.3V from
    the controller.

    Current pins define corresponding CD4051B multiplexer A,B pins. C pin is grounded
    and not available in the controller.
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
        power_button_timer=-1,
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
        self._state = PSUState()
        self._uart = uart
        self._uart_rx_pin = uart_rx_pin
        self._turn_off_voltage = turn_off_voltage

        if fan_tachometer_pin:
            self._tachometer = Tachometer(
                pin=machine.Pin(fan_tachometer_pin, machine.Pin.IN),
                period_ms=200,
                done_callback=self.on_tachometer,
                timer_id=fan_tachometer_timer,
            )

        try:
            self._power_button = ButtonController(
                listen_pin=power_button_pin,
                on_change=self.on_power_trigger,
                buzzer=buzzer,
                timer_id=power_button_timer,
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
        self._state.rpm = rpm
        logger.debug(f"PSU FAN RPM: {rpm}")

    def on_bms_state(self, bms_state):
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
                self.off()
        else:
            self._turn_off_confirmations = 0

    def set_current(self, channel):
        self._state.current_channel = channel
        channel_a = channel & 0x01
        channel_b = (channel >> 1) & 0x01
        self._current_a_pin.value(channel_a)  # LSB (A)
        self._current_b_pin.value(channel_b)  # MSB (B)
        logger.debug(
            f"Set PSU current channel: {channel} A: {channel_a} B: {channel_b} "
        )

    def on(self):
        self._uart.init(rx=self._uart_rx_pin, baud_rate=4800)
        self._power_gate_pin.on()
        self._state.on()
        logger.info("Power supply is on")

    def off(self):
        self._power_gate_pin.off()
        self._state.off()
        self._state.clear()
        logger.info("Power supply is off")

    def on_power_trigger(self):
        if self._state.active:
            self.off()
        else:
            self.on()

    async def run(self):
        logger.info("Running PSU...")
        while True:
            if self.state.active:
                self._state.parse_buffer(self._uart.sample(timeout=500))
                self._tachometer.measure()
                self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        return self._state
