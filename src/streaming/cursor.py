__all__ = [
    'AssignmentCursor',
    'BaseCursor',
    'DATETIME_MIN',
    'MessageThreadCursor',
    'TaskCursor',
    'TolokaClientSyncOrAsyncType',
    'UserBonusCursor',
    'UserRestrictionCursor',
    'UserSkillCursor',
]

import attr
import copy
import functools
from datetime import datetime
from typing import Any, AsyncIterator, Awaitable, Callable, Iterator, List, Optional, Set, Tuple, Union
from typing_extensions import Protocol

from ..client import (
    Assignment,
    MessageThread,
    Task,
    TolokaClient,
    UserBonus,
    UserRestriction,
    UserSkill,
    expand,
    search_requests,
    search_results,
    structure,
)
from ..client.search_requests import BaseSearchRequest
from ..util._codegen import fix_attrs_converters
from .event import AssignmentEvent, BaseEvent, MessageThreadEvent, TaskEvent, UserBonusEvent, UserRestrictionEvent, UserSkillEvent
from ..util.async_utils import AsyncMultithreadWrapper, ensure_async


class ResponseObjectType(Protocol):
    items: Optional[List[Any]]
    has_more: Optional[bool]


TolokaClientSyncOrAsyncType = Union[TolokaClient, AsyncMultithreadWrapper[TolokaClient]]

DATETIME_MIN = datetime.fromtimestamp(0)


@attr.s
class _ByIdCursor:
    """Iterate by id only."""
    fetcher: Callable[[BaseSearchRequest], ResponseObjectType] = attr.ib()
    request: BaseSearchRequest = attr.ib()

    def __iter__(self) -> Iterator[Any]:
        while True:
            response = self.fetcher(self.request, sort='id')  # Diff between sync and async.
            if response.items:
                for item in response.items:
                    yield item
                self.request = attr.evolve(self.request, id_gt=item.id)
            if not response.has_more:
                return

    async def __aiter__(self) -> AsyncIterator[Any]:
        while True:
            response = await ensure_async(self.fetcher)(self.request, sort='id')  # Diff between sync and async.
            if response.items:
                for item in response.items:
                    yield item
                self.request = attr.evolve(self.request, id_gt=item.id)
            if not response.has_more:
                return


