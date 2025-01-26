import asyncio
import machine
import time

from const import BLE_HISTORY_UUID, EVENT_STATE_CHANGE, EVENT_STATE_ON, EVENT_STATE_OFF


class UART:

    _uart = None
    _interface = None
    _rx_pin = None
    _tx_pin = None
    _baud_rate = None
    _timeout = None

    def __init__(
        self, interface, tx_pin=None, rx_pin=None, baud_rate=9600, timeout=None
    ):
        self._interface = interface
        self._rx_pin = rx_pin
        self._tx_pin = tx_pin
        self._baud_rate = baud_rate
        self._timeout = timeout

    def enable(self):

        tx = (
            machine.Pin(self._tx_pin, machine.Pin.OUT, machine.Pin.PULL_UP)
            if self._tx_pin
            else None
        )

        rx = (
            machine.Pin(self._rx_pin, machine.Pin.IN, machine.Pin.PULL_UP)
            if self._rx_pin
            else None
        )

        self._uart = machine.UART(
            self._interface,
            baudrate=self._baud_rate,
            rx=rx,
            tx=tx,
        )

    def disable(self):
        if self._uart:
            self._uart.deinit()

    def query(self, frame, delay=0):
        self._uart.write(frame)
        if delay:
            time.sleep_ms(delay)

        return self._uart.read()

    def sample(self, timeout=1000, max_size=512):
        """Read whatever data is available for `timeout` milliseconds or when `maxsize` bytes accumulated."""

        buffer = bytearray()

        started_at = time.ticks_ms()
        while True:
            data = self._uart.read()
            if data:
                buffer += data
                if len(buffer) > max_size:
                    break

            diff = time.ticks_ms() - started_at
            if diff > timeout:
                break

        return buffer


class BaseState:

    NAME = "BASE"

    BLE_STATE_UUID = None

    # internal loop stuck
    ERROR_TIMEOUT = 0

    # exception registered
    ERROR_EXCEPTION = 1

    # no response from external device
    ERROR_NO_RESPONSE = 2

    # invalid response from external device
    ERROR_BAD_RESPONSE = 3

    _ble = None

    # is external device active
    active = False

    # software error code
    internal_errors = 0

    # device error code
    external_errors = 0

    # last exception
    exception = None

    # last time snapshot function was called
    _state_modified = 0

    # last time history function was called
    _history_modified = 0

    history = None

    # how often to update display and BLE state
    STATE_FREQUENCY = 1

    # how often to record and update historical BLE state
    HISTORY_FREQUENCY = 1

    _callbacks = None

    def __init__(self):
        self._callbacks = {
            EVENT_STATE_CHANGE: [],
            EVENT_STATE_ON: [],
            EVENT_STATE_OFF: [],
        }

    def add_callback(self, event, callback):
        self._callbacks[event].append(callback)

    def on(self):
        self.active = True
        if self._callbacks[EVENT_STATE_ON]:
            for cb in self._callbacks[EVENT_STATE_ON]:
                cb()

        self.notify()

    def off(self):
        self.active = False
        if self._callbacks[EVENT_STATE_OFF]:
            for cb in self._callbacks[EVENT_STATE_OFF]:
                cb()
        self.notify()

    def fail(self, e=None):
        self.set_error(self.ERROR_EXCEPTION)
        self.exception = e

    async def sleep(self):
        await asyncio.sleep(self.STATE_FREQUENCY)

    def set_error(self, b):
        """turn on a given bit"""
        self.internal_errors = self.internal_errors | (1 << b)

    def reset_error(self, b):
        """turn on a given bit"""
        self.internal_errors = self.internal_errors & ~(1 << b)

    def clear_errors(self):
        self.internal_errors = 0

    def check_health(self):
        """check whether the loop runs normally"""
        diff = time.time() - self._state_modified
        if diff - 5 > self.STATE_FREQUENCY:
            self.set_error(self.ERROR_TIMEOUT)
        else:
            self.reset_error(self.ERROR_TIMEOUT)

    def snapshot(self):
        """"""
        self._state_modified = time.time()
        self.check_health()

        if self._state_modified - self._history_modified >= self.HISTORY_FREQUENCY:
            self.build_history()
            self._notify_history_update()
            self._history_modified = time.time()

        self.notify()

    @staticmethod
    def _pack(value):
        """Convert value into a numeric type where 0x00 represents NULL"""
        if value is None:
            return 0x00
        return int(value) + 1

    @staticmethod
    def _unpack(value):
        if value == 0:
            return None
        return value - 1

    @staticmethod
    def _pack_bool(value):
        if value is None:
            return 0x00

        if value is False:
            return 0x01

        if value is True:
            return 0x02

    @staticmethod
    def _pack_bms_temperature(value):
        if value is None:
            return 0

        # when disable
        if value == 140:
            return 0

        return value + 1

    @staticmethod
    def _pack_cell_voltage(voltage):
        if voltage is None:
            return 0

        return 1 + int(voltage / 10) - 250

    @staticmethod
    def _pack_voltage(voltage):
        if voltage is None:
            return 0
        return int(100 * voltage) + 1

    def get_ble_state(self):
        """Create a snapshot for BLE current and historical state"""
        pass

    def _notify_history_update(self):
        """Build incremental historical state"""

        if not self.history:
            return

        for chart_type, historical_data in self.history.items():
            self._ble.notify(BLE_HISTORY_UUID, historical_data.ble_update())

    def build_history(self):
        """Create a snapshot for BLE current and historical state"""
        pass

    def attach_ble(self, instance):
        self._ble = instance

    def notify(self):

        if self.BLE_STATE_UUID and self._ble:
            self._ble.notify(self.BLE_STATE_UUID, self.get_ble_state())

        if self._callbacks[EVENT_STATE_CHANGE]:
            for cb in self._callbacks[EVENT_STATE_CHANGE]:
                cb(self)

    def pull_history(self):

        if not self.history:
            return

        for metric_name, data in self.history.items():
            chunks = data.ble_chunks()
            for chunk in chunks:
                self._ble.notify(BLE_HISTORY_UUID, chunk)
