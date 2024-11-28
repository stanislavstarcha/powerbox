import asyncio
import machine
import re

from logging import logger
from drivers import BaseState


CREG_STATUSES = {
    0: "not registered not searching",
    1: "registered",
    2: "not registered but searching",
    3: "registration declined",
    4: "registration unknown",
    5: "registered in roaming",
}


class SIMState(BaseState):
    NAME = "SIM"


class SimController:

    BAUD_RATE = 57600
    UART_IF = 2
    UART_RX_PIN = 16
    UART_TX_PIN = 17

    # uart buffer to asynchronously process data
    _uart_buffer = None

    # network name
    _operator = None

    # signal strength
    _rssi = 0

    # error rate
    _ber = 99

    # network registration status
    _registration = 0

    # module readiness
    _ready = False  # overall state
    _module_ready = False
    _sms_ready = False
    _call_ready = False

    # currently processing AT command response
    _at_requests = None
    _at_buffer = ""

    def __init__(
        self,
        uart_if=UART_IF,
        baud_rate=BAUD_RATE,
        uart_tx_pin=UART_TX_PIN,
        uart_rx_pin=UART_RX_PIN,
    ):
        self._state = SIMState()

        try:
            self._uart = machine.UART(
                uart_if,
                baudrate=baud_rate,
                tx=machine.Pin(uart_tx_pin),
                rx=machine.Pin(uart_rx_pin, machine.Pin.IN, machine.Pin.PULL_UP),
            )
            self._uart_buffer = b""
            self._at_requests = []
            logger.info("Initialized SIM controller")
        except Exception as e:
            self._state.fail(e)
            logger.error("Failed to initialize SIM controller")

    def request(self, command):
        logger.debug("GSM REQ", command)
        self._at_requests.append(command)
        self._uart.write(f"{command}\r")

    async def setup_uart(self):
        logger.info("Setup GSM UART...")

        # ping
        self.request("AT")

        # turn echo mode off
        self.request("ATE0")

    def initialize(self):
        logger.info("Initialize GSM module...")

        # extended call status
        self.request("AT+COLP=1")

        # notify on text messages
        self.request("AT+CNMI=2,2,0,0,0")

        # get total sms stored
        self.request("AT+CPMS?")

    async def status(self):
        logger.debug("Check GSM status...")

        while True:
            # get network name
            self.request("AT+COPS?")

            # get signal strength
            self.request("AT+CSQ")

            # get registration status
            self.request("AT+CREG?")

            # self._uart.write('AT+CUSD=1,"*101#",15' + "\n")

            logger.info(
                f"GSM Ready: {self._ready}",
            )
            await asyncio.sleep_ms(10000)

    def handle(self, request, buffer):
        logger.debug(f"GSM OK {request} {buffer}")

        # when AT command returns nothing other than OK
        if not buffer:
            buffer = request

        if buffer == "ATE0":
            self.initialize()
            asyncio.create_task(self.status())
            return

        match = re.match(r"\+(\w+):\s*(.*)", buffer)
        if not match:
            logger.warning(f"Could not parse AT request: {request} response: {buffer}")
            return

        command = match.group(1)
        params = match.group(2).split(",")
        logger.debug(f"GSM parse command: {command} params: {params}")

        if command == "COPS":
            if len(params) == 3:
                _, _, self._operator = params
                if not self._operator:
                    logger.info(f"GSM operator: {self._operator}")
            else:
                logger.info(f"GSM no operator found")

        if command == "CSQ":
            self._rssi, self._ber = int(params[0]), int(params[1])
            dbm = -113 + self._rssi * 2
            logger.debug(f"GSM Signal: {dbm}dBm RSSI: {self._rssi} BER: {self._ber}")

        if command == "CREG":
            _, self._registration = params[0], int(params[1])
            status = CREG_STATUSES[self._registration]
            logger.debug(f"GSM registration: {status}")

        # received sms message
        if command == "CMTI":
            memory, text_id = params[0], int(params[1])
            # read the message
            if memory == "SM":
                self._uart.write(f"AT+CMGR={text_id}\n")

        gsm_ready = self._rssi >= 10 and self._ber <= 3 and self._registration == 1

        if gsm_ready and not self._ready:
            self.on_connected()

        if not gsm_ready and self._ready:
            self.on_disconnected()

        self._ready = gsm_ready

    def parse(self, response):
        if not response:
            return

        # module is ready to receive AT commands
        if response == "RDY":
            logger.debug(f"GSM module is ready")
            self._module_ready = True
            return

        if response == "Call Ready":
            logger.debug(f"GSM Call module is ready")
            self._call_ready = True
            return

        if response == "SMS Ready":
            self._sms_ready = True
            logger.debug(f"GSM SMS module is ready")
            return

        if response == "RING":
            logger.info(f"RING!")
            return

        if response == "BUSY":
            logger.info(f"BUSY!")
            return

        if response == "NO DIALTONE":
            logger.info(f"NO DIALTONE")
            return

        if response == "NO ANSWER":
            logger.info(f"NO ANSWER")
            return

        if response == "CONNECT":
            logger.info(f"CONNECT")
            return

        if response == "NO CARRIER":
            logger.info(f"NO CARRIER!")
            return

        if response == "ERROR":
            request = self._at_requests.pop(0)
            logger.error(f"AT {request} failed")
            self._at_buffer = ""
            return

        if response == "OK":
            request = self._at_requests.pop(0)
            self.handle(request, self._at_buffer)
            self._at_buffer = ""
            return

        # accumulate command response
        self._at_buffer += response

    def on_connected(self):
        logger.info("Connected to GSM network", self._operator)

        # read messages
        # self._uart.write(f"AT+CMGR=8\n")
        # self._uart.write(f"AT+CMGR=9\n")
        # self._uart.write(f"AT+CMGR=10\n")
        # self._uart.write(f"AT+CMGR=11\n")
        # self._uart.write(f"AT+CMGR=12\n")
        # self._uart.write(f"AT+CMGR=13\n")
        # self._uart.write(f"AT+CMGR=14\n")

        # self._uart.write("ATD+111;\n")
        # self._uart.write("ATD+380951476262;\n")

    def on_disconnected(self):
        logger.info("Disconnected from GSM network", self._gsm_operator)

    async def uart_reader(self):
        logger.info("Running SIM UART reader...")
        while True:
            if self._uart.any():
                logger.info("whoa!")
                data = self._uart.read()
                if data:
                    self._uart_buffer += data
                    logger.debug("UART buffer size", len(data), len(self._uart_buffer))
            # unblock other coroutines
            await asyncio.sleep_ms(10)

    async def uart_processor(self):
        logger.info("Running SIM UART processor...")
        while True:
            if b"\r" in self._uart_buffer:
                line, self._uart_buffer = self._uart_buffer.split(b"\r", 1)
                try:
                    line = line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    logger.error(f"Could not decode UART buffer: {line}")
                    continue
                if line.strip():
                    self.parse(line)
            await asyncio.sleep_ms(250)

    async def run(self):
        logger.info("Running SIM controller...")
        asyncio.create_task(self.uart_processor())
        asyncio.create_task(self.uart_reader())
        asyncio.create_task(self.setup_uart())
        while True:
            self._state.ping()
            await asyncio.sleep(1)

    def collect(self):
        return SIMState()
