import asyncio
import machine
import struct

from drivers.button import ButtonController
from drivers import BaseState, PowerCallbacksMixin
from drivers.history import HistoricalData

from logging import logger
from drivers.const import BLE_INVERTER_UUID

from drivers.const import (
    HISTORY_INVERTER_POWER,
    HISTORY_INVERTER_TEMPERATURE,
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
    BLE_STATE_UUID = BLE_INVERTER_UUID

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

    # if state is valid
    _valid = False

    history = {
        HISTORY_INVERTER_POWER: HistoricalData(
            chart_type=HISTORY_INVERTER_POWER,
            data_type=DATA_TYPE_WORD,
        ),
        HISTORY_INVERTER_TEMPERATURE: HistoricalData(
            chart_type=HISTORY_INVERTER_TEMPERATURE,
            data_type=DATA_TYPE_BYTE,
        ),
    }

    DISPLAY_METRICS = ["temperature", "power"]

    def clear(self):
        self.active = False
        self.ac = None
        self.power = None
        self.dc = None
        self.temperature = None
        self.level = None

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
        # inverter error status
        # 10 - under voltage protection
        # 20 - over voltage protection
        self.external_errors = int(f"{device_error:x}")
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

    def is_valid(self):
        return self._valid

    def set_display_metric(self, metric):
        self.display_metric_glyph = "on" if self.active else "off"

        if metric == "power":
            self.display_metric_value = self.power
            self.display_metric_type = "w"

        if metric == "temperature":
            self.display_metric_value = self.temperature
            self.display_metric_type = "c"

    def build_history(self):
        self.history[HISTORY_INVERTER_POWER].push(self._pack(self.power))
        self.history[HISTORY_INVERTER_TEMPERATURE].push(self._pack(self.temperature))

    def get_ble_state(self):
        return struct.pack(
            ">HBBBBB",
            self._pack(self.power),
            self._pack_bool(self.active),
            self._pack(self.ac),
            self._pack(self.temperature),
            self._pack(self.external_errors),
            self._pack(self.internal_errors),
        )


class InverterController(PowerCallbacksMixin):

    POWER_BUTTON_PIN = None
    POWER_GATE_PIN = None

    BAUD_RATE = 9600
    UART_IF = None
    UART_RX_PIN = None
    UART_TX_PIN = None

    STATUS_REQUEST = b"\xAE\x01\x01\x03\x05\xEE"
    SHUTDOWN_REQUEST = b"\xAE\x01\x02\x04\x01\x00\x08\xEE"
    TURN_ON_REQUEST = b"\xAE\x01\x02\x04\x00\x00\x07\xEE"

    _uart = None

    # state of the power
    _power_button = None
    _power_gate_pin = None

    # last inverter state
    _state = None

    def __init__(
        self,
        power_button_pin=POWER_BUTTON_PIN,
        power_gate_pin=POWER_GATE_PIN,
        uart_if=UART_IF,
        baud_rate=BAUD_RATE,
        uart_tx_pin=UART_TX_PIN,
        uart_rx_pin=UART_RX_PIN,
        buzzer=None,
    ):
        self._state = InverterState()

        if uart_if is not None:
            tx = machine.Pin(uart_tx_pin, machine.Pin.OUT)
            rx = machine.Pin(uart_rx_pin, machine.Pin.IN)
            self._uart = machine.UART(uart_if, baudrate=baud_rate, tx=tx, rx=rx)

        self._power_button = ButtonController(
            listen_pin=power_button_pin,
            on_change=self.on_power_trigger,
            buzzer=buzzer,
        )

        self._power_gate_pin = machine.Pin(
            power_gate_pin, machine.Pin.OUT, machine.Pin.PULL_DOWN
        )
        self._power_gate_pin.off()

        PowerCallbacksMixin.__init__(self)
        logger.info(f"Initialized inverter")

    def on(self):
        if self.power_on_callbacks:
            for cb in self.power_on_callbacks:
                cb()

        self._power_gate_pin.on()
        self._state.active = True
        self._state.notify()
        logger.info("Inverter is on")

    def off(self):
        if self.power_off_callbacks:
            for cb in self.power_off_callbacks:
                cb()

        self._power_gate_pin.off()
        self._state.active = False
        self._state.notify()
        logger.info("Inverter is off")

    def on_power_trigger(self):
        if self._state.active:
            self.off()
        else:
            self.on()

    async def run(self):
        logger.info("Running inverter controller...")
        asyncio.create_task(self.read_status())
        while True:

            if self._state.active:
                try:
                    logger.debug("Requesting inverter status")
                    self._uart.write(self.STATUS_REQUEST)
                except Exception as e:
                    logger.error("Failed request to inverter")
                    logger.critical(e)

            self._state.snapshot()
            await self._state.sleep()

    def _mock_uart_read(self):
        return b"\xae\x01\x12\x83\x022\x00\x00\x01\x08\x00\x17\x00\x00\x037\xee"

    def _mock_uart_any(self):
        return True

    async def read_status(self):

        if not self._uart:
            return

        buffer = b""
        logger.debug("Running inverter status reader")

        while True:

            if not self._state.active:
                await asyncio.sleep(5)
                continue

            if self._uart.any():
                # if self._mock_uart_any():
                data = self._uart.read()
                # data = self._mock_uart_read()
                if data:
                    logger.debug(f"Inverter received data: {data}")
                    buffer += data
                    if 0xAE in buffer and 0xEE in buffer:
                        frame_start = buffer.find(b"\xAE")
                        frame_end = buffer.find(b"\xEE") + 1
                        self.process_frame(buffer[frame_start:frame_end])
                        buffer = buffer[frame_end:]

                    # prevent OOM in case some garbage comes into the buffer
                    if len(buffer) > 1024:
                        logger.error("Inverter buffer has no frames")
                        buffer = b""

            # unblock other coroutines
            # await asyncio.sleep_ms(100)
            await asyncio.sleep_ms(1000)

    def process_frame(self, frame):
        try:
            self._state.parse(frame)
        except Exception as e:
            logger.critical(e)
            return

        if self._state.is_valid():
            logger.debug(
                f"AC: {self._state.ac}, Power: {self._state.power} Temperature: {self._state.temperature} DC: {self._state.dc}"
            )
            self._state.reset_error(self._state.ERROR_BAD_RESPONSE)
        else:
            self._state.set_error(self._state.ERROR_BAD_RESPONSE)
            logger.warning("Inverter state is not valid")

    @staticmethod
    def as_hex(data):
        # Convert each byte of the binary data to a 2-digit hex value and print it
        return " ".join(f"{byte:02X}" for byte in data)

    @property
    def state(self):
        return self._state
