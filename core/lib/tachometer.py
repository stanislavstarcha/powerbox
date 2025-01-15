import time
import machine


class Tachometer:

    # measurement start time in ticks
    _started_us = None

    # timer to stop measurement
    _timer = None

    # measurement time in milliseconds
    _period_ms = None

    _total_pulses = None

    def __init__(self, pin, period_ms, max_pulses=100, done_callback=None):
        self._pin = pin
        self._period_ms = period_ms
        self._max_pulses = max_pulses
        self._done_callback = done_callback

    def measure(self):
        print("Measurng...")
        self._started_us = time.ticks_us()
        self._total_pulses = 0
        self._timer = machine.Timer(-1)
        self._timer.init(
            period=self._period_ms,
            mode=machine.Timer.ONE_SHOT,
            callback=self.finish,
        )

        self._pin.irq(
            trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING,
            handler=self.callback,
        )

    def finish(self, t):
        print("total pulses", self._total_pulses)
        factor = 1000000 / time.ticks_diff(time.ticks_us(), self._started_us)
        self._pin.irq(handler=None)
        self._timer.deinit()
        frequency = int(factor * self._total_pulses)
        self._done_callback(frequency)

    def callback(self, pin):
        if self._pin.value():
            self._total_pulses += 1
            if self._total_pulses >= self._max_pulses:
                self.finish(self._timer)
