from typing import Callable, Optional, Coroutine, Union

from lega4e_library.algorithm.algorithm import nn
from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.emoji import Emoji
from tgui.src.managers.callback_query_manager import CallbackQueryManager
from tgui.src.states.branch import TgBranchState, BranchMessage, BranchButton, \
  BranchButtonAction, BranchKeyboard


class TgPagingState(TgBranchState):

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    pageCount: int,
    pageBuilder: Callable[[int, int], Union[BranchMessage, Coroutine]],
  ):
    TgBranchState.__init__(
      self,
      tg=tg,
      destination=destination,
      buttonsGetter=self._buildButtons,
      messageGetter=self._buildMessage,
      callbackManager=callbackManager,
    )
    self._nextButtonTitle = Emoji.ARROW_RIGHT
    self._prevButtonTitle = Emoji.ARROW_LEFT
    self._backButtonTitle = Emoji.RETURN
    self._getLeadButtons = lambda _, __: []
    self._getTrailButtons = lambda _, __: []
    self._middleButton = None
    self._pageCount = pageCount
    self._pageBuilder = pageBuilder
    self._pageNum = 0

  def configurePagingState(
    self,
    nextButtonTitle: Optional[str] = None,
    prevButtonTitle: Optional[str] = None,
    backButtonTitle: Optional[str] = None,
    enableBackButton: Optional[bool] = None,
    middleButton: Optional[BranchButton] = None,
    getLeadButtons: Optional[Callable[[int, int], BranchKeyboard]] = None,
    getTrailButtons: Optional[Callable[[int, int], BranchKeyboard]] = None,
  ):
    if enableBackButton is not None and not enableBackButton:
      self._middleButton = None

    if nextButtonTitle is not None:
      self._nextButtonTitle = nextButtonTitle

    if prevButtonTitle is not None:
      self._prevButtonTitle = prevButtonTitle

    if backButtonTitle is not None:
      self._backButtonTitle = backButtonTitle

    if middleButton is not None:
      self._middleButton = middleButton

    if getLeadButtons is not None:
      self._getLeadButtons = getLeadButtons

    if getTrailButtons is not None:
      self._getTrailButtons = getTrailButtons

    if enableBackButton:
      self._middleButton = BranchButton(
        self._backButtonTitle,
        BranchButtonAction(pop=True),
      )

    return self

  def updatePageCount(self, newPageCount: int):
    self._pageCount = newPageCount
    if self._pageNum >= self._pageCount:
      self._pageNum = max(self._pageCount - 1, 0)

  def getPageCount(self) -> int:
    return self._pageCount

  def setPageNum(self, num: int):
    self._pageNum = num

  def getPageNum(self) -> int:
    return self._pageNum

  def _buildButtons(self) -> BranchKeyboard:
    nav = nn([
      BranchButton(
        self._prevButtonTitle if self._pageNum > 0 else Emoji.SQUARE,
        self._onPrevButton,
      ) if self._pageCount > 1 else None,
      self._middleButton,
      BranchButton(
        self._nextButtonTitle \
          if self._pageNum + 1 < self._pageCount else Emoji.SQUARE,
        self._onNextButton,
      ) if self._pageCount > 1 else None,
    ])

    return self._getLeadButtons(self._pageNum, self._pageCount) + \
      nn([nav], notEmpty=False) + \
      self._getTrailButtons(self._pageNum, self._pageCount)

  async def _buildMessage(self) -> BranchMessage:
    return await maybeAwait(self._pageBuilder(self._pageNum, self._pageCount))

  # BUTTON HANDLERS
  async def _onNextButton(self):
    if self._pageNum + 1 < self._pageCount:
      self._pageNum += 1
      await self.translateMessage()

  async def _onPrevButton(self):
    if self._pageNum > 0:
      self._pageNum -= 1
      await self.translateMessage()
