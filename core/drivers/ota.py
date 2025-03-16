import struct
import time
import network

from drivers import BaseState


from const import (
    PROFILE_KEY_WIFI_SSID,
    PROFILE_KEY_WIFI_PASSWORD,
)

from logging import logger
from lib.ota.update import OTA

from const import BLE_OTA_STATE_UUID


STATUS_IDLE = 0
STATUS_PREPARING = 1
STATUS_DOWNLOADING = 2
STATUS_UPDATING = 3
STATUS_ERROR = 4
STATUS_FINISHED = 5


class OTAState(BaseState):
    NAME = "OTA"
    BLE_STATE_UUID = BLE_OTA_STATE_UUID

    status = STATUS_IDLE
    progress = None

    def get_ble_state(self):
        logger.debug("Getting OTA BLE state")
        return struct.pack(
            ">BBB",
            self._pack(self.status),
            self._pack(self.progress),
            self._pack(self.internal_errors),
        )


class OTAController:
    def __init__(self, firmware_url, ssid=None, password=None):
        self._firmware_url = firmware_url
        self._ssid = ssid
        self._password = password
        self.state = OTAState()

    def update(self):
        self.connect_wifi()

    def download_firmware(self):
        logger.info("Downloading firmware from", self._firmware_url)
        self.state.status = STATUS_DOWNLOADING
        self.state.notify()

        with OTA(
            True,
            True,
            True,
            progress_callback=self.on_progress,
        ) as ota_update:
            ota_update.from_json(self._firmware_url)

    def on_progress(self, total, current):
        if total:
            progress = int(100 * current / total)
            if self.state.progress != progress:
                self.state.status = STATUS_UPDATING
                self.state.progress = progress
                self.state.notify()

    def on_profile_state(self, state):
        self._ssid = state.get(PROFILE_KEY_WIFI_SSID)
        self._password = state.get(PROFILE_KEY_WIFI_PASSWORD)
        logger.info("Profile state changed", self._ssid, self._password)

    def connect_wifi(self):
        logger.info("Connecting to wifi...", self._ssid, self._password)
        self.state.status = STATUS_PREPARING
        self.state.notify()

        wlan = network.WLAN(network.STA_IF)
        wlan.active(False)
        wlan.active(True)
        wlan.config(pm=wlan.PM_NONE)
        wlan.config(txpower=5)
        wlan.connect(self._ssid, self._password)

        for _ in range(20):  # Try for 10 seconds
            if wlan.isconnected():
                logger.info("Connected to wife:", wlan.ifconfig())
                self.download_firmware()
                return True
            time.sleep(1)

        logger.error("Failed to connect to wifi")
        self.state.status = STATUS_ERROR
        self.state.notify()

        return False
