from typing import Optional

from attr import field, define
from attr.validators import instance_of
from lega4e_library.attrs.jsonkin import jsonkin

from tgui.src.constructor.utils.prove_pieces import prove_pieces
from tgui.src.domain.piece import Pieces


@jsonkin
@define
class YesNoTgItem:
  greeting: Pieces = field(
    validator=instance_of(Pieces),
    converter=prove_pieces,
  )
  yesTitle: str = field(validator=instance_of(str))
  noTitle: str = field(validator=instance_of(str))
  errorMessage: Pieces = field(
    validator=instance_of(Pieces),
    converter=prove_pieces,
  )
  yesAnswer: Optional[str] = field(
    validator=instance_of(Optional[str]),
    default=None,
  )
  noAnswer: Optional[str] = field(
    validator=instance_of(Optional[str]),
    default=None,
  )
