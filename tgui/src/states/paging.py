from typing import Callable, Optional, List, Coroutine, Union

from lega4e_library.algorithm.algorithm import nn
from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot

from tgui.src.domain import TgDestination, Emoji
from tgui.src.managers.callback_query_manager import CallbackQueryManager
from tgui.src.states.branch import TgBranchState, BranchMessage, BranchButton


class TgPagingState(TgBranchState):

  def __init__(
      self,
      tg: AsyncTeleBot,
      destination: TgDestination,
      callbackManager: CallbackQueryManager,
      pageCount: int,
      pageBuilder: Callable[[int], Union[BranchMessage, Coroutine]],
      nextButtonTitle: str,
      prevButtonTitle: str,
      backButton: Optional[BranchButton] = None,
      initialPageNum: int = 0,
      getLeadButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
      getTrailButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
  ):
    TgBranchState.__init__(
      self,
      tg=tg,
      destination=destination,
      buttonsGetter=self._buildButtons,
      messageGetter=self._buildMessage,
      callbackManager=callbackManager,
    )
    self._nextButtonTitle = nextButtonTitle
    self._prevButtonTitle = prevButtonTitle
    self._backButton = backButton
    self._pageCount = pageCount
    self._pageBuilder = pageBuilder
    self._pageNum = initialPageNum
    self._getLeadButtons = getLeadButtons or (lambda _: [])
    self._getTrailButtons = getTrailButtons or (lambda _: [])

  def updatePageCount(self, newPageCount: int):
    self._pageCount = newPageCount
    if self._pageNum >= self._pageCount:
      self._pageNum = max(self._pageCount - 1, 0)

  def _buildButtons(self) -> [[BranchButton]]:
    nav = nn([
      BranchButton(
        self._prevButtonTitle if self._pageNum > 0 else Emoji.SQUARE,
        self._onPrevButton,
      ) if self._pageCount > 1 else None,
      self._backButton,
      BranchButton(
        self._nextButtonTitle \
          if self._pageNum + 1 < self._pageCount else Emoji.SQUARE,
        self._onNextButton,
      ) if self._pageCount > 1 else None,
    ])

    return self._getLeadButtons(self._pageNum) + \
      nn([nav], notEmpty=False) + \
      self._getTrailButtons(self._pageNum)

  async def _buildMessage(self) -> BranchMessage:
    return await maybeAwait(self._pageBuilder(self._pageNum))

  # BUTTON HANDLERS
  async def _onNextButton(self):
    if self._pageNum + 1 < self._pageCount:
      self._pageNum += 1
      await self.translateMessage()

  async def _onPrevButton(self):
    if self._pageNum > 0:
      self._pageNum -= 1
      await self.translateMessage()
