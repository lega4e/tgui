import enum
from typing import List, Any

from attr import field, define
from attr.validators import instance_of
from lega4e_library.attrs.jsonkin import jsonkin, Jsonkin


@enum.unique
class FormTgConditionType(enum.StrEnum):
  value = 'value'
  custom = 'custom'


@jsonkin
@define
class FormTgCondition(Jsonkin):
  type: FormTgConditionType = field(
    validator=instance_of(FormTgConditionType),
    converter=FormTgConditionType,
  )


@jsonkin
@define
class FormTgConditionValue(FormTgCondition):
  itemId: str = field(validator=instance_of(str))
  value: Any = field()


@jsonkin
@define
class FormTgConditionCustom(FormTgCondition):
  subtype: str = field(validator=instance_of(str))
  data: Any = field(default=None)


def formTgConditionFromJson(json) -> FormTgCondition:
  if json['type'] == FormTgConditionType.value.value:
    return FormTgConditionValue.fromJson(json)
  elif json['type'] == FormTgConditionType.custom.value:
    return FormTgConditionCustom.fromJson(json)
  else:
    raise ValueError(f'Unsupported condition type: {json["type"]}')


FormTgCondition.fromJson = formTgConditionFromJson


@jsonkin
@define
class FormTgElement(Jsonkin):
  id: str = field(validator=instance_of(str))
  item: Any = field(validator=lambda _, __, value: value is not None)
  conditions: List[FormTgCondition] = FormTgCondition.attrListField()


@jsonkin
@define
class FormTgItem:
  elements: List[FormTgElement] = FormTgElement.attrListField()
