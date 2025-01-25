import struct

from bluetooth import BLE, FLAG_READ, FLAG_WRITE, FLAG_NOTIFY
from micropython import const
from drivers import BaseState
import time

from logging import logger

from drivers.const import (
    BLE_CORE_SERVICE_UUID,
    BLE_BMS_UUID,
    BLE_INVERTER_UUID,
    BLE_PSU_UUID,
    BLE_ESP_UUID,
    BLE_HISTORY_UUID,
    BLE_ATS_UUID,
    BLE_SET_COMMAND_UUID,
    BLE_SET_CHARGING_UUID,
    BLE_SET_DISCHARGING_UUID,
    BLE_SET_CURRENT_UUID,
    BLE_SET_ATS_UUID,
    BLE_INFO_SERVICE_UUID,
    BLE_MANUFACTURER_UUID,
    BLE_MODEL_NUMBER_UUID,
    BLE_FIRMWARE_REV_UUID,
)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = 0x03
_ADV_TYPE_UUID128_COMPLETE = const(0x07)
_ADV_TYPE_APPEARANCE = const(0x19)

COMMAND_PULL_HISTORY = 1


class BLEState(BaseState):
    NAME = "BLE"

    active = False

    def set_display_metric(self, metric):
        self.display_metric_glyph = "ble-client-on" if self.active else "ble-client-off"


