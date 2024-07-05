from logging import Logger

from telebot.async_telebot import ExceptionHandler


class TgExceptionHandler(ExceptionHandler):

  def __init__(self, logger: Logger):
    self.logger: Logger = logger

  def handle(self, exception):
    if exception is not None:
      self.logger.error(
        'Unhandled exception: ' + str(exception),
        exc_info=exception,
      )
    return True
