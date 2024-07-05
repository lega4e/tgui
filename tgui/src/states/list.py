from typing import Optional, List, Union, Callable, Any, Coroutine

from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot

from tgui.src.domain import TgDestination
from tgui.src.managers.callback_query_manager import CallbackQueryManager
from tgui.src.states.branch import BranchMessage, BranchButton
from tgui.src.states.paging import TgPagingState


class TgListState(TgPagingState):

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    getItems: Callable[[], List[Any]],
    pageBuilder: Callable[[int], Union[BranchMessage, Coroutine]],
    nextButtonTitle: str,
    prevButtonTitle: str,
    getButton: Optional[Callable[[Any], BranchButton]],
    pageBuilderOnChoice: Optional[Callable[
      [int, Any],
      Union[BranchMessage, Coroutine],
    ]] = None,
    rows: int = 5,
    cols: int = 1,
    initialPageNum: int = 0,
    backButton: Optional[BranchButton] = None,
    getLeadButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
    getMidButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
    getTrailButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
  ):
    TgPagingState.__init__(
      self,
      tg=tg,
      destination=destination,
      callbackManager=callbackManager,
      pageCount=(len(getItems()) - 1) // (rows * cols) + 1,
      pageBuilder=self.buildPage,
      nextButtonTitle=nextButtonTitle,
      prevButtonTitle=prevButtonTitle,
      backButton=backButton,
      initialPageNum=initialPageNum,
      getLeadButtons=self.buildLeadButtons,
      getTrailButtons=getTrailButtons,
    )
    self._getItems = getItems
    self._rows = rows
    self._cols = cols
    self._pageListBuilder = pageBuilder
    self._pageBuilderOnChoice = pageBuilderOnChoice
    self._getButton = getButton
    self._getLeadListButtons = getLeadButtons or (lambda _: [])
    self._getMidListButtons = getMidButtons or (lambda _: [])
    self._choicedItem = None

  def updateItemsCount(self, count: int):
    self.updatePageCount((count - 1) // (self._rows * self._cols) + 1)

  def buildLeadButtons(self, num: int) -> List[List[BranchButton]]:
    buttons = []
    buttons += self._getLeadListButtons(num)

    b, e = num * self._rows * self._cols, (num + 1) * self._rows * self._cols
    items = [self._makeButton(item) for item in self._getItems()[b:e]]
    for row in range(self._rows):
      itms = list(items[row * self._cols:(row + 1) * self._cols])
      if len(itms) == 0:
        break
      buttons.append(itms)

    buttons += self._getMidListButtons(num)
    return buttons

  async def buildPage(self, num: int) -> BranchMessage:
    if self._choicedItem is not None and self._pageBuilderOnChoice is not None:
      return await maybeAwait(self._pageBuilderOnChoice(num, self._choicedItem))
    return await maybeAwait(self._pageListBuilder(num))

  async def choiceItem(self, item: Any):
    self._choicedItem = item
    await self.translateMessage()

  def _makeButton(self, item: Any) -> BranchButton:
    button: BranchButton = self._getButton(item)
    if self._pageBuilderOnChoice is not None:
      button.action = lambda: self.choiceItem(item)
    return button
