__all__ = [
    'AssignmentEventsInPool',
    'AssignmentsInPool',
    'Balance',
    'bind_client',
    'PoolCompletedPercentage',
]

import datetime
from functools import lru_cache
from itertools import groupby
from operator import attrgetter
import re
import sys

if sys.version_info[:2] >= (3, 8):
    from functools import cached_property
else:
    from cached_property import cached_property

import attr
from typing import Any, Optional, Dict, List, Tuple
from ..async_client import AsyncTolokaClient
from ..client import (
    Requester,
    TolokaClient,
    Pool,
)
from ..client import analytics_request
from ..client.operations import Operation
from ..client._converter import structure
from ..streaming import cursor
from ..util.async_utils import Cooldown


@lru_cache(maxsize=128)
def get_pool(pool_id: str, toloka_client: TolokaClient) -> Pool:
    return toloka_client.get_pool(pool_id)


def bind_client(metrics: List['BaseMetric'], toloka_client: TolokaClient) -> None:
    """Sets/updates toloka_client for all metrics in list.

    Examples:
        How to bind same client for all metrics:
        >>> import toloka.client as toloka
        >>> from toloka.metrics import AssignmentsInPool, Balance, bind_client, MetricCollector
        >>>
        >>> toloka_client = toloka.TolokaClient(auth_token, 'PRODUCTION')
        >>>
        >>> collector = MetricCollector(
        >>>     [
        >>>         Balance(),
        >>>         AssignmentsInPool(pool_id),
        >>>     ],
        >>> )
        >>> bind_client(collector.metrics, toloka_client)
        ...

        How to bind several clients:
        >>> metrics_1 = bind_client([Balance(), AssignmentsInPool(pool_id_1)], toloka_client_1)
        >>> metrics_2 = bind_client([Balance(), AssignmentsInPool(pool_id_2)], toloka_client_2)
        >>> collector = MetricCollector(metrics_1 + metrics_2)
        ...
    """
    for metric in metrics:
        if not isinstance(metric, BaseMetric):
            raise TypeError(f'One of element is not instance of BaseMetric: "{metric}"')
        metric.toloka_client = toloka_client


@attr.s(auto_attribs=True)
class BaseMetric:
    """Base class for all metrics.

    Stores TolokaClient instance for this metric.
    """
    toloka_client: TolokaClient = attr.ib(kw_only=True, default=None)
    timeout: datetime.timedelta = attr.ib(kw_only=True, factory=lambda: datetime.timedelta(seconds=10))

    @cached_property
    def atoloka_client(self):
        assert self.toloka_client is not None
        return AsyncTolokaClient.from_sync_client(self.toloka_client)

    async def get_lines(self) -> Dict[str, List[Tuple[Any, Any]]]:
        """Gather and return metrics

        All metrics returned in the same format: named list, contain pairs of: datetime of some event, metric value.
        Could not return some metrics in dict on iteration or return it with empty list:
        means that is nothing being gathered on this step. This is not zero value!

        Return example:
        {
            'rejected_assignments_in_pool': [(datetime.datetime(2021, 8, 12, 10, 4, 44, 895232), 0)],
            'submitted_assignments_in_pool': [(datetime.datetime(2021, 8, 12, 10, 4, 45, 321904), 75)],
            'accepted_assignments_in_pool': [(datetime.datetime(2021, 8, 12, 10, 4, 45, 951156), 75)],
            'accepted_events_in_pool': [(datetime.datetime(2021, 8, 11, 15, 13, 3, 65000), 1), ... ],
            'rejected_events_in_pool': [],
            # no toloka_requester_balance on this iteration
        }
        """
        async with self.coldown:
            result = await self._get_lines_impl()
            return result

    async def _get_lines_impl(self) -> Dict[str, List[Tuple[Any, Any]]]:
        """Real method for gathering metrics"""
        raise NotImplementedError

    @cached_property
    def coldown(self) -> Cooldown:
        return Cooldown(self.timeout.total_seconds())

    def get_line_names(self) -> List[str]:
        """Returns a list of metric names that can be generated by this class instance.
        For example, if a class can generate 5 metrics, but some instance generate only 3 of them,
        this method will return a list with exactly 3 strings. If you call 'get_metrics' on this instance,
        it could return from 0 to 3 metrics.
        """
        raise NotImplementedError

    @cached_property
    def beautiful_name(self) -> str:
        """Used for creating chart from raw metric in jupyter notebook"""
        words = [word for word in re.split(r'([A-Z][a-z]*)', self.__class__.__name__) if word]
        return ' '.join(words).capitalize()


