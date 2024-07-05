import asyncio
from typing import Any, Optional

from lega4e_library.asyncio.async_completer import AsyncCompleter

from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.states.tg_state import TgState


async def calculate_executable_state(
  parent: TgState,
  state: TgExecutableMixin,
  silent: bool = False,
  finishSubstate: bool = True,
  cancelToken: Optional[str] = None,
):
  calculator = AsyncCompleter(cancelToken=cancelToken)
  substate = parent._substate

  def onFieldEntered(value: Any):

    async def callback():
      if finishSubstate:
        await parent.finishSubstate(finishDetached=False)
      parent.attachSubstate(substate)
      calculator.putResult(value)

    asyncio.create_task(callback())

  state.addCompletedListener(onFieldEntered)
  parent.detachSubstate()
  asyncio.create_task(parent.setTgState(state, silent=silent))
  try:
    return await calculator.result()
  finally:
    parent.attachSubstate(substate)
