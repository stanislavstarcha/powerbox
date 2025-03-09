import asyncio
import time
import machine

import ili9488  # NOQA
import lvgl as lv  # NOQA
import lcd_bus  # NOQA

from logging import logger

from drivers.display.screens.active import ActiveScreen
from drivers.display.screens.idle import IdleScreen


class DisplayController:

    BUFFER_SIZE = 65535
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
        self._sleep_timer = machine.Timer(-1)

        spi_bus = machine.SPI.Bus(host=2, mosi=mosi_pin, miso=miso_pin, sck=sck_pin)
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

        display.init()
        display.set_power(True)
        display.set_rotation(lv.DISPLAY_ROTATION._270)

        led = machine.Pin(led_pin, machine.Pin.OUT)
        led.on()

        self.active_screen = ActiveScreen()
        self.idle_screen = IdleScreen()

        self.active_screen.create_widgets()
        self.idle_screen.create_widgets()
        self.on_wake()

    async def run(self):
        logger.info("Running Display...")
        counter = 0
        start_time = time.time_ns()
        while True:
            counter += 1
            time_passed = time.time_ns() - start_time

            # Update LVGL internal time
            tick = int(time_passed / 1000000)
            lv.tick_inc(tick)
            lv.task_handler()
            await asyncio.sleep_ms(self.REFRESH_MS)

    def on_sleep(self, timer):
        lv.screen_load(self.idle_screen.get_screen())

    def on_wake(self):
        lv.screen_load(self.active_screen.get_screen())

    def on_ats_state(self, state):
        self.active_screen.set_ats_mode(state.mode)

    def on_bms_state(self, state):

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
        self.active_screen.on_psu_state(state)

    def on_inverter_state(self, state):
        self.active_screen.on_inverter_state(state)

    def on_mcu_state(self, state):
        self.active_screen.on_mcu_state(state)
