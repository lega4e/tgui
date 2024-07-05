from typing import Optional, List, Callable, Any, Coroutine, Union

from lega4e_library.algorithm.algorithm import rdc, nn
from lega4e_library.asyncio.utils import maybeAwait
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

from tgui.src.domain import TgDestination, Pieces
from tgui.src.managers.callback_query_manager import CallbackQueryManager
from tgui.src.states.branch import BranchButtonAction, BranchButton, BranchMessage
from tgui.src.states.paging import TgPagingState


class TgRefListState(TgPagingState):

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    getItems: Callable[[], List[Any]],
    itemBuilder: Callable[[Any, str], Pieces],
    nextButtonTitle: str,
    prevButtonTitle: str,
    actionGetter: Callable[[Any], Union[BranchButtonAction, Coroutine]],
    botName: str,
    headBuilder: Optional[Callable[[int], Pieces]] = None,
    tailBuilder: Optional[Callable[[int], Pieces]] = None,
    onEmptyBuilder: Optional[Callable[[], Pieces]] = None,
    elementsByPage: int = 15,
    initialPageNum: int = 0,
    backButton: Optional[BranchButton] = None,
    getLeadButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
    getTrailButtons: Optional[Callable[[int], List[List[BranchButton]]]] = None,
    startArgName: str = 'ref_list',
  ):
    TgPagingState.__init__(
      self,
      tg=tg,
      destination=destination,
      callbackManager=callbackManager,
      pageCount=1,
      pageBuilder=self.buildPage,
      nextButtonTitle=nextButtonTitle,
      prevButtonTitle=prevButtonTitle,
      backButton=backButton,
      initialPageNum=initialPageNum,
      getLeadButtons=getLeadButtons,
      getTrailButtons=getTrailButtons,
    )
    self.configureBranchState(self._update)
    self._getItems = getItems
    self._elementsByPage = elementsByPage
    self._itemBuilder = itemBuilder
    self._headBuilder = headBuilder
    self._tailBuilder = tailBuilder
    self._onEmptyBuilder = onEmptyBuilder
    self._actionGetter = actionGetter
    self._botName = botName
    self._startArgName = startArgName
    self._items = None

  def updateItemsCount(self, count: int):
    self.updatePageCount((count - 1) // self._elementsByPage + 1)

  async def buildPage(self, num: int) -> BranchMessage:
    ebp = self._elementsByPage
    items = self._items[num * ebp:(num + 1) * ebp]
    head, tail = None, None
    if self._headBuilder is not None:
      head = await maybeAwait(self._headBuilder(num))
    if self._tailBuilder is not None:
      tail = await maybeAwait(self._tailBuilder(num))
    startArgName = f't.me/{self._botName}?start={self._startArgName}_%i'
    items = [
      await maybeAwait(self._itemBuilder(item, startArgName % i))
      for i, item in enumerate(items)
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
    if m.text.startswith(f'/start {self._startArgName}_'):
      itemIndex = int(m.text.split(f'{self._startArgName}_')[1])
      item = self._items[self._pageNum * self._elementsByPage:][itemIndex]
      await self.delete(m)
      await self._proccessAction(item)
      return True

    return False

  async def _proccessAction(self, item: Any):
    action = await maybeAwait(self._actionGetter(item))
    await self._executeAction(action)

  async def _update(self):
    self._items = await maybeAwait(self._getItems())
    self.updateItemsCount(len(self._items))
