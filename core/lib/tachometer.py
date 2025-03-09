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

    def __init__(self, pin, period_ms, done_callback=None, timer_id=-1):
        self._pin = pin
        self._period_ms = period_ms
        self._done_callback = done_callback
        self._timer = machine.Timer(timer_id)

    def measure(self):
        print("START FAN MEASURE")
        self._started_us = time.ticks_us()
        self._total_pulses = 0
        self._timer.deinit()
        self._timer.init(
            period=self._period_ms,
            mode=machine.Timer.ONE_SHOT,
            callback=self.finish,
        )

        self._pin.irq(
            trigger=machine.Pin.IRQ_RISING,
            handler=self.on_raise,
        )

    def finish(self, t):
        print("======== FINISH MEASURE")
        t.deinit()
        factor = int(1000 / self._period_ms)
        self._pin.irq(handler=None)
        frequency = int(factor * self._total_pulses)
        if frequency < 1:
            return self._done_callback(0)

        rpm = round(60 / (1 / (frequency * 2)))
        self._done_callback(rpm)

    def on_raise(self, pin):
        self._total_pulses += 1
