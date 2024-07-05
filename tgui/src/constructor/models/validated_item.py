from typing import List

from attr import field, define
from attr.validators import instance_of
from lega4e_library.attrs.jsonkin import jsonkin
from lega4e_library.attrs.validators import list_list_validator

from tgui.src.constructor.models.choice_button import ChoiceButton
from tgui.src.constructor.models.validator_types import ValidatorDescription
from tgui.src.constructor.utils.prove_pieces import prove_pieces
from tgui.src.domain.piece import Pieces


@jsonkin
@define
class ValidatedTgItem:
  greeting: Pieces = field(
    validator=instance_of(Pieces),
    converter=prove_pieces,
  )
  validator: ValidatorDescription = field(
    validator=instance_of(ValidatorDescription))
  errorMessage: Pieces = field(
    validator=instance_of(Pieces),
    converter=prove_pieces,
  )
  buttons: List[List[ChoiceButton]] = field(
    validator=list_list_validator(ChoiceButton),
    default=[],
  )
