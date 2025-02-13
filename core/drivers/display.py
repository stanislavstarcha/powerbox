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

BUFFER_SIZE = 65535


ICON_ARROW_RIGHT = micropython.const(0xEAC9)
ICON_ARROW_UP = micropython.const(0xEACF)
ICON_ARROW_DOWN = micropython.const(0xEAD0)
ICON_BLE = micropython.const(0xE1A7)
ICON_BLE_ACTIVE = micropython.const(0xE1A8)
ICON_WARNING = micropython.const(0xE000)
ICON_BATTERY = micropython.const(0xF156)
ICON_CITY = micropython.const(0xE7EE)
ICON_DOTS = micropython.const(0xE5D3)
ICON_MCU = micropython.const(0xE322)
ICON_HEART = micropython.const(0xE87D)

DEVICE_BMS = micropython.const(0)
DEVICE_PSU = micropython.const(1)
DEVICE_INVERTER = micropython.const(2)
DEVICE_MCU = micropython.const(3)


class BaseScreen:

    _screen = None

    def __init__(self):
        self._screen = lv.obj(None)

    @staticmethod
    def hide_widget(widget):
        widget.add_flag(lv.obj.FLAG.HIDDEN)

    @staticmethod
    def show_widget(widget):
        widget.remove_flag(lv.obj.FLAG.HIDDEN)

    def get_screen(self):
        return self._screen

    def create_widgets(self):
        pass

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
            self.hide_widget(glyph)
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
            self.hide_widget(bar)
        return bar

    def create_label(
        self,
        col=None,
        row=None,
        t="",
        col_span=1,
        row_span=1,
        font_size=12,
        color="white",
        x=None,
        y=None,
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

        if x is not None:
            label.set_style_x(x, lv.PART.MAIN)

        if y is not None:
            label.set_style_y(y, lv.PART.MAIN)

        label.set_text(t)

        if col is not None and row is not None:
            label.set_grid_cell(
                lv.GRID_ALIGN.CENTER,
                col,
                col_span,
                lv.GRID_ALIGN.CENTER,
                row,
                row_span,
            )

        if is_hidden:
            self.hide_widget(label)

        return label

    def create_arc(
        self,
        x=0,
        y=0,
        rotation=0,
        start_angle=0,
        end_angle=360,
        radius=53,
        thickness=5,
        value=None,
    ):

        arc = lv.arc(self._screen)

        arc.set_x(x)
        arc.set_y(y)
        arc.set_size(radius * 2, radius * 2)
        arc.set_rotation(rotation)

        arc.remove_style(None, lv.PART.KNOB)

        arc.set_style_arc_rounded(False, lv.PART.MAIN | lv.STATE.DEFAULT)
        arc.set_style_arc_rounded(False, lv.PART.INDICATOR | lv.STATE.DEFAULT)

        arc.set_style_arc_width(thickness, lv.PART.MAIN | lv.STATE.DEFAULT)
        arc.set_style_arc_width(thickness, lv.PART.INDICATOR | lv.STATE.DEFAULT)

        if value:
            arc.set_style_arc_color(self.color_to_hex("grey"), lv.PART.MAIN)
            arc.set_bg_angles(start_angle, end_angle)

            offset = int(value * (end_angle - start_angle) / 100)
            arc.set_style_arc_color(self.color_to_hex("white"), lv.PART.INDICATOR)
            arc.set_angles(start_angle + offset, end_angle)
        else:
            arc.remove_style(None, lv.PART.INDICATOR)

            arc.set_style_arc_color(self.color_to_hex("white"), lv.PART.MAIN)
            arc.set_bg_angles(start_angle, end_angle)

        return arc

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


class ActiveScreen(BaseScreen):

    errors = None

    error_glyph = None
    error_label = None
    error = None

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

    ats = None
    ats_label = None

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

    mcu_label = None
    mcu_glyph = None
    mcu_temperature = None

    mcu_health_glyph = None

    def __init__(self):
        self.errors = [0, 0, 0, 0]
        super(ActiveScreen, self).__init__()

    def set_cell_voltage(self, v1, v2, v3, v4):
        self.bms_voltage_cell_1.set_text(f"{v1} В")
        self.bms_voltage_cell_2.set_text(f"{v2} В")
        self.bms_voltage_cell_3.set_text(f"{v3} В")
        self.bms_voltage_cell_4.set_text(f"{v4} В")

    def set_ats_mode(self, mode):
        if mode == 0:
            self.ats.set_text(chr(ICON_DOTS))

        if mode == 1:
            self.ats.set_text(chr(ICON_CITY))

        if mode == 2:
            self.ats.set_text(chr(ICON_BATTERY))

    def set_bms_temperature(
        self, temperature_mos, bms_temperature_bat_1, bms_temperature_bat_2
    ):
        self.bms_temperature_mos.set_text(f"{temperature_mos}°С")
        self.bms_temperature_bat_1.set_text(f"{bms_temperature_bat_1}°С")
        self.bms_temperature_bat_2.set_text(f"{bms_temperature_bat_2}°С")

    def set_version(self, version):
        self.version.set_text(version)

    def set_capacity(self, value):
        self.capacity.set_text(f"{value}%")
        self.capacity_bar.set_value(value, lv.ANIM.OFF)

    def set_psu_state(self, t1, t2, ac_voltage, tachometer):
        self.psu_temperature.set_text(f"{t1}°С / {t2}°С")
        self.psu_ac_voltage.set_text(f"{ac_voltage}В")
        self.psu_tachometer.set_text(f"{tachometer} об/хв")

    def set_inverter_state(self, temperature, ac_voltage, tachometer):
        self.inverter_temperature.set_text(f"{temperature}°С")
        self.inverter_ac_voltage.set_text(f"{ac_voltage}В")
        self.inverter_tachometer.set_text(f"{tachometer} об/хв")

    def set_power_consumption(self, direction, power, seconds):
        self.power.set_text(f"{power} Вт")
        if direction:
            self.power_timer.set_text(f"До повного розряду {seconds}")
        else:
            self.power_timer.set_text(f"До повного заряду {seconds}")

    def show_error_state(self):
        self.show_widget(self.error_glyph)
        self.show_widget(self.error_label)
        self.show_widget(self.error)

    def hide_error_state(self):
        self.hide_widget(self.error_glyph)
        self.hide_widget(self.error_label)
        self.hide_widget(self.error)

    def show_bms_state(self):
        self.show_widget(self.bms_voltage_label)
        self.show_widget(self.bms_temperature_label)
        self.show_widget(self.power_label)

        self.show_widget(self.capacity)
        self.show_widget(self.capacity_bar)

        self.show_widget(self.bms_voltage_cell_1)
        self.show_widget(self.bms_voltage_cell_2)
        self.show_widget(self.bms_voltage_cell_3)
        self.show_widget(self.bms_voltage_cell_4)

        self.show_widget(self.bms_temperature_mos)
        self.show_widget(self.bms_temperature_bat_1)
        self.show_widget(self.bms_temperature_bat_2)

        self.show_widget(self.power)

    def show_psu_state(self):
        self.show_widget(self.psu_label)
        self.show_widget(self.psu_temperature)
        self.show_widget(self.psu_tachometer)
        self.show_widget(self.psu_ac_voltage)
        self.show_widget(self.power_in_glyph_a)
        self.show_widget(self.power_in_glyph_b)
        self.show_widget(self.power_timer)

    def hide_psu_state(self):
        self.hide_widget(self.psu_label)
        self.hide_widget(self.psu_temperature)
        self.hide_widget(self.psu_tachometer)
        self.hide_widget(self.psu_ac_voltage)
        self.hide_widget(self.power_in_glyph_a)
        self.hide_widget(self.power_in_glyph_b)
        self.hide_widget(self.power_timer)

    def show_inverter_state(self):
        self.show_widget(self.inverter_label)
        self.show_widget(self.inverter_temperature)
        self.show_widget(self.inverter_tachometer)
        self.show_widget(self.inverter_ac_voltage)
        self.show_widget(self.power_out_glyph_a)
        self.show_widget(self.power_out_glyph_b)
        self.show_widget(self.power_timer)

    def hide_inverter_state(self):
        self.hide_widget(self.inverter_label)
        self.hide_widget(self.inverter_temperature)
        self.hide_widget(self.inverter_tachometer)
        self.hide_widget(self.inverter_ac_voltage)
        self.hide_widget(self.power_out_glyph_a)
        self.hide_widget(self.power_out_glyph_b)
        self.hide_widget(self.power_timer)

    def set_error(self, device_id, error):
        self.errors[device_id] = error
        if any(self.errors):
            codes = []

            if self.errors[DEVICE_BMS]:
                codes.append(f"В{self.errors[DEVICE_BMS]}")

            if self.errors[DEVICE_PSU]:
                codes.append(f"Р{self.errors[DEVICE_PSU]}")

            if self.errors[DEVICE_INVERTER]:
                codes.append(f"І{self.errors[DEVICE_INVERTER]}")

            if self.errors[DEVICE_MCU]:
                codes.append(f"М{self.errors[DEVICE_MCU]}")

            self.error.set_text(" ".join(codes))
            self.show_error_state()

    def reset_error(self, device_id):
        self.errors[device_id] = 0
        if not any(self.errors):
            self.hide_error_state()

    def create_widgets(self):
        self._screen.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)

        self._screen.set_style_pad_all(0, lv.PART.MAIN)
        self._screen.set_style_margin_all(0, lv.PART.MAIN)
        self._screen.set_style_pad_gap(0, lv.PART.MAIN)

        col_dsc = [40] * 12 + [lv.GRID_TEMPLATE_LAST]
        row_dsc = [24] * 13 + [lv.GRID_TEMPLATE_LAST]

        self._screen.set_style_grid_column_dsc_array(col_dsc, lv.PART.MAIN)
        self._screen.set_style_grid_row_dsc_array(row_dsc, lv.PART.MAIN)

        # cell voltage
        self.bms_voltage_label = self.create_label(
            0,
            0,
            "Напруга комірок",
            col_span=4,
            font_size=12,
            color="grey",
        )
        self.bms_voltage_cell_1 = self.create_label(0, 1, font_size=12)
        self.bms_voltage_cell_2 = self.create_label(1, 1, font_size=12)
        self.bms_voltage_cell_3 = self.create_label(2, 1, font_size=12)
        self.bms_voltage_cell_4 = self.create_label(3, 1, font_size=12)

        # battery temperature
        self.bms_temperature_label = self.create_label(
            5,
            0,
            "Температура",
            col_span=3,
            font_size=12,
            color="grey",
        )
        self.bms_temperature_mos = self.create_label(5, 1, font_size=12)
        self.bms_temperature_bat_1 = self.create_label(6, 1, font_size=12)
        self.bms_temperature_bat_2 = self.create_label(7, 1, font_size=12)

        # ats mode
        self.ats_label = self.create_label(
            8,
            0,
            "АВР",
            col_span=2,
            font_size=12,
            color="grey",
            is_hidden=False,
        )
        self.ats = self.create_glyph(
            8,
            1,
            code=ICON_DOTS,
            col_span=2,
            is_hidden=False,
        )

        # version
        self.version_label = self.create_label(
            10,
            0,
            "Версія",
            font_size=12,
            color="grey",
            is_hidden=False,
        )
        self.version = self.create_label(
            10,
            1,
            font_size=12,
            is_hidden=False,
        )

        self.ble = self.create_glyph(11, 0, ICON_BLE, row_span=2, is_hidden=False)

        # mcu data
        self.mcu_memory = self.create_label(
            0,
            4,
            col_span=2,
            font_size=12,
            color="grey",
            is_hidden=False,
        )

        self.mcu_glyph = self.create_glyph(
            0,
            5,
            code=ICON_MCU,
            col_span=2,
            color="grey",
            is_hidden=False,
        )

        self.mcu_temperature = self.create_label(
            0,
            6,
            col_span=2,
            color="grey",
            is_hidden=False,
        )

        # psu data
        self.psu_label = self.create_label(
            0,
            8,
            "Блок живлення",
            col_span=3,
            font_size=12,
            color="grey",
        )
        self.psu_temperature = self.create_label(0, 9, col_span=3, font_size=12)
        self.psu_ac_voltage = self.create_label(
            0, 10, col_span=3, row_span=2, font_size=24
        )
        self.psu_tachometer = self.create_label(0, 12, col_span=3, font_size=12)

        # capacity
        self.capacity = self.create_label(3, 2, col_span=6, row_span=5, font_size=120)
        self.capacity_bar = self.create_bar(3, 7, col_span=6)

        # inv data
        self.inverter_label = self.create_label(
            9, 8, "Інвертор", col_span=3, font_size=12, color="grey"
        )
        self.inverter_temperature = self.create_label(9, 9, col_span=3, font_size=12)
        self.inverter_ac_voltage = self.create_label(
            9, 10, col_span=3, row_span=2, font_size=24
        )
        self.inverter_tachometer = self.create_label(9, 12, col_span=3, font_size=12)

        # power stats
        self.power_label = self.create_label(
            3, 9, "Споживання", col_span=6, font_size=12, color="grey"
        )
        self.power = self.create_label(4, 10, col_span=4, row_span=2, font_size=24)
        self.power_timer = self.create_label(
            3, 12, col_span=6, font_size=12, color="grey"
        )

        # power direction
        self.power_in_glyph_a = self.create_glyph(3, 10, ICON_ARROW_RIGHT, row_span=2)
        self.power_out_glyph_a = self.create_glyph(8, 10, ICON_ARROW_RIGHT, row_span=2)
        self.power_in_glyph_b = self.create_glyph(3, 8, ICON_ARROW_UP, col_span=6)
        self.power_out_glyph_b = self.create_glyph(3, 8, ICON_ARROW_DOWN, col_span=6)

        # error
        self.error_glyph = self.create_glyph(
            10, 4, ICON_WARNING, col_span=2, color="red"
        )
        self.error_label = self.create_label(
            10, 5, "Помилка", col_span=2, font_size=12, color="red"
        )
        self.error = self.create_label(10, 6, col_span=2, font_size=12, color="red")

        self._screen.set_layout(lv.LAYOUT.GRID)

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


