import enum
from typing import List, Any

from attr import field, define
from attr.validators import instance_of
from lega4e_library.attrs.jsonkin import jsonkin, Jsonkin


@enum.unique
class FormTgConditionType(enum.StrEnum):
  value = 'value'
  equal = 'equal'
  not_equal = 'not_equal'
  is_none = 'is_none'
  not_ = 'not'
  and_ = 'and'
  or_ = 'or'
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
  id: str = field(validator=instance_of(str))
  value: Any = field()


@jsonkin
@define
class FormTgConditionEqual(FormTgCondition):
  id: str = field(validator=instance_of(str))
  value: Any = field()


@jsonkin
@define
class FormTgConditionNotEqual(FormTgCondition):
  id: str = field(validator=instance_of(str))
  value: Any = field()


@jsonkin
@define
class FormTgConditionNot(FormTgCondition):
  condition: FormTgCondition = FormTgCondition.attrField()


@jsonkin
@define
class FormTgConditionAnd(FormTgCondition):
  conditions: List[FormTgCondition] = FormTgCondition.attrListField()


@jsonkin
@define
class FormTgConditionOr(FormTgCondition):
  conditions: List[FormTgCondition] = FormTgCondition.attrListField()


@jsonkin
@define
class FormTgConditionIsNone(FormTgCondition):
  id: str = field(validator=instance_of(str))


@jsonkin
@define
class FormTgConditionCustom(FormTgCondition):
  subtype: str = field(validator=instance_of(str))
  data: Any = field(default=None)


def formTgConditionFromJson(json) -> FormTgCondition:
  if json['type'] == FormTgConditionType.value.value:
    return FormTgConditionValue.jsonConverter(json)
  elif json['type'] == FormTgConditionType.equal.value:
    return FormTgConditionEqual.jsonConverter(json)
  elif json['type'] == FormTgConditionType.not_equal.value:
    return FormTgConditionNotEqual.jsonConverter(json)
  elif json['type'] == FormTgConditionType.is_none.value:
    return FormTgConditionIsNone.jsonConverter(json)
  elif json['type'] == FormTgConditionType.not_.value:
    return FormTgConditionNot.jsonConverter(json)
  elif json['type'] == FormTgConditionType.and_.value:
    return FormTgConditionAnd.jsonConverter(json)
  elif json['type'] == FormTgConditionType.or_.value:
    return FormTgConditionOr.jsonConverter(json)
  elif json['type'] == FormTgConditionType.custom.value:
    return FormTgConditionCustom.jsonConverter(json)
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
