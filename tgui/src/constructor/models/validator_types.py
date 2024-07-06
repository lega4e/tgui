import enum
from typing import List, Any


@enum.unique
class ValidatorType(enum.StrEnum):
  ERROR = 'error'
  STRING = 'string'
  INTEGER = 'integer'
  FLOAT = 'float'
  CONTACT = 'contact'
  LOCATION_ENTITY = 'location_entity'
  LOCATION_TEXT = 'location_text'
  LOCATION = 'location'
  MESSAGE_WITH_TEXT = 'message_with_text'
  MULTIPLE_CHOICE_COUNT = 'multiple_choice_count'

  @staticmethod
  def values() -> List[Any]:
    return [
      ValidatorType.ERROR,
      ValidatorType.STRING,
      ValidatorType.INTEGER,
      ValidatorType.FLOAT,
      # ValidatorType.CONTACT,
      # ValidatorType.LOCATION_ENTITY,
      # ValidatorType.LOCATION_TEXT,
      # ValidatorType.LOCATION,
      ValidatorType.MESSAGE_WITH_TEXT,
    ]


class ValidatorDescription:

  def __init__(
    self,
    type: ValidatorType,
    **kwargs,
  ):
    self.type = type
    if type == ValidatorType.INTEGER:
      self.min = kwargs.get('min', None)
      self.minErrorMessage = kwargs.get('minErrorMessage', None)
      self.max = kwargs.get('max', None)
      self.maxErrorMessage = kwargs.get('maxErrorMessage', None)
    elif type == ValidatorType.FLOAT:
      self.min = kwargs.get('min', None)
      self.minErrorMessage = kwargs.get('minErrorMessage', None)
      self.max = kwargs.get('max', None)
      self.maxErrorMessage = kwargs.get('maxErrorMessage', None)
    elif type == ValidatorType.MULTIPLE_CHOICE_COUNT:
      self.min = kwargs.get('min', None)
      self.minErrorMessage = kwargs.get('minErrorMessage', None)
      self.max = kwargs.get('max', None)
      self.maxErrorMessage = kwargs.get('maxErrorMessage', None)
    elif type not in ValidatorType.values():
      raise ValueError(f'Invalid validator type: {type}')
