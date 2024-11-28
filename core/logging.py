import machine
import time
import socket
import uio
import sys

from boot import CONF


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


class WIFILoggerTransport(BaseLoggerTransport):
    HOST = None
    PORT = None

    _wifi = None
    _sock = None
    _active = None

    def __init__(self, wifi=None, host=HOST, port=PORT):
        self._wifi = wifi
        self._host = host
        self._port = port
        self.connect()

    def connect(self):

        if not self._wifi._station:
            return

        if not self._wifi._station.isconnected():
            return

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockaddr = socket.getaddrinfo(self._host, self._port)[0][-1]
        self._sock.connect(sockaddr)
        self._active = True

    def send(self, message):

        if not self._wifi.connected():
            return super().send(message)

        if not self._active:
            return super().send(message)

        try:
            self._sock.sendall(message.encode())
        except Exception as e:
            self._active = False
            logger.critical(e)
            self.connect()

        debug = True
        if debug:
            super().send(message)


class SDCardTransport(BaseLoggerTransport):

    _fd = None

    def __init__(self, sd):
        self._sd = sd
        self.open()

    def open(self):
        filename = "/logs"
        self._fd = open(filename, "rb")

    def send(self, message):
        pass


class Logger:

    _transport = None
    _level = 4

    def __init__(self):
        self._transport = BaseLoggerTransport()

    def setup(self, transport=None, level=None, wifi=None):
        self._level = level
        if transport == "wifi":
            self._transport = WIFILoggerTransport(
                wifi=wifi,
                host=CONF.WIFILogger.HOST,
                port=CONF.WIFILogger.PORT,
            )

        if transport == "uart":
            self._transport = UARTLoggerTransport(
                uart_if=CONF.UARTLogger.UART_IF,
                baud_rate=CONF.UARTLogger.BAUD_RATE,
                uart_rx_pin=CONF.UARTLogger.UART_RX_PIN,
                uart_tx_pin=CONF.UARTLogger.UART_TX_PIN,
            )

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