@attr.s
class BaseCursor:
    toloka_client: TolokaClientSyncOrAsyncType = attr.ib()
    _request: BaseSearchRequest = attr.ib()
    _prev_response: Optional[ResponseObjectType] = attr.ib(default=None, init=False)
    _seen_ids: Set[str] = attr.ib(factory=set, init=False)

    @attr.s
    class CursorFetchContext:
        """Context manager to return from `BaseCursor.try_fetch_all method`.
        Commit cursor state only if no error occured.
        """
        _cursor: 'BaseCursor' = attr.ib()
        _start_state: Optional[Tuple] = attr.ib(default=None, init=False)
        _finish_state: Optional[Tuple] = attr.ib(default=None, init=False)

        def __enter__(self) -> List[BaseEvent]:
            self._start_state = copy.deepcopy(self._cursor._get_state())
            res = [item for item in self._cursor]
            self._finish_state = self._cursor._get_state()
            self._cursor._set_state(self._start_state)
            return res

        async def __aenter__(self) -> List[BaseEvent]:
            self._start_state = copy.deepcopy(self._cursor._get_state())
            res = [item async for item in self._cursor]
            self._finish_state = self._cursor._get_state()
            self._cursor._set_state(self._start_state)
            return res

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            if exc_type is None:
                self._cursor._set_state(self._finish_state)

        async def __aexit__(self, exc_type, exc_value, traceback) -> Awaitable[None]:
            if exc_type is None:
                self._cursor._set_state(self._finish_state)

    def _get_state(self) -> Tuple:
        return self._request, self._prev_response, self._seen_ids

    def _set_state(self, state: Tuple) -> None:
        self._request, self._prev_response, self._seen_ids = state

    def inject(self, injection: 'BaseCursor') -> None:
        self._set_state(injection._get_state())

    def try_fetch_all(self) -> CursorFetchContext:
        return self.CursorFetchContext(self)

    def __attrs_post_init__(self):
        if not getattr(self._request, self._time_field_gte):
            self._request = attr.evolve(self._request, **{self._time_field_gte: DATETIME_MIN})

    def _get_fetcher(self) -> Callable[..., ResponseObjectType]:
        """Return toloka_client method from here."""
        raise NotImplementedError

    def _get_time_field(self) -> str:
        """Getter for time field."""
        raise NotImplementedError

    def _construct_event(self, item: Any) -> BaseEvent:
        """Create event based on object."""
        raise NotImplementedError

    def _get_time(self, item: Any) -> datetime:
        return getattr(item, self._get_time_field())

    @property
    def _time_field_gte(self) -> str:
        return f'{self._get_time_field()}_gte'

    @property
    def _time_field_lte(self) -> str:
        return f'{self._get_time_field()}_lte'  # To iterate by id for fixed time.

    @property
    def _time_field_gt(self) -> str:
        return f'{self._get_time_field()}_gt'  # To use after iteration by id.

    def __iter__(self) -> Iterator[BaseEvent]:
        fetcher = self._get_fetcher()
        while True:
            response = fetcher(self._request, sort=self._get_time_field())  # Diff between sync and async.
            if response.items:
                max_time = self._get_time(response.items[-1])
                self._prev_response = response
                for item in response.items:
                    if item.id not in self._seen_ids:
                        self._request = attr.evolve(self._request, **{self._time_field_gte: self._get_time(item)})
                        self._seen_ids.add(item.id)
                        yield self._construct_event(item)

                if not response.has_more:
                    return

                if self._get_time(response.items[0]) == max_time:
                    fixed_time_request = attr.evolve(self._request, **{self._time_field_lte: max_time})
                    for item in _ByIdCursor(fetcher, fixed_time_request):  # Diff between sync and async.
                        if item.id not in self._seen_ids:
                            self._seen_ids.add(item.id)
                            yield self._construct_event(item)
                    self._request = attr.evolve(self._request, **{self._time_field_gt: max_time})

                # Strip it to the current response size.
                self._seen_ids = {item.id for item in response.items}
            else:
                return

    async def __aiter__(self) -> AsyncIterator[BaseEvent]:
        fetcher = self._get_fetcher()
        while True:
            response = await ensure_async(fetcher)(self._request, sort=self._get_time_field())  # Diff between sync and async.
            if response.items:
                max_time = self._get_time(response.items[-1])
                self._prev_response = response
                for item in response.items:
                    if item.id not in self._seen_ids:
                        self._request = attr.evolve(self._request, **{self._time_field_gte: self._get_time(item)})
                        self._seen_ids.add(item.id)
                        yield self._construct_event(item)

                if not response.has_more:
                    return

                if self._get_time(response.items[0]) == max_time:
                    fixed_time_request = attr.evolve(self._request, **{self._time_field_lte: max_time})
                    async for item in _ByIdCursor(fetcher, fixed_time_request):  # Diff between sync and async.
                        if item.id not in self._seen_ids:
                            self._seen_ids.add(item.id)
                            yield self._construct_event(item)
                    self._request = attr.evolve(self._request, **{self._time_field_gt: max_time})

                # Strip it to the current response size.
                self._seen_ids = {item.id for item in response.items}
            else:
                return


@expand('request')
@fix_attrs_converters
@attr.s
class AssignmentCursor(BaseCursor):
    """Iterator over Assignment objects of seleted AssignmentEventType.

    Args:
        toloka_client: TolokaClient object that is being used to search assignments.
        request: Base request to search assignments by.
        event_type: Assignments event's type to search.

    Examples:
        Iterate over assignment acceptances events.

        >>> it = AssignmentCursor(pool_id='123', event_type='ACCEPTED', toloka_client=toloka_client)
        >>> current_events = list(it)
        >>> # ... new events may occur ...
        >>> new_events = list(it)  # Contains only new events, occured since the previous call.
        ...
    """

    _event_type: AssignmentEvent.Type = attr.ib(converter=functools.partial(structure, cl=AssignmentEvent.Type))
    _request: search_requests.AssignmentSearchRequest = attr.ib(
        factory=search_requests.AssignmentSearchRequest,
    )

    def _get_fetcher(self) -> Callable[..., search_results.AssignmentSearchResult]:
        return self.toloka_client.find_assignments

    def _get_time_field(self) -> str:
        return self._event_type.time_key

    def _construct_event(self, item: Assignment) -> AssignmentEvent:
        return AssignmentEvent(assignment=item,
                               event_type=self._event_type,
                               event_time=getattr(item, self._event_type.time_key))


@expand('request')
@fix_attrs_converters
@attr.s
class TaskCursor(BaseCursor):
    """Iterator over tasks by create time.

    Args:
        toloka_client: TolokaClient object that is being used to search tasks.
        request: Base request to search tasks by.

    Examples:
        Iterate over tasks.

        >>> it = TaskCursor(pool_id='123', toloka_client=toloka_client)
        >>> current_tasks = list(it)
        >>> # ... new tasks could appear ...
        >>> new_tasks = list(it)  # Contains only new tasks, appeared since the previous call.
        ...
    """

    _request: search_requests.TaskSearchRequest = attr.ib(
        factory=search_requests.TaskSearchRequest,
    )

    def _get_fetcher(self) -> Callable[..., search_results.TaskSearchResult]:
        return self.toloka_client.find_tasks

    def _get_time_field(self) -> str:
        return 'created'

    def _construct_event(self, item: Task) -> TaskEvent:
        return TaskEvent(task=item, event_time=item.created)


