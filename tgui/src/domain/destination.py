from typing import Union, Optional

from attr import define, field
from attr.validators import instance_of

from lega4e_library import jsonkin, Jsonkin


@jsonkin
@define
class TgDestination(Jsonkin):
  """
  Представляет собой чат или топик, куда может быть отправлено сообщение; либо
  само сообщение, которое должно быть обновлено
  """

  chatId: Union[int, str] = field(validator= \
    lambda _, __, value: isinstance(value, int) or isinstance(value, str))
  replyToMessageId: Optional[int] = field(
    validator=instance_of(Optional[int]),
    default=None,
  )
  translateToMessageId: Optional[int] = field(
    validator=instance_of(Optional[int]),
    default=None,
  )
  chatLogin: Optional[str] = field(
    validator=instance_of(Optional[str]),
    default=None,
  )

  def url(self):
    if self.chatLogin is not None:
      chat = self.chatLogin
    elif isinstance(self.chatId, str):
      chat = self.chatId[1:]
    elif self.chatId < 0:
      chat = 'c/' + str(self.chatId)[4:]
    else:
      chat = 'c/' + str(self.chatId)

    topic = ''
    if self.replyToMessageId is not None:
      topic = '/' + str(self.replyToMessageId)

    message = ''
    if self.translateToMessageId is not None:
      message = '/' + str(self.translateToMessageId)

    return f't.me/{chat}{topic}{message}'

  def copyWith(
    self,
    chatId: Optional[Union[int, str]] = None,
    replyToMessageId: Optional[int] = None,
    translateToMessageId: Optional[int] = None,
    chatLogin: Optional[str] = None,
  ):
    return TgDestination(
      chatId=chatId if chatId is not None else self.chatId,
      replyToMessageId=replyToMessageId
      if replyToMessageId is not None else self.replyToMessageId,
      translateToMessageId=translateToMessageId
      if translateToMessageId is not None else self.translateToMessageId,
      chatLogin=chatLogin if chatLogin is not None else self.chatLogin,
    )


def proveTgDestination(chat) -> TgDestination:
  if isinstance(chat, TgDestination):
    return chat
  return TgDestination(chatId=chat)


# END
