import random

from typing import Optional, List

from lega4e_library.algorithm.callback_wrapper import CallbackWrapper
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, KeyboardButton, ReplyKeyboardMarkup

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import P
from tgui.src.domain.validators import ValidatorObject, Validator
from tgui.src.managers.callback_query_manager import CallbackQueryIdentifier, \
  CallbackSourceType, CallbackQueryAnswer, CallbackQueryManager
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.states.branch import TgBranchState, BranchButton, BranchMessage
from tgui.src.states.tg_state import KeyboardAction


class InputFieldButton:
  """
  Одна из кнопок, которую можно нажать вместо ручного ввода значения
  """

  def __init__(
    self,
    title: str = None,
    value=None,
    answer: Optional[str] = None,
    keyboard: Optional[KeyboardButton] = None,
  ):
    """
    :param title: Какой текст будет отображён на кнопке
    :param value: какое значение будет возвращено как "введённое"
    :param answer: что будет отображено в инфо-шторке при нажатии на кнопку
    """
    self.title = title
    self.value = value
    self.answer = answer
    self.data = str(random.random())
    self.keyboard = keyboard

  def identifier(self, chatId: int) -> CallbackQueryIdentifier:
    return CallbackQueryIdentifier(
      type=CallbackSourceType.CHAT_ID,
      id=chatId,
      data=self.data,
    )

  def callbackAnswer(self, action) -> CallbackQueryAnswer:
    return CallbackQueryAnswer(
      action=action,
      logMessage=f'Выбрано «{self.title}»',
      answerText=self.answer or f'Выбрано «{self.title}»',
    )


class TgInputField(TgBranchState, TgExecutableMixin):
  """
  Представляет собой класс для запроса единичного значения у пользователя.
  Позволяет:
  - Выводить приглашение к вводу
  - Выводить сообщение, если ввод прерван
  - Проверять корректность ввода данных с помощью класса Validator (и выводить
    сообщение об ошибке, в случае ошибки)
  - Устанавливать кнопки, по нажатию на которые возвращается любые данные в
    качестве введённых
  - Вызывает коллбэк, когда значение успешно введено (или нажата кнопка)
  """
  ON_FIELD_ENTERED_EVENT = 'ON_FIELD_ENTERED_EVENT'

  async def _handleMessage(self, m: Message):
    """
    Обрабатываем сообщение: проверяем, что оно корректно (с помощью валидатора),
    выводим ошибку, если ошибка, и вызываем коллбэк, если корректно

    :param m: сообщение, которое нужно обработать
    """
    if self._ignoreMessageInput:
      return False

    if self._validator is None:
      await self._onFieldEntered(m)

    answer = await self._validator.validate(ValidatorObject(message=m))

    if not answer.success:
      await self.send(text=answer.error)
    else:
      await self._onFieldEntered(answer.data)

    return True

  async def sendGreeting(self):
    pass

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    buttons: List[List[InputFieldButton]] = None,
    ignoreMessageInput: bool = False,
    validator: Optional[Validator] = None,
  ):
    TgBranchState.__init__(
      self,
      tg=tg,
      destination=destination,
      callbackManager=callbackManager,
      messageGetter=self.buildMessage,
      buttonsGetter=self.buildButtons,
    )
    TgExecutableMixin.__init__(self)

    self._validator = validator
    self._ignoreMessageInput = ignoreMessageInput
    self._ifButtons = buttons or []

  async def buildMessage(self) -> BranchMessage:
    return BranchMessage(self._greeting or P('Message undefined'))

  async def buildButtons(self):
    if len(self._ifButtons) == 0 or len(self._ifButtons[0]) == 0:
      return []

    if self._ifButtons[0][0].keyboard is not None:
      markup = ReplyKeyboardMarkup(resize_keyboard=True)
      for row in self._ifButtons:
        markup.add(*[btn.keyboard for btn in row])
      return KeyboardAction.set(markup)

    return [[
      BranchButton(
        btn.title,
        CallbackWrapper(self._onFieldEntered, btn.value),
        answer=btn.answer,
      ) for btn in row
    ] for row in self._ifButtons]

  # SERVICE METHODS
  async def _onFieldEntered(self, value):
    self.notify(event=TgInputField.ON_FIELD_ENTERED_EVENT, value=value)
    await self.executableStateOnCompleted(value)
