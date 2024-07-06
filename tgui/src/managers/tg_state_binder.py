import asyncio

from typing import List, Callable, Optional, Coroutine

from attr import field, define
from attr.validators import instance_of
from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand, Message, CallbackQuery

from tgui.src.domain.piece import P, Pieces
from tgui.src.logging.logger_wrapper import TgLoggerWrapper
from tgui.src.logging.tg_logger import TgLogger
from tgui.src.managers.callback_query_manager import CallbackQueryManager, \
  CallbackQueryIdentifier, CallbackSourceType
from tgui.src.states.tg_state import TgState


@define
class Command:
  name: str = field(validator=instance_of(str))
  preview: str = field(validator=instance_of(str))
  description: str = field(validator=instance_of(str))
  handler: Optional[str] = field(
    validator=instance_of(Optional[str]),
    default=None,
  )
  addToMenu: bool = field(
    validator=instance_of(Optional[bool]),
    default=True,
  )


class TgStateBinder:

  def __init__(
    self,
    commands: List[Command],
    tg: AsyncTeleBot,
    logger: TgLogger,
    stateGetter: Callable[[Message], TgState],
    callbackQueryManager: CallbackQueryManager,
    ignoreGroups: bool = True,
  ):
    self._commands = commands
    self._tg = tg
    self._logger = logger
    self._stateGetter = stateGetter
    self._callbackQueryManager = callbackQueryManager
    self._ignoreGroups = ignoreGroups

  def _task(self, coro: Coroutine):
    asyncio.create_task(coro)

  async def addCommandsToMenu(self):
    await self._tg.set_my_commands([
      BotCommand(com.preview, com.description)
      for com in self._commands
      if com.addToMenu
    ])

  # handlers
  def addHandlers(self):
    self.addCommandHandlers()
    self.addMessageHandlers()
    self.addCallbackQueryHandlers()

  def addCommandHandlers(self):
    for command in self._commands:
      if command.handler is None:
        continue
      # pylint: disable=W0122
      exec(f'''
@self._tg.message_handler(commands=[command.name])
@self._logCommandDecorator
@self._findUserDecorator
def handle_{command.name}(user, m, __):
  if user is not None:
    exec(f'asyncio.create_task(user.{command.handler}(m))')
      ''')

    @self._tg.message_handler(func=lambda m: m.text.startswith('/'))
    @self._logCommandDecorator
    @self._findUserDecorator
    def handle_any_command(user, m, __):
      if user is not None:
        self._task(user.handleCommand(m))

  def addMessageHandlers(self):

    @self._tg.message_handler(content_types=[
      'text',
      'photo',
      'video',
      'audio',
      'voice',
      'location',
      'contact',
    ])
    @self._logMessageDecorator
    def handle_message(m: Message, __=False):
      user = self._stateGetter(m)
      if user is not None:
        self._task(user.handleMessage(m))

  def addCallbackQueryHandlers(self):

    @self._tg.callback_query_handler(func=lambda call: True)
    async def handle_callback_query(q: CallbackQuery):
      answer = self._callbackQueryManager.find(
        CallbackQueryIdentifier(
          type=CallbackSourceType.USER_ID,
          id=q.from_user.id,
          data=q.data,
        ))

      if answer is None:
        answer = self._callbackQueryManager.find(
          CallbackQueryIdentifier(
            type=CallbackSourceType.CHAT_ID,
            id=q.message.chat.id,
            data=q.data,
          ))

      if answer is None:
        await self._tg.answer_callback_query(
          q.id,
          text='Эта кнопка недоступна',
          show_alert=True,
        )
        return

      if answer.logMessage is not None:
        self._logger.message(
          P(f'{TgLoggerWrapper.cqAnswerPrefix(q)} {answer.logMessage}'),
          header=False,
        )

      if answer.answerText is not None:
        self._task(
          self._tg.answer_callback_query(
            q.id,
            text=answer.answerText,
            show_alert=answer.showAlert,
            url=answer.url,
          ))

      self._task(maybeAwait(answer.action(q)))

  # decorators
  def _logCommandDecorator(self, func):

    async def wrapper(m: Message, res=False):
      message = (P(f'{TgLoggerWrapper.textPrefix(m)}') + '\n' +
                 Pieces.fromMessage(
                   m.text or m.caption or 'None',
                   m.entities or m.caption_entities or [],
                 ))
      self._logger.message(message, header=False)
      func(m, res)

    return wrapper

  def _logMessageDecorator(self, func):

    async def wrapper(m: Message, res=False):
      if m.chat.id > 0:
        message = (P(f'{TgLoggerWrapper.textPrefix(m)}') + '\n' +
                   Pieces.fromMessage(
                     m.text or m.caption or 'None',
                     m.entities or m.caption_entities or [],
                   ))
        self._logger.message(message, header=False)
        func(m, res)

    return wrapper

  def _findUserDecorator(self, func):

    def wrapper(m: Message, res=False):
      if self._ignoreGroups and (m.chat.id < 0 or m.is_topic_message):
        user = None
      else:
        user = self._stateGetter(m)
      func(user, m, res)

    return wrapper
