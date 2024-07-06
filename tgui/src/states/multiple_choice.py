import random

from typing import Optional, List, Union, Any, Callable

from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import Pieces, P
from tgui.src.domain.emoji import Emoji
from tgui.src.managers.callback_query_manager import CallbackQueryIdentifier, \
  CallbackSourceType, CallbackQueryAnswer, \
  CallbackQueryManager
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.mixin.tg_message_translate_mixin import TgTranslateToMessageMixin
from tgui.src.states.tg_state import TgState, KeyboardAction


class MultipleChoiceButton:
  """
  Одна из кнопок, которую можно нажать вместо ручного ввода значения
  """

  def __init__(
    self,
    titleOn: str,
    titleOff,
    value,
    answer: str = None,
    isOnInitial: bool = False,
    isEndButton: bool = False,
  ):
    """
    :param titleOn: Какой текст будет отображён на кнопке, когда элементы выбран
    :param titleOff: какой текст будет отображён на кнопке, когда элемент не выбран
    :param value: какое значение будет возвращено как "введённое"
    :param answer: что будет отображено в инфо-шторке при нажатии на кнопку
    """
    self.titleOn = titleOn
    self.titleOff = titleOff
    self.value = value
    self.answer = answer
    self.qb = str(random.random())
    self.isOn = isOnInitial
    self.isEndButton = isEndButton

  def identifier(self, chatId: int) -> CallbackQueryIdentifier:
    return CallbackQueryIdentifier(
      type=CallbackSourceType.CHAT_ID,
      id=chatId,
      data=self.qb,
    )

  def callbackAnswer(self, action) -> CallbackQueryAnswer:
    title = self.titleOn if self.isOn else self.titleOff
    return CallbackQueryAnswer(
      action=action,
      logMessage=f'Нажато «{title}»',
      answerText=self.answer or f'Нажато «{title}»',
    )


class TgMultipleChoice(TgState, TgTranslateToMessageMixin, TgExecutableMixin):
  ON_FIELD_ENTERED_EVENT = 'ON_FIELD_ENTERED_EVENT'

  async def _onEnterState(self):
    self._registerButtons()

  async def _onFinish(self, status: Any = None):
    """
    Когда ввод прерван, выводим сообщение о прерванном вводе
    """
    for row in self._buttons or []:
      for button in row:
        identifier = button.identifier(self.destination.chatId)
        self._callbackManager.remove(identifier)
    if status is not None and self._terminateMessage is not None:
      await self.send(text=self._terminateMessage)

  async def sendGreeting(self):
    await self.translateMessage()

  def __init__(
      self,
      tg: AsyncTeleBot,
      destination: TgDestination,
      callbackManager: CallbackQueryManager,
      buttons: List[List[MultipleChoiceButton]],
      terminateMessage: Union[str, Pieces] = None,
      checkChoice: Optional[Callable] = None,  # maybe async -> bool
  ):
    """
    :param tg: Телебот, используется для отправки сообщений
    :param destination: чат, куда посылать приглашения к вводу или сообщение о прерванном вводе
    :param terminateMessage: сообщение, отображающееся, когда ввод прерван
    :param buttons: кнопки, с помощью которых человек может выбирать значение
    """
    TgState.__init__(self, tg=tg, destination=destination)
    TgTranslateToMessageMixin.__init__(self)
    TgExecutableMixin.__init__(self)

    self._callbackManager = callbackManager
    self._buttons = buttons
    self._checkChoice = checkChoice

    self._terminateMessage = terminateMessage
    if isinstance(self._terminateMessage, str):
      self._terminateMessage = P(self._terminateMessage, emoji=Emoji.WARNING)

  async def translateMessage(self):
    self.setMessage((await self.translate(
      text=self.getGreeting(),
      m=self.getMessage(),
      keyboardAction=self._makeKeyboardAction(),
    )))

  # SERVICE METHODS
  def _makeKeyboardAction(self) -> Optional[KeyboardAction]:
    """
    Создаём разметку для кнопок

    :return: Разметка для кнопок (если кнопки указаны)
    """
    markup = InlineKeyboardMarkup()
    for row in self._buttons:
      markup.add(
        *[
          InlineKeyboardButton(
            text=b.titleOn if b.isOn or b.isEndButton else b.titleOff,
            callback_data=b.qb,
          ) for b in row
        ],
        row_width=len(row),
      )
    return KeyboardAction.set(markup)

  def _collectData(self) -> List[Any]:
    data = []
    for row in self._buttons:
      for button in row:
        if button.isOn:
          data.append(button.value)
    return data

  def _registerButtons(self):

    def makeAction(btn: MultipleChoiceButton):

      async def action(_):
        if btn.isEndButton:
          data = self._collectData()
          if (self._checkChoice is None or
              await maybeAwait(self._checkChoice(data, end=True))):
            self.notify(
              event=TgMultipleChoice.ON_FIELD_ENTERED_EVENT,
              value=data,
            )
            await self.executableStateOnCompleted(data)
        else:
          btn.isOn = not btn.isOn
          if (self._checkChoice is not None and not await maybeAwait(
              self._checkChoice(self._collectData(), end=False))):
            btn.isOn = not btn.isOn
          else:
            await self.translateMessage()
        return True

      return action

    for row in self._buttons or []:
      for button in row:
        self._callbackManager.register(
          button.identifier(self.destination.chatId),
          button.callbackAnswer(makeAction(button)),
        )
