from typing import Optional, List, Callable, Any, Coroutine, Union

from lega4e_library.algorithm.algorithm import rdc, nn
from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from tgui.src.domain.destination import TgDestination
from tgui.src.domain.piece import Pieces, P
from tgui.src.managers.callback_query_manager import CallbackQueryManager
from tgui.src.states.branch import BranchButtonAction, BranchMessage
from tgui.src.states.paging import TgPagingState


class TgRefListState(TgPagingState):

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    getItems: Callable[[], Union[List[Any], Coroutine]],
    itemBuilder: Callable[[Any, str], Pieces],
    actionGetter: Callable[[Any], Union[BranchButtonAction, Coroutine]],
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
    self._getItems = getItems
    self._itemBuilder = itemBuilder
    self._actionGetter = actionGetter
    self._elementsPerPage = 15
    self._headBuilder = None
    self._tailBuilder = None
    self._onEmptyBuilder = lambda: P('Empty')
    self._botName = None
    self._startArgName = None
    self._items = None

  def configureRefListState(
    self,
    headBuilder: Optional[Callable[[int, int], Pieces]] = None,
    tailBuilder: Optional[Callable[[int, int], Pieces]] = None,
    onEmptyBuilder: Optional[Callable[[], Pieces]] = None,
    botName: Optional[str] = None,
    startArgName: Optional[str] = None,
    elementsPerPage: Optional[int] = None,
  ):
    if headBuilder is not None:
      self._headBuilder = headBuilder

    if tailBuilder is not None:
      self._tailBuilder = tailBuilder

    if onEmptyBuilder is not None:
      self._onEmptyBuilder = onEmptyBuilder

    if botName is not None:
      self._botName = botName

    if startArgName is not None:
      self._startArgName = startArgName

    if elementsPerPage is not None:
      self._elementsPerPage = elementsPerPage
      
    return self

  def updateItemsCount(self, count: int):
    self.updatePageCount((count - 1) // self._elementsPerPage + 1)

  async def buildPage(self, num: int, count: int) -> BranchMessage:
    epp = self._elementsPerPage
    items = self._items[num * epp:(num + 1) * epp]
    head, tail, url = None, None, None
    if self._headBuilder is not None:
      head = await maybeAwait(self._headBuilder(num, count))
    if self._tailBuilder is not None:
      tail = await maybeAwait(self._tailBuilder(num, count))
    if self._botName is not None and self._startArgName is not None:
      url = f't.me/{self._botName}?start={self._startArgName}_%i'
    items = [
      await
      maybeAwait(self._itemBuilder(
        item,
        url % i if url is not None else None,
      )) for i, item in enumerate(items)
    ]
    if len(items) == 0:
      items = [await maybeAwait(self._onEmptyBuilder())]
    return BranchMessage(
      rdc(
        lambda a, b: a + '\n\n' + b,
        nn([
          head,
          rdc(lambda a, b: a + '\n' + b, nn(items, notEmpty=False)),
          tail,
        ]),
      ))

  async def _handleCommand(self, m: Message) -> bool:
    if self._botName is None or self._startArgName is None:
      return False

    if m.text.startswith(f'/start {self._startArgName}_'):
      itemIndex = int(m.text.split(f'{self._startArgName}_')[1])
      item = self._items[self._pageNum * self._elementsPerPage:][itemIndex]
      await self.delete(m)
      await self._processAction(item)
      return True

    return False

  async def _processAction(self, item: Any):
    action = await maybeAwait(self._actionGetter(item))
    await self._executeAction(action)

  async def _update(self):
    self._items = await maybeAwait(self._getItems())
    self.updateItemsCount(len(self._items))