@attr.s(auto_attribs=True)
class BasePoolMetric(BaseMetric):
    """Base class for all pool metrics"""
    pool_id : str = attr.ib(kw_only=False)

    @cached_property
    def beautiful_name(self) -> str:
        name = super(BasePoolMetric, self).beautiful_name
        pool = get_pool(self.pool_id, self.toloka_client)
        return f'{name} \'{pool.private_name}\' ({pool.id})'


@attr.s(auto_attribs=True)
class AssignmentEventsInPool(BasePoolMetric):
    """Tracking the change of response statuses in the pool.
    The metric is convenient for tracking that the pool is generally "alive" and working.
    If you want to track assignments counts, it's better to use AssignmentsInPool.

    Metrics starts gathering if they name are set. If the metric name is set to None, they don't gathering.

    Args:
        pool_id: From which pool track metrics.
        created_name: Metric name for a count of created events. Default None.
        submitted_name: Metric name for a count of submitted events. Default 'submitted_events_in_pool'.
        accepted_name : Metric name for a count of accepted events. Default 'accepted_events_in_pool'.
        rejected_name : Metric name for a count of rejected events. Default 'rejected_events_in_pool'.
        skipped_name: Metric name for a count of skipped events. Default None.
        expired_name: Metric name for a count of expired events. Default None.
        join_events: Count all events in one point.  Default False.

    Raises:
        ValueError: If all metric names are set to None or if there are duplicate metric names.

    Example:
        How to collect this metrics:
        >>>  def print_metric(metric_dict):
        >>>     print(metric_dict)
        >>>
        >>> collector = MetricCollector(AssignmentEventsInPool(pool_id, toloka_client=toloka_client))
        >>> asyncio.run(collector.run())
        {
            'submitted_events_in_pool': [(datetime.datetime(2021, 8, 11, 15, 13, 4, 31000), 5)],
            'accepted_events_in_pool': [(datetime.datetime(2021, 8, 11, 15, 13, 3, 65000), 1)],
            'rejected_events_in_pool': [],
        }
    """
    _created_name : Optional[str] = None
    _submitted_name : Optional[str] = None
    _accepted_name : Optional[str] = None
    _rejected_name : Optional[str] = None
    _skipped_name : Optional[str] = None
    _expired_name : Optional[str] = None

    _join_events : bool = False

    _status_dict = {
        '_created_name': 'CREATED',
        '_submitted_name': 'SUBMITTED',
        '_accepted_name': 'ACCEPTED',
        '_rejected_name': 'REJECTED',
        '_skipped_name': 'SKIPPED',
        '_expired_name': 'EXPIRED',
    }

    def __attrs_post_init__(self):
        metric_names = self.get_line_names()
        if not metric_names:
            self._submitted_name = 'submitted_events_in_pool'
            self._accepted_name = 'accepted_events_in_pool'
            self._rejected_name = 'rejected_events_in_pool'
        elif len(metric_names) != len(set(metric_names)):
            raise ValueError('Duplicate metric names.')

    def get_line_names(self) -> List[str]:
        """Returns a list of metric names that can be generated by this class instance.
        """
        return [getattr(self, attr_name) for attr_name in self._status_dict if getattr(self, attr_name) is not None]

    @cached_property
    def _cursors(self) -> Dict[str, cursor.AssignmentCursor]:
        # key - metric name. One of the value of paramets: created_name, submitted_name, etc.
        # val - cursor configured for gathering this metric
        cursors = {}
        start_time = datetime.datetime.utcnow()
        for attr_name, status_value in self._status_dict.items():
            metric_name = getattr(self, attr_name)
            if metric_name:
                cursors[metric_name] = cursor.AssignmentCursor(
                    pool_id=self.pool_id,
                    event_type=status_value,
                    toloka_client=self.atoloka_client,
                    **{f'{status_value.lower()}_gte': start_time},
                )
        return cursors

    async def _get_lines_impl(self) -> Dict[str, List[Tuple[Any, Any]]]:
        result = {}
        for metric_name, it in self._cursors.items():
            event_list = [event async for event in it]
            if self._join_events:
                event = None
                count = sum(1 for event in event_list)
                result[metric_name] = [(event.event_time, count)] if count else [(datetime.datetime.utcnow(), 0)]
            else:
                result[metric_name] = [
                    (event_time, sum(1 for _ in events))
                    for event_time, events in groupby(event_list, attrgetter('event_time'))
                ]
        return result


