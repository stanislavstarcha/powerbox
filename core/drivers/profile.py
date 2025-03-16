import os
import json
import struct

from drivers import BaseState

from const import (
    PROFILE_KEY_ATS,
    PROFILE_KEY_PSU_CURRENT,
    PROFILE_KEY_WIFI_SSID,
    PROFILE_KEY_WIFI_PASSWORD,
    PROFILE_KEY_MIN_VOLTAGE,
    PROFILE_KEY_MAX_VOLTAGE,
    DATA_TYPE_BOOL,
    DATA_TYPE_INT8,
    DATA_TYPE_INT32,
    DATA_TYPE_FLOAT32,
    DATA_TYPE_STRING,
)

import conf
from logging import logger

KEY_TYPES = {
    PROFILE_KEY_ATS: DATA_TYPE_BOOL,
    PROFILE_KEY_PSU_CURRENT: DATA_TYPE_INT8,
    PROFILE_KEY_WIFI_SSID: DATA_TYPE_STRING,
    PROFILE_KEY_WIFI_PASSWORD: DATA_TYPE_STRING,
    PROFILE_KEY_MIN_VOLTAGE: DATA_TYPE_FLOAT32,
    PROFILE_KEY_MAX_VOLTAGE: DATA_TYPE_FLOAT32,
}


class ProfileState(BaseState):
    NAME = "PROFILE"
    conf = None

    def initialize(self, values):
        self.conf = values

    def set(self, param, raw_value):
        self.conf[hex(param)] = self._cast(param, raw_value)
        self.notify()

    def get(self, param):
        return self.conf.get(hex(param))

    def _cast(self, param, value):
        data_type = KEY_TYPES.get(param)

        if data_type == DATA_TYPE_BOOL:
            return bool(int.from_bytes(value, "big"))

        if data_type in [DATA_TYPE_INT8, DATA_TYPE_INT32]:
            return int.from_bytes(value, "big")

        if data_type in [DATA_TYPE_FLOAT32]:
            return struct.unpack("<f", value)[0]

        if data_type == DATA_TYPE_STRING:
            return value.decode("utf-8")

        return value


class ProfileController:

    FILENAME = "./profile.json"

    def __init__(self):
        self.state = ProfileState()
        try:
            os.stat(self.FILENAME)
            self.state.initialize(self._read())
            logger.info(json.dumps(self.state.conf))
        except OSError:
            self.state.initialize(
                {
                    hex(PROFILE_KEY_ATS): False,
                    hex(PROFILE_KEY_WIFI_SSID): None,
                    hex(PROFILE_KEY_WIFI_PASSWORD): None,
                    hex(PROFILE_KEY_PSU_CURRENT): 0,
                    hex(PROFILE_KEY_MIN_VOLTAGE): conf.PSU_MAX_CELL_VOLTAGE,
                    hex(PROFILE_KEY_MAX_VOLTAGE): conf.INVERTER_MIN_CELL_VOLTAGE,
                }
            )
            self._write()

    def get(self, param, default=None):
        return self.state.get(param) or default

    def set(self, param, value):
        self.state.set(param, value)
        self._write()
        logger.info(json.dumps(self.state.conf))

    def _read(self):
        with open(self.FILENAME) as f:
            return json.load(f)

    def _write(self):
        with open(self.FILENAME, "w") as f:
            f.write(json.dumps(self.state.conf))
