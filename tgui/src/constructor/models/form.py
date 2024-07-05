from typing import List, Any

from attr import field, define
from attr.validators import instance_of
from lega4e_library.attrs.jsonkin import jsonkin
from lega4e_library.attrs.validators import list_validator


@jsonkin
@define
class FormTgCondition:
  itemId: str = field(validator=instance_of(str))
  value: Any = field()


@jsonkin
@define
class FormTgElement:
  id: str = field(validator=instance_of(str))
  item: Any = field(validator=lambda _, __, value: value is not None)
  conditions: List[FormTgCondition] = field(
    validator=list_validator(FormTgCondition),
    default=[],
  )


@jsonkin
@define
class FormTgItem:
  elements: List[FormTgElement] = field(validator=list_validator(FormTgElement))