@attr.s(auto_attribs=True)
class PoolCompletedPercentage(BasePoolMetric):
    """Track pool completion in percentage

    Args:
        pool_id: From which pool track metrics.
        percents_name: Metric name for pool completion percentage. Default 'completion_percentage'.
        toloka_client: Client for connection to Toloka. You can set toloka_client for several metrics via "bind_client" function.

    Example:
        How to collect this metric:
        >>>  def print_metric(metric_dict):
        >>>     print(metric_dict)
        >>>
        >>> collector = MetricCollector(PoolCompletedPercentage(pool_id, toloka_client=toloka_client))
        >>> asyncio.run(collector.run())
        {
            'completion_percentage': [(datetime.datetime(2021, 8, 11, 15, 13, 4, 31000), 55)],
        }
    """
    _percents_name : Optional[str] = None
    _previous_operation : Optional[Operation] = attr.ib(init=False, default=None)

    def __attrs_post_init__(self):
        if self._percents_name is None:
            self._percents_name = 'completion_percentage'

    def get_line_names(self) -> List[str]:
        """Returns a list of metric names that can be generated by this class instance.
        """
        return [self._percents_name]

    async def _get_lines_impl(self) -> Dict[str, List[Tuple[Any, Any]]]:
        result = {}
        operation = await self.atoloka_client.get_analytics([analytics_request.CompletionPercentagePoolAnalytics(subject_id=self.pool_id)])
        operation = await self.atoloka_client.wait_operation(operation)

        if operation.status == Operation.Status.SUCCESS:
            for response in operation.details['value']:
                result[self._percents_name] = [(structure(response['finished'], datetime.datetime), response['result']['value'])]

        return result


