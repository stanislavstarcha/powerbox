"""
Profile module.

This module provides the implementation of the `ProfileState` and `ProfileController`
classes, which manage the configuration and state of the system profile.
"""

import json
import os
import struct

import conf
from const import (
    PROFILE_KEY_ATS,
    PROFILE_KEY_PSU_CURRENT,
    PROFILE_KEY_WIFI_SSID,
    PROFILE_KEY_WIFI_PASSWORD,
    PROFILE_KEY_MIN_VOLTAGE,
    PROFILE_KEY_MAX_VOLTAGE,
    PROFILE_KEY_MCU_POWER,
    DATA_TYPE_BOOL,
    DATA_TYPE_INT8,
    DATA_TYPE_INT32,
    DATA_TYPE_FLOAT32,
    DATA_TYPE_STRING,
)
from drivers import BaseState
from logging import logger

KEY_TYPES = {
    PROFILE_KEY_ATS: DATA_TYPE_BOOL,
    PROFILE_KEY_PSU_CURRENT: DATA_TYPE_INT8,
    PROFILE_KEY_WIFI_SSID: DATA_TYPE_STRING,
    PROFILE_KEY_WIFI_PASSWORD: DATA_TYPE_STRING,
    PROFILE_KEY_MIN_VOLTAGE: DATA_TYPE_FLOAT32,
    PROFILE_KEY_MAX_VOLTAGE: DATA_TYPE_FLOAT32,
    PROFILE_KEY_MCU_POWER: DATA_TYPE_FLOAT32,
}


class ProfileState(BaseState):
    """
    Represents the state of the system profile.

    Attributes:
        NAME (str): The name of the state.
        conf (dict): The configuration dictionary for the profile.
    """

    NAME = "PROFILE"
    conf = None

    def initialize(self, values):
        """
        Initializes the profile state with the given values.

        Args:
            values (dict): A dictionary of configuration values.
        """
        self.conf = values

    def set(self, param, value, as_bytes=True):
        """
        Sets a configuration parameter in the profile.

        Args:
            param (int): The parameter key.
            value (bytes|object): The raw value to set for the parameter.
            as_bytes (bool, optional): Whether to cast the value to the appropriate data type.
        """
        if as_bytes:
            self.conf[hex(param)] = self._cast(param, value)
        else:
            self.conf[hex(param)] = value

        self.notify()

    def get(self, param):
        """
        Retrieves a configuration parameter from the profile.

        Args:
            param (int): The parameter key.

        Returns:
            Any: The value of the parameter, or None if not found.
        """
        return self.conf.get(hex(param))

    def _cast(self, param, value):
        """
        Casts a raw value to the appropriate data type based on the parameter.

        Args:
            param (int): The parameter key.
            value (bytes): The raw value to cast.

        Returns:
            Any: The cast value.
        """
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
    """
    Controller for managing the system profile.

    This class handles reading, writing, and updating the profile configuration.

    Attributes:
        FILENAME (str): The file path for storing the profile configuration.
        state (ProfileState): The current state of the profile.
    """

    FILENAME = "./profile.json"

    def __init__(self):
        """
        Initializes the ProfileController.

        Loads the profile configuration from a file or initializes it with default values.
        """
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
                    hex(PROFILE_KEY_MIN_VOLTAGE): conf.BATTERY_MIN_CELL_VOLTAGE,
                    hex(PROFILE_KEY_MAX_VOLTAGE): conf.BATTERY_MAX_CELL_VOLTAGE,
                    hex(PROFILE_KEY_MCU_POWER): 0,
                }
            )
            self._write()

    def get(self, param, default=None):
        """
        Retrieves a configuration parameter from the profile.

        Args:
            param (int): The parameter key.
            default (Any): The default value to return if the parameter is not found.

        Returns:
            Any: The value of the parameter, or the default value if not found.
        """
        value = self.state.get(param)
        return value if value is not None else default

    def set(self, param, value, as_bytes=True):
        """
        Sets a configuration parameter in the profile.

        Args:
            param (int): The parameter key.
            value (Any): The value to set for the parameter.
            as_bytes (bool, optional): Whether to cast the value to the appropriate data type.
        """
        self.state.set(param, value, as_bytes)
        self._write()
        logger.info(json.dumps(self.state.conf))

    def _read(self):
        """
        Reads the profile configuration from the file.

        Returns:
            dict: The configuration dictionary.
        """
        with open(self.FILENAME) as f:
            return json.load(f)

    def _write(self):
        """
        Writes the profile configuration to the file.
        """
        with open(self.FILENAME, "w") as f:
            f.write(json.dumps(self.state.conf))
