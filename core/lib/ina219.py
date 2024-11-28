import machine

from logging import logger


class INA219:

    SCL_PIN = 22
    SDA_PIN = 21

    # INA219 device address
    INA219_ADDR = 0x40

    # INA219 Registers
    REG_SHUNT_VOLTAGE = 0x01
    REG_BUS_VOLTAGE = 0x02
    REG_CALIBRATION = 0x05

    def __init__(
        self,
        i2c=None,
        scl_pin=SCL_PIN,
        sda_pin=SDA_PIN,
        ina219_addr=INA219_ADDR,
    ):
        self._ina219_addr = ina219_addr

        self._i2c = i2c
        # self._i2c = machine.I2C(
        #     0,
        #     scl=machine.Pin(scl_pin),
        #     sda=machine.Pin(sda_pin),
        #     freq=100000,
        # )

        devices = self._i2c.scan()
        if devices:
            logger.info("I2C devices found:", devices)
        else:
            logger.warning("No I2C devices found")

    def write_register(self, register, value):
        data = value.to_bytes(2, "big")
        self._i2c.writeto_mem(self._ina219_addr, register, data)

    # Function to read a register (2 bytes)
    def read_register(self, register):
        data = self._i2c.readfrom_mem(self._ina219_addr, register, 2)
        return int.from_bytes(data, "big")

    # Initialize the INA219 (calibration values can vary)
    def init_ina219(self):
        # Calibration value for a specific configuration (e.g., 32V, 2A)
        calibration_value = 0x2000
        self.write_register(self.REG_CALIBRATION, calibration_value)

    # Function to read bus voltage in volts
    def read_bus_voltage(self):
        raw_voltage = self.read_register(self.REG_BUS_VOLTAGE)
        # Conversion factor (each LSB = 4mV, hence multiply by 4 and divide by 1000 to get volts)
        voltage = (raw_voltage >> 3) * 0.004 + 0.03
        return voltage

    def read_shunt_voltage(self):
        raw_voltage = self.read_register(self.REG_SHUNT_VOLTAGE)
        # Conversion factor (each LSB = 10µV, hence multiply by 10 to get microvolts)
        voltage = (raw_voltage >> 3) * 0.004 + 0.03
        # voltage = raw_voltage * 0.01  # millivolts
        return voltage
