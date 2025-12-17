import random

import lvgl as lv  # NOQA
import micropython

from drivers.display.screens import BaseScreen

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


class ActiveScreen(BaseScreen):
    """
    ActiveScreen class displays real-time system status and error information.

    Attributes:
        errors (list): List to keep error codes for various devices.
        error_glyph, error_label, error: Widgets for showing error information.
        bms_voltage_label, bms_voltage_cell_1, bms_voltage_cell_2, bms_voltage_cell_3, bms_voltage_cell_4:
            Widgets for battery cell voltage.
        bms_temperature_label, bms_temperature_mos, bms_temperature_bat_1, bms_temperature_bat_2:
            Widgets for battery temperature.
        version_label, version: Widgets for version information.
        ats, ats_label: Widgets for ATS mode display.
        ble: Widget for BLE state indication.
        psu_label, psu_temperature, psu_ac_voltage, psu_current:
            Widgets for PSU data.
        inverter_label, inverter_temperature, inverter_ac_voltage, inverter_rpm:
            Widgets for inverter data.
        power_label, power, power_timer, power_in_glyph_a, power_out_glyph_a, power_in_glyph_b, power_out_glyph_b:
            Widgets for power statistics and direction.
        capacity, capacity_bar: Widgets for battery capacity.
        mcu_label, mcu_glyph, mcu_temperature, mcu_health_glyph: Widgets for MCU data.
    """

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
    psu_current = None

    inverter_label = None
    inverter_temperature = None
    inverter_ac_voltage = None
    inverter_rpm = None

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
        """
        Initializes the ActiveScreen by setting initial error states and creating the screen.
        """
        self.errors = [0, 0, 0, 0]
        super(ActiveScreen, self).__init__()

    def on_invalidate(self):
        pass

    def set_cell_voltage(self, v1, v2, v3, v4):
        """
        Sets the voltage values for battery cells.

        Args:
            v1 (float): Voltage of cell 1.
            v2 (float): Voltage of cell 2.
            v3 (float): Voltage of cell 3.
            v4 (float): Voltage of cell 4.
        """
        self.bms_voltage_cell_1.set_text(f"{v1} В")
        self.bms_voltage_cell_2.set_text(f"{v2} В")
        self.bms_voltage_cell_3.set_text(f"{v3} В")
        self.bms_voltage_cell_4.set_text(f"{v4} В")

    def set_ats_mode(self, mode):
        """
        Sets the ATS (Automatic Transfer Switch) mode using corresponding icon.

        Args:
            mode (int): ATS mode (0, 1, or 2).
        """
        if mode == 0:
            self.ats.set_text(chr(ICON_DOTS))

        if mode == 1:
            self.ats.set_text(chr(ICON_CITY))

        if mode == 2:
            self.ats.set_text(chr(ICON_BATTERY))

    def set_bms_temperature(
        self, temperature_mos, bms_temperature_bat_1, bms_temperature_bat_2
    ):
        """
        Sets battery management system temperatures.

        Args:
            temperature_mos (int or float): MOS temperature.
            bms_temperature_bat_1 (int or float): Temperature of battery sensor 1.
            bms_temperature_bat_2 (int or float): Temperature of battery sensor 2.
        """
        self.bms_temperature_mos.set_text(f"{temperature_mos}°С")
        self.bms_temperature_bat_1.set_text(f"{bms_temperature_bat_1}°С")
        self.bms_temperature_bat_2.set_text(f"{bms_temperature_bat_2}°С")

    def set_version(self, version):
        """
        Displays the version string on the screen.

        Args:
            version (str): Version information.
        """
        self.version.set_text(version)

    def set_capacity(self, value):
        """
        Sets the battery capacity value and updates the capacity bar.

        Args:
            value (int): Battery capacity percentage.
        """
        if value is not None:
            self.capacity.set_text(f"{value}%")
            self.capacity_bar.set_value(value, lv.ANIM.OFF)
            self.capacity_bar.invalidate()

    def set_psu_state(self, t1, t2, ac_voltage, current):
        """
        Updates the PSU state display with temperature, AC voltage, and RPM.

        Args:
            t1 (int or float): First temperature value.
            t2 (int or float): Second temperature value.
            ac_voltage (int or float): AC voltage.
            current (int): Current mode.
        """
        if t1 and t2:
            self.psu_temperature.set_text(f"{t1}°С / {t2}°С")
        if ac_voltage:
            self.psu_ac_voltage.set_text(f"{ac_voltage}В")
        if current:
            self.psu_current.set_text(f"{current}%")

    def set_inverter_state(self, temperature, ac_voltage, rpm):
        """
        Updates the inverter state display with temperature, AC voltage, and RPM.

        Args:
            temperature (int or float): Inverter temperature.
            ac_voltage (int or float): Inverter AC voltage.
            rpm (int): Inverter fan RPM.
        """
        if temperature:
            self.inverter_temperature.set_text(f"{temperature}°С")
        if ac_voltage:
            self.inverter_ac_voltage.set_text(f"{ac_voltage}В")
        if rpm:
            self.inverter_rpm.set_text(f"{rpm} об/хв")

    def set_power_consumption(self, direction, power, seconds):
        """
        Updates the power consumption display.

        Args:
            direction (bool): Direction flag indicating charging/discharging.
            power (int or float): Power consumption in Watts.
            seconds (int): Time in seconds until full charge/discharge.
        """
        if power is not None:
            self.power.set_text(f"{power} Вт")

        if direction:
            self.power_timer.set_text(f"До повного розряду {seconds}")
        else:
            self.power_timer.set_text(f"До повного заряду {seconds}")

    def show_error_state(self):
        """
        Displays the error state by showing associated widgets.
        """
        self.show_widget(self.error_glyph)
        self.show_widget(self.error_label)
        self.show_widget(self.error)

    def hide_error_state(self):
        """
        Hides the error state widgets.
        """
        self.hide_widget(self.error_glyph)
        self.hide_widget(self.error_label)
        self.hide_widget(self.error)

    def show_bms_state(self):
        """
        Displays the battery management system state by showing relevant widgets.
        """
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
        """
        Displays the PSU state by showing relevant widgets.
        """
        self.show_widget(self.psu_label)
        self.show_widget(self.psu_temperature)
        self.show_widget(self.psu_current)
        self.show_widget(self.psu_ac_voltage)
        self.show_widget(self.power_in_glyph_a)
        self.show_widget(self.power_in_glyph_b)
        self.show_widget(self.power_timer)

    def hide_psu_state(self):
        """
        Hides the PSU state widgets.
        """
        self.hide_widget(self.psu_label)
        self.hide_widget(self.psu_temperature)
        self.hide_widget(self.psu_current)
        self.hide_widget(self.psu_ac_voltage)
        self.hide_widget(self.power_in_glyph_a)
        self.hide_widget(self.power_in_glyph_b)
        self.hide_widget(self.power_timer)

    def show_inverter_state(self):
        """
        Displays the inverter state by showing relevant widgets.
        """
        self.show_widget(self.inverter_label)
        self.show_widget(self.inverter_temperature)
        self.show_widget(self.inverter_rpm)
        self.show_widget(self.inverter_ac_voltage)
        self.show_widget(self.power_out_glyph_a)
        self.show_widget(self.power_out_glyph_b)
        self.show_widget(self.power_timer)

    def hide_inverter_state(self):
        """
        Hides the inverter state widgets.
        """
        self.hide_widget(self.inverter_label)
        self.hide_widget(self.inverter_temperature)
        self.hide_widget(self.inverter_rpm)
        self.hide_widget(self.inverter_ac_voltage)
        self.hide_widget(self.power_out_glyph_a)
        self.hide_widget(self.power_out_glyph_b)
        self.hide_widget(self.power_timer)

    def set_error(self, device_id, error):
        """
        Sets error information for a device and displays error state if any error exists.

        Args:
            device_id (int): The device identifier.
            error (int): The error code.
        """
        self.errors[device_id] = error
        if any(self.errors):
            codes = []

            if self.errors[DEVICE_BMS]:
                codes.append(f"1{self.errors[DEVICE_BMS]}")

            if self.errors[DEVICE_PSU]:
                codes.append(f"2{self.errors[DEVICE_PSU]}")

            if self.errors[DEVICE_INVERTER]:
                codes.append(f"3{self.errors[DEVICE_INVERTER]}")

            if self.errors[DEVICE_MCU]:
                codes.append(f"4{self.errors[DEVICE_MCU]}")

            self.error.set_text(" ".join(codes))
            self.show_error_state()

    def reset_error(self, device_id):
        """
        Resets error information for a device and hides the error state if no errors exist.

        Args:
            device_id (int): The device identifier.
        """
        self.errors[device_id] = 0
        if not any(self.errors):
            self.hide_error_state()

    def create_widgets(self):
        """
        Creates and arranges all widgets on the ActiveScreen.
        """
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

        self.ble = self.create_glyph(
            11, 0, ICON_BLE, row_span=2, is_hidden=False, color="grey"
        )

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
        self.psu_current = self.create_label(0, 12, col_span=3, font_size=12)

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
        self.inverter_rpm = self.create_label(9, 12, col_span=3, font_size=12)

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

    def _generate_random_state(self):
        """
        Generates a random state for testing by randomly setting PSU or inverter values.
        """
        is_charging = random.randint(0, 1)

        if is_charging:
            self.set_power_consumption(
                False, power=random.randint(16, 42), seconds=random.randint(0, 3600)
            )

            self.set_psu_state(
                t1=random.randint(16, 42),
                t2=random.randint(16, 42),
                ac_voltage=random.randint(207, 230),
                current=random.randint(
                    0,
                    100,
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
                rpm=random.randint(
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

    def on_bms_state(self, state):
        """
        Processes BMS state updates, updating widget data and errors accordingly.

        Args:
            state: BMS state object with attributes for errors, soc, temperatures, and cell voltages.
        """
        if state.internal_errors:
            self.set_error(DEVICE_BMS, state.internal_errors)
            return

        self.reset_error(DEVICE_BMS)

        self.set_capacity(state.get_soc())
        self.set_power_consumption(
            direction=state.get_direction(),
            power=state.get_power(),
            seconds=0,
        )

        self.set_bms_temperature(
            temperature_mos=state.mos_temperature,
            bms_temperature_bat_1=state.sensor1_temperature,
            bms_temperature_bat_2=state.sensor2_temperature,
        )

        self.set_cell_voltage(
            v1=round(state.cells[0] / 1000, 2),
            v2=round(state.cells[1] / 1000, 2),
            v3=round(state.cells[2] / 1000, 2),
            v4=round(state.cells[3] / 1000, 2),
        )

    def on_psu_state(self, state):
        """
        Processes PSU state updates and updates PSU widget data and errors accordingly.

        Args:
            state: PSU state object containing internal/external errors and telemetry.
        """
        if state.internal_errors:
            self.set_error(DEVICE_PSU, state.internal_errors)
            return

        if state.external_errors:
            self.set_error(DEVICE_PSU, state.external_errors)
            return

        self.reset_error(DEVICE_PSU)

        current_channels = {0: 25, 1: 50, 2: 75, 3: 100}
        average_temperature = None

        if state.active:
            if state.t1 and state.t2 and state.t3:
                average_temperature = int((state.t1 + state.t2) / 2)

            self.set_psu_state(
                t1=average_temperature,
                t2=state.t3,
                ac_voltage=state.ac,
                current=current_channels.get(state.current_channel),
            )

        if not state.active:
            self.set_psu_state(t1="", t2="", ac_voltage="", current="")

    def on_inverter_state(self, state):
        """
        Processes inverter state updates and updates inverter widget data and errors accordingly.

        Args:
            state: Inverter state object containing errors and telemetry.
        """
        if state.internal_errors:
            self.set_error(DEVICE_INVERTER, state.internal_errors)
        else:
            self.reset_error(DEVICE_INVERTER)

        if state.active:
            self.set_inverter_state(
                temperature=state.temperature,
                ac_voltage=state.ac,
                rpm=state.get_avg_rpm(),
            )
        else:
            self.set_inverter_state(
                temperature="",
                ac_voltage="",
                rpm="",
            )

    def on_mcu_state(self, state):
        """
        Processes MCU state updates and updates MCU widget data and errors accordingly.

        Args:
            state: MCU state object containing temperature, memory, and internal errors.
        """
        if state.internal_errors:
            self.set_error(DEVICE_MCU, state.internal_errors)
            return

        self.reset_error(DEVICE_MCU)
        self.mcu_temperature.set_text(f"{state.temperature}°С")
        self.mcu_memory.set_text(f"{state.memory}%")

    def on_ble_state(self, state):
        """
        Processes BLE state updates by updating the BLE widget color.

        Args:
            state: BLE state object with an 'active' flag.
        """
        if state.active:
            self.ble.set_style_text_color(self.color_to_hex("blue"), 0)
        else:
            self.ble.set_style_text_color(self.color_to_hex("grey"), 0)
