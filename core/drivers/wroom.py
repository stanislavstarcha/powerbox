import esp32
import gc
import struct
import time

from drivers import BaseState
from drivers.const import BLE_ESP_UUID

from logging import logger


class WROOMState(BaseState):
    NAME = "ESP"
    BLE_STATE_UUID = BLE_ESP_UUID

    FREQUENCY = 1
    GC_FREQUENCY = 5

    memory = 0
    temperature = 0
    heartbeat = True

    DISPLAY_METRICS = ["temperature", "memory"]

    def clear(self):
        self.memory = None
        self.temperature = None

    def set_display_metric(self, metric):
        self.display_metric_glyph = "heart" if self.heartbeat else None

        if metric == "memory":
            self.display_metric_value = self.memory
            self.display_metric_type = "%"

        if metric == "temperature":
            self.display_metric_value = int(self.temperature)
            self.display_metric_type = "c"

    def get_ble_state(self):
        uptime = int(time.time())
        return struct.pack(
            ">IBBB",
            self._pack(uptime),
            self._pack(self.temperature),
            self._pack(self.memory),
            self._pack(self.internal_errors),
        )


class WROOMController:

    _state = None

    def __init__(self):
        self._state = WROOMState()

    async def run(self):
        gc_counter = 0
        while True:
            self._state.heartbeat = not self._state.heartbeat
            free_mem = gc.mem_free()
            used_mem = gc.mem_alloc()
            total_mem = free_mem + used_mem
            self._state.memory = int((used_mem / total_mem) * 100)
            self._state.temperature = int((esp32.raw_temperature() - 32) / 1.8)

            gc_counter += 1
            if gc_counter >= self._state.GC_FREQUENCY:
                gc.collect()
                gc_counter = 0
                logger.debug(
                    "ESP stats memory",
                    self._state.memory,
                    "temperature",
                    self._state.temperature,
                )

            self._state.snapshot()
            await self._state.sleep()

    @property
    def state(self):
        return self._state
