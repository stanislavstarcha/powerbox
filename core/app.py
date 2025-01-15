import asyncio
import micropython
import network
import time

from logging import logger

from drivers.ats import ATSController
from drivers.ble import BLEServerController
from drivers.inverter import InverterController
from drivers.psu import PowerSupplyController
from drivers.bms import BMSController
from drivers.buzzer import BuzzerController
from drivers.telemetry import Telemetry
from drivers.wroom import WROOMController

from lib.queue import InstructionsQueue

import conf


def disable_wifi():
    network.WLAN(network.STA_IF).active(False)
    network.WLAN(network.AP_IF).active(False)
    logger.debug("Disabled wifi")


def disable_keyboard_interrupt():
    micropython.kbd_intr(-1)


async def main():
    # disable_keyboard_interrupt()
    logger.info("Bootstrapping app ver: ", conf.FIRMWARE)
    disable_wifi()

    buzzer = BuzzerController(signal_pin=conf.BUZZER_SIGNAL_PIN)
    buzzer.boot()

    instructions = InstructionsQueue()

    logger.setup(
        transport=conf.LOGGER_TRANSPORT,
        level=conf.LOGGER_LEVEL,
    )

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
        power_gate_pin=conf.INVERTER_POWER_GATE_PIN,
        uart_if=conf.INVERTER_UART_IF,
        uart_rx_pin=conf.INVERTER_UART_RX_PIN,
        uart_tx_pin=conf.INVERTER_UART_TX_PIN,
        buzzer=buzzer,
        turn_off_voltage=conf.INVERTER_MIN_CELL_VOLTAGE,
    )

    psu = PowerSupplyController(
        power_button_pin=conf.PSU_POWER_BUTTON_PIN,
        power_gate_pin=conf.PSU_POWER_GATE_PIN,
        current_a_pin=conf.PSU_CURRENT_A_PIN,
        current_b_pin=conf.PSU_CURRENT_B_PIN,
        turn_off_voltage=conf.PSU_MAX_CELL_VOLTAGE,
        fan_tachometer_pin=conf.PSU_FAN_TACHOMETER_PIN,
        uart_tx_pin=conf.PSU_UART_TX_PIN,
        current_limit=conf.PSU_CURRENT_CHANNEL,
        buzzer=buzzer,
    )

    bms.add_state_callback(inverter.on_bms_state)
    bms.add_state_callback(psu.on_bms_state)

    wroom = WROOMController()

    ble = BLEServerController(
        manufacturer=conf.MANUFACTURER,
        model=conf.MODEL,
        firmware=conf.FIRMWARE,
        bms=bms,
        psu=psu,
        inverter=inverter,
        wroom=wroom,
        ats=ats,
        instructions=instructions,
    )

    telemetry = Telemetry(
        ats=ats,
        ble=ble,
        bms=bms,
        inverter=inverter,
        psu=psu,
        esp=wroom,
    )

    psu.add_power_callback(True, inverter.off)
    psu.add_power_callback(True, bms.enable_charge)
    psu.add_power_callback(False, bms.disable_charge)

    inverter.add_power_callback(True, psu.off)
    inverter.add_power_callback(True, bms.enable_discharge)
    inverter.add_power_callback(False, bms.disable_discharge)

    coroutines = [
        asyncio.create_task(instructions.run()),
        asyncio.create_task(telemetry.run()),
        asyncio.create_task(ats.run()),
        asyncio.create_task(ble.run()),
        asyncio.create_task(bms.run()),
        asyncio.create_task(inverter.run()),
        asyncio.create_task(psu.run()),
        asyncio.create_task(wroom.run()),
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
