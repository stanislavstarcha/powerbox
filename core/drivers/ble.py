import struct

from bluetooth import BLE, FLAG_READ, FLAG_WRITE, FLAG_NOTIFY
from micropython import const
from drivers import BaseState
import time

from logging import logger

from const import (
    BLE_CORE_SERVICE_UUID,
    BLE_ATS_STATE_UUID,
    BLE_BMS_STATE_UUID,
    BLE_INVERTER_STATE_UUID,
    BLE_PSU_STATE_UUID,
    BLE_MCU_STATE_UUID,
    BLE_OTA_STATE_UUID,
    BLE_HISTORY_STATE_UUID,
    BLE_RUN_COMMAND_UUID,
    BLE_INFO_SERVICE_UUID,
    BLE_MANUFACTURER_UUID,
    BLE_MODEL_NUMBER_UUID,
    BLE_FIRMWARE_REV_UUID,
    PROFILE_KEY_ATS,
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

COMMAND_PULL_HISTORY = const(0x01)

COMMAND_PSU_ENABLE = const(0x10)
COMMAND_PSU_DISABLE = const(0x11)
COMMAND_PSU_CURRENT = const(0x12)

COMMAND_INVERTER_ENABLE = const(0x20)
COMMAND_INVERTER_DISABLE = const(0x21)

COMMAND_ATS_ENABLE = const(0x30)
COMMAND_ATS_DISABLE = const(0x31)

COMMAND_CONF_SET_KEY = const(0x40)
COMMAND_CONF_PROFILE = const(0x41)
COMMAND_UPDATE_FIRMWARE = const(0x50)


class BLEState(BaseState):
    NAME = "BLE"

    active = False


class BLEServerController:

    _name = None
    _ble = None
    _state = None
    _connection = None
    _service = None

    HANDLE = {
        BLE_ATS_STATE_UUID: None,
        BLE_BMS_STATE_UUID: None,
        BLE_INVERTER_STATE_UUID: None,
        BLE_PSU_STATE_UUID: None,
        BLE_MCU_STATE_UUID: None,
        BLE_OTA_STATE_UUID: None,
        BLE_HISTORY_STATE_UUID: None,
        BLE_RUN_COMMAND_UUID: None,
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
        mcu=None,
        ats=None,
        ota=None,
        profile=None,
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
        self._mcu = mcu
        self._ats = ats
        self._ota = ota
        self._profile = profile

        self._bms.state.attach_ble(self)
        self._psu.state.attach_ble(self)
        self._inverter.state.attach_ble(self)
        self._mcu.state.attach_ble(self)
        self._ota.state.attach_ble(self)

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
                self.HANDLE[BLE_ATS_STATE_UUID],
                self.HANDLE[BLE_BMS_STATE_UUID],
                self.HANDLE[BLE_INVERTER_STATE_UUID],
                self.HANDLE[BLE_PSU_STATE_UUID],
                self.HANDLE[BLE_MCU_STATE_UUID],
                self.HANDLE[BLE_OTA_STATE_UUID],
                self.HANDLE[BLE_HISTORY_STATE_UUID],
                self.HANDLE[BLE_RUN_COMMAND_UUID],
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
                        (BLE_ATS_STATE_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_BMS_STATE_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_INVERTER_STATE_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_PSU_STATE_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_MCU_STATE_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_OTA_STATE_UUID, FLAG_READ | FLAG_NOTIFY),
                        (BLE_HISTORY_STATE_UUID, FLAG_NOTIFY),
                        (BLE_RUN_COMMAND_UUID, FLAG_WRITE),
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
            logger.info("BLE client connected")
            connection, addr_type, addr = data
            self._connection = connection
            self._state.active = True
            return self.stop_advertising()

        if event == _IRQ_CENTRAL_DISCONNECT:
            logger.info("BLE client disconnected")
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

        if handle == self.HANDLE[BLE_ATS_STATE_UUID]:
            state = self._ats.state.get_ble_state()
            logger.info("BLE reading ATS state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_BMS_STATE_UUID]:
            state = self._bms.state.get_ble_state()
            logger.info("BLE reading BMS state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_INVERTER_STATE_UUID]:
            state = self._inverter.state.get_ble_state()
            logger.debug("BLE reading Inverter state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_PSU_STATE_UUID]:
            state = self._psu.state.get_ble_state()
            logger.debug("BLE reading PSU state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_MCU_STATE_UUID]:
            state = self._mcu.state.get_ble_state()
            logger.debug("BLE reading MCU state", state, len(state))
            self._ble_write(handle, state)
            return

        if handle == self.HANDLE[BLE_OTA_STATE_UUID]:
            state = self._ota.state.get_ble_state()
            logger.debug("BLE reading OTA state", state, len(state))
            self._ble_write(handle, state)
            return

    def on_write_state(self, connection, handle):
        if not self._ble:
            return

        data = self._ble.gatts_read(handle)
        if data is None:
            logger.warning("BLE received no data")
            return

        logger.info("BLE received data", data.hex())
        if handle != self.HANDLE[BLE_RUN_COMMAND_UUID]:
            logger.warning("BLE not a run command")
            return

        subcommand = struct.unpack_from(">B", data, 0)[0]
        logger.info("BLE subcommand", subcommand)

        if subcommand == COMMAND_PULL_HISTORY:
            logger.debug("Pulling history via BLE command")
            self._instructions.add(self._inverter.state.pull_history)
            self._instructions.add(self._bms.state.pull_history)
            self._instructions.add(self._psu.state.pull_history)

        if subcommand == COMMAND_PSU_ENABLE:
            logger.debug("Turn on PSU via BLE command")
            self._instructions.add(self._psu.on)

        if subcommand == COMMAND_PSU_DISABLE:
            logger.debug("Turn off PSU via BLE command")
            self._instructions.add(self._psu.off)

        if subcommand == COMMAND_PSU_CURRENT:
            logger.debug("Set PSU current via BLE command")
            level = struct.unpack_from(">B", data, 1)[0]
            self._instructions.add(self._psu.set_current, level)

        if subcommand == COMMAND_INVERTER_ENABLE:
            logger.debug("Turn on INVERTER via BLE command")
            self._instructions.add(self._inverter.on)

        if subcommand == COMMAND_INVERTER_DISABLE:
            logger.debug("Turn off INVERTER via BLE command")
            self._instructions.add(self._inverter.off)

        if subcommand == COMMAND_ATS_ENABLE:
            logger.debug("Turn on ATS via BLE command")
            self._instructions.add(self._profile.set, PROFILE_KEY_ATS, b"\x01")
            self._instructions.add(self._ats.enable)

        if subcommand == COMMAND_ATS_DISABLE:
            logger.debug("Turn off ATS via BLE command")
            self._instructions.add(self._profile.set, PROFILE_KEY_ATS, b"\x00")
            self._instructions.add(self._ats.disable)

        if subcommand == COMMAND_CONF_SET_KEY:
            param = struct.unpack_from(">B", data, 1)[0]
            self._instructions.add(self._profile.set, param, data[2:])
            logger.debug("Set config key via BLE command", param, data[2:])

        if subcommand == COMMAND_CONF_PROFILE:
            logger.debug("Set profile via BLE command")

        if subcommand == COMMAND_UPDATE_FIRMWARE:
            logger.debug("Update firmware via BLE command")
            self._instructions.add(self._ota.update)

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
