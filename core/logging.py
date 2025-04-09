"""
Logging module.

This module provides logging functionality for the application. It allows
logging messages at various levels (info, debug, error) and supports
different transport mechanisms for log output.
"""

import machine
import time
import uio
import sys

from const import BLE_LOG_STATE_UUID


class LogLevels:
    """
    Defines log levels for the application.
    """

    CRITICAL = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5


class TerminalColors:
    """
    Defines terminal colors for log messages.
    """

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
    """
    Base class for logger transport mechanisms.
    """

    @staticmethod
    def send(message):
        """
        Send a log message.

        Args:
            message (str): The log message to send.
        """
        print(message)


class UARTLoggerTransport(BaseLoggerTransport):
    """
    UART-based logger transport.

    This class provides a transport mechanism for logging messages over UART.
    """

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
        """
        Initialize the UARTLoggerTransport.

        Args:
            uart_if (int): UART interface number.
            baud_rate (int): Baud rate for the UART interface.
            uart_tx_pin (int): Pin number for UART TX.
            uart_rx_pin (int): Pin number for UART RX.
        """
        self._uart = machine.UART(
            uart_if,
            baudrate=baud_rate,
            tx=machine.Pin(uart_tx_pin),
            rx=machine.Pin(uart_rx_pin),
        )

    def send(self, message):
        """
        Send a log message over UART.

        Args:
            message (str): The log message to send.
        """
        self._uart.write(message + "\n")


class Logger:
    """
    Logger class for managing log messages and transports.
    """

    def __init__(self):
        """
        Initialize the Logger instance.
        """
        self._transport = BaseLoggerTransport()
        self._level = 4
        self._ble = None
        self._ble_forwarding = False

    def setup(self, transport=None, level=None, wifi=None):
        """
        Set up the logger with the specified transport and log level.

        Args:
            transport (BaseLoggerTransport): The transport mechanism for log output.
            level (int): The log level.
            wifi (str): WiFi configuration (optional).
        """
        self._level = level

    def debug(self, *messages):
        """
        Log a debug message.

        Args:
            *messages: The messages to log.
        """
        self._log(LogLevels.DEBUG, *messages)

    def info(self, *messages):
        """
        Log an info message.

        Args:
            *messages: The messages to log.
        """
        self._log(LogLevels.INFO, *messages)

    def warning(self, *messages):
        """
        Log a warning message.

        Args:
            *messages: The messages to log.
        """
        self._log(LogLevels.WARNING, *messages)

    def error(self, *messages):
        """
        Log an error message.

        Args:
            *messages: The messages to log.
        """
        self._log(LogLevels.ERROR, *messages)

    def critical(self, e):
        """
        Log a critical error message.

        Args:
            e (Exception): The exception to log.
        """
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        self._log(LogLevels.CRITICAL, e, buf.getvalue())

    def _log(self, level, *messages):
        """
        Internal method to log a message at a specific level.

        Args:
            level (int): The log level.
            *messages: The messages to log.
        """
        if level > self._level:
            return
        message = self._format(level, *messages)
        self._transport.send(message)

        if self._ble and self._ble_forwarding:
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
        """
        Format a log message.

        Args:
            level (int): The log level.
            *messages: The messages to format.

        Returns:
            str: The formatted log message.
        """
        timestamp = time.time()
        color_prefix = LEVEL_COLORS.get(level, "")
        color_suffix = TerminalColors.ENDC if color_prefix else ""
        message = " ".join(str(m) for m in messages)
        level_name = LEVEL_NAMES.get(level, "UNKNOWN")
        return f"{color_prefix} {level_name} [{timestamp}] {message} {color_suffix}"

    def attach_ble(self, ble):
        """
        Attach a BLE transport to the logger.

        Args:
            ble: The BLE instance to attach.
        """
        self._ble = ble

    def start_ble_forwarding(self):
        """
        Start forwarding logs over BLE.
        """
        self._ble_forwarding = True

    def stop_ble_forwarding(self):
        """
        Stop forwarding logs over BLE.
        """
        self._ble_forwarding = False


logger = Logger()
