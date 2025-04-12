import time
from collections import deque

import machine


class Tachometer:
    """
    A class for measuring fan RPM using a tachometer signal.
    
    This class provides functionality to measure the RPM of a fan by counting
    pulses from a tachometer signal over a specified period of time.
    """

    _name = None

    # measurement start time in ticks
    _started_us = None

    # timer to stop measurement
    _timer = None

    # measurement time in milliseconds
    _period_ms = None

    _total_pulses = None

    def __init__(
        self,
        pin,
        period_ms,
        done_callback=None,
        timer_id=-1,
        buffer_size=5,
        name="FAN X",
    ):
        """
        Initialize the Tachometer object.
        
        Args:
            pin: The pin object connected to the tachometer signal.
            period_ms: The measurement period in milliseconds.
            done_callback: Optional callback function to be called when measurement is complete.
            timer_id: The ID of the timer to use for measurement timing.
            buffer_size: The size of the buffer for storing RPM measurements.
            name: A name identifier for the tachometer.
        """
        self._name = name
        self._pin = pin
        self._period_ms = period_ms
        self._done_callback = done_callback
        self._timer = machine.Timer(timer_id)
        self._buffer_size = buffer_size
        self._buffer = deque((), buffer_size)

    def measure(self):
        """
        Start a new RPM measurement.
        
        This method initializes the measurement by resetting the pulse counter,
        setting up a timer for the measurement period, and configuring the pin
        interrupt to count rising edges.
        """
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

    def get_average_rpm(self):
        """
        Calculate the average RPM from the measurement buffer.
        
        Returns:
            int: The average RPM value, or 0 if no measurements are available.
        """
        if len(self._buffer) == 0:
            return 0
        return int(sum(self._buffer) / len(self._buffer))

    def finish(self, t):
        """
        Complete the RPM measurement and calculate the result.
        
        This method is called by the timer when the measurement period is complete.
        It calculates the RPM based on the number of pulses counted and adds the
        result to the measurement buffer.
        
        Args:
            t: The timer object that triggered this callback.
            
        Returns:
            The result of the done_callback function if provided, otherwise None.
        """
        t.deinit()
        factor = int(1000 / self._period_ms)
        self._pin.irq(handler=None)
        frequency = int(factor * self._total_pulses)
        if frequency < 1:
            rpm = 0
        else:
            rpm = round(60 / (1 / (frequency * 2)))

        self._buffer.append(rpm)
        return self._done_callback(self.get_average_rpm())

    def on_raise(self, pin):
        """
        Handle the rising edge interrupt from the tachometer pin.
        
        This method is called each time a rising edge is detected on the tachometer pin,
        incrementing the pulse counter.
        
        Args:
            pin: The pin object that triggered the interrupt.
        """
        self._total_pulses += 1
