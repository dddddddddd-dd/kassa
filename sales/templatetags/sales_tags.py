from django import template
from sales.utils import format_tenge, format_profit, format_sale_time

register = template.Library()


@register.filter(name='tenge')
def tenge_filter(value):
    """Форматирует число в валюту: 184 000 ₸."""
    return format_tenge(value)


@register.filter(name='profit_display')
def profit_filter(value):
    """Форматирует прибыль: +1 200 ₸."""
    return format_profit(value)


@register.filter(name='sale_time')
def sale_time_filter(dt):
    """Форматирует время продажи в часовом поясе Almaty."""
    if not dt:
        return ''
    return format_sale_time(dt)

