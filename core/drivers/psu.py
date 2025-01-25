import asyncio
import machine
import struct
import time

from drivers.button import ButtonController
from drivers import BaseState, PowerCallbacksMixin
from drivers.history import HistoricalData

from drivers.const import BLE_PSU_UUID

from lib.tachometer import Tachometer


from drivers.const import (
    HISTORY_PSU_VOLTAGE,
    HISTORY_PSU_TEMPERATURE,
    DATA_TYPE_BYTE,
    DATA_TYPE_WORD,
)

from logging import logger


class PSUState(BaseState):

    NAME = "PSU"
    STATE_FREQUENCY = 5

    BLE_STATE_UUID = BLE_PSU_UUID
    ERROR_PIN = 6

    # on/off
    active = False

    # current channel (0-3)
    current = 0

    # telemetry
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
        HISTORY_PSU_VOLTAGE: HistoricalData(
            chart_type=HISTORY_PSU_VOLTAGE,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_PSU_TEMPERATURE: HistoricalData(
            chart_type=HISTORY_PSU_TEMPERATURE,
            data_type=DATA_TYPE_BYTE,
        ),
    }

    def __init__(self):
        pass

    def clear(self):
        self.active = False

    def get_ble_state(self):
        return struct.pack(
            ">HBBBBB",
            self._pack_voltage(0),
            self._pack_bool(self.active),
            self._pack(self.current),
            self._pack(0),
            self._pack(self.external_errors),
            self._pack(self.internal_errors),
        )

    def build_history(self):
        voltage = self._pack_voltage(0)
        self.history[HISTORY_PSU_VOLTAGE].push(voltage)
        self.history[HISTORY_PSU_TEMPERATURE].push(self._pack(0))

    def set_display_metric(self, metric):
        self.display_metric_glyph = "on" if self.active else "off"

    def crc(self, data):
        return sum(b for b in data) % 0xFF

    def parse(self, frame):
        print("parsing frame")
        offset = 0
        header = struct.unpack_from(">BB", frame)
        if header != (0x49, 0x34):
            self.error = 101
            print("bad frame header")
            return
        offset += 2

        power1 = struct.unpack_from(">BB", frame, offset)
        offset += 2

        power2 = struct.unpack_from(">BB", frame, offset)
        offset += 2

        actual_crc = struct.unpack_from(">B", frame, offset)[0]
        offset += 1

        power_crc = self.crc(frame[2:6])
        if power_crc != actual_crc:
            self.error = 2
            print("bad header crc", power_crc, actual_crc)
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

        data_crc = self.crc(frame[9:21]) - 3
        if data_crc != actual_data_crc:
            self.error = 3
            print("bad data crc", data_crc, actual_data_crc)
            return False

        self.power1 = power1
        self.power2 = power2
        self.ac = ac
        self.state = state
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        print("succeeded", self.ac, self.t1, self.t2, self.t3)


class PowerSupplyController(PowerCallbacksMixin):
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

    # UART parameters
    UART_IF = 0
    BAUD_RATE = 4800
    FRAME_SIZE = 22
    _buffer = None

    def __init__(
        self,
        power_button_pin=POWER_BUTTON_PIN,
        power_gate_pin=POWER_GATE_PIN,
        current_a_pin=CURRENT_A_PIN,
        current_b_pin=CURRENT_B_PIN,
        fan_tachometer_pin=None,
        uart_if=None,
        uart_rx_pin=None,
        buzzer=None,
        turn_off_voltage=TURN_OFF_VOLTAGE,
        current_limit=CURRENT_CHANNEL,
    ):
        self._state = PSUState()
        self._turn_off_voltage = turn_off_voltage

        self._uart = None
        self._uart_if = uart_if
        self._uart_rx_pin = uart_rx_pin

        if fan_tachometer_pin:
            self._tachometer = Tachometer(
                pin=machine.Pin(fan_tachometer_pin, machine.Pin.IN),
                period_ms=300,
                done_callback=self.on_tachometer,
            )

        try:
            self._power_button = ButtonController(
                listen_pin=power_button_pin,
                on_change=self.on_power_trigger,
                buzzer=buzzer,
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
            self.set_current(current_limit)
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.critical(e)

        try:
            self._current_a_pin = machine.Pin(
                current_a_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN
            )
            self._current_b_pin = machine.Pin(
                current_b_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN
            )
            self.set_current(current_limit)
        except Exception as e:
            self._state.set_error(self._state.ERROR_PIN)
            logger.error("PSU current pin failed")

        PowerCallbacksMixin.__init__(self)
        logger.info("Initialized power supply controller")

    async def start_metrics_samping(self, timeout=1000):

        if not self._uart_if:
            return

        self._uart = machine.UART(
            self._uart_if,
            baudrate=self.BAUD_RATE,
            rx=machine.Pin(self._uart_rx_pin, machine.Pin.IN, machine.Pin.PULL_UP),
        )

        buffer = bytearray()

        started_at = time.ticks_ms()
        while True:
            await asyncio.sleep_ms(100)
            data = self._uart.read()

            if data:
                print(type(data), type(buffer), data)
                buffer += data
                self.extract_frames(buffer)

            diff = time.ticks_ms() - started_at
            if diff > 1000:
                break

        self._uart.deinit()
        self._uart = None
        self._buffer = None
        print("Stop measuring samples")

    def extract_frames(self, buffer):

        frame_start = buffer.find(b"\x49\x34")
        if frame_start < 0:
            return

        # incomplete buffer
        if (frame_start + self.FRAME_SIZE) > len(buffer):
            return

        frame = buffer[frame_start : frame_start + self.FRAME_SIZE]
        try:
            print("Extracted frame")
            error = self.state.parse(frame)
            if not error:
                return True

            buffer = buffer[frame_start + self.FRAME_SIZE :]
        except Exception as e:
            print(e)

    def on_tachometer(self, frequency):
        print("Fan frequency", frequency)

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
        self._state.current = channel
        self._current_a_pin.value(channel & 0x01)  # LSB (A)
        self._current_b_pin.value((channel >> 1) & 0x01)  # MSB (B)

    def on(self):
        if self.power_on_callbacks:
            for cb in self.power_on_callbacks:
                cb()

        self._power_gate_pin.on()
        self._state.active = True
        self._state.notify()
        logger.info("Power supply is on")

    def off(self):

        if self._uart:
            self._uart.deinit()
            self._uart = None

        if self.power_off_callbacks:
            for cb in self.power_off_callbacks:
                cb()
        self._power_gate_pin.off()
        self._state.active = False
        self._state.notify()
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
                asyncio.create_task(self.start_metrics_samping())
                self._tachometer.measure()

            self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        return self._state
