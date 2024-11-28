import asyncio

from logging import logger
from drivers.glyphs import GLYPHS


COLUMN_WIDTH = 16
HEADER_Y = 0
GLYPH_Y = 10
ERROR_Y = 27
ERROR_X = 1
METRIC_Y = 20
METRIC_X = 1


POSITIONS = {
    "psu": 0,
    "bms": 1,
    "inverter": 2,
    "storage": 3,
    "ats": 4,
    "esp": 5,
    "ble": 6,
}


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
        oled=None,
        ats=None,
        bms=None,
        inverter=None,
        psu=None,
        ble=None,
        storage=None,
        esp=None,
        channels=None,
        frequency=FREQUENCY,
    ):
        self._oled = oled
        self._ats = ats
        self._bms = bms
        self._inverter = inverter
        self._psu = psu
        self._ble = ble
        self._storage = storage
        self._esp = esp

        self._channels = channels
        self._frequency = frequency

    async def run(self):
        logger.info("Running telemetry...")
        while True:
            try:
                self.draw()
            except Exception as e:
                logger.error("Telemetry drawing failed")
                logger.critical(e)
            await asyncio.sleep_ms(self._frequency)

    def draw_headers(self):
        self._oled.glyph(COLUMN_WIDTH * POSITIONS["inverter"], HEADER_Y, GLYPHS["inv"])
        self._oled.glyph(COLUMN_WIDTH * POSITIONS["bms"], HEADER_Y, GLYPHS["bms"])
        self._oled.glyph(COLUMN_WIDTH * POSITIONS["psu"], HEADER_Y, GLYPHS["psu"])
        self._oled.glyph(
            COLUMN_WIDTH * POSITIONS["storage"], HEADER_Y, GLYPHS["storage"]
        )
        self._oled.glyph(COLUMN_WIDTH * POSITIONS["ats"], HEADER_Y, GLYPHS["ats"])
        self._oled.glyph(COLUMN_WIDTH * POSITIONS["esp"], HEADER_Y, GLYPHS["esp"])
        self._oled.glyph(COLUMN_WIDTH * POSITIONS["ble"], HEADER_Y, GLYPHS["ble"])

    def draw_state(self, x, state):
        glyph, value, unit = state.get_display_metric()
        if glyph:
            self._oled.glyph(x, GLYPH_Y, GLYPHS[glyph], width=16, height=10)
        self._oled.metric(x + METRIC_X, METRIC_Y, value, unit)
        self._oled.error(x + ERROR_X, ERROR_Y, state.internal_errors)

    def draw(self):
        if not self._oled.initialized():
            return

        self._oled.clear()
        self.draw_headers()
        self.draw_state(COLUMN_WIDTH * POSITIONS["ats"], self._ats.state)
        self.draw_state(COLUMN_WIDTH * POSITIONS["storage"], self._storage.state)
        self.draw_state(COLUMN_WIDTH * POSITIONS["esp"], self._esp.state)
        self.draw_state(COLUMN_WIDTH * POSITIONS["bms"], self._bms.state)
        self.draw_state(COLUMN_WIDTH * POSITIONS["inverter"], self._inverter.state)
        self.draw_state(COLUMN_WIDTH * POSITIONS["psu"], self._psu.state)
        self.draw_state(COLUMN_WIDTH * POSITIONS["ble"], self._ble.state)
        self._oled.show()
