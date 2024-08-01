from typing import Optional, List, Union, Callable, Any, Coroutine

from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot

from tgui.src.domain.destination import TgDestination
from tgui.src.managers.callback_query_manager import CallbackQueryManager
from tgui.src.states.branch import BranchMessage, BranchButton
from tgui.src.states.paging import TgPagingState


class TgListState(TgPagingState):

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    getItems: Callable[[], Union[Coroutine, List[Any]]],
    pageBuilder: Callable[[int], Union[BranchMessage, Coroutine]],
    getButton: Optional[Callable[[Any], BranchButton]],
    pageBuilderOnChoice: Optional[Callable[
      [int, int, Any],
      Union[BranchMessage, Coroutine],
    ]] = None,
  ):
    TgPagingState.__init__(
      self,
      tg=tg,
      destination=destination,
      callbackManager=callbackManager,
      pageCount=1,
      pageBuilder=self.buildPage,
    )
    self.configureBranchState(self._update)
    self._rows = 5
    self._cols = 1
    self._items = []
    self._getItems = getItems
    self._pageListBuilder = pageBuilder
    self._pageBuilderOnChoice = pageBuilderOnChoice
    self._getButton = getButton
    self._getLeadListButtons = lambda _, __: []
    self._getMidButtons = lambda _, __: []
    self._chosenItem = None
    super().configurePagingState(getLeadButtons=self.buildLeadButtons)

  def configureListState(
    self,
    getMidButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
    rows: Optional[int] = None,
    cols: Optional[int] = None,
  ):
    if rows is not None:
      self._rows = rows

    if cols is not None:
      self._cols = cols

    if getMidButtons is not None:
      self._getMidButtons = getMidButtons

    return self

  def configurePagingState(self, **kwargs):
    if kwargs.get('getLeadButtons'):
      self._getLeadListButtons = kwargs.get('getLeadButtons')
      del kwargs['getLeadButtons']

    return super().configurePagingState(**kwargs)

  def updateItemsCount(self, count: int):
    self.updatePageCount((count - 1) // (self._rows * self._cols) + 1)

  def buildLeadButtons(self, num: int, count: int) -> List[List[BranchButton]]:
    buttons = self._getLeadListButtons(num, count)

    b, e = num * self._rows * self._cols, (num + 1) * self._rows * self._cols
    items = [self._makeButton(item) for item in self._getItems()[b:e]]
    for row in range(self._rows):
      itms = list(items[row * self._cols:(row + 1) * self._cols])
      if len(itms) == 0:
        break
      buttons.append(itms)

    buttons += self._getMidButtons(num, count)
    return buttons

  async def buildPage(self, num: int, count: int) -> BranchMessage:
    if self._chosenItem is not None and self._pageBuilderOnChoice is not None:
      return await maybeAwait(
        self._pageBuilderOnChoice(
          num,
          count,
          self._chosenItem,
        ))
    return await maybeAwait(self._pageListBuilder(num))

  async def choiceItem(self, item: Any):
    self._chosenItem = item
    await self.translateMessage()

  def _makeButton(self, item: Any) -> BranchButton:
    button: BranchButton = self._getButton(item)
    if self._pageBuilderOnChoice is not None:
      button.action = lambda: self.choiceItem(item)
    return button

  async def _update(self):
    self._items = await maybeAwait(self._getItems())
    self.updatePageCount(len(self._items))
