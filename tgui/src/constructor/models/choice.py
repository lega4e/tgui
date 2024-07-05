from typing import List, Optional

from attr import field, define
from attr.validators import instance_of
from lega4e_library.attrs.jsonkin import jsonkin
from lega4e_library.attrs.validators import list_list_validator

from tgui.src.constructor.models.choice_button import ChoiceButton
from tgui.src.constructor.utils.prove_pieces import prove_pieces
from tgui.src.domain.piece import Pieces


@jsonkin
@define
class ChoiceTgItem:
  greeting: Pieces = field(
    validator=instance_of(Pieces),
    converter=prove_pieces,
  )
  buttons: List[List[ChoiceButton]] = field(
    validator=list_list_validator(ChoiceButton))
  errorOnInput: bool = field(validator=instance_of(bool), default=True)
  errorMessage: Optional[Pieces] = field(
    validator=instance_of(Optional[Pieces]),
    converter=prove_pieces,
    default=None,
  )
