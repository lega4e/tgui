from types import NoneType
from typing import Any, Dict, Union, Optional

from tgui.src.domain.piece import Pieces, P


def prove_pieces(
    value: Union[
      NoneType,
      str,
      Dict[str, Any],
    ]) -> Optional[Pieces]:
  if isinstance(value, NoneType):
    return None
  elif isinstance(value, dict):
    return Pieces.fromDict(value)
  elif isinstance(value, str):
    return P(value)
  elif isinstance(value, Pieces):
    return value
  else:
    raise ValueError(f'Cannot prove pieces of type {type(value)}')
