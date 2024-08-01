# pylint: disable=W0212
import asyncio
import enum
from random import random
from typing import Any, Optional, List, Callable, Tuple

from attr import define, field
from attr.validators import instance_of
from lega4e_library import Notifier
from lega4e_library.asyncio.async_completer import CompleterCanceledException, \
  AsyncCompleter
from lega4e_library.asyncio.utils import maybeAwait
from lega4e_library.attrs.jsonkin import jsonkin
from telebot.async_telebot import AsyncTeleBot
from telebot.types import JsonSerializable, Message, ReplyKeyboardMarkup, \
  CallbackQuery, ReplyKeyboardRemove

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import Pieces
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.utils.send_message import send_message


@enum.unique
class KeyboardActionType(enum.Enum):
  CLEAR = 'CLEAR'
  RESET = 'RESET'
  HOLD = 'HOLD'
  SET = 'SET'


@jsonkin
@define
class KeyboardAction:
  type: KeyboardActionType = field(validator=instance_of(KeyboardActionType))
  markup: Optional[JsonSerializable] = field(
    validator=instance_of(Optional[JsonSerializable]),
    default=None,
  )

  @staticmethod
  def clear():
    return KeyboardAction(type=KeyboardActionType.CLEAR)

  @staticmethod
  def reset():
    return KeyboardAction(type=KeyboardActionType.RESET)

  @staticmethod
  def hold():
    return KeyboardAction(type=KeyboardActionType.HOLD)

  @staticmethod
  def set(markup: JsonSerializable):
    return KeyboardAction(type=KeyboardActionType.SET, markup=markup)


