from logging import Logger
from typing import Callable, Union

from tgui.src.domain.piece import Pieces, provePiece
from tgui.src.logging.tg_logger import TgLogger


class TgUniversalLogger:

  def __init__(
    self,
    systemLogger: Logger,
    publicLogger: TgLogger,
    privateLogger: TgLogger,
  ):
    self.systemLogger = systemLogger
    self.publicLogger = publicLogger
    self.privateLogger = privateLogger

  def info(self, pieces: Pieces):
    self._useLoggerWithoutEcho(lambda l: l.message(pieces), self.publicLogger)
    self.privateLogger.message(pieces)

  def tech(self, pieces: Union[Pieces, str]):
    self.privateLogger.message(provePiece(pieces))

  def sys(self, report: str):
    self.systemLogger.info(report)

  def all(self, report: str):
    self._useLoggerWithoutEcho(lambda l: l.info(report), self.publicLogger)
    self._useLoggerWithoutEcho(lambda l: l.info(report), self.privateLogger)
    self.systemLogger.info(report)

  def _useLoggerWithoutEcho(self, action: Callable, logger: TgLogger):
    enabled = logger.enableSystem
    logger.enableSystem = False
    action(logger)
    logger.enableSystem = enabled
