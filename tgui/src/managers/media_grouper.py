import asyncio

from typing import List, Optional

from attr.validators import instance_of
from attrs import define, field
from lega4e_library import Notifier
from lega4e_library.attrs.validators import list_validator
from telebot.types import Message


@define
class MediaGroup:
  group: str = field(validator=instance_of(str))
  messages: List[Message] = field(validator=list_validator(Message))


@define
class _MediaGroupWrapper:
  group: MediaGroup = field(validator=instance_of(MediaGroup))
  ticks: int = field(validator=instance_of(int), default=0)


class MediaGrouper(Notifier):

  def __init__(self, sleepTime: float = 0.1, ticks: int = 10):
    super().__init__()
    self.sleepTime = sleepTime
    self.ticks = ticks
    self._runflag = True
    self._mediagroups: List[_MediaGroupWrapper] = []
    self._tasks = []

  async def run(self):
    while True:
      await asyncio.sleep(self.sleepTime)
      newMediaGroups = []
      for mgw in self._mediagroups:
        mgw: _MediaGroupWrapper = mgw
        mgw.ticks += 1
        if mgw.ticks < self.ticks:
          newMediaGroups.append(mgw)
        else:
          mgw.group.messages.sort(key=lambda m: m.message_id)
          self.notify(mgw.group)
      self._mediagroups = newMediaGroups

  def pushMessage(self, m: Message):
    if m.media_group_id is None:
      self.notify(MediaGroup('', [m]))
      return

    mgw = self._findGroup(m.media_group_id)
    if mgw is not None:
      mgw.group.messages.append(m)
    else:
      self._mediagroups.append(
        _MediaGroupWrapper(group=MediaGroup(
          group=m.media_group_id,
          messages=[m],
        )))

  def _findGroup(self, group: str) -> Optional[_MediaGroupWrapper]:
    for mgw in self._mediagroups:
      if group == mgw.group.group:
        return mgw
    return None
