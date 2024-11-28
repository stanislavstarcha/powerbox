VERSION = "0.7.0"

import asyncio
import machine
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
from drivers.oled import OLEDController
from drivers.storage import StorageController
from drivers.telemetry import Telemetry
from drivers.wroom import WROOMController

from lib.queue import InstructionsQueue

from boot import CONF


micropython.kbd_intr(-1)


def disable_wifi():
    network.WLAN(network.STA_IF).active(False)
    network.WLAN(network.AP_IF).active(False)
    logger.debug("Disabled wifi")


async def main():
    logger.info("Bootstrapping the app...")
    disable_wifi()

    buzzer = BuzzerController(signal_pin=CONF.BuzzerController.SIGNAL_PIN)
    buzzer.boot()

    instructions = InstructionsQueue()

    i2c = machine.I2C(
        0,
        scl=machine.Pin(CONF.I2C.SCL_PIN),
        sda=machine.Pin(CONF.I2C.SDA_PIN),
        freq=400000,
    )

    oled = OLEDController(
        i2c=i2c,
        i2c_address=CONF.OLEDController.ADDRESS,
    )

    oled.syslog("Init logger...")
    logger.setup(
        transport=CONF.LoggerController.transport,
        level=CONF.LoggerController.level,
    )

    oled.syslog("Init AST...")
    ats = ATSController(
        nc_pin=CONF.ATSController.NC_PIN,
        no_pin=CONF.ATSController.NO_PIN,
    )

    oled.syslog("Init BMS...")
    bms = BMSController(
        baud_rate=CONF.BMSController.BAUD_RATE,
        uart_if=CONF.BMSController.UART_IF,
        uart_rx_pin=CONF.BMSController.UART_RX_PIN,
        uart_tx_pin=CONF.BMSController.UART_TX_PIN,
    )

    oled.syslog("Init Inverter...")
    inverter = InverterController(
        power_button_pin=CONF.InverterController.POWER_BUTTON_PIN,
        power_gate_pin=CONF.InverterController.POWER_GATE_PIN,
        uart_if=CONF.InverterController.UART_IF,
        uart_rx_pin=CONF.InverterController.UART_RX_PIN,
        uart_tx_pin=CONF.InverterController.UART_TX_PIN,
        buzzer=buzzer,
    )

    oled.syslog("Init PSU...")
    psu = PowerSupplyController(
        power_button_pin=CONF.PowerSupplyController.POWER_BUTTON_PIN,
        power_gate_pin=CONF.PowerSupplyController.POWER_GATE_PIN,
        temperature_pin=CONF.PowerSupplyController.TEMPERATURE_PIN,
        i2c=i2c,
        current_a_pin=CONF.PowerSupplyController.CURRENT_A_PIN,
        current_b_pin=CONF.PowerSupplyController.CURRENT_B_PIN,
        buzzer=buzzer,
    )

    oled.syslog("Init WROOM...")
    wroom = WROOMController()

    oled.syslog("Init BLE...")
    ble = BLEServerController(
        bms=bms, psu=psu, inverter=inverter, wroom=wroom, instructions=instructions
    )

    oled.syslog("Init storage...")
    storage = StorageController(
        cs=CONF.StorageController.CS_PIN,
        miso=CONF.StorageController.MISO_PIN,
        mosi=CONF.StorageController.MOSI_PIN,
        sck=CONF.StorageController.SCK_PIN,
    )

    oled.syslog("Init Telemetry...")
    telemetry = Telemetry(
        ats=ats,
        ble=ble,
        bms=bms,
        inverter=inverter,
        oled=oled,
        psu=psu,
        storage=storage,
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
        # asyncio.create_task(ats.run()),
        asyncio.create_task(ble.run()),
        asyncio.create_task(bms.run()),
        asyncio.create_task(inverter.run()),
        asyncio.create_task(oled.run()),
        asyncio.create_task(psu.run()),
        asyncio.create_task(storage.run()),
        asyncio.create_task(wroom.run()),
    ]

    oled.syslog("Running controllers...")
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
