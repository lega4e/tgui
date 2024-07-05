from abc import abstractmethod
from typing import Optional, Callable, Union, Any

from telebot.types import Message

from tgui.src.states.tg_state import TgState

MessageGetter = Optional[Callable[[], Optional[Message]]]
MessageSetter = Optional[Callable[[Message], None]]


class TgTranslateToMessageMixin:

  def __init__(self):
    self._rootMessage = None

    def getter() -> Message:
      return self._rootMessage

    def setter(m: Message):
      self._rootMessage = m

    self.getMessage = getter
    self.setMessage = setter

  def configureTranslateToMessageMixin(
    self,
    messageToTranslateGetter: Optional[Union[MessageGetter, Any]] = None,
    messageToTranslateSetter: Optional[MessageSetter] = None,
  ):
    if isinstance(messageToTranslateGetter, TgTranslateToMessageMixin):
      return self.configureTranslateToMessageMixin(
        messageToTranslateGetter.getMessage,
        messageToTranslateGetter.setMessage,
      )
    if messageToTranslateGetter is None or messageToTranslateSetter is None:
      return self
    self.getMessage = messageToTranslateGetter
    self.setMessage = messageToTranslateSetter
    return self

  def getTranslateToMessageId(self) -> Optional[int]:
    message = self.getMessage()
    return message.message_id if message is not None else None

  async def setTgTranslationState(self, state: TgState):
    get, set = self.getMessage, self.setMessage
    if not isinstance(self, TgState):
      raise ValueError('self must be TgState')

    if not isinstance(state, TgTranslateToMessageMixin):
      raise ValueError('state must be TgTranslateToMessageMixin')

    await self.setTgState(state.configureTranslateToMessageMixin(get, set))

  @abstractmethod
  async def translateMessage(self):
    pass
