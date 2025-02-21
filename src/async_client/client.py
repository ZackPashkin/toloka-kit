__all__ = [
    'AsyncTolokaClient',
]

import asyncio
import datetime
import logging

from ..client import TolokaClient, operations
from ..util import AsyncMultithreadWrapper

logger = logging.getLogger(__name__)


class AsyncTolokaClient:
    """Class that implements interaction with [Toloka API], in an asynchronous way.

    All methods are wrapped as async. So all methods calls must be awaited.
    All arguments, same as in TolokaClient.
    """
    def __init__(self, *args, **kwargs):
        self._async_wrapped_client = AsyncMultithreadWrapper(TolokaClient(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self._async_wrapped_client, name)

    @classmethod
    def from_sync_client(cls, client: TolokaClient) -> 'AsyncTolokaClient':
        return AsyncTolokaClient(
            token=client.token,
            url=client.url,
            timeout=client.default_timeout,
            retryer_factory=client.retryer_factory,
        )

    async def wait_operation(self, op: operations.Operation, timeout: datetime.timedelta = datetime.timedelta(minutes=10), logger=logger) -> operations.Operation:
        """Asynchronous version of wait_operation
        """
        default_time_to_wait = datetime.timedelta(seconds=1)
        default_initial_delay = datetime.timedelta(milliseconds=500)

        if op.is_completed():
            return op

        utcnow = datetime.datetime.utcnow()
        wait_until_time = utcnow + timeout

        if not op.started or utcnow - op.started < default_initial_delay:
            await asyncio.sleep(default_initial_delay.total_seconds())

        while True:
            op = await self.get_operation(op.id)
            if op.is_completed():
                return op
            await asyncio.sleep(default_time_to_wait.total_seconds())
            if datetime.datetime.utcnow() > wait_until_time:
                raise TimeoutError
