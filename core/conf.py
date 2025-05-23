"""
Configuration module.

This module contains configuration constants and settings used throughout
the application. These settings define hardware pin mappings, timers, and
other system-wide parameters.
"""

from micropython import const

FIRMWARE_URL = "https://github.com/stanislavstarcha/powerbox/releases/latest/download/firmware.json"

BUZZER_SIGNAL_PIN = const(1)
LED_PIN = const(8)

BLE_ENABLED = True
BLE_GAP_NAME = "Trypillia"
BLE_MANUFACTURER = "egg17"

LOGGER_TRANSPORT = const(0)
LOGGER_LEVEL = const(4)

UART_IF = const(2)

BUTTON_TIMER_ID = const(0)

BMS_BAUD_RATE = const(115200)
BMS_UART_IF = const(1)
BMS_UART_RX_PIN = const(42)
BMS_UART_TX_PIN = const(41)

PSU_POWER_BUTTON_PIN = const(18)
PSU_POWER_GATE_PIN = const(15)
PSU_FAN_TACHOMETER_A_PIN = const(6)
PSU_FAN_TACHOMETER_B_PIN = const(4)
PSU_FAN_TACHOMETER_TIMER = const(1)
PSU_UART_RX_PIN = const(7)
PSU_CURRENT_A_PIN = const(17)
PSU_CURRENT_B_PIN = const(16)
PSU_CURRENT_CHANNEL = const(2)
PSU_MAX_CELL_VOLTAGE = const(3.5)

INVERTER_MIN_CELL_VOLTAGE = const(2.75)
INVERTER_POWER_BUTTON_PIN = const(40)
INVERTER_POWER_GATE_PIN = const(39)
INVERTER_UART_RX_PIN = const(45)
INVERTER_UART_TX_PIN = const(48)
INVERTER_FAN_TACHOMETER_A_PIN = const(21)
INVERTER_FAN_TACHOMETER_B_PIN = const(47)
INVERTER_FAN_TACHOMETER_A_TIMER = const(2)
INVERTER_FAN_TACHOMETER_B_TIMER = const(3)

ATS_NO_PIN = const(14)
ATS_NC_PIN = const(13)

DISPLAY_ENABLED = True
DISPLAY_WIDTH = const(320)
DISPLAY_HEIGHT = const(480)

DISPLAY_LED_PIN = const(12)
DISPLAY_DC_PIN = const(9)
DISPLAY_MOSI_PIN = const(10)
DISPLAY_SCLK_PIN = const(11)
DISPLAY_CS_PIN = const(3)
DISPLAY_RESET_PIN = const(46)
DISPLAY_MISO_PIN = const(-1)

DISPLAY_FREQ = const(40000000)
DISPLAY_OFFSET_X = const(0)
DISPLAY_OFFSET_Y = const(0)
