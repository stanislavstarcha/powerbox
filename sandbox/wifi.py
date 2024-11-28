import asyncio
import network
import time

from drivers import BaseState

from logging import logger


class WIFIState(BaseState):
    NAME = "WIFI"
    ERROR_NO_NETWORK = 1
    connected = False


class WiFiController:

    ENABLED = False
    SSID = None
    PASSWORD = None
    ATTEMPTS = 10

    _connecting = False
    _connected = False
    _ssid = None
    _password = None
    _timeout = None

    _station = None
    _state = None

    def __init__(
        self,
        ssid=SSID,
        password=PASSWORD,
        enabled=ENABLED,
        attempts=ATTEMPTS,
        onconnect=None,
    ):

        self._enabled = enabled
        self._ssid = ssid
        self._password = password
        self._attempts = attempts
        self._state = WIFIState()
        self._station = network.WLAN(network.STA_IF)
        self._onconnect = onconnect

        if not ssid or not password or not enabled:
            self._enabled = False

    async def connect(self):

        if self._connecting:
            return

        logger.debug("Connecting to wifi network")
        self._connecting = True
        self._station.active(False)
        self._station.active(True)
        self._station.connect(self._ssid, self._password)

        attempts = 0
        while not self._station.isconnected():
            await asyncio.sleep(1)
            attempts += 1
            if attempts == self._attempts:
                self._state.connected = False
                self._state.set_error(self._state.ERROR_NO_NETWORK)
                return

        logger.debug("Connected to wifi successfully")
        self._connecting = False
        self._state.connected = True
        self._state.reset_error(self._state.ERROR_NO_NETWORK)
        if self._onconnect:
            self._onconnect(self)

    def connected(self):
        return self._state.connected

    async def run(self):
        while True:
            self._state.connected = self._station.isconnected()
            if not self._state.connected:
                print("connect to wifi")
                asyncio.create_task(self.connect())
            await self._state.sleep()

    def collect(self):
        return self._state
