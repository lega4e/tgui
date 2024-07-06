import asyncio
import logging
from copy import deepcopy

from datetime import datetime
from logging import Logger
from typing import Optional, List

from telebot.async_telebot import AsyncTeleBot

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import Pieces, P
from tgui.src.logging.tg_logger_stream import TgLoggerStream


class TgLogger(Logger):

  def __init__(
    self,
    tgLoggerName: str,
    tg: AsyncTeleBot,
    tgFmt: str,
    tgTimestampFmt: str,
    tgIgnoreList: List[str],
    chats: List[TgDestination],
    systemLogger: Logger = None,
    sysIgnoreList: Optional[List[str]] = None,
  ):
    super().__init__(tgLoggerName)

    self.enableSystem = True
    self.chats = chats
    self.tg = tg
    self.tgTimestampFmt = tgTimestampFmt
    self.syslog = systemLogger
    self.sysIgnoreList = sysIgnoreList or []

    tgFormatter = logging.Formatter(fmt=tgFmt, datefmt=tgTimestampFmt)
    tgHandler = logging.StreamHandler()
    tgHandler.setFormatter(tgFormatter)
    tgHandler.setStream(
      TgLoggerStream(
        tg=tg,
        chats=chats,
        ignoreList=tgIgnoreList,
      ))

    self.tglog = logging.getLogger(tgLoggerName)
    self.tglog.addHandler(tgHandler)
    self.tglog.setLevel(logging.DEBUG)

  def message(self, pieces: Pieces, header: bool = True, **kwargs):
    if self.syslog is not None and self.enableSystem:
      self.syslog.info(pieces.toString())

    if header:
      pieces = deepcopy(pieces)
      emoji = pieces.emoji + ' ' if pieces.emoji is not None else ''
      pieces.emoji = None
      timestamp = datetime.now().strftime(self.tgTimestampFmt)
      pieces = P(f'[INFO {timestamp}]\n{emoji}') + pieces

    for chat in self.chats:
      from tgui.src.utils.send_message import send_message
      asyncio.create_task(
        send_message(
          self.tg,
          chat,
          pieces,
          **kwargs,
          log=False,
        ))

  async def answer(
    self,
    pieces: Pieces,
    username: Optional[str],
    answerToChatId: int,
    answerToMessageId: Optional[int] = None,
    **kwargs,
  ):
    pieces = deepcopy(pieces)
    emoji = pieces.emoji + ' ' if pieces.emoji is not None else ''
    pieces.emoji = None

    url = f'tg://user?id={answerToChatId}'
    if username is not None:
      answerTo = P(f'@{username}', url=url)
    else:
      answerTo = P(f'@{answerToChatId}', url=url)
    if answerToMessageId is not None:
      answerTo += P(f'/{answerToMessageId}')

    timestamp = datetime.now().strftime(self.tgTimestampFmt)
    pieces = P(f'[ANSWER {timestamp} to ') + answerTo + f']\n{emoji}' + pieces

    if self.syslog is not None and self.enableSystem:
      self.syslog.info('\n' + pieces.toString())

    for chat in self.chats:
      from tgui.src.utils.send_message import send_message
      asyncio.create_task(
        send_message(
          self.tg,
          chat,
          pieces,
          **kwargs,
          log=False,
        ))

  def setLevel(self, level):
    if self.syslog is not None and self.enableSystem:
      self.syslog.setLevel(level)
    self.tglog.setLevel(level)

  def debug(self, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.debug(msg, *args, **kwargs)
    self.tglog.debug(msg, *args, **kwargs)

  def info(self, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.info(msg, *args, **kwargs)
    self.tglog.info(msg, *args, **kwargs)

  def warning(self, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.warning(msg, *args, **kwargs)
    self.tglog.warning(msg, *args, **kwargs)

  def warn(self, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.warn(msg, *args, **kwargs)
    self.tglog.warn(msg, *args, **kwargs)

  def error(self, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.error(msg, *args, **kwargs)
    self.tglog.error(msg, *args, **kwargs)

  def exception(self, msg, *args, exc_info=True, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.exception(msg, *args, exc_info=exc_info, **kwargs)
    self.tglog.exception(msg, *args, exc_info=exc_info, **kwargs)

  def critical(self, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.critical(msg, *args, **kwargs)
    self.tglog.critical(msg, *args, **kwargs)

  def fatal(self, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.fatal(msg, *args, **kwargs)
    self.tglog.fatal(msg, *args, **kwargs)

  def log(self, level, msg, *args, **kwargs):
    if (self.syslog is not None and self.enableSystem and
        not self._checkSysIgnoreList(msg)):
      self.syslog.log(level, msg, *args, **kwargs)
    self.tglog.log(level, msg, *args, **kwargs)

  def _checkSysIgnoreList(self, msg):
    for ignore in self.sysIgnoreList:
      if ignore in str(msg):
        return True
    return False
