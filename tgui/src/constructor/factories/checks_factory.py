from typing import Optional, Callable, Any, List

from telebot.async_telebot import AsyncTeleBot

from tgui.src.constructor.models.validator_types import ValidatorDescription, \
  ValidatorType
from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import Pieces
from tgui.src.utils.send_message import send_message


class TgChecksFactory:

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
  ):
    self.tg = tg
    self.destination = destination

  def get(self, validator: ValidatorDescription):
    if validator.type == ValidatorType.MULTIPLE_CHOICE_COUNT:
      return self.multipleChoiceCheck(
        min=validator.min,
        max=validator.max,
        minErr=validator.minErrorMessage,
        maxErr=validator.maxErrorMessage,
      )
    else:
      raise ValueError(f'Unsupported validator type: {validator.type}')

  def multipleChoiceCheck(
    self,
    min: Optional[int],
    max: Optional[int],
    minErr: Optional[Pieces] = None,
    maxErr: Optional[Pieces] = None,
  ) -> Callable:

    async def check(values: List[Any], end: bool) -> bool:
      if end and min is not None and len(values) < min:
        await send_message(
          tg=self.tg,
          chat=self.destination,
          text=minErr,
        )
        return False
      if max is not None and len(values) > max:
        await send_message(
          tg=self.tg,
          chat=self.destination,
          text=maxErr,
        )
        return False
      return True

    return check
