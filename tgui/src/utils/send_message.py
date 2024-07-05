import asyncio
from copy import copy
from typing import Union, List, Optional

from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaAudio

from tgui.src.domain.destination import TgDestination, proveTgDestination
from tgui.src.domain.piece import Pieces, provePiece
from tgui.src.logging.tg_logger import TgLogger


class TgMediaType:
  PHOTO = 'photo'
  VIDEO = 'video'
  AUDIO = 'audio'


_logger: Optional[TgLogger] = None


def set_send_message_logger(logger: TgLogger = None):
  global _logger
  _logger = logger


async def send_message(
  tg: AsyncTeleBot,
  chat: Union[TgDestination, str, int],
  text: Union[str, Pieces],
  media: Optional[List[str]] = None,
  mediaType: Optional[Union[str, TgMediaType]] = None,
  disableWebPagePreview: bool = True,
  replyMarkup=None,
  answerCallbackQueryId: Optional[int] = None,
  answerCallbackQueryText: Optional[str] = None,
  pinMessage: Optional[bool] = False,
  unpinMessage: Optional[bool] = False,
  disablePinNotification: Optional[bool] = False,
  ignoreMessageNotEdited: Optional[bool] = True,
  resendIfMessageNotFround: Optional[bool] = False,
  log: bool = True,
) -> List[Message]:
  """
  Отправляет или обновляет сообщение в телеграм

  :param resendIfMessageNotFround:
  
  :param ignoreMessageNotEdited: игнорировать ошибку, если сообщение не изменено
  
  :param log: Логировать ли ответ
  
  :param tg: Телебот

  :param chat: куда отправить (или какое сообщение обновить)

  :param text: текст, который отправить

  :param media: фото, видео или аудио, которые нужно отправить

  :param mediaType: тип медиа

  :param disableWebPagePreview: см. Telebot.send_message()

  :param replyMarkup: см. Telebot.send_message()

  :param answerCallbackQueryId: см. Telebot.send_message()

  :param answerCallbackQueryText: см. Telebot.send_message()
  
  :param pinMessage: закреплять ли сообщение
  
  :param unpinMessage: откреплять ли сообщение (только для существующего)
  
  :param disablePinNotification: уведомлять ли о закрепе сообщения
  
  :return: то же, что и Telebot.send_message(), но список
  """
  if media is not None and not isinstance(media, list):
    media = [media]

  chat = proveTgDestination(chat)
  pieces = provePiece(text)
  text, entities = pieces.toMessage()
  media_exists = media is not None and len(media) > 0 and mediaType is not None
  if media_exists and len(text) > 1000 or len(text) > 3900:
    first_len = 1000 if media_exists else 3900
    m = []
    m += await send_message(
      tg,
      chat,
      pieces[0:first_len],
      media=media,
      mediaType=mediaType,
      disableWebPagePreview=disableWebPagePreview,
      replyMarkup=replyMarkup,
      answerCallbackQueryId=answerCallbackQueryId,
      answerCallbackQueryText=answerCallbackQueryText,
      pinMessage=pinMessage,
      unpinMessage=unpinMessage,
      disablePinNotification=disablePinNotification,
    )
    original_chat = copy(chat)
    for i in range(first_len, len(text), 3900):
      if chat.translateToMessageId is not None:
        chat.translateToMessageId = original_chat.translateToMessageId + len(m)
      m += await send_message(
        tg,
        chat,
        pieces[i:i + 3900],
        disableWebPagePreview=disableWebPagePreview,
      )
    return m

  kwargs = {
    'chat_id': chat.chatId,
    'reply_markup': replyMarkup,
  }

  if media_exists:
    kwargs['media'] = _transform_media(media, mediaType, text, entities)
  else:
    kwargs['text'] = text
    kwargs['entities'] = entities
    kwargs['disable_web_page_preview'] = disableWebPagePreview

  if chat.translateToMessageId is not None:  # edit message
    if 'media' in kwargs:
      media = kwargs.pop('media')
      m = [None] * len(media)

      async def fun(index):
        m[index] = await tg.edit_message_media(
          **kwargs,
          media=media[index],
          message_id=chat.translateToMessageId + index,
        )

      def makeLambda(index):
        return lambda: fun(index)

      for i in range(len(media)):
        await _ignore_message_is_not_modified(
          makeLambda(i),
          ignoreMessageNotEdited,
        )
    else:
      m = [None]

      async def fun():
        m[0] = await tg.edit_message_text(
          **kwargs,
          message_id=chat.translateToMessageId,
        )

      if not resendIfMessageNotFround:
        await _ignore_message_is_not_modified(fun, ignoreMessageNotEdited)
      else:
        try:
          await _ignore_message_is_not_modified(fun, ignoreMessageNotEdited)
        except ApiTelegramException as e:
          if 'message to edit not found' in str(e):
            m[0] = await send_message(
              tg,
              TgDestination(
                chatId=chat.chatId,
                replyToMessageId=chat.replyToMessageId,
              ),
              pieces,
              disableWebPagePreview=disableWebPagePreview,
              replyMarkup=replyMarkup,
              answerCallbackQueryId=answerCallbackQueryId,
              answerCallbackQueryText=answerCallbackQueryText,
              pinMessage=pinMessage,
              unpinMessage=unpinMessage,
              disablePinNotification=disablePinNotification,
            )
          else:
            raise e

  else:  # send message
    kwargs['reply_to_message_id'] = chat.replyToMessageId
    if 'media' in kwargs:
      if mediaType == TgMediaType.PHOTO and len(media) == 1:
        kwargs['photo'] = kwargs['media'][0].media
        kwargs['caption'] = kwargs['media'][0].caption
        kwargs['caption_entities'] = kwargs['media'][0].caption_entities
        del kwargs['media']
        m = await tg.send_photo(**kwargs)
      else:
        del kwargs['reply_markup']
        m = await tg.send_media_group(**kwargs)
    else:
      m = await tg.send_message(**kwargs)
      if _logger is not None and log:
        asyncio.create_task(
          _logger.answer(
            pieces,
            username=m.from_user.username if m.from_user is not None else None,
            answerToChatId=kwargs['chat_id'],
            answerToMessageId=kwargs.get('reply_to_message_id'),
          ))

  # pins
  m = m if isinstance(m, list) else [m]
  messageToPinId = chat.translateToMessageId or (m[0].message_id
                                                 if m[0] is not None else None)
  if pinMessage and messageToPinId is not None:

    async def pin():
      await tg.pin_chat_message(
        chat_id=kwargs['chat_id'],
        message_id=messageToPinId,
        disable_notification=disablePinNotification,
      )

    await _ignore_message_is_not_modified(pin, ignoreMessageNotEdited)

  if unpinMessage and messageToPinId is not None:

    async def unpin():
      await tg.unpin_chat_message(
        chat_id=kwargs['chat_id'],
        message_id=messageToPinId,
      )

    await _ignore_message_is_not_modified(unpin, ignoreMessageNotEdited)

  # callback query
  if answerCallbackQueryId is not None:
    await tg.answer_callback_query(
      callback_query_id=answerCallbackQueryId,
      text=answerCallbackQueryText or text,
    )

  return m


def _transform_media(media: [], type: TgMediaType, text, entities) -> []:
  type = {
    TgMediaType.PHOTO: InputMediaPhoto,
    TgMediaType.VIDEO: InputMediaVideo,
    TgMediaType.AUDIO: InputMediaAudio,
  }.get(type)
  return [
    type(media=media[0], caption=text, caption_entities=entities),
    *[type(media=m) for m in media[1:]]
  ]


async def _ignore_message_is_not_modified(fun, ignore: bool):
  if not ignore:
    await fun()
    return

  try:
    await fun()
  except ApiTelegramException as e:
    if 'message is not modified' not in str(e):
      raise e
