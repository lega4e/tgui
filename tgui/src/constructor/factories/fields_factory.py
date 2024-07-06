from typing import Any, Optional, Callable

from telebot.async_telebot import AsyncTeleBot

from tgui.src.constructor.factories.checks_factory import TgChecksFactory
from tgui.src.constructor.models.form import FormTgItem
from tgui.src.managers.callback_query_manager import CallbackQueryManager
from tgui.src.constructor.factories.validators_factory import \
  TgValidatorsFactory
from tgui.src.constructor.models.choice import ChoiceTgItem
from tgui.src.constructor.models.choice_button import ChoiceButton
from tgui.src.constructor.models.multiple_choice import MultipleChoiceTgItem
from tgui.src.constructor.models.validated_item import ValidatedTgItem
from tgui.src.constructor.models.yes_no import YesNoTgItem
from tgui.src.mixin.executable import TgExecutableMixin
from tgui.src.states.form import TgFormState
from tgui.src.states.input_field import TgInputField, InputFieldButton
from tgui.src.states.multiple_choice import TgMultipleChoice, \
  MultipleChoiceButton
from tgui.src.domain.destination import TgDestination


class TgInputFieldsFactory:

  def __init__(
    self,
    tg: AsyncTeleBot,
    destination: TgDestination,
    callbackManager: CallbackQueryManager,
    validators: TgValidatorsFactory,
    checks: TgChecksFactory,
    checkCustomCondition: Optional[Callable] = None,
  ):
    self.tg = tg
    self.destination = destination
    self.callbackManager = callbackManager
    self.validators = validators
    self.checks = checks
    self.checkCustomCondition = checkCustomCondition

  def get(self, item: Any) -> TgExecutableMixin:
    if isinstance(item, ValidatedTgItem):
      return self.field(item)
    elif isinstance(item, YesNoTgItem):
      return self.yesNo(item)
    elif isinstance(item, ChoiceTgItem):
      return self.choice(item)
    elif isinstance(item, MultipleChoiceTgItem):
      return self.multipleChoice(item)
    elif isinstance(item, FormTgItem):
      return self.form(item)
    else:
      raise ValueError(f'Unknown item type: {type(item)}')

  def field(self, item: ValidatedTgItem) -> TgInputField:
    return TgInputField(
      tg=self.tg,
      destination=self.destination,
      validator=self.validators.get(item.validator, item.errorMessage),
      callbackManager=self.callbackManager,
      buttons=list(
        map(
          lambda row: list(map(self.choiceButton2InputFieldButton, row)),
          item.buttons,
        )),
    ).configureTgState(greeting=item.greeting)

  def yesNo(self, item: YesNoTgItem) -> TgInputField:
    return TgInputField(
      tg=self.tg,
      destination=self.destination,
      validator=self.validators.alwaysError(item.errorMessage),
      callbackManager=self.callbackManager,
      buttons=[
        [
          InputFieldButton(
            title=item.noTitle,
            value=False,
            answer=item.noAnswer,
          ),
          InputFieldButton(
            title=item.yesTitle,
            value=True,
            answer=item.yesAnswer,
          ),
        ],
      ],
      ignoreMessageInput=False,
    ).configureTgState(greeting=item.greeting)

  def choice(self, choice: ChoiceTgItem) -> TgInputField:
    return TgInputField(
      tg=self.tg,
      destination=self.destination,
      validator=self.validators.alwaysError(choice.errorMessage),
      callbackManager=self.callbackManager,
      buttons=list(
        map(
          lambda row: list(map(self.choiceButton2InputFieldButton, row)),
          choice.buttons,
        )),
      ignoreMessageInput=not choice.errorOnInput,
    ).configureTgState(greeting=choice.greeting)

  def multipleChoice(self, choice: MultipleChoiceTgItem) -> TgMultipleChoice:
    check = None
    if choice.validator is not None:
      check = self.checks.get(choice.validator)

    return TgMultipleChoice(
      tg=self.tg,
      destination=self.destination,
      callbackManager=self.callbackManager,
      buttons=list(
        map(
          lambda row: list(map(self.choiceButton2MultipleChoiceButton, row)),
          choice.buttons,
        )),
      checkChoice=check,
    ).configureTgState(greeting=choice.greeting)

  def form(
    self,
    form: FormTgItem,
    checkCustomCondition: Optional[Callable] = None,
  ) -> TgFormState:
    return TgFormState(
      tg=self.tg,
      destination=self.destination,
      fieldsFactory=self,
      elements=form.elements,
      checkCustomCondition=checkCustomCondition or self.checkCustomCondition,
    )

  # SERVICE
  @staticmethod
  def choiceButton2InputFieldButton(button: ChoiceButton) -> InputFieldButton:
    return InputFieldButton(
      title=button.title,
      value=button.value,
      answer=button.answer,
    )

  @staticmethod
  def choiceButton2MultipleChoiceButton(
      button: ChoiceButton) -> MultipleChoiceButton:
    return MultipleChoiceButton(
      titleOn=button.title,
      titleOff=button.offTitle,
      value=button.value,
      answer=button.answer,
      isOnInitial=button.isOnInitial,
      isEndButton=button.isEndButton,
    )