@attr.s(auto_attribs=True)
class AssignmentsInPool(BasePoolMetric):
    """Tracking the count of assignments in different states in the pool.

    Metrics starts gathering if they name are set. If the metric name is set to None, they don't gathering.
    This metric could "skip" get_metrics and return an empty list if the inner operation was still in progress.

    Args:
        pool_id: From which pool track metrics.
        submitted_name: Metric name for a count of submitted assignments. Default 'submitted_assignments_in_pool'.
        accepted_name : Metric name for a count of accepted assignments. Default 'accepted_assignments_in_pool'.
        rejected_name : Metric name for a count of rejected assignments. Default 'rejected_assignments_in_pool'.
        skipped_name: Metric name for a count of skipped assignments. Default None.

    Raises:
        ValueError: If all metric names are set to None.

    Example:
        How to collect this metrics:
        >>>  def print_metric(metric_dict):
        >>>     print(metric_dict)
        >>>
        >>> collector = MetricCollector(AssignmentsInPool(pool_id, toloka_client=toloka_client))
        >>> asyncio.run(collector.run())
        {
            'rejected_assignments_in_pool': [(datetime.datetime(2021, 8, 12, 10, 4, 44, 895232), 0)],
            'submitted_assignments_in_pool': [(datetime.datetime(2021, 8, 12, 10, 4, 45, 321904), 75)],
            'accepted_assignments_in_pool': [(datetime.datetime(2021, 8, 12, 10, 4, 45, 951156), 75)],
        }
    """
    _submitted_name : Optional[str] = None
    _accepted_name : Optional[str] = None
    _rejected_name : Optional[str] = None
    _skipped_name : Optional[str] = None

    _previous_operation : Optional[Operation] = attr.ib(init=False, default=None)

    _analytics_dict = {
        '_submitted_name': analytics_request.SubmitedAssignmentsCountPoolAnalytics,
        '_accepted_name': analytics_request.ApprovedAssignmentsCountPoolAnalytics,
        '_rejected_name': analytics_request.RejectedAssignmentsCountPoolAnalytics,
        '_skipped_name': analytics_request.SkippedAssignmentsCountPoolAnalytics,
    }

    def __attrs_post_init__(self):
        metric_names = self.get_line_names()
        if not metric_names:
            self._submitted_name = 'submitted_assignments_in_pool'
            self._accepted_name = 'accepted_assignments_in_pool'
            self._rejected_name = 'rejected_assignments_in_pool'
        elif len(metric_names) != len(set(metric_names)):
            raise ValueError('Duplicate metric names.')

    def get_line_names(self) -> List[str]:
        """Returns a list of metric names that can be generated by this class instance.
        """
        return [getattr(self, attr_name) for attr_name in self._analytics_dict if getattr(self, attr_name) is not None]

    @cached_property
    def _analytics_request(self) -> List[analytics_request.PoolAnalyticsRequest]:
        analytics_for_request = []
        for attr_name, analytic in self._analytics_dict.items():
            attr_val = getattr(self, attr_name)
            if attr_val:
                analytics_for_request.append(analytic(subject_id=self.pool_id))

        return analytics_for_request

    @cached_property
    def _analytic_classes_to_metric_names(self) -> Dict[str, str]:
        return {str(analytic_class.name.value): field_name for field_name, analytic_class in self._analytics_dict.items()}

    async def _get_lines_impl(self) -> Dict[str, List[Tuple[Any, Any]]]:
        result = {}
        operation = await self.atoloka_client.get_analytics(self._analytics_request)
        operation = await self.atoloka_client.wait_operation(operation)

        if operation.status == Operation.Status.SUCCESS:
            for response in operation.details['value']:
                metric_name = response['request']['name']
                metric_name = self._analytic_classes_to_metric_names[metric_name]
                metric_name = getattr(self, metric_name)
                result[metric_name] = [(structure(response['finished'], datetime.datetime), response['result'])]

        return result


@attr.s(auto_attribs=True)
class Balance(BaseMetric):
    """Traking your Toloka balance.

    Returns only one metric: don't spend and don't reserved money on your acount.

    Args:
        balance_name: Metric name. Default 'toloka_requester_balance'.

    Raises:
        ValueError: If all metric names are set to None.

    Example:
        How to collect this metrics:
        >>>  def print_metric(metric_dict):
        >>>     print(metric_dict)
        >>>
        >>> collector = MetricCollector(Balance(toloka_client=toloka_client))
        >>> asyncio.run(collector.run())
        {
            toloka_requester_balance: [(datetime.datetime(2021, 8, 30, 10, 30, 59, 628239), Decimal('123.4500'))],
        }
    """

    balance_name : Optional[str] = None

    def __attrs_post_init__(self):
        if self.balance_name is None:
            self.balance_name = 'toloka_requester_balance'

    def get_line_names(self) -> List[str]:
        """Returns a list of metric names that can be generated by this class instance.
        """
        return [self.balance_name]

    async def _get_lines_impl(self) -> Dict[str, List[Tuple[Any, Any]]]:
        requester: Requester = await self.atoloka_client.get_requester()
        result = {self.balance_name: [(datetime.datetime.utcnow(), requester.balance)]}
        return result
