from random import random
from typing import Any, Dict, List, Optional, Callable

from lega4e_library.asyncio.async_completer import AsyncCompleter, \
  CompleterCanceledException
from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot

from tgui.src.constructor.models.form import FormTgElement, FormTgCondition, \
  FormTgConditionCustom, FormTgConditionValue
from tgui.src.domain.destination import TgDestination
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.states.tg_state import TgState
from tgui.src.utils.calculate_tg_state import calculate_executable_state


class TgFormState(TgState, TgExecutableMixin):

  async def _onFinish(self, status: Any = None):
    self.cancel()

  async def _onEnterState(self):
    try:
      for elem in self._elements:
        if not await self._checkConditions(elem.conditions):
          continue
        field = self._fields.get(elem.item)
        self._id = elem.id
        self._values[elem.id] = await calculate_executable_state(
          self,
          field,
          cancelToken=self._cancelToken,
        )
      self._id = None
      await self.executableStateOnCompleted(self._values)
    except CompleterCanceledException:
      pass

  def __init__(
      self,
      tg: AsyncTeleBot,
      destination: TgDestination,
      fieldsFactory: Any,  # TgInputFieldsFactory,
      elements: List[FormTgElement],
      checkCustomCondition: Optional[Callable] = None,  # maybe await
  ):
    from tgui.src.constructor.factories.fields_factory import \
      TgInputFieldsFactory

    TgState.__init__(self, tg=tg, destination=destination)
    TgExecutableMixin.__init__(self)
    self._fields: TgInputFieldsFactory = fieldsFactory
    self._values: Dict[str, Any] = dict()
    self._elements = elements
    self._checkCustomCondition = checkCustomCondition
    self._cancelToken = f'{self.destination.chatId}-{random()}'
    self._id: Optional[str] = None

  def getValues(self) -> Dict[str, Any]:
    return self._values

  def getCurrentElementId(self) -> Optional[str]:
    return self._id

  async def _checkConditions(self, conditions: List[FormTgCondition]) -> bool:
    for condition in conditions:
      if isinstance(condition, FormTgConditionValue):
        if isinstance(self._values.get(condition.itemId), list):
          if condition.value not in self._values[condition.itemId]:
            return False
        else:
          if condition.value != self._values.get(condition.itemId):
            return False
      elif isinstance(condition, FormTgConditionCustom):
        if self._checkCustomCondition is None:
          raise ValueError(
            'checkCustomCondition is None, but custom condition appears')
        if not await maybeAwait(
            self._checkCustomCondition(
              condition,
              self._values,
            )):
          return False
    return True

  def cancel(self):
    AsyncCompleter.cancelByToken(self._cancelToken)
