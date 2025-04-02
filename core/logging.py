import machine
import time
import uio
import sys

from const import BLE_LOG_STATE_UUID


class LogLevels:
    CRITICAL = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5


class TerminalColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


LEVEL_COLORS = {
    LogLevels.DEBUG: TerminalColors.OKBLUE,
    LogLevels.INFO: TerminalColors.OKBLUE,
    LogLevels.WARNING: TerminalColors.WARNING,
    LogLevels.ERROR: TerminalColors.FAIL,
    LogLevels.CRITICAL: TerminalColors.FAIL,
}

LEVEL_NAMES = {
    LogLevels.DEBUG: "DEBUG",
    LogLevels.INFO: "INFO",
    LogLevels.WARNING: "WARNING",
    LogLevels.ERROR: "ERROR",
    LogLevels.CRITICAL: "CRITICAL",
}


class BaseLoggerTransport:

    @staticmethod
    def send(message):
        print(message)


class UARTLoggerTransport(BaseLoggerTransport):

    BAUD_RATE = 115200
    UART_IF = None
    UART_RX_PIN = None
    UART_TX_PIN = None

    def __init__(
        self,
        uart_if=UART_IF,
        baud_rate=BAUD_RATE,
        uart_tx_pin=UART_TX_PIN,
        uart_rx_pin=UART_RX_PIN,
    ):
        self._uart = machine.UART(
            uart_if,
            baudrate=baud_rate,
            tx=machine.Pin(uart_tx_pin),
            rx=machine.Pin(uart_rx_pin),
        )

    def send(self, message):
        self._uart.write(message + "\n")


class Logger:

    _transport = None
    _level = 4

    _ble = None
    _ble_forwarding = False

    def __init__(self):
        self._transport = BaseLoggerTransport()

    def setup(self, transport=None, level=None, wifi=None):
        self._level = level

    def debug(self, *messages):
        self._log(LogLevels.DEBUG, *messages)

    def info(self, *messages):
        self._log(LogLevels.INFO, *messages)

    def warning(self, *messages):
        self._log(LogLevels.WARNING, *messages)

    def error(self, *messages):
        self._log(LogLevels.ERROR, *messages)

    def critical(self, e):
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        self._log(LogLevels.CRITICAL, e, buf.getvalue())

    def _log(self, level, *messages):
        if level > self._level:
            return
        message = self._format(level, *messages)
        self._transport.send(message)

        if self._ble:
            chunk_size = 19
            full_message = " ".join(str(m) for m in messages).encode("utf-8")

            for i in range(0, len(full_message), chunk_size):
                chunk = full_message[i : i + chunk_size]

                if i == 0:
                    format_flag = 0  # Start
                elif i + chunk_size >= len(full_message):
                    format_flag = 2  # End
                else:
                    format_flag = 1  # Middle

                header = bytes(
                    [(level & 0b111) | (format_flag << 3)]
                )  # Pack level (3 bits) + format (2 bits)
                self._ble.notify(BLE_LOG_STATE_UUID, header + chunk)

    @staticmethod
    def _format(level, *messages):
        timestamp = time.time()
        color_prefix = ""
        color_suffix = ""
        if LEVEL_COLORS[level]:
            color_prefix = LEVEL_COLORS[level]
            color_suffix = TerminalColors.ENDC

        message = " ".join(str(m) for m in messages)
        level_name = LEVEL_NAMES[level]
        return f"{color_prefix} {level_name} [{timestamp}] {message} {color_suffix}"

    def attach_ble(self, ble):
        self._ble = ble

    def start_ble_forwarding(self):
        self._ble_forwarding = True

    def stop_ble_forwarding(self):
        self._ble_forwarding = False


logger = Logger()
