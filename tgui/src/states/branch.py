import random
from dataclasses import dataclass
from typing import Callable, Optional, Any, List, Union, BinaryIO

from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, \
  InlineKeyboardButton

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import Pieces
from tgui.src.managers.callback_query_manager import CallbackQueryIdentifier, \
  CallbackSourceType, CallbackQueryAnswer, CallbackQueryManager
from tgui.src.mixin.tg_message_translate_mixin import TgTranslateToMessageMixin
from tgui.src.states.tg_state import TgState, KeyboardAction
from tgui.src.utils.send_message import TgMediaType


@dataclass
class BranchButtonAction:
  action: Optional[Callable] = None
  state: Optional[TgState] = None
  pop: bool = False
  update: bool = False


@dataclass
class BranchMessage:
  pieces: Pieces
  media: Optional[Union[List[str], BinaryIO, bytes]] = None
  mediaType: Optional[Union[str, TgMediaType]] = None


class BranchButton:
  """
  Кнопка, по нажатию на которую устанавливается подсостояние
  """

  def __init__(
    self,
    title: str,
    action: Optional[Union[
      TgState,
      BranchButtonAction,
      Callable[[], BranchButtonAction],
      Callable[[], TgState],
      Callable,
    ]] = None,
    url: Optional[str] = None,
    answer: Optional[str] = None,
    logMessage: Optional[str] = None,
    showAlert: bool = False,
  ):
    """
    :param title: Строка, которая будет отображатся на кнопке
    
    :param answer: сообщение, которое нарисуется пользователю в инфо-шторке
    
    :param logMessage: сообщение для логгера
    """
    assert (url is None) != (action is None)
    self.title = title
    self.action = action
    self.url = url
    self.answer = answer
    self.logMessage = logMessage
    self.data = str(random.random())
    self.showAlert = showAlert

  def identifier(self, chatId: int) -> CallbackQueryIdentifier:
    return CallbackQueryIdentifier(
      type=CallbackSourceType.CHAT_ID,
      id=chatId,
      data=self.data,
    )

  def callbackAnswer(self, action) -> CallbackQueryAnswer:
    return CallbackQueryAnswer(
      action=action,
      logMessage=self.logMessage or f'Выбрано «{self.title}»',
      answerText=self.answer or f'Выбрано «{self.title}»',
      showAlert=self.showAlert,
    )


BranchKeyboard = Union[KeyboardAction, List[List[BranchButton]]]


class TgBranchState(TgState, TgTranslateToMessageMixin):
  """
  Сообщение в телеграмме, под которым есть кнопки; нажав на любую из кнопок
  будет установлено соответствующее подсостояние; как только это состояние
  завершится, будет снова установлено корневое состояние. Если будет нажата
  другая кнопка до того, как предыдущее подсостояние не завершится, оно будет
  прервано и установлено новое. Вместо установки новых состояний можно
  назначать коллбэки
  """
  ON_TRANSLATE_EVENT = 'ON_TRANSLATE_EVENT'

  async def _onEnterState(self):
    await self.translateMessage()

  async def _onReturnFromPoppedState(self, _: Any = None, __: TgState = None):
    await self.translateMessage()

  async def _onFinish(self, _: Any = None):
    self._parentState: TgState
    self._freeButtons()
    if self._clearButtonsOnFinish:
      await self.translateMessage(buttons=False)
    if self._clearButtonsOnFinishIfLeaf and \
       self._tgStateData.get('isLeaf', True) and \
      (self._parentState is None or
       (self._parentState._tgStateData.get('preparedToFinish', False) and
       self._tgStateData.get('cleanButtons', True))):
      self._setDataToParents(isLeaf=False)
      await self.translateMessage(buttons=False)

  async def translateMessage(self, buttons: bool = True):
    if self._beforeTranslationCallback is not None:
      await maybeAwait(self._beforeTranslationCallback())
    self._freeButtons()
    if buttons:
      self._buttons = await maybeAwait(self._buttonsGetter())
      self._registerButtons()
    message: BranchMessage = await maybeAwait(self._messageGetter())
    self.setMessage(await self.translate(
      text=message.pieces,
      media=message.media,
      mediaType=message.mediaType,
      m=self.getMessage(),
      keyboardAction=self._makeKeyboardAction(),
    ))
    self.notify(event=self.ON_TRANSLATE_EVENT)

  def __init__(
      self,
      tg: AsyncTeleBot,
      destination: TgDestination,
      callbackManager: CallbackQueryManager,
      messageGetter: Callable,  # -> BranchMessage (maybe async)
      buttonsGetter: Callable,  # -> BranchKeyboard (maybe async)
  ):
    TgState.__init__(self, tg=tg, destination=destination)
    TgTranslateToMessageMixin.__init__(self)

    self._buttonsGetter = buttonsGetter
    self._messageGetter = messageGetter
    self._callbackManager = callbackManager
    self._buttons: Union[KeyboardAction, List[List[BranchButton]]] = []
    self._beforeTranslationCallback: Optional[Callable] = None
    self._clearButtonsOnFinish: bool = False
    self._clearButtonsOnFinishIfLeaf: bool = False

  def configureBranchState(
    self,
    beforeTranslationCallback: Optional[Callable] = None,
    clearButtonsOnFinish: Optional[bool] = None,
    clearButtonsOnFinishIfLeaf: Optional[bool] = None,
  ):
    if beforeTranslationCallback is not None:
      self._beforeTranslationCallback = beforeTranslationCallback
    if clearButtonsOnFinish is not None:
      self._clearButtonsOnFinish = clearButtonsOnFinish
    if clearButtonsOnFinishIfLeaf is not None:
      self._clearButtonsOnFinishIfLeaf = clearButtonsOnFinishIfLeaf
    return self

  # SERVICE METHODS
  def _makeKeyboardAction(self) -> Optional[KeyboardAction]:
    if isinstance(self._buttons, KeyboardAction) or self._buttons is None:
      return self._buttons

    markup = InlineKeyboardMarkup()
    for row in self._buttons:
      markup.add(
        *[
          InlineKeyboardButton(
            text=b.title,
            url=b.url,
            callback_data=b.data,
          ) for b in row
        ],
        row_width=len(row),
      )
    return KeyboardAction.set(markup)

  def _freeButtons(self):
    if isinstance(self._buttons, KeyboardAction):
      return

    for row in self._buttons or []:
      for button in row:
        identifier = button.identifier(self.destination.chatId)
        self._callbackManager.remove(identifier)
    self._buttons = []

  async def _executeAction(
    self,
    someAction: Union[Callable, TgState, BranchButtonAction],
  ):
    if someAction is None:
      return

    if isinstance(someAction, TgState):
      await self.setTgState(someAction)
      return

    if isinstance(someAction, Callable):
      await self._executeAction(await maybeAwait(someAction()))
      return

    if isinstance(someAction, BranchButtonAction):
      if someAction.action is not None:
        await maybeAwait(someAction.action())
      elif someAction.state is not None:
        await self.setTgState(someAction.state)
      if someAction.update:
        await self.translateMessage()
      if someAction.pop:
        await self.pop()

  def _registerButtons(self):
    if isinstance(self._buttons, KeyboardAction):
      return

    def makeAction(btn: BranchButton):
      return lambda _: self._executeAction(btn.action)

    for row in self._buttons:
      for button in row:
        self._callbackManager.register(
          button.identifier(self.destination.chatId),
          button.callbackAnswer(makeAction(button)),
        )
