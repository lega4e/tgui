import re
from datetime import datetime, timedelta
from logging import Logger
from typing import Callable, Optional, Tuple

from lega4e_library.algorithm.algorithm import rdc
from lega4e_library.datetime.utils import datetime_copy_with
from telebot.async_telebot import AsyncTeleBot

from tgui.src.constructor.models.validator_types import ValidatorDescription, \
  ValidatorType
from tgui.src.domain.emoji import Emoji
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
    self._emailRegex = re.compile(
      r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

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
    elif validator.type == ValidatorType.EMAIL:
      return self.email(errorMessage)
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

  def email(self, err: Pieces) -> Validator:

    def validate(o: ValidatorObject):
      if o.message.text is None or len(o.message.text) == 0:
        return self._error(o, err)

      if not re.match(self._emailRegex, o.message.text):
        return self._error(o, err)

      o.data = o.message.text
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

  def messageUrl(self) -> Validator:  # TgDestination

    def getError():
      title = P('Ссылка на сообщение должна иметь вид:', Emoji.WARNING)
      lines = [
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/channel_or_group_login/5',
          types='code',
        ) + P(' — пост/сообщение в открытом канале/чате или'),
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/fasad_zemlyanki/27910/85066',
          types='code',
        ) + P(' — сообщение в открытом чате с топиками'),
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/c/2128168470/1357',
          types='code',
        ) + P(' — пост/сообщение в закрытом канале/чате или'),
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/c/1620091980/21703/21968',
          types='code',
        ) + P(' — сообщение в закрытом чате с топиками')
      ]
      return title + '\n\n' + rdc(lambda a, b: a + '\n' + b, lines)

    def validate(o: ValidatorObject) -> ValidatorObject:
      # https://t.me/c/2139685032/4 — пост в закрытом канале
      # https://t.me/c/2128168470/1357 — сообщение в закрытом чате
      # https://t.me/c/1620091980/21703/21968 — сообщение в priv чате с топиками
      m = re.match(
        r'^(https?://)?t\.me/c/(\d+)/(\d+)/?(\d+)?$',
        o.message.text,
      )
      if m is not None:
        o.data = TgDestination(
          chatId=-int('100' + m.group(2)),
          translateToMessageId= \
            int(m.group(4) if m.group(4) is not None else m.group(3)),
        )
        return o

      # https://t.me/kommuna_zemlyanka/553 — пост в канале
      # https://t.me/vypugaetededa/17624 — сообщение в чате
      # https://t.me/fasad_zemlyanki/27910/85066 — сообщение в чате с топиками
      m = re.match(r'^(https?://)?t\.me/(\w+)/(\d+)/?(\d+)?$', o.message.text)
      if m is not None:
        o.data = TgDestination(
          chatId='@' + m.group(2),
          translateToMessageId= \
            int(m.group(4) if m.group(4) is not None else m.group(3)),
          chatLogin=m.group(2),
        )
        return o

      return self._error(o, getError())

    return self._handleExceptionWrapper(validate)

  def destinationUrl(self) -> Validator:  # TgDestination

    def getError():
      title = P('Ссылка на чат/канал должна иметь вид:', emoji=Emoji.WARNING)
      lines = [
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/channel_or_group_login',
          types='code',
        ) + P(' — открытый канал/чат или'),
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/fasad_zemlyanki/27910',
          types='code',
        ) + P(' — открытый канал/чат с топиками'),
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/c/2128168470',
          types='code',
        ) + P(' — закрытый канал/чат'),
        P(f'{Emoji.POINT_RIGHT} ') + P(
          'https://t.me/c/1620091980/21703',
          types='code',
        ) + P(' — закрытый чат с топиками')
      ]
      return title + '\n\n' + rdc(lambda a, b: a + '\n' + b, lines)

    def validate(o: ValidatorObject) -> ValidatorObject:  # TgDestination
      # https://t.me/c/2139685032 — закрытый канал/чат
      # https://t.me/c/2128168470/1357 — закрытый чат с топиками
      m = re.match(r'^(https?://)?t\.me/c/(\d+)/?(\d+)?$', o.message.text)
      if m is not None:
        o.data = TgDestination(
          chatId=-int('100' + m.group(2)),
          replyToMessageId=int(m.group(3)) if m.group(3) is not None else None,
        )
        return o

      # https://t.me/kommuna_zemlyanka — открытый канал
      # https://t.me/vypugaetededa — открытый чат
      # https://t.me/fasad_zemlyanki/27182 — открытый чат с топиками
      m = re.match(r'^(https?://)?t\.me/(\w+)/?(\d+)?$', o.message.text)
      if m is not None:
        o.data = TgDestination(
          chatId='@' + m.group(2),
          replyToMessageId=int(m.group(3)) if m.group(3) is not None else None,
          chatLogin=m.group(2),
        )
        return o

      # @vypugaetededa — открытый чат
      m = re.match(r'^@?(\w+)/?(\d+)?$', o.message.text)
      if m is not None:
        o.data = TgDestination(
          chatId='@' + m.group(1),
          replyToMessageId=int(m.group(2)) if m.group(2) is not None else None,
          chatLogin=m.group(1),
        )
        return o

      return self._error(o, getError())

    return self._handleExceptionWrapper(validate)

  def datetime(self, isFuture: bool = False) -> Validator:  # datetime

    def validate(o: ValidatorObject) -> ValidatorObject:
      timestamp, error = self._parseDatetime(o.message.text)
      if timestamp is not None:
        o.data = correct_datetime(timestamp, isfuture=isFuture)
        return o
      return self._error(o, error)

    return self._handleExceptionWrapper(validate)

  def time(self) -> Validator:  # Tuple[int, int]

    def validate(o: ValidatorObject):
      err = P('Введите время в одном из форматов:\n\n', Emoji.FAIL) \
            + P('12\n', types='code') + P('12:00\n', types='code') \
            + P('12 00\n', types='code')

      if o.message.text is None:
        return self._error(o, err)

      m = re.match(r'^(\d{1,2})$', o.message.text)
      if m is not None:
        hours = int(m.group(1))
        if not (0 <= hours <= 23):
          return self._error(o, err)
        o.data = hours, 0
        return o

      m = re.match(r'^(\d{1,2})[:\s](\d{1,2})$', o.message.text)
      if m is not None:
        hours = int(m.group(1))
        minutes = int(m.group(2))
        if not (0 <= hours <= 23) or not (0 <= minutes <= 59):
          return self._error(o, err)
        o.data = hours, minutes
        return o

      return self._error(o, err)

    return self._handleExceptionWrapper(validate)

  def date(self, isFuture: bool = False):

    def validate(o: ValidatorObject) -> ValidatorObject:
      date, error = self._parseDate(o.message.text)
      if date is not None:
        o.data = correct_date(date, isfuture=isFuture)
        return o
      return self._error(o, error)

    return self._handleExceptionWrapper(validate)

  def url(self):

    def validate(o: ValidatorObject) -> ValidatorObject:
      m = re.match(r'^(https?://)?\w+\.\w+\S*$', o.message.text)
      if m is not None:
        o.data = m.group(0)
        return o

      m = re.match(r'^@([a-zA-Z]\w{2,})$', o.message.text)
      if m is not None:
        o.data = 't.me/' + m.group(1)
        return o

      error = P('Что-то это не похоже на корректную ссылку', emoji=Emoji.FAIL)
      return self._error(o, error)

    return self._handleExceptionWrapper(validate)

  def photoId(self, err: Pieces):

    def validate(o: ValidatorObject) -> ValidatorObject:
      if o.message.content_type != 'photo':
        return self._error(o, err)

      o.data = o.message.photo[-1].file_id
      return o

    return self._handleExceptionWrapper(validate)

  # SERVICE
  def _parseDatetime(
    self,
    text: str,
  ) -> Tuple[Optional[datetime], Optional[Pieces]]:
    formats = [
      '%d.%m %H:%M',
      '%d.%m %H %M',
      '%d %B %H:%M',
      '%d %B %H %M',
      '%d %B %Y %H:%M',
      '%d %B %Y %H:%M',
    ]
    for fmt in formats:
      try:
        return datetime.strptime(text, fmt), None
      except:
        continue

    title = P(
      'Не получилось считать дату и время. '
      'Введи время в одном из следующих форматов:',
      emoji=Emoji.FAIL)
    fmts = [
      P(Emoji.POINT_RIGHT + ' ') + P(datetime.now().strftime(fmt), types='code')
      for fmt in formats
    ]
    pieces = title + '\n\n' + rdc(lambda a, b: a + '\n' + b, fmts)
    return None, pieces

  def _parseDate(
    self,
    text: str,
  ) -> Tuple[Optional[datetime], Optional[Pieces]]:
    formats = [
      '%d.%m',
      '%d %B',
      '%d %B %Y',
    ]
    for fmt in formats:
      try:
        return datetime.strptime(text, fmt), None
      except:
        continue

    title = P(
      'Не получилось считать дату. '
      'Введи её в одном из следующих форматов:',
      emoji=Emoji.FAIL)
    fmts = [
      P(Emoji.POINT_RIGHT + ' ') + P(datetime.now().strftime(fmt), types='code')
      for fmt in formats
    ]
    pieces = title + '\n\n' + rdc(lambda a, b: a + '\n' + b, fmts)
    return None, pieces

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


def correct_datetime(
    value: datetime,
    isfuture: bool = True,
    delta: timedelta = timedelta(weeks=1),
) -> datetime:
  value = datetime_copy_with(value, datetime.now().year)
  if isfuture and value < datetime.now() - delta:
    return datetime_copy_with(value, value.year + 1)
  else:
    return value


def correct_date(
    value: datetime,
    isfuture: bool = True,
    delta: timedelta = timedelta(weeks=1),
) -> datetime:
  value = datetime_copy_with(value, datetime.now().year)
  if isfuture and value < datetime.now() - delta:
    return datetime_copy_with(value, value.year + 1)
  else:
    return value
