class CONF:

    class LoggerController:
        transport = None  # stdout
        level = 4

    class WiFiController:
        ENABLED = False
        SSID = None
        PASSWORD = None

    class StorageController:
        CS_PIN = 5
        SCK_PIN = 18
        MOSI_PIN = 19
        MISO_PIN = 23

    class BMSController:
        BAUD_RATE = 115200
        UART_IF = 1
        UART_RX_PIN = 16
        UART_TX_PIN = 17

    class PowerSupplyController:
        VOLTMETER_ENABLED = False
        TEMPERATURE_ENABLED = True
        POWER_BUTTON_PIN = 34
        POWER_GATE_PIN = 27
        TEMPERATURE_PIN = 33
        CURRENT_A_PIN = 14
        CURRENT_B_PIN = 12

    class InverterController:
        POWER_BUTTON_PIN = 22
        POWER_GATE_PIN = 21

        UART_IF = 2
        UART_RX_PIN = 2
        UART_TX_PIN = 4

    class ATSController:
        NO_PIN = 35
        NC_PIN = 32

    class I2C:
        SDA_PIN = 25
        SCL_PIN = 26

    class OLEDController:
        ADDRESS = 0x3C

    class BuzzerController:
        SIGNAL_PIN = 13
