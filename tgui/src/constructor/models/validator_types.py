from typing import List, Any


class ValidatorType:
  ERROR = 'error'
  STRING = 'string'
  INTEGER = 'integer'
  FLOAT = 'float'
  CONTACT = 'contact'
  LOCATION_ENTITY = 'location_entity'
  LOCATION_TEXT = 'location_text'
  LOCATION = 'location'
  MESSAGE_WITH_TEXT = 'message_with_text'

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
    **kargs,
  ):
    self.type = type
    if type == ValidatorType.INTEGER:
      self.min = kargs.get('min', None)
      self.max = kargs.get('max', None)
    elif type == ValidatorType.FLOAT:
      self.min = kargs.get('min', None)
      self.max = kargs.get('max', None)
    elif type not in ValidatorType.values():
      raise ValueError(f'Invalid validator type: {type}')
