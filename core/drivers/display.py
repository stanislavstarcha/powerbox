import asyncio
import time
import machine
import micropython
import gc
import random

import ili9488  # NOQA
import lvgl as lv  # NOQA
import lcd_bus  # NOQA

from logging import logger


ICON_ARROW_RIGHT = micropython.const(0xEAC9)
ICON_ARROW_UP = micropython.const(0xEACF)
ICON_ARROW_DOWN = micropython.const(0xEAD0)
ICON_BLE = micropython.const(0xE1A7)
ICON_BLE_ACTIVE = micropython.const(0xE1A8)
ICON_WARNING = micropython.const(0xE000)


class DisplayObjects:
    bms_voltage_label = None
    bms_voltage_cell_1 = None
    bms_voltage_cell_2 = None
    bms_voltage_cell_3 = None
    bms_voltage_cell_4 = None

    bms_temperature_label = None
    bms_temperature_mos = None
    bms_temperature_bat_1 = None
    bms_temperature_bat_2 = None

    version_label = None
    version = None

    avr = None
    avr_label = None

    ble = None

    psu_label = None
    psu_temperature = None
    psu_ac_voltage = None
    psu_tachometer = None

    inverter_label = None
    inverter_temperature = None
    inverter_ac_voltage = None
    inverter_tachometer = None

    power_label = None
    power = None
    power_timer = None
    power_in_glyph_a = None
    power_out_glyph_a = None
    power_in_glyph_b = None
    power_out_glyph_b = None

    capacity = None
    capacity_bar = None


