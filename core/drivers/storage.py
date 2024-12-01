import os
import machine

from logging import logger
from drivers import BaseState


class StorageState(BaseState):
    NAME = "STORAGE"

    ERROR_NO_DEVICE = 1

    def set_display_metric(self, metric):
        self.display_metric_glyph = "na"


class StorageController:

    ENABLED = False
    CS_PIN = 10
    SCK_PIN = 12
    MOSI_PIN = 11
    MISO_PIN = 13

    _sd = None
    _state = None

    def __init__(
        self, cs=CS_PIN, sck=SCK_PIN, mosi=MOSI_PIN, miso=MISO_PIN, enabled=ENABLED
    ):

        self._state = StorageState()
        if not enabled:
            return

        try:
            self._sd = machine.SDCard(
                slot=2,
                width=1,
                sck=sck,
                miso=miso,
                mosi=mosi,
                cs=cs,
                freq=1320000,
            )

            vfs = os.VfsFat(self._sd)
            os.mount(vfs, "/sd")
            logger.info(
                f"Initialized Storage controller cs={cs}, sck={sck}, mosi={mosi}, miso={miso}"
            )

        except Exception as e:
            self._state.set_error(self._state.ERROR_NO_DEVICE)
            logger.critical("Failed to initialize storage controller")

    async def run(self):
        logger.info("Running Storage controller")
        while True:
            self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        return self._state
