import random

from typing import Optional, List, Union

from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, \
  KeyboardButton, ReplyKeyboardMarkup

from tgui.src.domain import ValidatorObject, TgDestination, Pieces, Validator, P, Emoji
from tgui.src.managers.callback_query_manager import CallbackQueryIdentifier, CallbackSourceType, CallbackQueryAnswer, \
  CallbackQueryManager
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.mixin.tg_message_translate_mixin import TgTranslateToMessageMixin
from tgui.src.states.tg_state import TgState, KeyboardAction


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


class TgInputField(TgState, TgTranslateToMessageMixin, TgExecutableMixin):
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

  async def _onEnterState(self):
    self._registerButtons()

  async def _onFinish(self, status=None):
    """
    Когда ввод прерван, выводим сообщение о прерванном вводе
    """
    for row in self._buttons or []:
      for button in row:
        identifier = button.identifier(self.destination.chatId)
        self._callbackManager.remove(identifier)
    # self._buttons = []
    # await self.translateMessage()
    if status is not None and self._terminateMessage is not None:
      await self.send(self._terminateMessage)

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

    answer = await maybeAwait(
      self._validator.validate(ValidatorObject(message=m)))

    if not answer.success:
      await self.send(text=answer.error)
    else:
      await self._onFieldEntered(answer.data)

    return True

  async def translateMessage(self):
    self.setMessage((await self.send(
      text=self._greeting,
      translateToMessageId=self.getTranslateToMessageId(),
      keyboardAction=self._makeKeyboardAction(),
    ))[0])

  async def greet(self):
    await self.translateMessage()

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    buttons: List[List[InputFieldButton]] = None,
    terminateMessage: Union[str, Pieces] = None,
    ignoreMessageInput: bool = False,
    validator: Optional[Validator] = None,
  ):
    TgState.__init__(self, tg=tg, destination=destination)
    TgTranslateToMessageMixin.__init__(self)
    TgExecutableMixin.__init__(self)

    self._validator = validator
    self._callbackManager = callbackManager
    self._ignoreMessageInput = ignoreMessageInput
    self._buttons = buttons

    self._terminateMessage = terminateMessage
    if isinstance(self._terminateMessage, str):
      self._terminateMessage = P(self._terminateMessage, emoji=Emoji.WARNING)

  # SERVICE METHODS
  def _makeKeyboardAction(self) -> Optional[KeyboardAction]:
    """
    Создаём разметку для кнопок
    
    :return: Разметка для кнопок (если кнопки указаны)
    """
    if self._buttons is None or len(self._buttons) == 0:
      return None

    if self._buttons[0][0].keyboard is not None:
      markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
      for row in self._buttons:
        markup.add(*[btn.keyboard for btn in row])
      return KeyboardAction.set(markup)

    markup = InlineKeyboardMarkup()
    for row in self._buttons:
      markup.add(
        *[
          InlineKeyboardButton(text=b.title, callback_data=b.data) for b in row
        ],
        row_width=len(row),
      )
    return KeyboardAction.set(markup)

  def _registerButtons(self):

    def makeAction(btn: InputFieldButton):

      async def action(_):
        await self._onFieldEntered(btn.value)

      return action

    for row in self._buttons or []:
      for button in row:
        self._callbackManager.register(
          button.identifier(self.destination.chatId),
          button.callbackAnswer(makeAction(button)),
        )

  async def _onFieldEntered(self, value):
    self.notify(event=TgInputField.ON_FIELD_ENTERED_EVENT, value=value)
    await self.executableStateOnCompleted(value)