class TgState(Notifier):
  """
  Представляет собой состояние, в котором находится телеграм бот. Позволяет:
  - установить события на вход и выход из состояния;
  - установить обработчики сообщений и запросов (перегрузите соответствующие
    функции)
  - устанавливать подсостояния, которым будет делегировать обработка сообщений
    и запросов
  """
  ON_START_STATE_EVENT = 'ON_START_STATE_EVENT'
  ON_ENTER_STATE_EVENT = 'ON_ENTER_STATE_EVENT'
  ON_DETACH_STATE_EVENT = 'ON_DETACH_STATE_EVENT'
  ON_ATTACH_STATE_EVENT = 'ON_ATTACH_STATE_EVENT'
  ON_FINISH_STATE_EVENT = 'ON_FINISH_STATE_EVENT'
  ON_ENTER_SUBSTATE_EVENT = 'ON_ENTER_SUBSTATE_EVENT'
  ON_FINISH_SUBSTATE_EVENT = 'ON_FINISH_SUBSTATE_EVENT'
  ON_GREETING_EVENT = 'ON_GREETING_EVENT'
  ON_RETURN_FROM_POPPED_STATE_EVENT = 'ON_RETURN_FROM_POPPED_STATE_EVENT'
  ON_HANDLE_MESSAGE = 'ON_HANDLE_MESSAGE'
  ON_HANDLE_COMMAND = 'ON_HANDLE_COMMAND'
  ON_HANDLE_CALLBACK_QUERY = 'ON_HANDLE_CALLBACK_QUERY'

  def __init__(self, destination: TgDestination, tg: AsyncTeleBot):
    Notifier.__init__(self)

    self.tg = tg
    self.destination = destination
    self.catchedMessages: List[Message] = []
    self._greeting = None
    self._silent = False
    self._substate = None
    self._parentState = None
    self._detachedStates: List[TgState] = []
    self._completerCancelToken: Optional[str] = None
    self._collectMessage = False
    self._tgStateData = dict()

  def configureTgState(
    self,
    greeting: Optional[Pieces] = None,
    silent: Optional[bool] = False,
    collectMessage=False,
  ):
    self._greeting = greeting
    self._silent = silent
    self._collectMessage = collectMessage
    return self

  def getGreeting(self) -> Optional[Pieces]:
    return self._greeting

  def getKeyboardMarkup(self) -> Optional[ReplyKeyboardMarkup]:
    """
    Можно перегрузить, если у данного состояния есть своя клавиатура
    """
    return self._parentState.getKeyboardMarkup() \
      if self._parentState is not None else None

  async def calc(
    self,
    state: TgExecutableMixin,
    finishSubstate: bool = True,
  ):
    if self._completerCancelToken is not None:
      self.cancelCompleter()
    self._completerCancelToken = str(self.destination.chatId) + str(random())
    from tgui.src.utils.calculate_tg_state import calculate_executable_state
    return await calculate_executable_state(
      parent=self,
      state=state,
      finishSubstate=finishSubstate,
      cancelToken=self._completerCancelToken,
    )

  async def calcWithDeletion(
    self,
    fields: List[Tuple[str, Any]],  # TgInputField
    onSuccess: Callable,
    remove: List[Message] = None,
  ):
    from tgui.src.states.input_field import TgInputField
    remove = remove or []
    try:
      self.catchedMessages = remove
      values = {}
      for name, field in fields:
        field: TgInputField
        field.configureTgState(
          greeting=field._greeting,
          silent=field._silent,
          collectMessage=True,
        )
        values[name] = await self.calc(field)
        self.catchedMessages.extend(field.catchedMessages)
      await maybeAwait(onSuccess(**values))

    except CompleterCanceledException:
      pass

    finally:
      [self.scheduleMessageDeletion(m, 0.0) for m in set(self.catchedMessages)]
      self.catchedMessages = []

  def scheduleMessageDeletion(
    self,
    m: Optional[Message],
    duration: float = 3.0,
  ):
    if m is None:
      return

    async def removeMessage():
      await asyncio.sleep(duration)
      await self.delete(m)

    asyncio.create_task(removeMessage())

  def cancelCompleter(self):
    AsyncCompleter.cancelByToken(self._completerCancelToken)
    self._completerCancelToken = None

  async def start(self, silent: bool = False):
    """
    Должно быть вызвано при вхождении в состояние
    """
    if not self._silent and not silent:
      await self.sendGreeting()
      await self._onEnterState()
      self.notify(event=self.ON_ENTER_STATE_EVENT)
    self.notify(event=self.ON_START_STATE_EVENT)

  async def greet(self):
    markup = self.getKeyboardMarkup()
    await self.send(
      self.getGreeting(),
      keyboardAction=KeyboardAction.set(markup) if markup is not None else None,
    )

  async def sendGreeting(self):
    if self._greeting is None:
      return
    await self.greet()
    self.notify(event=TgState.ON_GREETING_EVENT)

  async def finish(self, status: Any = None):
    """
    Должно быть вызвано после выхода из состояния
    """
    self._tgStateData['preparedToFinish'] = True
    await self._onFinishBeforeFinishSubstate(status)
    await self.finishSubstate(status)
    await self._onFinish(status)
    self.cancelCompleter()
    self.notify(event=TgState.ON_FINISH_STATE_EVENT, status=status)

  async def finishSubstate(
    self,
    status: Any = None,
    finishDetached: bool = True,
  ):
    """
    Вызывается, когда завершается подстотояние
    """
    if finishDetached:
      for state in self._detachedStates:
        await state.finish(status)
      self._detachedStates = []

    if self._substate is not None:
      await self._substate.finish(status)
      self._resetTgState()
      self.notify(event=TgState.ON_FINISH_SUBSTATE_EVENT)

  async def pop(self, status: Any = None):
    """
    Вызовите, чтобы вернуться к родительскому состоянию
    """
    if self._parentState is not None:
      self._parentState.notify(event=TgState.ON_RETURN_FROM_POPPED_STATE_EVENT)
      parentState: TgState = self._parentState
      await parentState.finishSubstate(status)
      await parentState._onReturnFromPoppedState(status, self)

  async def popBack(self, count: int = 1, status: Any = None):
    if self._substate is None:
      state = self
      for _ in range(count - 1):
        if state._parentState is None:
          break
        state = state._parentState
      await state.pop(status)
    else:
      await self._substate.popBack(count, status)

  async def setTgState(
    self,
    state,
    silent: bool = False,
    status: Any = None,
    finishDeatched: bool = False,
  ):
    """
    Установка подсостояния

    :param finishDeatched: Завершать ли отсоединённые состояния.
    :param state: Подстотояние (extends TgState).
    :param silent: Вызывать ли start у подсостояния.
    :param status: Статус завершения подсостояния.
    """
    await self.finishSubstate(status, finishDetached=finishDeatched)
    self._substate = state
    self._substate._parentState = self
    await state.start(silent=silent)
    self.notify(event=TgState.ON_ENTER_SUBSTATE_EVENT)

  async def replaceTgState(
    self,
    state,
    silent: bool = False,
    status: Any = None,
  ):
    """
    Заменяет текущее подсостояние на указанное у родителя

    :param state: Состояние, на которое нужно заменить текущее.
    :param silent: Вызывать ли start у устанавливаемого подсостояния.
    :param status: Статус завершения текущего состояния.
    :return:
    """
    if self._parentState is None:
      raise Exception("Can't replace tg state without parent")

    await self._parentState.setTgState(state, silent=silent, status=status)

  def _resetTgState(self):
    """
    Очищает подсостояние
    """
    if self._substate is not None:
      self._substate._parentState = None
      self._substate = None

  async def handleMessage(self, m: Message) -> bool:
    """
    Обрабатывает сообщение (можно перегрузить метод _handleMessageBefore в
    дочернем классе, чтобы перехватить обработку; если этот метод возвратет
    True, то на этом обработка сообщения завершится). Если есть подсостояние,
    то в первую очередь происходит попытка обработать сообщение с помощью
    подсостояния.

    :param m: Сообщение, которое нужно обработать
    :return: было ли обработано состояние
    """
    if self._collectMessage:
      self.catchedMessages.append(m)
    if (await self._handleMessageBefore(m) or
        (self._substate is not None and await self._substate.handleMessage(m))):
      self.notify(event=TgState.ON_HANDLE_MESSAGE, message=m)
      return True
    result = await self._handleMessage(m)
    self.notify(event=TgState.ON_HANDLE_MESSAGE, message=m)
    return result

  async def handleCommand(self, m: Message) -> bool:
    """
    Обрабатывает команду (можно перегрузить метод _handleCommandBefore в
    дочернем классе, чтобы перехватить обработку; если этот метод возвратет
    True, то на этом обработка команды завершится). Если есть подсостояние,
    то в первую очередь происходит попытка обработать сообщение с помощью
    подсостояния.

    :param m: Команда, которую нужно обработать
    :return: была ли обработана команда
    """
    if (await self._handleCommandBefore(m) or
        (self._substate is not None and await self._substate.handleCommand(m))):
      self.notify(event=TgState.ON_HANDLE_COMMAND, message=m)
      return True
    result = await self._handleCommand(m)
    self.notify(event=TgState.ON_HANDLE_COMMAND, message=m)
    return result

  async def handleCallbackQuery(self, q: CallbackQuery) -> bool:
    """
    Обрабатывает CallbackQuery (если есть подсостояние, то сначала пытаемся
    обработать подсостоянием)

    :param q: запрос, который нужно обработать
    :return: был ли обработан запрос
    """
    if (self._substate is not None and
        await self._substate.handleCallbackQuery(q)):
      self.notify(event=TgState.ON_HANDLE_CALLBACK_QUERY, query=q)
      return True
    result = await self._handleCallbackQuery(q)
    self.notify(event=TgState.ON_HANDLE_CALLBACK_QUERY, query=q)
    return result

  def detachSubstate(self) -> Any:
    if self._substate is not None:
      substate = self._substate
      self._detachedStates.append(self._substate)
      self._resetTgState()
      substate.notify(event=TgState.ON_DETACH_STATE_EVENT, parent=self)
      return substate
    return None

  def attachLastSubstate(self) -> bool:
    if len(self._detachedStates) == 0:
      return False

    self.attachSubstate(self._detachedStates.pop(-1))
    return True

  def attachSubstate(self, substate: Any) -> bool:
    if substate not in self._detachedStates:
      return False

    self._detachedStates.remove(substate)
    self._substate = substate
    self._substate._parentState = self
    substate.notify(event=TgState.ON_ATTACH_STATE_EVENT)
    return True

  async def _onEnterState(self):
    """
    Вызывается при старте состояния (если silent = False)
    """

  async def _onFinishBeforeFinishSubstate(self, status: Any = None):
    """
    Вызывается при завершении состояния
    """

  async def _onFinish(self, status: Any = None):
    """
    Вызывается при завершении состояния
    """

  async def _onReturnFromPoppedState(self, status: Any = None, state=None):
    """
    Вызывается, когда у подсостянию вызывается pop
    """

  async def _handleCommandBefore(self, _: Message) -> bool:
    """
    Обработка команды перед обработкой подсостоянием

    :param _: сообщение (команда), которое нужно обработать
    :return: было ли обработана команда (следует ли остановить обработку?)
    """
    return False

  async def _handleMessageBefore(self, _: Message) -> bool:
    """
    Обработка сообщения перед обработкой подсостоянием

    :param _: сообщение, которое нужно обработать
    :return: было ли обработано сообщение (следует ли остановить обработку?)
    """
    return False

  async def _handleMessage(self, _: Message) -> bool:
    """
    Обработка сообщения (уже после подсостояния)

    :param _: сообщение, которое нужно обработать
    :return: было ли обработано сообщение
    """
    return False

  async def _handleCommand(self, _: Message) -> bool:
    """
    Обработка команды (уже после подсостояния)

    :param _: сообщение (команда), которое нужно обработать
    :return: была ли обработана команда
    """
    return False

  async def _handleCallbackQuery(self, _: CallbackQuery) -> bool:
    """
    Обработа запроса callbackQuery

    :param _: запрос, который нужно обработать
    :return: был ли обработан запрос
    """
    return False

  # SERVICE FUNCTION
  async def send(
    self,
    text,
    translateToMessageId: Optional[int] = None,
    keyboardAction: Optional[KeyboardAction] = None,
    collectMessage: bool = True,
    **kwargs,
  ) -> List[Message]:
    markup = None
    if keyboardAction is not None:
      if keyboardAction.type == KeyboardActionType.CLEAR:
        markup = ReplyKeyboardRemove()
      elif keyboardAction.type == KeyboardActionType.HOLD:
        markup = None
      elif keyboardAction.type == KeyboardActionType.RESET:
        markup = self.getKeyboardMarkup()
      elif keyboardAction.type == KeyboardActionType.SET:
        markup = keyboardAction.markup
      else:
        raise Exception('Unknown KeyboardActionType')

    value = await send_message(
      tg=self.tg,
      chat=self.destination.copyWith(translateToMessageId=translateToMessageId),
      text=text,
      replyMarkup=markup,
      **kwargs,
    )
    if self._collectMessage and collectMessage:
      self.catchedMessages.extend(value)
    return value

  async def translate(
    self,
    text: Pieces,
    m: Optional[Message] = None,
    keyboardAction: Optional[KeyboardAction] = None,
    **kwargs,
  ) -> Message:
    return (await self.send(
      text,
      translateToMessageId=m.message_id if m is not None else None,
      keyboardAction=keyboardAction,
      **kwargs,
    ))[0]

  async def sendTmp(self, *args, duration: float = 3.0, **kwargs):
    messages = await self.send(*args, collectMessage=False, **kwargs)
    for m in messages:
      self.scheduleMessageDeletion(m, duration)
    return messages

  async def delete(self, m: Message):
    await self.tg.delete_message(m.chat.id, m.message_id)

  def findSubstateByType(self, type) -> Optional[Any]:  # TgState
    substate: TgState = self._substate
    while substate is not None:
      if isinstance(substate, type):
        return substate
      substate = substate._substate
    return None

  def printStateTrace(self, forward: bool = False):
    if forward:
      print(type(self), self._tgStateData)
      if self._substate is not None:
        self._substate.printStateTrace(forward=True)
      else:
        print('END')
    else:
      if self._parentState is None:
        print('BEGIN')
        self.printStateTrace(forward=True)
      else:
        self._parentState.printStateTrace(forward=False)

  def _setDataToParentsAndMyself(self, **kwargs):
    for key, value in kwargs.items():
      self._tgStateData[key] = value
    self._parentState: TgState
    if self._parentState is not None:
      self._parentState._setDataToParentsAndMyself(**kwargs)

  def _setDataToParents(self, **kwargs):
    self._parentState: TgState
    if self._parentState is not None:
      self._parentState._setDataToParentsAndMyself(**kwargs)

  def _setDataToChildrensAndMyself(self, **kwargs):
    for key, value in kwargs.items():
      self._tgStateData[key] = value
    self._substate: TgState
    if self._substate is not None:
      self._substate._setDataToChildrensAndMyself(**kwargs)

  def _setDataToChildrens(self, **kwargs):
    if self._substate is not None:
      self._substate: TgState
      self._substate._setDataToChildrensAndMyself(**kwargs)

  @staticmethod
  def buildKeyboard(buttons: List[List[str]]) -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for row in buttons:
      markup.add(*row)
    return markup
