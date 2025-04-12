from collections import deque
import struct

from const import HISTORY_SIZE


# 0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 0123456789




class HistoricalData:
    """
    A class for managing historical data with BLE communication capabilities.

    This class maintains a buffer of historical data points and provides methods
    to update and retrieve this data in formats suitable for BLE transmission.

    Attributes:
        _chart_type (int): Unique chart identifier (6 bits)
        _data_type (int): Data type indicator (0 for 8-bit, 1 for 16-bit per value)
        _length (int): Number of elements in the buffer
        _snapshot (int): Snapshot counter
        _buffer (deque): Circular buffer storing historical data points
    """

    # unique chart ID
    _chart_type = None

    # 0 for 8 bit, 1 - 16 bit per value
    _data_type = None

    # number of elements
    _length = None

    _snapshot = 0
    _buffer = None

    def __init__(self, chart_type, data_type, length=HISTORY_SIZE):
        """
        Initialize the HistoricalData object.

        Args:
            chart_type (int): The unique chart identifier
            data_type (int): Data type indicator (0 for 8-bit, 1 for 16-bit)
            length (int, optional): Buffer length. Defaults to HISTORY_SIZE.
        """
        self._chart_type = chart_type
        self._data_type = data_type
        self._length = length
        self._buffer = deque((), length)

    def ble_update(self):
        """
        Generate a BLE update packet with the most recent data point.

        Returns:
            bytes: Packed header and the most recent data point, or None if buffer is empty
        """
        if len(self._buffer) == 0:
            return

        data_type = "B" if self._data_type == 0 else "H"
        return self._pack_header(
            chart_type=self._chart_type,
            data_type=self._data_type,
            incremental=True,
            length=1,
            offset=0,
        ) + struct.pack(data_type, self._buffer[-1])

    def ble_chunks(self, mtu=20):
        """
        Get history data in chunks suitable for BLE transmission.

        Args:
            mtu (int, optional): Maximum Transmission Unit size. Defaults to 20.

        Returns:
            list: List of data chunks, each containing a header and data points,
                  or None if buffer is empty
        """
        data_type = "B" if self._data_type == 0 else "H"
        payload_size = mtu - 4
        points = payload_size
        if self._data_type == 1:
            points //= 2

        queue = list(self._buffer)

        if len(queue) == 0:
            return

        base_offset = HISTORY_SIZE - len(queue)
        return [
            self._pack_header(
                chart_type=self._chart_type,
                data_type=self._data_type,
                incremental=False,
                length=points,
                offset=base_offset + i,
            )
            + struct.pack(
                data_type * len(queue[i : i + points]), *queue[i : i + points]
            )
            for i in range(0, len(queue), points)
        ]

    def push(self, point):
        """
        Push a single data point to the history buffer.

        Args:
            point: The data point to add to the buffer
        """
        self._buffer.append(point)

    @staticmethod
    def _pack_header(chart_type, data_type, incremental, length, offset):
        """
        Pack header information into a 32-bit integer for BLE transmission.

        Args:
            chart_type (int): The unique chart identifier
            data_type (int): Data type indicator (0 for 8-bit, 1 for 16-bit)
            incremental (int): Flag indicating if this is an incremental update
            length (int): Number of data points in this packet
            offset (int): Starting offset in the history buffer

        Returns:
            bytes: Packed header as a 4-byte string
        """
        overflow = (offset + length) - HISTORY_SIZE
        if overflow > 0:
            length -= overflow

        # ensure data types
        chart_type &= 0b111111  # 6 bits
        data_type &= 0b1  # 1 bit
        incremental &= 0b1  # 1 bit
        length &= 0xFF  # 8 bits
        offset &= 0xFF  # 8 bits

        # Pack each field into a 32-bit integer
        packed_value = (
            (chart_type << 18)
            | (data_type << 17)
            | (incremental << 16)
            | (offset << 8)
            | length
        )

        return struct.pack("I", packed_value)
