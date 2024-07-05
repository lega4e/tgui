import asyncio
from typing import List, Any

from telebot.async_telebot import AsyncTeleBot

from tgui.src.domain.destination import TgDestination


class ChainStream:

  def __init__(self, streams: List[Any]):
    self.streams = streams

  def write(self, report: str):
    for stream in self.streams:
      stream.write(report)


class TgLoggerStream:

  def __init__(
    self,
    tg: AsyncTeleBot,
    chats: List[TgDestination],
    ignoreList: List[str] = None,
  ):
    self.tg = tg
    self.chats = chats
    self.ignoreList = ignoreList or []
    self.ignoreList.append('Too Many Requests: retry after')

  def write(self, report: str):
    for ignore in self.ignoreList:
      if ignore in report:
        return

    for chat in self.chats:
      asyncio.create_task(
        self.tg.send_message(
          chat_id=chat.chatId,
          reply_to_message_id=chat.replyToMessageId,
          text=report,
          disable_web_page_preview=True,
        ))