class SleepScreen(BaseScreen):

    BASE_X = 200
    BASE_Y = 120

    progress_body = None
    left_eye = None
    right_eye = None
    capacity = None

    def create_widgets(self):

        self._screen.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)

        self._screen.set_style_pad_all(0, lv.PART.MAIN)
        self._screen.set_style_margin_all(0, lv.PART.MAIN)
        self._screen.set_style_pad_gap(0, lv.PART.MAIN)

        self.capacity = self.create_label(
            None,
            None,
            is_hidden=False,
            x=self.BASE_X + 45,
            y=self.BASE_Y + 50,
        )
        self.progress_body = self.create_arc(
            x=self.BASE_X,
            y=self.BASE_Y,
            rotation=340,
            start_angle=0,
            end_angle=290,
            radius=53,
            thickness=5,
            value=90,
        )

        # head
        self.create_arc(
            x=self.BASE_X + 46,
            y=self.BASE_Y - 26,
            rotation=200,
            start_angle=0,
            end_angle=32,
            radius=43,
            thickness=5,
        )
        self.create_arc(
            x=self.BASE_X - 15,
            y=self.BASE_Y - 35,
            rotation=330,
            start_angle=0,
            end_angle=20,
            radius=43,
            thickness=5,
        )

        self.create_arc(
            x=self.BASE_X + 17,
            y=self.BASE_Y - 3,
            rotation=280,
            start_angle=0,
            end_angle=32,
            radius=43,
            thickness=5,
        )
        self.create_arc(
            x=self.BASE_X + 67,
            y=self.BASE_Y - 3,
            rotation=230,
            start_angle=0,
            end_angle=20,
            radius=43,
            thickness=5,
        )
        self.create_arc(
            x=self.BASE_X + 15,
            y=self.BASE_Y - 37,
            rotation=350,
            start_angle=0,
            end_angle=62,
            radius=43,
            thickness=5,
        )

        self.create_arc(
            x=self.BASE_X + 44,
            y=self.BASE_Y - 8,
            rotation=55,
            start_angle=0,
            end_angle=90,
            radius=26,
            thickness=5,
        )

        # arc(scr, x=self.BASE_X+57, y=self.BASE_Y+12, rotation=60, start_angle=0, end_angle=110, radius=6, thickness=3,)
        # arc(scr, x=self.BASE_X+70, y=self.BASE_Y+18, rotation=60, start_angle=0, end_angle=110, radius=6, thickness=3,)

        # eyes
        self.left_eye = self.create_arc(
            x=self.BASE_X + 57,
            y=self.BASE_Y + 12,
            rotation=60,
            start_angle=0,
            end_angle=110,
            radius=6,
            thickness=3,
        )
        self.right_eye = self.create_arc(
            x=self.BASE_X + 70,
            y=self.BASE_Y + 18,
            rotation=60,
            start_angle=0,
            end_angle=110,
            radius=6,
            thickness=3,
        )

    def set_eyes(self, is_open):

        if is_open:
            self.left_eye.set_bg_end_angle(350)
            self.right_eye.set_bg_end_angle(350)
        else:
            self.left_eye.set_bg_end_angle(110)
            self.right_eye.set_bg_end_angle(110)

    def set_capacity(self, value):
        start_angle = self.progress_body.get_bg_angle_start()
        end_angle = self.progress_body.get_bg_angle_end()
        offset = int(value * (end_angle - start_angle) / 100)
        self.progress_body.set_angles(start_angle + offset, end_angle)
        self.capacity.set_text(f"{value}%")

    def generate_random_state(self):
        self.set_eyes(random.randint(0, 1))
        self.set_capacity(random.randint(0, 100))


