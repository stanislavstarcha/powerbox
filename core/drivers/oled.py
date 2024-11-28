import framebuf
from machine import Pin, I2C

from lib.ssd1306 import SSD1306_I2C
from drivers.glyphs import GLYPHS

from logging import logger


class OLEDController:

    SDA_PIN = None
    SCL_PIN = None
    I2C_ADDRESS = 0x3C

    width = 128
    height = 32

    _oled = None
    _initialized = False

    def __init__(self, i2c=None, i2c_address=I2C_ADDRESS):
        try:
            self._oled = SSD1306_I2C(self.width, self.height, i2c, addr=i2c_address)
        except OSError as e:
            logger.warning("No OLED display found")
            return

        self._initialized = True
        logger.info("Initialized OLED display")

    def initialized(self):
        return self._initialized

    def syslog(self, message):
        if not self._initialized:
            return
        self._oled.fill(0)
        self._oled.text(message, 0, 10)
        self._oled.show()

    async def run(self):
        logger.info("Running OLED display...")
        if not self._initialized:
            return
        self._oled.show()

    def glyph(self, x, y, glyph, width=None, height=None):

        if width is not None:
            x_offset = (width - glyph["width"]) // 2
            x += x_offset

        if height is not None:
            y_offset = (height - glyph["height"]) // 2
            y += y_offset

        for row in range(glyph["height"]):
            row_data = glyph["bitmap"][row]

            for col in range(glyph["width"]):
                if row_data & (1 << (glyph["width"] - 1 - col)):
                    self._oled.pixel(x + col, y + row, 1)

    def metric(self, x, y, value, symbol=None):

        if value is None:
            return

        formatted = "{:02}".format(value)
        for idx, char in enumerate(formatted):
            self.glyph(x + idx * 4, y, GLYPHS[char])

        if symbol is not None:
            self.glyph(x + len(formatted) * 4, y, GLYPHS[symbol])

    def error(self, x, y, code):
        if not code:
            return

        formatted = "{:02}".format(code)
        self.glyph(x, y, GLYPHS["e"])
        for idx, char in enumerate(formatted):
            self.glyph(x + (idx + 1) * 4, y, GLYPHS[char])

    def show(self):
        self._oled.show()

    def clear(self):
        self._oled.fill(0)
