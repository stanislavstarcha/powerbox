# queue.py: adapted from uasyncio V2

# Copyright (c) 2018-2020 Peter Hinch
# Released under the MIT License (MIT) - see LICENSE file

# Code is based on Paul Sokolovsky's work.
# This is a temporary solution until uasyncio V3 gets an efficient official version

import asyncio


# Exception raised by get_nowait().
class QueueEmpty(Exception):
    """Exception raised when attempting to get an item from an empty queue."""
    pass


# Exception raised by put_nowait().
class QueueFull(Exception):
    """Exception raised when attempting to put an item into a full queue."""
    pass


class Queue:
    """A queue implementation for asynchronous operations.
    
    This class provides a thread-safe queue implementation that supports
    asynchronous put and get operations. It is designed to work with
    asyncio and provides both blocking and non-blocking methods.
    """

    def __init__(self, maxsize=0):
        """Initialize the queue.
        
        Args:
            maxsize (int): Maximum size of the queue. If 0 or negative, the queue size is unlimited.
        """
        self.maxsize = maxsize
        self._queue = []
        self._evput = asyncio.Event()  # Triggered by put, tested by get
        self._evget = asyncio.Event()  # Triggered by get, tested by put

        self._jncnt = 0
        self._jnevt = asyncio.Event()
        self._upd_jnevt(0)  # update join event

    def _get(self):
        """Internal method to get an item from the queue.
        
        Returns:
            The first item from the queue.
        """
        self._evget.set()  # Schedule all tasks waiting on get
        self._evget.clear()
        return self._queue.pop(0)

    async def get(self):
        """Get an item from the queue.
        
        If the queue is empty, wait until an item is available.
        
        Returns:
            The first item from the queue.
        """
        while self.empty():  # May be multiple tasks waiting on get()
            # Queue is empty, suspend task until a put occurs
            # 1st of N tasks gets, the rest loop again
            await self._evput.wait()
        return self._get()

    def get_nowait(self):
        """Get an item from the queue without blocking.
        
        Returns:
            The first item from the queue.
            
        Raises:
            QueueEmpty: If the queue is empty.
        """
        if self.empty():
            raise QueueEmpty()
        return self._get()

    def _put(self, val):
        """Internal method to put an item into the queue.
        
        Args:
            val: The item to put into the queue.
        """
        self._upd_jnevt(1)  # update join event
        self._evput.set()  # Schedule tasks waiting on put
        self._evput.clear()
        self._queue.append(val)

    async def put(self, val):
        """Put an item into the queue.
        
        If the queue is full, wait until a slot is available.
        
        Args:
            val: The item to put into the queue.
        """
        while self.full():
            # Queue full
            await self._evget.wait()
            # Task(s) waiting to get from queue, schedule first Task
        self._put(val)

    def put_nowait(self, val):
        """Put an item into the queue without blocking.
        
        Args:
            val: The item to put into the queue.
            
        Raises:
            QueueFull: If the queue is full.
        """
        if self.full():
            raise QueueFull()
        self._put(val)

    def qsize(self):
        """Get the current size of the queue.
        
        Returns:
            int: The number of items in the queue.
        """
        return len(self._queue)

    def empty(self):
        """Check if the queue is empty.
        
        Returns:
            bool: True if the queue is empty, False otherwise.
        """
        return len(self._queue) == 0

    def full(self):
        """Check if the queue is full.
        
        Returns:
            bool: True if the queue is full, False otherwise.
            Note: If maxsize is 0 or negative, this method always returns False.
        """
        return self.maxsize > 0 and self.qsize() >= self.maxsize

    def _upd_jnevt(self, inc: int):
        """Update the join count and join event.
        
        Args:
            inc (int): The increment to add to the join count.
        """
        self._jncnt += inc
        if self._jncnt <= 0:
            self._jnevt.set()
        else:
            self._jnevt.clear()

    def task_done(self):
        """Indicate that a formerly enqueued task is complete.
        
        Used by queue consumers. For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.
        """
        self._upd_jnevt(-1)

    async def join(self):
        """Wait until all items in the queue have been processed.
        
        Blocks until all items have been processed (i.e., until task_done()
        has been called for each item that has been put into the queue).
        """
        await self._jnevt.wait()


class InstructionsQueue:
    """A queue for managing and executing instructions asynchronously.
    
    This class provides a mechanism to queue up instructions (callbacks with their arguments)
    and execute them sequentially in an asynchronous manner.
    """

    def __init__(self):
        """Initialize an empty instructions queue."""
        self._instructions = Queue()

    def add(self, callback, *args, **kwargs):
        """Add an instruction to the queue.
        
        Args:
            callback: The function to be executed
            *args: Positional arguments to be passed to the callback
            **kwargs: Keyword arguments to be passed to the callback
        """
        self._instructions.put_nowait((callback, args, kwargs))

    async def run(self):
        """Run the instructions queue continuously.
        
        This method runs indefinitely, processing instructions from the queue as they become
        available. Each instruction is executed with its associated arguments.
        """
        while True:
            instruction, args, kwargs = await self._instructions.get()
            instruction(*args, **kwargs)
            self._instructions.task_done()
