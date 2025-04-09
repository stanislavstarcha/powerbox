"""
Display module.

This module provides the `DisplayController` class, which manages the display hardware,
handles screen transitions, and updates the display based on system states.
"""

import asyncio
import time

import ili9488  # NOQA
import lcd_bus  # NOQA
import lvgl as lv  # NOQA
import machine

from drivers.display.screens.active import ActiveScreen
from drivers.display.screens.idle import IdleScreen
from logging import logger


class DisplayController:
    """
    Controller for managing the display hardware and screen transitions.

    This class handles the initialization of the display, manages active and idle screens,
    and updates the display based on system states.

    Attributes:
        BUFFER_SIZE (int): The size of the display buffer.
        REFRESH_MS (int): The refresh interval in milliseconds.
        _sleep_timer (machine.Timer): Timer for managing sleep transitions.
        _idle (bool): Whether the display is in idle mode.
        active_screen (ActiveScreen): The active screen instance.
        idle_screen (IdleScreen): The idle screen instance.
    """

    BUFFER_SIZE = 65536
    REFRESH_MS = 500

    _sleep_timer = None
    _idle = False

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
        """
        Initializes the DisplayController.

        Args:
            width (int, optional): Display width.
            height (int, optional): Display height.
            led_pin (int, optional): Backlight pin.
            mosi_pin (int, optional): SPI MOSI pin.
            miso_pin (int, optional): SPI MISO pin.
            sck_pin (int, optional): SPI SCK pin.
            dc_pin (int, optional): SPI DC pin.
            cs_pin (int, optional): SPI CS pin.
            reset_pin (int, optional): Display reset pin.
            frequency (int, optional): SPI frequency.
        """
        self._sleep_timer = machine.Timer(-1)
        spi_bus = machine.SPI.Bus(host=1, mosi=mosi_pin, miso=miso_pin, sck=sck_pin)
        display_bus = lcd_bus.SPIBus(
            spi_bus=spi_bus,
            freq=frequency,
            dc=dc_pin,
            cs=cs_pin,
        )

        frame_buffer = display_bus.allocate_framebuffer(
            self.BUFFER_SIZE, lcd_bus.MEMORY_SPIRAM
        )

        frame_buffer_2 = display_bus.allocate_framebuffer(
            self.BUFFER_SIZE, lcd_bus.MEMORY_SPIRAM
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
        )

        reset = machine.Pin(reset_pin, machine.Pin.OUT)
        reset.on()

        display.set_power(True)
        display.init()
        display.set_rotation(lv.DISPLAY_ROTATION._270)

        led = machine.Pin(led_pin, machine.Pin.OUT)
        led.on()

        self.active_screen = ActiveScreen()
        self.idle_screen = IdleScreen()

        self.active_screen.create_widgets()
        self.idle_screen.create_widgets()
        self.on_wake()

    async def run(self):
        """
        Asynchronously runs the display controller, handling display tasks and managing the refresh rate.

        This function starts an infinite loop that continuously updates the display.
        It calculates the time passed in nanoseconds since the start time, converts it to milliseconds,
        and increments the LittlevGL tick counter accordingly. The task handler of LittlevGL is called
        to process any pending tasks, and the loop then sleeps for the specified refresh interval.

        The loop ensures that the display is updated at a regular interval defined by REFRESH_MS.

        Raises:
            asyncio.CancelledError: If the task is cancelled.
        """
        logger.info("Running Display...")

        counter = 0
        start_time = time.time_ns()
        while True:
            counter += 1
            time_passed = time.time_ns() - start_time

            tick = int(time_passed / 1000000)
            lv.tick_inc(tick)
            lv.task_handler()
            await asyncio.sleep_ms(self.REFRESH_MS)

    def on_sleep(self, timer):
        """
        Handles the transition to the idle screen when the system goes to sleep.

        Args:
            timer (machine.Timer): The timer triggering the sleep transition.
        """
        logger.info("Load idle screen")
        lv.screen_load(self.idle_screen.get_screen())

    def on_wake(self):
        """
        Handles the transition to the active screen when the system wakes up.
        """
        lv.screen_load(self.active_screen.get_screen())
        logger.info("Load active screen")

    def on_ats_state(self, state):
        """
        Updates the display based on the ATS (Automatic Transfer Switch) state.

        Args:
            state: The ATS state object.
        """
        self.active_screen.set_ats_mode(state.mode)

    def on_bms_state(self, state):
        """
        Updates the display based on the BMS (Battery Management System) state.

        Args:
            state: The BMS state object.
        """
        allow_sleep_counter = (
            state.get_power() == 0
            and not state.charging_allowed
            and not state.discharging_allowed
            and not state.internal_errors
        )

        if allow_sleep_counter:
            if not self._idle:
                self._sleep_timer.init(
                    period=60000,
                    mode=machine.Timer.ONE_SHOT,
                    callback=self.on_sleep,
                )
                self._idle = True
        else:
            self._sleep_timer.deinit()
            if self._idle:
                self.on_wake()
                self._idle = False

        self.active_screen.on_bms_state(state)
        self.idle_screen.on_bms_state(state)

    def on_psu_state(self, state):
        """
        Updates the display based on the PSU (Power Supply Unit) state.

        Args:
            state: The PSU state object.
        """
        self.active_screen.on_psu_state(state)

    def on_inverter_state(self, state):
        """
        Updates the display based on the inverter state.

        Args:
            state: The inverter state object.
        """
        self.active_screen.on_inverter_state(state)

    def on_mcu_state(self, state):
        """
        Updates the display based on the MCU (Microcontroller Unit) state.

        Args:
            state: The MCU state object.
        """
        self.active_screen.on_mcu_state(state)

    def on_ble_state(self, state):
        """
        Updates the display based on the BLE (Bluetooth Low Energy) state.

        Args:
            state: The BLE state object.
        """
        self.active_screen.on_ble_state(state)
