import asyncio

from logging import logger


class Telemetry:

    FREQUENCY = 1000

    _oled = None
    _ats = None
    _bms = None
    _inverter = None
    _psu = None
    _ble = None
    _storage = None
    _esp = None

    # a list of objects that support "report" method
    _channels = None

    # how often to collect and report data
    _frequency = None

    def __init__(
        self,
        ats=None,
        bms=None,
        inverter=None,
        psu=None,
        ble=None,
        esp=None,
        channels=None,
        frequency=FREQUENCY,
    ):
        self._ats = ats
        self._bms = bms
        self._inverter = inverter
        self._psu = psu
        self._ble = ble
        self._esp = esp

        self._channels = channels
        self._frequency = frequency

    async def run(self):
        logger.info("Running telemetry...")
        while True:
            await asyncio.sleep_ms(self._frequency)
