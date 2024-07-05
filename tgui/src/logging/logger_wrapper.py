from logging import Logger

from telebot.types import Message, CallbackQuery


class TgLoggerWrapper:

  def __init__(self, logger: Logger):
    self.logger = logger

  def text(self, m: Message, *args, **kwargs):
    self.logger.info(
      f'{self.textPrefix(m)} {m.text or m.caption}',
      *args,
      **kwargs,
    )

  def cqAnswer(self, q: CallbackQuery, answer, *args, **kwargs):
    self.logger.info(
      f'{self.cqAnswerPrefix(q)} {answer}',
      *args,
      **kwargs,
    )

  @staticmethod
  def _usernameIdOrId(m):
    return (f'@{m.from_user.username}|{m.from_user.id}'
            if m.from_user.username is not None else m.from_user.id)

  @staticmethod
  def textPrefix(m: Message):
    return f'[{TgLoggerWrapper._usernameIdOrId(m)}]'

  @staticmethod
  def cqAnswerPrefix(q: CallbackQuery):
    return f'[{TgLoggerWrapper._usernameIdOrId(q)} CQ]'
