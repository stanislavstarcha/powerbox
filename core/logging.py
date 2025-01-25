import machine
import time
import uio
import sys


class LogLevels:
    CRITICAL = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4


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


logger = Logger()
