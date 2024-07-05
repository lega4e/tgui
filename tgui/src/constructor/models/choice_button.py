from typing import Any, Optional

from attr import field, define
from attr.validators import instance_of
from lega4e_library.attrs.jsonkin import jsonkin


@jsonkin
@define
class ChoiceButton:
  title: str = field(validator=instance_of(str))
  value: Any = field(default=None)
  offTitle: Optional[str] = field(
    validator=instance_of(Optional[str]),
    default=None,
  )
  answer: Optional[str] = field(
    validator=instance_of(Optional[str]),
    default=None,
  )
  isOnInitial: bool = field(validator=instance_of(bool), default=False)
  isEndButton: bool = field(validator=instance_of(bool), default=False)
