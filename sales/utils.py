import zoneinfo
from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Sum, Avg, Count
from .models import Sale

TIMEZONE_ALMATY = zoneinfo.ZoneInfo("Asia/Almaty")

MONTHS_RU = [
    '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
]

MONTHS_RU_SHORT = [
    '', 'янв.', 'февр.', 'мар.', 'апр.', 'мая', 'июн.',
    'июл.', 'авг.', 'сент.', 'окт.', 'нояб.', 'дек.'
]

WEEKDAYS_RU = [
    'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье'
]


def get_almaty_now():
    """Возвращает текущее время в часовом поясе Asia/Almaty."""
    return timezone.now().astimezone(TIMEZONE_ALMATY)


def format_today_russian(now=None):
    """Форматирует текущую дату на русском языке: '12 ноября, четверг'."""
    if now is None:
        now = get_almaty_now()
    return f"{now.day} {MONTHS_RU[now.month]}, {WEEKDAYS_RU[now.weekday()]}"


def format_tenge(value):
    """Форматирует число с пробелами между разрядами и знаком тенге: 184 000 ₸."""
    if value is None:
        value = 0
    formatted = f"{int(round(value)):,}".replace(",", " ")
    return f"{formatted} ₸"


def format_profit(profit):
    """Форматирует прибыль со знаком: +1 200 ₸ или 0 ₸ или -500 ₸."""
    if profit is None:
        profit = 0
    num = int(round(profit))
    sign = "+" if num > 0 else ""
    formatted = f"{num:,}".replace(",", " ")
    return f"{sign}{formatted} ₸"


def format_sale_time(dt, now=None):
    """Форматирует время продажи."""
    if now is None:
        now = get_almaty_now()
    sale_dt = dt.astimezone(TIMEZONE_ALMATY)

    is_today = (sale_dt.year == now.year and
                sale_dt.month == now.month and
                sale_dt.day == now.day)

    if is_today:
        return sale_dt.strftime("%H:%M")
    else:
        return f"{sale_dt.day} {MONTHS_RU_SHORT[sale_dt.month]}, {sale_dt.strftime('%H:%M')}"


def get_period_boundaries(now=None):
    """Границы периодов в Asia/Almaty."""
    if now is None:
        now = get_almaty_now()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return {
        'today': today_start,
        'week': week_start,
        'month': month_start,
    }


def calculate_stats_for_period(start_datetime, end_datetime=None):
    """Считает агрегированную статистику за период."""
    sales_qs = Sale.objects.filter(created_at__gte=start_datetime)
    if end_datetime:
        sales_qs = sales_qs.filter(created_at__lte=end_datetime)

    aggregates = sales_qs.aggregate(
        total_sales=Sum('sale_price'),
        kaspi_sales=Sum('kaspi_amount'),
        cash_sales=Sum('cash_amount'),
        avg_check=Avg('sale_price'),
        count=Count('id')
    )

    total_sales = aggregates['total_sales'] or 0
    kaspi_sum = aggregates['kaspi_sales'] or 0
    cash_sum = aggregates['cash_sales'] or 0
    avg_check = aggregates['avg_check'] or 0
    count = aggregates['count'] or 0

    return {
        'total_sales': total_sales,
        'total_sales_formatted': format_tenge(total_sales),
        'kaspi_sum': kaspi_sum,
        'kaspi_formatted': format_tenge(kaspi_sum),
        'cash_sum': cash_sum,
        'cash_formatted': format_tenge(cash_sum),
        'avg_check': avg_check,
        'avg_check_formatted': format_tenge(avg_check),
        'count': count,
    }


def get_all_periods_stats():
    """Считает статистику по всем трём периодам (сегодня, неделя, месяц)."""
    now = get_almaty_now()
    boundaries = get_period_boundaries(now)

    return {
        'today': calculate_stats_for_period(boundaries['today']),
        'week': calculate_stats_for_period(boundaries['week']),
        'month': calculate_stats_for_period(boundaries['month']),
    }
