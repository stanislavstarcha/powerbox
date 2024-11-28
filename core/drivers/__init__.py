import asyncio
import time

from drivers.const import BLE_HISTORY_UUID
from logging import logger


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

    # a list of display metrics to build
    # the metrics will be rotating on each snapshot call
    DISPLAY_METRICS = None
    _rotating_metric_index = 0
    display_metric_value = None
    display_metric_type = None
    display_metric_glyph = None

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

        # build display metric
        display_metric = None
        if self.DISPLAY_METRICS:
            display_metric = self.DISPLAY_METRICS[self._rotating_metric_index]
            self._rotating_metric_index = (self._rotating_metric_index + 1) % len(
                self.DISPLAY_METRICS
            )

        self.set_display_metric(display_metric)
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

    def get_display_metric(self):
        """Return a tuple of metric value and type"""
        return (
            self.display_metric_glyph,
            self.display_metric_value,
            self.display_metric_type,
        )

    def set_display_metric(self, metric):
        """Custom method to set controller metric, glyph and unit"""
        pass

    def pull_history(self):

        if not self.history:
            return

        for metric_name, data in self.history.items():
            chunks = data.ble_chunks()
            for chunk in chunks:
                self._ble.notify(BLE_HISTORY_UUID, chunk)


class PowerCallbacksMixin:

    power_on_callbacks = None
    power_off_callbacks = None

    def __init__(self):
        self.power_on_callbacks = []
        self.power_off_callbacks = []

    def add_power_callback(self, state, callback):
        if state:
            self.power_on_callbacks.append(callback)
        else:
            self.power_off_callbacks.append(callback)