@expand('request')
@fix_attrs_converters
@attr.s
class UserBonusCursor(BaseCursor):
    """Iterator over user bonuses by create time.

    Args:
        toloka_client: TolokaClient object that is being used to search user bonuses.
        request: Base request to search user bonuses by.

    Examples:
        Iterate over user bonuses.

        >>> it = UserBonusCursor(toloka_client=toloka_client)
        >>> current_bonuses = list(it)
        >>> # ... new user bonuses could appear ...
        >>> new_bonuses = list(it)  # Contains only new user bonuses, appeared since the previous call.
        ...
    """

    _request: search_requests.UserBonusSearchRequest = attr.ib(
        factory=search_requests.UserBonusSearchRequest,
    )

    def _get_fetcher(self) -> Callable[..., search_results.UserBonusSearchResult]:
        return self.toloka_client.find_user_bonuses

    def _get_time_field(self) -> str:
        return 'created'

    def _construct_event(self, item: UserBonus) -> UserBonusEvent:
        return UserBonusEvent(user_bonus=item, event_time=item.created)


@expand('request')
@fix_attrs_converters
@attr.s
class UserSkillCursor(BaseCursor):
    """Iterator over UserSkillEvent objects of seleted event_type.

    Args:
        toloka_client: TolokaClient object that is being used to search user skills.
        request: Base request to search user skills by.
        event_type: User skill event's type to search.

    Examples:
        Iterate over user skills acceptances events.

        >>> it = UserSkillCursor(event_type='MODIFIED', toloka_client=toloka_client)
        >>> current_events = list(it)
        >>> # ... new user skills could be set ...
        >>> new_events = list(it)  # Contains only new events, occured since the previous call.
        ...
    """

    _event_type: UserSkillEvent.Type = attr.ib(converter=functools.partial(structure, cl=UserSkillEvent.Type))
    _request: search_requests.UserSkillSearchRequest = attr.ib(
        factory=search_requests.UserSkillSearchRequest,
    )

    def _get_fetcher(self) -> Callable[..., search_results.UserSkillSearchResult]:
        return self.toloka_client.find_user_skills

    def _get_time_field(self) -> str:
        return self._event_type.time_key

    def _construct_event(self, item: UserSkill) -> UserSkillEvent:
        return UserSkillEvent(user_skill=item,
                              event_type=self._event_type,
                              event_time=getattr(item, self._event_type.time_key))


@expand('request')
@fix_attrs_converters
@attr.s
class UserRestrictionCursor(BaseCursor):
    """Iterator over user restrictions by create time.

    Args:
        toloka_client: TolokaClient object that is being used to search user restrictions.
        request: Base request to search user restrictions.

    Examples:
        Iterate over user restrictions in project.

        >>> it = UserRestrictionCursor(toloka_client=toloka_client, project_id=my_proj_id)
        >>> current_restrictions = list(it)
        >>> # ... new restrictions could appear ...
        >>> new_restrictions = list(it)  # Contains only new user restrictions, appeared since the previous call.
        ...
    """

    _request: search_requests.UserRestrictionSearchRequest = attr.ib(
        factory=search_requests.UserRestrictionSearchRequest,
    )

    def _get_fetcher(self) -> Callable[..., search_results.UserRestrictionSearchResult]:
        return self.toloka_client.find_user_restrictions

    def _get_time_field(self) -> str:
        return 'created'

    def _construct_event(self, item: UserRestriction) -> UserRestrictionEvent:
        return UserRestrictionEvent(user_restriction=item, event_time=getattr(item, self._get_time_field()))


@expand('request')
@fix_attrs_converters
@attr.s
class MessageThreadCursor(BaseCursor):
    """Iterator over messages by create time.

    Args:
        toloka_client: TolokaClient object that is being used to search messages.
        request: Base request to search messages.

    Examples:
        Iterate over all messages.

        >>> it = MessageThreadCursor(toloka_client=toloka_client)
        >>> all_messages = list(it)
        >>> # ... new messages could appear ...
        >>> new_messages = list(it)  # Contains only new messages, appeared since the previous call.
        ...
    """

    _request: search_requests.MessageThreadSearchRequest = attr.ib(
        factory=search_requests.MessageThreadSearchRequest,
    )

    def _get_fetcher(self) -> Callable[..., search_results.MessageThreadSearchResult]:
        return self.toloka_client.find_message_threads

    def _get_time_field(self) -> str:
        return 'created'

    def _construct_event(self, item: MessageThread) -> MessageThreadEvent:
        return MessageThreadEvent(message_thread=item, event_time=getattr(item, self._get_time_field()))
