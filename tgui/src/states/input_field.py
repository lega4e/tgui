import random

from typing import Optional, List, Union, Callable, Any

from lega4e_library.algorithm.callback_wrapper import CallbackWrapper
from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, KeyboardButton, ReplyKeyboardMarkup

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import P, Pieces
from tgui.src.domain.validators import ValidatorObject, Validator
from tgui.src.managers.callback_query_manager import CallbackQueryIdentifier, \
  CallbackSourceType, CallbackQueryAnswer, CallbackQueryManager
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.states.branch import TgBranchState, BranchButton, BranchMessage
from tgui.src.states.tg_state import KeyboardAction, TgMessage


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
  ON_FIELD_ENTERED_EVENT = 'ON_FIELD_ENTERED_EVENT'

  async def _handleMessage(self, m: Message):
    if self._ignoreMessageInput:
      return False

    if self._validator is None:
      await self._onFieldEntered(m)
      return True

    answer = await self._validator.validate(ValidatorObject(message=m))

    if not answer.success:
      await self.send(text=answer.error)
    else:
      await self._onFieldEntered(answer.data)

    return True

  async def sendGreeting(self):
    if self._prepareMessages is None:
      return

    for m in self._prepareMessages:
      await self.send(m)

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
    self._prepareMessages: Optional[List[Union[Pieces, TgMessage]]] = None
    self._checkGreeting: Optional[Union[Pieces, TgMessage]] = None
    self._checkMessageGetter: Optional[Callable[[Any], TgMessage]] = None
    self._checkSeparateMessage: Optional[Union[Pieces, TgMessage]] = None
    self._checkYesTitle: str = 'Yes'
    self._checkNoTitle: str = 'No'
    self._inputFieldGreeting: Optional[Union[Pieces, TgMessage]] = None

  def configureInputField(
    self,
    greeting: Optional[Union[Pieces, TgMessage]] = None,
    prepareMessages: Optional[List[TgMessage]] = None,
    checkGreeting: Optional[Pieces] = None,
    checkMessageGetter: Optional[Callable[[Any], TgMessage]] = None,
    checkSeparateMessage: Optional[TgMessage] = None,
    checkYesTitle: Optional[str] = None,
    checkNoTitle: Optional[str] = None,
  ):
    if greeting is not None:
      self._inputFieldGreeting = greeting

    if prepareMessages is not None:
      self._prepareMessages = prepareMessages

    if checkGreeting is not None:
      self._checkGreeting = checkGreeting

    if checkMessageGetter is not None:
      self._checkMessageGetter = checkMessageGetter

    if checkSeparateMessage is not None:
      self._checkSeparateMessage = checkSeparateMessage

    if checkYesTitle is not None:
      self._checkYesTitle = checkYesTitle

    if checkNoTitle is not None:
      self._checkNoTitle = checkNoTitle

    return self

  async def buildMessage(self) -> BranchMessage:
    if self._inputFieldGreeting is None \
        or isinstance(self._inputFieldGreeting, Pieces):
      return BranchMessage(self._inputFieldGreeting or self._greeting or
                           P('Message undefined'))
    return BranchMessage(
      pieces=self._inputFieldGreeting.pieces,
      media=self._inputFieldGreeting.media[0].media
      if len(self._inputFieldGreeting.media) > 0 else None,
      mediaType=self._inputFieldGreeting.media[0].type
      if len(self._inputFieldGreeting.media) > 0 else None,
    )

  async def buildButtons(self):
    if len(self._ifButtons) == 0 or len(self._ifButtons[0]) == 0:
      if self._inputFieldGreeting is not None \
          and isinstance(self._inputFieldGreeting, TgMessage):
        return self._inputFieldGreeting.keyboardAction or []
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
    if self._checkMessageGetter is None:
      self.notify(event=TgInputField.ON_FIELD_ENTERED_EVENT, value=value)
      await self.executableStateOnCompleted(value)
      return

    if self._checkGreeting is not None:
      await self.send(self._checkGreeting)

    m: TgMessage = await maybeAwait(self._checkMessageGetter(value))
    field = TgInputField(
      tg=self.tg,
      destination=self.destination,
      callbackManager=self._callbackManager,
      ignoreMessageInput=True,
      buttons=[
        [
          InputFieldButton(self._checkNoTitle, False),
          InputFieldButton(self._checkYesTitle, True),
        ],
      ],
    ).configureInputField(self._checkSeparateMessage or m)

    if self._checkSeparateMessage is not None:
      await self.send(m)

    try:
      if await self.calc(field):
        self.notify(event=TgInputField.ON_FIELD_ENTERED_EVENT, value=value)
        await self.executableStateOnCompleted(value)
      else:
        self.setMessage(None)
        await self.translateMessage()
    except CompleterCanceledException:
      pass
