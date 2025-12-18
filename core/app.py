"""
Main application module.

This module initializes all drivers, controllers, and event loops required
for the application to function. It serves as the entry point for the system.
"""

import asyncio
import machine
import micropython
import time

from lib.ota.status import current_ota, cancel as cancel_ota
from logging import logger

from drivers import UART
from drivers.ats import ATSController
from drivers.led import LedController
from drivers.ble import BLEServerController
from drivers.inverter import InverterController
from drivers.psu import PowerSupplyController
from drivers.bms import BMSController
from drivers.buzzer import BuzzerController
from drivers.mcu import MCUController
from drivers.display import DisplayController
from drivers.ota import OTAController
from drivers.profile import ProfileController

from lib.queue import InstructionsQueue
from const import (
    EVENT_STATE_ON,
    EVENT_STATE_OFF,
    EVENT_STATE_CHANGE,
    EVENT_BATTERY_CHARGED,
    EVENT_BATTERY_DISCHARGED,
    PROFILE_KEY_ATS,
    PROFILE_KEY_WIFI_SSID,
    PROFILE_KEY_WIFI_PASSWORD,
    PROFILE_KEY_MAX_VOLTAGE,
    PROFILE_KEY_MIN_VOLTAGE,
    PROFILE_KEY_MODEL,
)

import conf
import version

led = LedController(pin=conf.LED_PIN)
led.on()

buzzer = None
# buzzer = BuzzerController(signal_pin=conf.BUZZER_SIGNAL_PIN)
# buzzer.boot()


def disable_keyboard_interrupt():
    """
    Production code must not listen for keyboard interrupts.
    Sometimes ESP32 may produce noise on the UART0 interface
    due to floating pins that eventually causes keyboard interrupts.
    """
    micropython.kbd_intr(-1)


async def mark_boot_as_successful():
    """Mark partition as successful after 10 seconds."""
    await asyncio.sleep(10)
    cancel_ota()
    logger.info(f"Marked OTA partition {current_ota} as successful.")