class BLEServerController:

    _name = None
    _ble = None
    _state = None
    _connection = None
    _service = None

    HANDLE = {
        BLE_BMS_UUID: None,
        BLE_INVERTER_UUID: None,
        BLE_PSU_UUID: None,
        BLE_ESP_UUID: None,
        BLE_ATS_UUID: None,
        BLE_HISTORY_UUID: None,
        BLE_SET_COMMAND_UUID: None,
        BLE_SET_CHARGING_UUID: None,
        BLE_SET_DISCHARGING_UUID: None,
        BLE_SET_CURRENT_UUID: None,
        BLE_SET_ATS_UUID: None,
    }

    def __init__(
        self,
        gap_name=None,
        manufacturer=None,
        model=None,
        firmware=None,
        instructions=None,
        bms=None,
        psu=None,
        inverter=None,
        wroom=None,
        ats=None,
    ):
        self._state = BLEState()

        self._gap_name = gap_name
        self._manufacturer = manufacturer
        self._model = model
        self._firmware = firmware
        self._instructions = instructions

        self._bms = bms
        self._psu = psu
        self._inverter = inverter
        self._wroom = wroom
        self._ats = ats

        self._bms.state.attach_ble(self)
        self._psu.state.attach_ble(self)
        self._inverter.state.attach_ble(self)
        self._wroom.state.attach_ble(self)

    async def run(self):
        logger.info("Running Bluetooth controller...")
        while True:
            self._state.snapshot()
            await self._state.sleep()

    def collect(self):
        return self._state

    def initialize(
        self,
    ):
        self._ble = BLE()
        self._ble.active(False)
        self._ble.active(True)
        # get some sleep otherwise ic restarts
        time.sleep_ms(100)

        self._ble.irq(self.on_ble_irq)
        self._ble.config(gap_name=self._gap_name)

        (
            (
                self.HANDLE[BLE_BMS_UUID],
                self.HANDLE[BLE_INVERTER_UUID],
                self.HANDLE[BLE_PSU_UUID],
                self.HANDLE[BLE_ESP_UUID],
                self.HANDLE[BLE_ATS_UUID],
                self.HANDLE[BLE_HISTORY_UUID],
                self.HANDLE[BLE_SET_COMMAND_UUID],
                self.HANDLE[BLE_SET_CHARGING_UUID],
                self.HANDLE[BLE_SET_DISCHARGING_UUID],
                self.HANDLE[BLE_SET_CURRENT_UUID],
                self.HANDLE[BLE_SET_ATS_UUID],
            ),
            (
                self.HANDLE[BLE_MANUFACTURER_UUID],
                self.HANDLE[BLE_MODEL_NUMBER_UUID],
                self.HANDLE[BLE_FIRMWARE_REV_UUID],
            ),
        ) = self._ble.gatts_register_services(
            [
                (
                    BLE_CORE_SERVICE_UUID,
                    (
                        (BLE_BMS_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_INVERTER_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_PSU_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_ESP_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_ATS_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_HISTORY_UUID, FLAG_NOTIFY),
                        (BLE_SET_COMMAND_UUID, FLAG_WRITE),
                        (BLE_SET_CHARGING_UUID, FLAG_WRITE),
                        (BLE_SET_DISCHARGING_UUID, FLAG_WRITE),
                        (BLE_SET_CURRENT_UUID, FLAG_WRITE),
                        (BLE_SET_ATS_UUID, FLAG_WRITE),
                    ),
                ),
                (
                    BLE_INFO_SERVICE_UUID,
                    (
                        (BLE_MANUFACTURER_UUID, FLAG_READ),
                        (BLE_MODEL_NUMBER_UUID, FLAG_READ),
                        (BLE_FIRMWARE_REV_UUID, FLAG_READ),
                    ),
                ),
            ]
        )

        self._ble.gatts_write(self.HANDLE[BLE_MANUFACTURER_UUID], self._manufacturer)
        self._ble.gatts_write(self.HANDLE[BLE_MODEL_NUMBER_UUID], self._model)
        self._ble.gatts_write(self.HANDLE[BLE_FIRMWARE_REV_UUID], self._firmware)

        self.start_advertising()

    @staticmethod
    def _get_advertisement_payload(name=None, services=None, appearance=0):
        payload = bytearray()
        if name:
            payload += struct.pack("BB", len(name) + 1, _ADV_TYPE_NAME) + name

        if services:
            for uuid in services:
                b = bytes(uuid)
                if len(b) == 2:
                    payload += struct.pack("BB", 3, _ADV_TYPE_UUID16_COMPLETE) + b
                elif len(b) == 16:
                    payload += (
                        struct.pack("BB", len(b) + 1, _ADV_TYPE_UUID128_COMPLETE) + b
                    )

        return payload

    def start_advertising(self):

        if not self._ble:
            return

        adv_data = self._get_advertisement_payload(
            name=self._gap_name,
            services=[BLE_INFO_SERVICE_UUID, BLE_CORE_SERVICE_UUID],
            appearance=960,
        )
        self._ble.gap_advertise(100000, adv_data)

    def stop_advertising(self):
        self._ble.gap_advertise(None)

    def on_ble_irq(self, event, data):

        if event == _IRQ_CENTRAL_CONNECT:
            connection, addr_type, addr = data
            self._connection = connection
            self._state.active = True
            return self.stop_advertising()

        if event == _IRQ_CENTRAL_DISCONNECT:
            connection, _, _ = data
            self._connection = None
            self._state.active = False
            self.start_advertising()

        if event == _IRQ_GATTS_READ_REQUEST:
            connection, handle = data
            return self.on_read_state(connection, handle)

        if event == _IRQ_GATTS_WRITE:
            connection, attr_handle = data
            return self.on_write_state(connection, attr_handle)

    def on_read_state(self, connection, handle):

        if handle == self.HANDLE[BLE_BMS_UUID]:
            state = self._bms.state.get_ble_state()
            logger.info("BLE reading bms state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_INVERTER_UUID]:
            state = self._inverter.state.get_ble_state()
            logger.info("BLE reading inverter state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_PSU_UUID]:
            state = self._psu.state.get_ble_state()
            logger.info("BLE reading PSU state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_ESP_UUID]:
            state = self._wroom.state.get_ble_state()
            logger.info("BLE reading ESP state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_ATS_UUID]:
            state = self._ats.state.get_ble_state()
            logger.info("BLE reading BLE_ATS state", state, len(state))
            self._ble_write(handle, state)
            return

    def on_write_state(self, connection, handle):
        if not self._ble:
            return

        data = self._ble.gatts_read(handle)
        if data is None:
            return

        logger.info("BLE received data", data.hex())
        value = int.from_bytes(data, "big")

        if handle == self.HANDLE[BLE_SET_CHARGING_UUID]:
            logger.debug("Writing charging state", data, value, data == 0x01)
            if value:
                self._instructions.add(self._psu.on)
            else:
                self._instructions.add(self._psu.off)

        if handle == self.HANDLE[BLE_SET_DISCHARGING_UUID]:
            logger.debug("Writing discharging state", value)
            if value:
                self._instructions.add(self._inverter.on)
            else:
                self._instructions.add(self._inverter.off)

        if handle == self.HANDLE[BLE_SET_CURRENT_UUID]:
            logger.debug("Writing current state", value)
            self._instructions.add(self._psu.set_current, value)

        if handle == self.HANDLE[BLE_SET_ATS_UUID]:
            logger.debug("Writing ats state", value)
            if value:
                self._instructions.add(self._ats.enable)
            else:
                self._instructions.add(self._ats.disable)

        if handle == self.HANDLE[BLE_SET_COMMAND_UUID]:
            logger.debug("Writing command state", value)
            if value == COMMAND_PULL_HISTORY:
                self._instructions.add(self._inverter.state.pull_history)
                self._instructions.add(self._bms.state.pull_history)
                self._instructions.add(self._psu.state.pull_history)

    def notify(self, uuid, state):
        if not self._ble or self._connection is None:
            return

        if self.HANDLE.get(uuid):
            try:
                self._ble_write(self.HANDLE.get(uuid), state)
                self._ble_notify(self._connection, self.HANDLE.get(uuid), state)
            except OSError:
                pass

    def _ble_write(self, handle, data):
        try:
            self._ble.gatts_write(handle, data)
        except Exception as e:
            logger.critical(e)

    def _ble_notify(self, connection, handle, data):
        try:
            self._ble.gatts_notify(connection, handle, data)
        except OSError:
            pass

    @property
    def state(self):
        return self._state
