from typing import Any, Callable

from lega4e_library.asyncio.utils import maybeAwait


class TgExecutableMixin:

  def __init__(self):
    self._completedListeners = []

  def addCompletedListener(self, listener: Callable[[Any], Any]):
    self._completedListeners.append(listener)

  async def executableStateOnCompleted(self, value: Any):
    for listener in self._completedListeners:
      await maybeAwait(listener(value))
