import micropython

import asyncio
import time

from logging import logger

from drivers import UART
from drivers.ats import ATSController
from drivers.ble import BLEServerController
from drivers.inverter import InverterController
from drivers.psu import PowerSupplyController
from drivers.bms import BMSController
from drivers.buzzer import BuzzerController
from drivers.mcu import MCUController
from drivers.display import DisplayController

from lib.queue import InstructionsQueue
from const import (
    EVENT_STATE_ON,
    EVENT_STATE_OFF,
    EVENT_STATE_CHANGE,
    EVENT_STATE_ERROR,
)

import conf


def disable_keyboard_interrupt():
    micropython.kbd_intr(-1)


async def main():
    disable_keyboard_interrupt()
    logger.info("Bootstrapping app ver: ", conf.BLE_FIRMWARE)

    buzzer = BuzzerController(signal_pin=conf.BUZZER_SIGNAL_PIN)
    buzzer.boot()

    instructions = InstructionsQueue()
    mcu = MCUController()

    logger.setup(
        transport=conf.LOGGER_TRANSPORT,
        level=conf.LOGGER_LEVEL,
    )

    uart = UART(conf.UART_IF)

    ats = ATSController(
        nc_pin=conf.ATS_NC_PIN,
        no_pin=conf.ATS_NO_PIN,
    )

    bms = BMSController(
        baud_rate=conf.BMS_BAUD_RATE,
        uart_if=conf.BMS_UART_IF,
        uart_rx_pin=conf.BMS_UART_RX_PIN,
        uart_tx_pin=conf.BMS_UART_TX_PIN,
    )

    inverter = InverterController(
        power_button_pin=conf.INVERTER_POWER_BUTTON_PIN,
        power_button_timer=conf.INVERTER_POWER_BUTTON_TIMER,
        power_gate_pin=conf.INVERTER_POWER_GATE_PIN,
        uart=uart,
        uart_rx_pin=conf.INVERTER_UART_RX_PIN,
        uart_tx_pin=conf.INVERTER_UART_TX_PIN,
        buzzer=buzzer,
        turn_off_voltage=conf.INVERTER_MIN_CELL_VOLTAGE,
    )

    psu = PowerSupplyController(
        power_button_pin=conf.PSU_POWER_BUTTON_PIN,
        power_button_timer=conf.PSU_POWER_BUTTON_TIMER,
        power_gate_pin=conf.PSU_POWER_GATE_PIN,
        current_a_pin=conf.PSU_CURRENT_A_PIN,
        current_b_pin=conf.PSU_CURRENT_B_PIN,
        turn_off_voltage=conf.PSU_MAX_CELL_VOLTAGE,
        fan_tachometer_pin=conf.PSU_FAN_TACHOMETER_PIN,
        fan_tachometer_timer=conf.PSU_FAN_TACHOMETER_TIMER,
        uart=uart,
        uart_rx_pin=conf.PSU_UART_RX_PIN,
        current_channel=conf.PSU_CURRENT_CHANNEL,
        buzzer=buzzer,
    )

    if conf.BLE_ENABLED:
        ble = BLEServerController(
            gap_name=conf.BLE_GAP_NAME,
            manufacturer=conf.BLE_MANUFACTURER,
            model=conf.BLE_MODEL,
            firmware=conf.BLE_FIRMWARE,
            instructions=instructions,
            ats=ats,
            bms=bms,
            inverter=inverter,
            psu=psu,
            mcu=mcu,
        )
        ble.initialize()

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

    bms.state.add_callback(EVENT_STATE_CHANGE, inverter.on_bms_state)
    bms.state.add_callback(EVENT_STATE_CHANGE, psu.on_bms_state)

    psu.state.add_callback(EVENT_STATE_ON, inverter.off)
    psu.state.add_callback(EVENT_STATE_ON, bms.enable_charge)
    psu.state.add_callback(EVENT_STATE_OFF, bms.disable_charge)

    inverter.state.add_callback(EVENT_STATE_ON, psu.off)
    inverter.state.add_callback(EVENT_STATE_ON, bms.enable_discharge)
    inverter.state.add_callback(EVENT_STATE_OFF, bms.disable_discharge)

    coroutines = []

    if conf.DISPLAY_ENABLED:
        coroutines.append(asyncio.create_task(display.run()))

    if conf.BLE_ENABLED:
        coroutines.append(asyncio.create_task(ble.run()))

    coroutines += [
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
        time.sleep(5)
