import re
from logging import Logger
from typing import Callable, Optional

from telebot.async_telebot import AsyncTeleBot

from tgui.src.constructor.models.validator_types import ValidatorDescription, \
  ValidatorType
from tgui.src.domain.piece import Pieces, P
from tgui.src.domain.destination import TgDestination
from tgui.src.domain.validators import Validator, ValidatorObject, \
  FunctionValidator


class TgValidatorsFactory:

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    syslog: Logger,
    tglog: Logger,
  ):
    self.tg = tg
    self.destination = destination
    self.syslog = syslog
    self.tglog = tglog

  def get(
    self,
    validator: ValidatorDescription,
    errorMessage: Pieces,
  ) -> Validator:
    if validator.type == ValidatorType.ERROR:
      return self.alwaysError(errorMessage)
    elif validator.type == ValidatorType.STRING:
      return self.string(errorMessage)
    elif validator.type == ValidatorType.INTEGER:
      return self.integer(
        errorMessage,
        validator.min,
        validator.max,
        validator.minErrorMessage,
        validator.maxErrorMessage,
      )
    elif validator.type == ValidatorType.FLOAT:
      return self.floating(
        errorMessage,
        validator.min,
        validator.max,
        validator.minErrorMessage,
        validator.maxErrorMessage,
      )
    elif validator.type == ValidatorType.MESSAGE_WITH_TEXT:
      return self.messageWithText(errorMessage)
    else:
      raise ValueError(f'Invalid validator type: {validator.type}')

  def alwaysError(self, err: Pieces) -> Validator:
    return self._handleExceptionWrapper(lambda o: ValidatorObject(
      message=o.error,
      success=False,
      error=err,
    ))

  def string(self, err: Pieces) -> Validator:

    def validate(o: ValidatorObject):
      if o.message.text is None or len(o.message.text) == 0:
        o.success = False
        o.error = err
      else:
        o.data = o.message.text
      return o

    return self._handleExceptionWrapper(validate)

  def integer(
    self,
    err: Pieces,
    min: Optional[int] = None,
    max: Optional[int] = None,
    minErr: Optional[Pieces] = None,
    maxErr: Optional[Pieces] = None,
  ) -> Validator:

    def validate(o: ValidatorObject):
      o.data = o.message.text
      if not re.match(r'^-?\d+$', o.data):
        return self._error(o, err)
      o.data = int(o.data)

      if min is not None and o.data < min:
        return self._error(o, minErr or err)
      elif max is not None and o.data > max:
        return self._error(o, maxErr or err)
      return o

    return self._handleExceptionWrapper(validate)

  def floating(
    self,
    err: Pieces,
    min: Optional[int] = None,
    max: Optional[int] = None,
    minErr: Optional[Pieces] = None,
    maxErr: Optional[Pieces] = None,
  ) -> Validator:

    def validate(o: ValidatorObject):
      o.data = o.message.text
      if not re.match(r'^-?\d+(\.\d+)?$', o.data):
        return self._error(o, err)
      o.data = float(o.data)

      if min is not None and o.data < min:
        return self._error(o, minErr or err)
      elif max is not None and o.data > max:
        return self._error(o, maxErr or err)
      return o

    return self._handleExceptionWrapper(validate)

  def messageWithText(self, err: Pieces) -> Validator:

    def validate(o: ValidatorObject):
      if (o.message.text is None or len(o.message.text) == 0) \
          and (o.message.caption is None or len(o.message.caption) == 0):
        o.success = False
        o.error = err
      else:
        if o.message.text is None:
          o.message.text = o.message.caption
        if o.message.entities is None:
          o.message.entities = o.message.caption_entities
        o.data = o.message
      return o

    return self._handleExceptionWrapper(validate)

  def _handleExceptionWrapper(self, validateFunction: Callable) -> Validator:

    def validate(o: ValidatorObject):
      try:
        o = validateFunction(o)
      except Exception as e:
        o.success = False
        o.error = P(
          'Something went wrong while checking the value. Error text: ',
          emoji='fail',
        ) + P(str(e), types='code')
        self.tglog.error(e, exc_info=e)
      return o

    return FunctionValidator(validate)

  def _error(self, o: ValidatorObject, err: Pieces) -> ValidatorObject:
    o.success = False
    o.error = err
    return o