class DisplayController:

    widgets = None

    def __init__(
        self,
        width=None,
        height=None,
        led_pin=None,
        mosi_pin=None,
        miso_pin=None,
        sck_pin=None,
        dc_pin=None,
        cs_pin=None,
        frequency=None,
    ):
        self.widgets = DisplayObjects()

        led = machine.Pin(led_pin, machine.Pin.OUT)
        led.on()

        spi_bus = machine.SPI.Bus(host=1, mosi=mosi_pin, miso=miso_pin, sck=sck_pin)
        logger.debug("Display SPI bus initialised", gc.mem_free())

        display_bus = lcd_bus.SPIBus(
            spi_bus=spi_bus,
            freq=frequency,
            dc=dc_pin,
            cs=cs_pin,
        )
        print("Display bus initialised", gc.mem_free())
        micropython.mem_info(True)

        frame_buffer = display_bus.allocate_framebuffer(
            25000, lcd_bus.MEMORY_INTERNAL | lcd_bus.MEMORY_DMA
        )

        display = ili9488.ILI9488(
            data_bus=display_bus,
            display_width=width,
            display_height=height,
            frame_buffer1=frame_buffer,
            reset_state=0,
            offset_x=0,
            offset_y=0,
            color_space=lv.COLOR_FORMAT.RGB888,
            color_byte_order=ili9488.BYTE_ORDER_RGB,
        )
        print("Display initialised", gc.mem_free())

        display.set_power(True)
        display.init()
        # display.set_backlight(10)
        display.set_rotation(lv.DISPLAY_ROTATION._270)

        self.create_widgets()

    async def run(self):
        logger.info("Running Display...")

        self.set_version("0.1.0")
        self.set_cell_voltage(3.23, 3.22, 3.21, 3.2)
        self.set_capacity(67)
        self.set_bms_temperature(27, 32, 33)
        self.set_psu_state(29, 38, 218, 3400)
        self.set_inverter_state(28, 232, 4500)
        self.set_power_consumption(True, 1800, "2:32")

        self.show_bms_state()
        self.show_inverter_state()
        self.show_psu_state()

        counter = 0
        start_time = time.time_ns()
        while True:
            counter += 1
            time_passed = time.time_ns() - start_time
            self._generata_random_state()

            # Update LVGL internal time
            tick = int(time_passed / 1000000)
            lv.tick_inc(tick)
            lv.task_handler()
            await asyncio.sleep_ms(1000)

    def create_widgets(self):

        self._screen = lv.screen_active()
        self._screen.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)

        self._screen.set_style_pad_all(0, lv.PART.MAIN)
        self._screen.set_style_margin_all(0, lv.PART.MAIN)
        self._screen.set_style_pad_gap(0, lv.PART.MAIN)

        col_dsc = [40] * 12 + [lv.GRID_TEMPLATE_LAST]
        row_dsc = [24] * 13 + [lv.GRID_TEMPLATE_LAST]

        self._screen.set_style_grid_column_dsc_array(col_dsc, lv.PART.MAIN)
        self._screen.set_style_grid_row_dsc_array(row_dsc, lv.PART.MAIN)

        # cell voltage
        self.widgets.bms_voltage_label = self.create_label(
            0,
            0,
            "Напруга комірок",
            col_span=4,
            font_size=12,
            color="grey",
        )
        self.widgets.bms_voltage_cell_1 = self.create_label(0, 1, font_size=12)
        self.widgets.bms_voltage_cell_2 = self.create_label(1, 1, font_size=12)
        self.widgets.bms_voltage_cell_3 = self.create_label(2, 1, font_size=12)
        self.widgets.bms_voltage_cell_4 = self.create_label(3, 1, font_size=12)

        # battery temperature
        self.widgets.bms_temperature_label = self.create_label(
            5,
            0,
            "Температура",
            col_span=3,
            font_size=12,
            color="grey",
        )
        self.widgets.bms_temperature_mos = self.create_label(5, 1, font_size=12)
        self.widgets.bms_temperature_bat_1 = self.create_label(6, 1, font_size=12)
        self.widgets.bms_temperature_bat_2 = self.create_label(7, 1, font_size=12)

        # ats mode
        self.widgets.avr_label = self.create_label(
            8,
            0,
            "АВР",
            col_span=2,
            font_size=12,
            color="grey",
            is_hidden=False,
        )
        self.widgets.avr = self.create_label(
            8,
            1,
            "Мережа",
            col_span=2,
            font_size=12,
            is_hidden=False,
        )

        # version
        self.widgets.version_label = self.create_label(
            10,
            0,
            "Версія",
            font_size=12,
            color="grey",
            is_hidden=False,
        )
        self.widgets.version = self.create_label(
            10,
            1,
            font_size=12,
            is_hidden=False,
        )

        self.widgets.ble = self.create_glyph(
            11, 0, ICON_BLE, row_span=2, is_hidden=False
        )

        # psu data
        self.widgets.psu_label = self.create_label(
            0,
            8,
            "Блок живлення",
            col_span=3,
            font_size=12,
            color="grey",
        )
        self.widgets.psu_temperature = self.create_label(0, 9, col_span=3, font_size=12)
        self.widgets.psu_ac_voltage = self.create_label(
            0, 10, col_span=3, row_span=2, font_size=24
        )
        self.widgets.psu_tachometer = self.create_label(0, 12, col_span=3, font_size=12)

        # capacity
        self.widgets.capacity = self.create_label(
            3, 2, col_span=6, row_span=5, font_size=120
        )
        self.widgets.capacity_bar = self.create_bar(3, 7, col_span=6)

        # inv data
        self.widgets.inverter_label = self.create_label(
            9, 8, "Інвертор", col_span=3, font_size=12, color="grey"
        )
        self.widgets.inverter_temperature = self.create_label(
            9, 9, col_span=3, font_size=12
        )
        self.widgets.inverter_ac_voltage = self.create_label(
            9, 10, col_span=3, row_span=2, font_size=24
        )
        self.widgets.inverter_tachometer = self.create_label(
            9, 12, col_span=3, font_size=12
        )

        # power stats
        self.widgets.power_label = self.create_label(
            3, 9, "Споживання", col_span=6, font_size=12, color="grey"
        )
        self.widgets.power = self.create_label(
            4, 10, col_span=4, row_span=2, font_size=24
        )
        self.widgets.power_timer = self.create_label(
            3, 12, col_span=6, font_size=12, color="grey"
        )

        # power direction
        self.widgets.power_in_glyph_a = self.create_glyph(
            3, 10, ICON_ARROW_RIGHT, row_span=2
        )
        self.widgets.power_out_glyph_a = self.create_glyph(
            8, 10, ICON_ARROW_RIGHT, row_span=2
        )
        self.widgets.power_in_glyph_b = self.create_glyph(
            3, 8, ICON_ARROW_UP, col_span=6
        )
        self.widgets.power_out_glyph_b = self.create_glyph(
            3, 8, ICON_ARROW_DOWN, col_span=6
        )

        # error
        self.widgets.error_glyph = self.create_glyph(
            10, 4, ICON_WARNING, col_span=2, color="red"
        )
        self.widgets.error_label = self.create_label(
            10, 5, "Помилка", col_span=2, font_size=12, color="red"
        )
        self.widgets.error = self.create_label(
            10, 6, col_span=2, font_size=12, color="red"
        )

        self._screen.set_layout(lv.LAYOUT.GRID)
        print("Created widgets", gc.mem_free())

    def create_glyph(
        self, col, row, code, col_span=1, row_span=1, color="white", is_hidden=True
    ):
        glyph = lv.label(self._screen)
        glyph.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        glyph.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        glyph.set_style_text_font(lv.font_material_24, 0)
        glyph.set_style_text_color(self.color_to_hex(color), 0)
        glyph.set_text(chr(code))
        glyph.set_grid_cell(
            lv.GRID_ALIGN.CENTER, col, col_span, lv.GRID_ALIGN.CENTER, row, row_span
        )
        if is_hidden:
            self._hide_widget(glyph)
        return glyph

    def create_bar(self, col, row, col_span=1, row_span=1, is_hidden=True):
        bar = lv.bar(self._screen)
        bar.set_size(200, 20)
        bar.set_value(75, lv.ANIM.OFF)

        bar.set_style_bg_color(self.color_to_hex("green"), lv.PART.INDICATOR)

        bar.set_style_radius(3, lv.PART.MAIN)
        bar.set_style_radius(3, lv.PART.INDICATOR)
        bar.set_grid_cell(
            lv.GRID_ALIGN.CENTER, col, col_span, lv.GRID_ALIGN.CENTER, row, row_span
        )
        if is_hidden:
            self._hide_widget(bar)
        return bar

    def create_label(
        self,
        col,
        row,
        t="",
        col_span=1,
        row_span=1,
        font_size=14,
        color="white",
        is_hidden=True,
    ):
        label = lv.label(self._screen)
        label.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        label.set_style_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT, 0)
        label.set_style_text_color(self.color_to_hex(color), 0)

        if font_size == 12:
            label.set_style_text_font(lv.font_roboto_12, 0)

        if font_size == 120:
            label.set_style_text_font(lv.font_roboto_120, 0)

        if font_size == 10:
            label.set_style_text_font(lv.font_montserrat_10, 0)

        if font_size == 24:
            label.set_style_text_font(lv.font_roboto_24, 0)

        label.set_text(t)
        label.set_grid_cell(
            lv.GRID_ALIGN.CENTER, col, col_span, lv.GRID_ALIGN.CENTER, row, row_span
        )
        if is_hidden:
            self._hide_widget(label)

        return label

    @staticmethod
    def color_to_hex(color):
        if color == "white":
            return lv.color_hex(0x000000)

        if color == "grey":
            return lv.color_hex(0x888888)

        if color == "red":
            return lv.color_hex(0x44FFFF)

        if color == "green":
            return lv.color_hex(0xFF44FF)

        return lv.color_hex(0x000000)

    def set_cell_voltage(self, v1, v2, v3, v4):
        self.widgets.bms_voltage_cell_1.set_text(f"{v1} В")
        self.widgets.bms_voltage_cell_2.set_text(f"{v2} В")
        self.widgets.bms_voltage_cell_3.set_text(f"{v3} В")
        self.widgets.bms_voltage_cell_4.set_text(f"{v4} В")

    def set_ats_mode(self, mode):
        pass

    def set_bms_temperature(
        self, temperature_mos, bms_temperature_bat_1, bms_temperature_bat_2
    ):
        self.widgets.bms_temperature_mos.set_text(f"{temperature_mos}°С")
        self.widgets.bms_temperature_bat_1.set_text(f"{bms_temperature_bat_1}°С")
        self.widgets.bms_temperature_bat_2.set_text(f"{bms_temperature_bat_2}°С")

    def set_version(self, version):
        self.widgets.version.set_text(version)

    def set_error(self, code):
        self.widgets.error.set_text(code)

    def set_capacity(self, value):
        self.widgets.capacity.set_text(f"{value}%")
        self.widgets.capacity_bar.set_value(value, lv.ANIM.OFF)

    def set_psu_state(self, t1, t2, ac_voltage, tachometer):
        self.widgets.psu_temperature.set_text(f"{t1}°С / {t2}°С")
        self.widgets.psu_ac_voltage.set_text(f"{ac_voltage}В")
        self.widgets.psu_tachometer.set_text(f"{tachometer} об/хв")

    def set_inverter_state(self, temperature, ac_voltage, tachometer):
        self.widgets.inverter_temperature.set_text(f"{temperature}°С")
        self.widgets.inverter_ac_voltage.set_text(f"{ac_voltage}В")
        self.widgets.inverter_tachometer.set_text(f"{tachometer} об/хв")

    def set_power_consumption(self, direction, power, seconds):
        self.widgets.power.set_text(f"{power} Вт")
        if direction:
            self.widgets.power_timer.set_text(f"До повного розряду {seconds}")
        else:
            self.widgets.power_timer.set_text(f"До повного заряду {seconds}")

    def show_bms_state(self):
        self._show_widget(self.widgets.bms_voltage_label)
        self._show_widget(self.widgets.bms_temperature_label)
        self._show_widget(self.widgets.power_label)

        self._show_widget(self.widgets.capacity)
        self._show_widget(self.widgets.capacity_bar)

        self._show_widget(self.widgets.bms_voltage_cell_1)
        self._show_widget(self.widgets.bms_voltage_cell_2)
        self._show_widget(self.widgets.bms_voltage_cell_3)
        self._show_widget(self.widgets.bms_voltage_cell_4)

        self._show_widget(self.widgets.bms_temperature_mos)
        self._show_widget(self.widgets.bms_temperature_bat_1)
        self._show_widget(self.widgets.bms_temperature_bat_2)

        self._show_widget(self.widgets.power)

    def show_psu_state(self):
        self._show_widget(self.widgets.psu_label)
        self._show_widget(self.widgets.psu_temperature)
        self._show_widget(self.widgets.psu_tachometer)
        self._show_widget(self.widgets.psu_ac_voltage)
        self._show_widget(self.widgets.power_in_glyph_a)
        self._show_widget(self.widgets.power_in_glyph_b)
        self._show_widget(self.widgets.power_timer)

    def hide_psu_state(self):
        self._hide_widget(self.widgets.psu_label)
        self._hide_widget(self.widgets.psu_temperature)
        self._hide_widget(self.widgets.psu_tachometer)
        self._hide_widget(self.widgets.psu_ac_voltage)
        self._hide_widget(self.widgets.power_in_glyph_a)
        self._hide_widget(self.widgets.power_in_glyph_b)
        self._hide_widget(self.widgets.power_timer)

    def show_inverter_state(self):
        self._show_widget(self.widgets.inverter_label)
        self._show_widget(self.widgets.inverter_temperature)
        self._show_widget(self.widgets.inverter_tachometer)
        self._show_widget(self.widgets.inverter_ac_voltage)
        self._show_widget(self.widgets.power_out_glyph_a)
        self._show_widget(self.widgets.power_out_glyph_b)
        self._show_widget(self.widgets.power_timer)

    def hide_inverter_state(self):
        self._hide_widget(self.widgets.inverter_label)
        self._hide_widget(self.widgets.inverter_temperature)
        self._hide_widget(self.widgets.inverter_tachometer)
        self._hide_widget(self.widgets.inverter_ac_voltage)
        self._hide_widget(self.widgets.power_out_glyph_a)
        self._hide_widget(self.widgets.power_out_glyph_b)
        self._hide_widget(self.widgets.power_timer)

    def _hide_widget(self, widget):
        widget.add_flag(lv.obj.FLAG.HIDDEN)

    def _show_widget(self, widget):
        widget.remove_flag(lv.obj.FLAG.HIDDEN)

    def _generata_random_state(self):
        is_charging = random.randint(0, 1)

        if is_charging:
            self.set_power_consumption(
                False, power=random.randint(16, 42), seconds=random.randint(0, 3600)
            )

            self.set_psu_state(
                t1=random.randint(16, 42),
                t2=random.randint(16, 42),
                ac_voltage=random.randint(207, 230),
                tachometer=random.randint(
                    1000,
                    10000,
                ),
            )

            self.hide_inverter_state()
            self.show_psu_state()

        else:
            self.set_power_consumption(
                True, power=random.randint(16, 42), seconds=random.randint(0, 3600)
            )

            self.set_inverter_state(
                temperature=random.randint(16, 42),
                ac_voltage=random.randint(207, 230),
                tachometer=random.randint(
                    1000,
                    4500,
                ),
            )

            self.hide_psu_state()
            self.show_inverter_state()

        self.set_capacity(random.randint(0, 100))
        self.set_bms_temperature(
            temperature_mos=random.randint(16, 42),
            bms_temperature_bat_1=random.randint(16, 42),
            bms_temperature_bat_2=random.randint(16, 42),
        )

        self.set_cell_voltage(
            v1=random.randint(280, 340) / 100,
            v2=random.randint(280, 340) / 100,
            v3=random.randint(280, 340) / 100,
            v4=random.randint(280, 340) / 100,
        )
