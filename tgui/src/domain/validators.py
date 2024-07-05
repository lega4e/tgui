from abc import abstractmethod
from copy import copy
from typing import Callable, Union

from telebot.types import Message

from src.utils.tg.domain.piece import Pieces
from src.utils.utils import maybeAwait


class ValidatorObject:

  def __init__(
    self,
    success: bool = True,
    data=None,
    error: Union[str, Pieces] = None,
    message: Message = None,
  ):
    self.success = success
    self.data = data
    self.error = error
    self.message = message


class Validator:
  """
  Класс, который 1) проверяет значение на корректность, 2) меняет его, если надо
  """

  async def validate(self, o: ValidatorObject) -> ValidatorObject:
    """
    Основная функция, возвращает результат валидации
    """
    return await self._validate(copy(o))

  @abstractmethod
  async def _validate(self, o: ValidatorObject) -> ValidatorObject:
    """
    Сама проверка, должна быть переопределена в конкретных классах
    """
    pass


class FunctionValidator(Validator):
  """
  Позволяет задать валидатор не классом, а функцией
  """

  def __init__(self, function: Callable):
    self.function = function

  async def _validate(self, o: ValidatorObject) -> ValidatorObject:
    return await maybeAwait(self.function(o))
