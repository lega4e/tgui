import re
from datetime import timedelta, datetime

from lega4e_library.algorithm.algorithm import rdc
from pytils.numeral import get_plural

from tgui.src.domain.piece import P, Pieces


class TgTexter:

  @staticmethod
  def makeItem(key, value, minWidth=0, prefix=P('')) -> Pieces:
    addSpaces = max(0, minWidth - len(key))
    prefix = prefix + P(key + ' ' * addSpaces, types='code') + '  '
    if value is None:
      return prefix + P('—', types='code')
    elif isinstance(value, Pieces):
      return prefix + value
    elif isinstance(value, datetime):
      return prefix + P(value.strftime("%d %B %Y %H:%M"), types='code')
    elif isinstance(value, str) and re.match(r'@[a-zA-Z]\w{2,}', value):
      return prefix + P(value)
    elif isinstance(value, str) and TgTexter.isUrl(value):
      return prefix + P(value)
    return prefix + P(str(value), types='code')

  @staticmethod
  def fmtTimedelta(delta: timedelta) -> str:
    if delta.days > 0:
      return (f'{TgTexter.days(delta.days)}, '
              f'{TgTexter.hours(delta.seconds//60**2)}')
    elif delta.total_seconds() // 60**2 > 0:
      return f'{TgTexter.hours(delta.seconds//60**2)}, ' \
             f'{TgTexter.minutes(delta.seconds//60**60)}'
    else:
      return f'{TgTexter.minutes(delta.seconds//60**2)}'

  @staticmethod
  def days(days):
    return get_plural(days, ['день', 'дня', 'дней'])

  @staticmethod
  def hours(hours):
    return get_plural(hours, ['час', 'часа', 'часов'])

  @staticmethod
  def minutes(minutes):
    return get_plural(minutes, ['минута', 'минуты', 'минут'])

  @staticmethod
  def tries(tries):
    return get_plural(tries, ['попытка', 'попытки', 'попыток'])

  @staticmethod
  def rdc1(args):
    return rdc(lambda a, b: a + '\n' + b, args)

  @staticmethod
  def rdc2(args):
    return rdc(lambda a, b: a + '\n\n' + b, args)

  @staticmethod
  def title(emoji, text):
    text = P(text, types=['bold', 'italic', 'underline'])
    if emoji is not None:
      text = P(f'{emoji} ') + text
    return text

  @staticmethod
  def title2(emoji, text):
    text = P(text, types=['bold', 'italic'])
    if emoji is not None:
      text = P(f'{emoji} ') + text
    return text

  @staticmethod
  def userUrl(tgId):
    return f'tg://user?id={tgId}'

  @staticmethod
  def isUrl(text):
    return re.match(r'^(https?://)?\w+\.\w+\S*$', text) is not None
