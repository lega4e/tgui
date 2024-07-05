from random import random
from typing import Any, Dict, List

from lega4e_library.asyncio.async_completer import AsyncCompleter, CompleterCanceledException
from telebot.async_telebot import AsyncTeleBot

from tgui.src.constructor.models.form import FormTgElement, FormTgCondition
from tgui.src.domain import TgDestination
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.states.tg_state import TgState
from tgui.src.utils.calculate_tg_state import calculate_executable_state


class TgFormState(TgState, TgExecutableMixin):

  async def _onFinish(self, status: Any = None):
    AsyncCompleter.cancelByToken(self._cancelToken)

  async def _onEnterState(self):
    try:
      for elem in self._elements:
        if not self._checkConditions(elem.conditions):
          continue
        field = self._fields.get(elem.item)
        self._values[elem.id] = await calculate_executable_state(
          self,
          field,
          cancelToken=self._cancelToken,
        )
      await self.executableStateOnCompleted(self._values)
    except CompleterCanceledException:
      pass

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    fieldsFactory: Any,  # TgInputFieldsFactory,
    elements: List[FormTgElement],
  ):
    from tgui.src.constructor.factories.fields_factory import TgInputFieldsFactory

    TgState.__init__(self, tg=tg, destination=destination)
    TgExecutableMixin.__init__(self)
    self._fields: TgInputFieldsFactory = fieldsFactory
    self._values: Dict[str, Any] = dict()
    self._elements = elements
    self._cancelToken = f'{self.destination.chatId}-{random()}'

  def _checkConditions(self, conditions: List[FormTgCondition]) -> bool:
    for condition in conditions:
      if isinstance(self._values.get(condition.itemId), list):
        if condition.value not in self._values[condition.itemId]:
          return False
      else:
        if condition.value != self._values.get(condition.itemId):
          return False
    return True

  def cancel(self):
    AsyncCompleter.cancelByToken(self._cancelToken)
