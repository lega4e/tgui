from abc import abstractmethod
from copy import copy
from typing import Callable, Union, List

from lega4e_library.asyncio.utils import maybeAwait
from telebot.types import Message

from tgui.src.domain.piece import Pieces


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


class ChainValidator(Validator):

  def __init__(self, validators: List[Validator]):
    self.validators = validators

  async def _validate(self, o: ValidatorObject) -> ValidatorObject:
    for validator in self.validators:
      o = await validator.validate(o)
      if not o.success:
        break
    return o