async def main():
    """
    Main application entry point.

    This function initializes all the drivers, controllers, and event loops.
    It sets up the hardware, configures the system, and starts the asynchronous
    tasks required for the application to run.
    """
    await asyncio.sleep(3)
    disable_keyboard_interrupt()
    logger.info(f"Bootstrapping from {current_ota} app ver: {version.FIRMWARE}")

    uart = UART(conf.UART_IF)
    profile = ProfileController()
    instructions = InstructionsQueue()
    mcu = MCUController(led=led)

    logger.setup(
        transport=conf.LOGGER_TRANSPORT,
        level=conf.LOGGER_LEVEL,
    )

    ota = OTAController(
        firmware_url=conf.FIRMWARE_URL,
        ssid=profile.get(PROFILE_KEY_WIFI_SSID),
        password=profile.get(PROFILE_KEY_WIFI_PASSWORD),
    )

    ats = ATSController(
        nc_pin=conf.ATS_NC_PIN,
        no_pin=conf.ATS_NO_PIN,
        enabled=profile.get(PROFILE_KEY_ATS, False),
    )

    bms = BMSController(
        baud_rate=conf.BMS_BAUD_RATE,
        uart_if=conf.BMS_UART_IF,
        uart_rx_pin=conf.BMS_UART_RX_PIN,
        uart_tx_pin=conf.BMS_UART_TX_PIN,
        profile=profile,
        turn_off_min_voltage=profile.get(
            PROFILE_KEY_MIN_VOLTAGE,
            conf.BATTERY_MIN_CELL_VOLTAGE,
        ),
        turn_off_max_voltage=profile.get(
            PROFILE_KEY_MAX_VOLTAGE,
            conf.BATTERY_MAX_CELL_VOLTAGE,
        ),
    )

    button_timer = machine.Timer(conf.BUTTON_TIMER_ID)

    inverter = InverterController(
        power_button_pin=conf.INVERTER_POWER_BUTTON_PIN,
        power_button_timer=button_timer,
        power_gate_pin=conf.INVERTER_POWER_GATE_PIN,
        uart=uart,
        uart_rx_pin=conf.INVERTER_UART_RX_PIN,
        uart_tx_pin=conf.INVERTER_UART_TX_PIN,
        buzzer=buzzer,
        fan_tachometer_a_pin=None,
        fan_tachometer_b_pin=None,
        fan_tachometer_a_timer=None,
        fan_tachometer_b_timer=None,
    )

    psu = PowerSupplyController(
        power_button_pin=conf.PSU_POWER_BUTTON_PIN,
        power_button_timer=button_timer,
        power_gate_pin=conf.PSU_POWER_GATE_PIN,
        current_a_pin=conf.PSU_CURRENT_A_PIN,
        current_b_pin=conf.PSU_CURRENT_B_PIN,
        fan_tachometer_pin=None,
        fan_tachometer_timer=None,
        uart=uart,
        uart_rx_pin=conf.PSU_UART_RX_PIN,
        profile=profile,
        buzzer=buzzer,
    )

    if conf.BLE_ENABLED:
        ble = BLEServerController(
            gap_name=conf.BLE_GAP_NAME,
            manufacturer=conf.BLE_MANUFACTURER,
            model=profile.get(
                PROFILE_KEY_MODEL,
                version.MODEL,
            ),
            firmware=version.FIRMWARE,
            instructions=instructions,
            ats=ats,
            bms=bms,
            inverter=inverter,
            psu=psu,
            mcu=mcu,
            ota=ota,
            profile=profile,
        )
        ble.initialize()
        logger.attach_ble(ble)

    if conf.DISPLAY_ENABLED:
        display = DisplayController(
            width=conf.DISPLAY_WIDTH,
            height=conf.DISPLAY_HEIGHT,
            led_pin=conf.DISPLAY_LED_PIN,
            miso_pin=conf.DISPLAY_MISO_PIN,
            mosi_pin=conf.DISPLAY_MOSI_PIN,
            sck_pin=conf.DISPLAY_SCLK_PIN,
            dc_pin=conf.DISPLAY_DC_PIN,
            cs_pin=conf.DISPLAY_CS_PIN,
            reset_pin=conf.DISPLAY_RESET_PIN,
            frequency=conf.DISPLAY_FREQ,
        )

        display.active_screen.set_version(version.FIRMWARE)
        mcu.state.add_callback(EVENT_STATE_CHANGE, display.on_mcu_state)
        bms.state.add_callback(EVENT_STATE_CHANGE, display.on_bms_state)
        ats.state.add_callback(EVENT_STATE_CHANGE, display.on_ats_state)
        psu.state.add_callback(EVENT_STATE_CHANGE, display.on_psu_state)
        inverter.state.add_callback(EVENT_STATE_CHANGE, display.on_inverter_state)

        psu.state.add_callback(
            EVENT_STATE_ON,
            display.active_screen.show_psu_state,
        )
        psu.state.add_callback(
            EVENT_STATE_OFF,
            display.active_screen.hide_psu_state,
        )
        inverter.state.add_callback(
            EVENT_STATE_ON,
            display.active_screen.show_inverter_state,
        )
        inverter.state.add_callback(
            EVENT_STATE_OFF,
            display.active_screen.hide_inverter_state,
        )

        display.active_screen.hide_psu_state()
        display.active_screen.hide_inverter_state()
        display.active_screen.show_bms_state()

    profile.state.add_callback(EVENT_STATE_CHANGE, ota.on_profile_state)
    profile.state.add_callback(EVENT_STATE_CHANGE, ats.on_profile_state)

    bms.state.add_callback(EVENT_BATTERY_CHARGED, psu.off)
    bms.state.add_callback(EVENT_BATTERY_DISCHARGED, inverter.off)
    bms.state.add_callback(EVENT_STATE_CHANGE, psu.check_threshold)

    psu.state.add_callback(EVENT_STATE_ON, inverter.off)
    psu.state.add_callback(EVENT_STATE_ON, bms.enable_charge)
    psu.state.add_callback(EVENT_STATE_OFF, bms.disable_charge)

    inverter.state.add_callback(EVENT_STATE_ON, psu.off)
    inverter.state.add_callback(EVENT_STATE_ON, bms.enable_discharge)
    inverter.state.add_callback(EVENT_STATE_OFF, bms.disable_discharge)

    if conf.BLE_ENABLED and conf.DISPLAY_ENABLED:
        ble.state.add_callback(EVENT_STATE_CHANGE, display.on_ble_state)

    coroutines = []

    if conf.DISPLAY_ENABLED:
        coroutines.append(asyncio.create_task(display.run()))

    if conf.BLE_ENABLED:
        coroutines.append(asyncio.create_task(ble.run()))

    coroutines += [
        asyncio.create_task(mark_boot_as_successful()),
        asyncio.create_task(instructions.run()),
        asyncio.create_task(ats.run()),
        asyncio.create_task(bms.run()),
        asyncio.create_task(inverter.run()),
        asyncio.create_task(psu.run()),
        asyncio.create_task(mcu.run()),
    ]

    await asyncio.gather(*coroutines)
    logger.info(f"Running...")

    while True:
        await asyncio.sleep(1)
    logger.info("Finishing up")


while True:
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(e)
        while True:
            led.pulse(color=(100, 0, 0), duration=50, n=3)
            time.sleep(3)
