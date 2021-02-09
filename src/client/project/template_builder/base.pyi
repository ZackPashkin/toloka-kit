from enum import Enum
from typing import Any, Dict, Optional, Type

from ...primitives.base import BaseTolokaObject


class ComponentType(Enum):
    ...

class BaseTemplate(BaseTolokaObject):

    def __repr__(self): ...

    def __str__(self): ...

    def __eq__(self, other): ...

    def __ne__(self, other): ...

    def __lt__(self, other): ...

    def __le__(self, other): ...

    def __gt__(self, other): ...

    def __ge__(self, other): ...

    def __init__(self) -> None: ...

    _unexpected: Optional[Dict[str, Any]]

class BaseComponent(BaseTemplate):

    def __repr__(self): ...

    def __str__(self): ...

    def __eq__(self, other): ...

    def __ne__(self, other): ...

    def __lt__(self, other): ...

    def __le__(self, other): ...

    def __gt__(self, other): ...

    def __ge__(self, other): ...

    def __init__(self) -> None: ...

    _unexpected: Optional[Dict[str, Any]]

class BaseComponentOr(BaseTolokaObject):

    def __repr__(self): ...

    def __str__(self): ...

    def __eq__(self, other): ...

    def __ne__(self, other): ...

    def __lt__(self, other): ...

    def __le__(self, other): ...

    def __gt__(self, other): ...

    def __ge__(self, other): ...

    def __init__(self) -> None: ...

    _unexpected: Optional[Dict[str, Any]]

def base_component_or(type_: Type, class_name_suffix: Optional[str] = ...): ...

class VersionedBaseComponent(BaseComponent):

    def __repr__(self): ...

    def __str__(self): ...

    def __eq__(self, other): ...

    def __ne__(self, other): ...

    def __lt__(self, other): ...

    def __le__(self, other): ...

    def __gt__(self, other): ...

    def __ge__(self, other): ...

    def __setattr__(self, name, val): ...

    def __init__(self, *, version: Optional[str] = ...) -> None: ...

    _unexpected: Optional[Dict[str, Any]]
    version: Optional[str]

class UnknownComponent(BaseTemplate):

    def __repr__(self): ...

    def __str__(self): ...

    def __eq__(self, other): ...

    def __ne__(self, other): ...

    def __lt__(self, other): ...

    def __le__(self, other): ...

    def __gt__(self, other): ...

    def __ge__(self, other): ...

    def __init__(self) -> None: ...

    _unexpected: Optional[Dict[str, Any]]

class RefComponent(BaseTemplate):
    """If you need to insert the same or similar code snippets many times, reuse them.

    This helps make your configuration shorter and makes it easier for you to edit duplicate chunks of code.

    You can insert a code snippet from another part of the configuration anywhere inside the configuration. To do this,
    use the structure RefComponent(ref="path.to.element").

    This is useful when you need to insert the same snippet at multiple places in your code. For example, if you need
    to run the same action using multiple buttons, put this action in a variable and call it using RefComponent.
    """

    def __repr__(self): ...

    def __str__(self): ...

    def __eq__(self, other): ...

    def __ne__(self, other): ...

    def __lt__(self, other): ...

    def __le__(self, other): ...

    def __gt__(self, other): ...

    def __ge__(self, other): ...

    def __init__(self, *, ref: Optional[str] = ...) -> None: ...

    _unexpected: Optional[Dict[str, Any]]
    ref: Optional[str]

class ListDirection(Enum):
    ...

class ListSize(Enum):
    ...