class DisplayController:

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
        reset_pin=None,
        frequency=None,
    ):

        spi_bus = machine.SPI.Bus(host=2, mosi=mosi_pin, miso=miso_pin, sck=sck_pin)
        display_bus = lcd_bus.SPIBus(
            spi_bus=spi_bus,
            freq=frequency,
            dc=dc_pin,
            cs=cs_pin,
        )

        frame_buffer = display_bus.allocate_framebuffer(
            BUFFER_SIZE, lcd_bus.MEMORY_SPIRAM
        )

        frame_buffer_2 = display_bus.allocate_framebuffer(
            BUFFER_SIZE, lcd_bus.MEMORY_SPIRAM
        )

        display = ili9488.ILI9488(
            data_bus=display_bus,
            display_width=width,
            display_height=height,
            frame_buffer1=frame_buffer,
            frame_buffer2=frame_buffer_2,
            offset_x=0,
            offset_y=0,
            color_space=lv.COLOR_FORMAT.RGB888,
            # color_byte_order=ili9488.BYTE_ORDER_RGB,
        )

        reset = machine.Pin(reset_pin, machine.Pin.OUT)
        reset.on()

        display.init()
        display.set_power(True)
        display.set_rotation(lv.DISPLAY_ROTATION._270)

        led = machine.Pin(led_pin, machine.Pin.OUT)
        led.on()

        self.active_screen = ActiveScreen()
        self.sleep_screen = SleepScreen()
        self.active_screen.create_widgets()
        self.sleep_screen.create_widgets()
        self.on_sleep()

    async def run(self):
        logger.info("Running Display...")

        self.active_screen.show_bms_state()
        self.active_screen.show_inverter_state()
        self.active_screen.show_psu_state()

        counter = 0
        start_time = time.time_ns()
        while True:
            counter += 1
            time_passed = time.time_ns() - start_time
            self.active_screen._generata_random_state()
            self.sleep_screen.generate_random_state()

            # Update LVGL internal time
            tick = int(time_passed / 1000000)
            lv.tick_inc(tick)
            lv.task_handler()
            await asyncio.sleep_ms(1000)

    def on_sleep(self):
        lv.screen_load(self.sleep_screen.get_screen())

    def on_wake(self):
        lv.screen_load(self.active_screen.get_screen())

    def on_ats_state(self, state):
        self.active_screen.set_ats_mode(state.mode)

    def on_bms_state(self, state):
        if state.internal_errors:
            self.active_screen.set_error(DEVICE_BMS, state.internal_errors)
            return

        self.active_screen.reset_error(DEVICE_BMS)
        direction = state.current & (1 << 15)
        current = round((state.current & (0xFFFF >> 1)) / 100)
        power = state.voltage * current

        self.active_screen.set_capacity(state.soc)
        self.active_screen.set_power_consumption(
            direction=direction,
            power=power,
            seconds=0,
        )

        self.active_screen.set_bms_temperature(
            temperature_mos=state.mos_temperature,
            bms_temperature_bat_1=state.sensor1_temperature,
            bms_temperature_bat_2=state.sensor2_temperature,
        )

        self.active_screen.set_cell_voltage(
            v1=state.cells[0],
            v2=state.cells[1],
            v3=state.cells[2],
            v4=state.cells[3],
        )

    def on_psu_state(self, state):
        if state.internal_errors:
            self.active_screen.set_error(DEVICE_PSU, state.internal_errors)
            return

        self.active_screen.reset_error(DEVICE_PSU)
        average_temperature = int((state.t1 + state.t2) / 2)
        self.active_screen.set_psu_state(
            t1=average_temperature,
            t2=state.t2,
            ac_voltage=state.ac,
            tachometer=state.tachometer,
        )

    def on_inverter_state(self, state):
        if state.internal_errors:
            self.active_screen.set_error(DEVICE_INVERTER, state.internal_errors)
            return

        self.active_screen.reset_error(DEVICE_INVERTER)
        self.active_screen.set_inverter_state(
            temperature=state.temperature,
            ac_voltage=state.ac,
            tachometer=state.tachometer,
        )

    def on_mcu_state(self, state):
        if state.internal_errors:
            self.active_screen.set_error(DEVICE_MCU, state.internal_errors)
            return

        self.active_screen.reset_error(DEVICE_MCU)
        self.active_screen.mcu_temperature.set_text(f"{state.temperature}°С")
        self.active_screen.mcu_memory.set_text(f"{state.memory}%")
