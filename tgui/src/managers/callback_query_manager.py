import enum

from dataclasses import dataclass
from logging import Logger
from typing import Tuple, Dict, Callable, Any, Optional

from telebot.types import CallbackQuery


@enum.unique
class CallbackSourceType(enum.IntEnum):
  USER_ID = 1
  CHAT_ID = 2


@dataclass
class CallbackQueryIdentifier:
  type: CallbackSourceType
  id: int
  data: str


@dataclass
class CallbackQueryAnswer:
  action: Callable[[CallbackQuery], Any]
  logMessage: Optional[str]
  answerText: Optional[str]
  showAlert: Optional[bool] = None
  url: Optional[str] = None


class CallbackQueryManager:

  def __init__(self, logger: Logger):
    self.logger: Logger = logger

    self._userCallbacks: Dict[
      Tuple[int, str],
      CallbackQueryAnswer,
    ] = {}

    self._chatCallbacks: Dict[
      Tuple[int, str],
      CallbackQueryAnswer,
    ] = {}

  def register(
    self,
    identifier: CallbackQueryIdentifier,
    answer: CallbackQueryAnswer,
  ):
    self._dispatchDict(identifier.type)[(
      identifier.id,
      identifier.data,
    )] = answer

  def find(
    self,
    identifier: CallbackQueryIdentifier,
  ) -> Optional[CallbackQueryAnswer]:
    return self._dispatchDict(identifier.type).get((
      identifier.id,
      identifier.data,
    ))

  def remove(
    self,
    identifier: CallbackQueryIdentifier,
  ) -> Optional[CallbackQueryAnswer]:
    try:
      return self._dispatchDict(identifier.type).pop((
        identifier.id,
        identifier.data,
      ))
    except Exception as e:
      self.logger.error(e, exc_info=e)
      return None

  def _dispatchDict(
    self,
    type: CallbackSourceType,
  ) -> Dict[Tuple[int, str], CallbackQueryAnswer]:
    if type == CallbackSourceType.USER_ID:
      return self._userCallbacks
    elif type == CallbackSourceType.CHAT_ID:
      return self._chatCallbacks
    else:
      raise Exception('find: Unknown callback identifier type')
