import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Sale
from .forms import SaleForm
from .utils import (
    get_almaty_now,
    format_today_russian,
    format_tenge,
    format_sale_time,
    get_all_periods_stats,
    calculate_stats_for_period,
    TIMEZONE_ALMATY,
)


@login_required
@ensure_csrf_cookie
def index(request):
    """Главный экран: онлайн-тетрадь продаж."""
    now = get_almaty_now()
    today_russian = format_today_russian(now)
    all_stats = get_all_periods_stats()

    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('sales:index')
    else:
        form = SaleForm(initial={'payment_method': Sale.PAYMENT_KASPI})

    # Последние 50 записей
    recent_sales = Sale.objects.all().order_by('-created_at')[:50]

    context = {
        'active_nav': 'sales',
        'today_russian': today_russian,
        'today_stats': all_stats['today'],
        'all_stats_json': json.dumps(all_stats),
        'form': form,
        'recent_sales': recent_sales,
        'user': request.user,
    }
    return render(request, 'sales/index.html', context)


@login_required
def report_view(request):
    """Отдельная страница: Отчёт о продажах."""
    now = get_almaty_now()
    today_russian = format_today_russian(now)

    period = request.GET.get('period', 'today')
    custom_date_str = request.GET.get('date', '')

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if custom_date_str:
        try:
            custom_d = datetime.strptime(custom_date_str, '%Y-%m-%d').date()
            start_dt = datetime.combine(custom_d, datetime.min.time()).replace(tzinfo=TIMEZONE_ALMATY)
            end_dt = datetime.combine(custom_d, datetime.max.time()).replace(tzinfo=TIMEZONE_ALMATY)
            period_title = f"Отчёт за {custom_d.strftime('%d.%m.%Y')}"
            period = 'custom'
        except ValueError:
            start_dt = today_start
            end_dt = None
            period_title = "Отчёт за сегодня"
            period = 'today'
    elif period == 'yesterday':
        yesterday_date = (now - timedelta(days=1)).date()
        start_dt = datetime.combine(yesterday_date, datetime.min.time()).replace(tzinfo=TIMEZONE_ALMATY)
        end_dt = datetime.combine(yesterday_date, datetime.max.time()).replace(tzinfo=TIMEZONE_ALMATY)
        period_title = "Отчёт за вчера"
    elif period == 'week':
        start_dt = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = None
        period_title = "Отчёт за текущую неделю"
    elif period == 'month':
        start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_dt = None
        period_title = "Отчёт за текущий месяц"
    else:  # today
        start_dt = today_start
        end_dt = None
        period_title = "Отчёт за сегодня"
        period = 'today'

    # Статистика за выбранный период
    stats = calculate_stats_for_period(start_dt, end_dt)

    # Список всех продаж за период
    sales_qs = Sale.objects.filter(created_at__gte=start_dt)
    if end_dt:
        sales_qs = sales_qs.filter(created_at__lte=end_dt)
    sales = sales_qs.order_by('-created_at')

    context = {
        'active_nav': 'report',
        'today_russian': today_russian,
        'period': period,
        'period_title': period_title,
        'custom_date': custom_date_str,
        'stats': stats,
        'sales': sales,
        'user': request.user,
    }
    return render(request, 'sales/report.html', context)


@login_required
@require_POST
def api_add_sale(request):
    """API для асинхронного добавления продажи через fetch."""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        form = SaleForm(data)
        if form.is_valid():
            sale = form.save()
            all_stats = get_all_periods_stats()
            now = get_almaty_now()

            # Текст для бейджа способа оплаты
            if sale.payment_method == Sale.PAYMENT_SPLIT:
                method_display = f"Kaspi: {format_tenge(sale.kaspi_amount)} + Нал: {format_tenge(sale.cash_amount)}"
            else:
                method_display = sale.get_payment_method_display()

            return JsonResponse({
                'success': True,
                'sale': {
                    'id': sale.id,
                    'sale_price': sale.sale_price,
                    'kaspi_amount': sale.kaspi_amount,
                    'cash_amount': sale.cash_amount,
                    'payment_method': sale.payment_method,
                    'payment_method_display': sale.get_payment_method_display(),
                    'split_details': method_display,
                    'formatted_sale_price': format_tenge(sale.sale_price),
                    'time_display': format_sale_time(sale.created_at, now),
                    'created_at_iso': sale.created_at.isoformat(),
                },
                'stats': all_stats,
            })
        else:
            errors = {field: [str(e) for e in err_list] for field, err_list in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_edit_sale(request, sale_id):
    """API для редактирования записи."""
    sale = get_object_or_404(Sale, id=sale_id)
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST

        form = SaleForm(data, instance=sale)
        if form.is_valid():
            sale = form.save()
            all_stats = get_all_periods_stats()
            now = get_almaty_now()

            if sale.payment_method == Sale.PAYMENT_SPLIT:
                method_display = f"Kaspi: {format_tenge(sale.kaspi_amount)} + Нал: {format_tenge(sale.cash_amount)}"
            else:
                method_display = sale.get_payment_method_display()

            return JsonResponse({
                'success': True,
                'sale': {
                    'id': sale.id,
                    'sale_price': sale.sale_price,
                    'kaspi_amount': sale.kaspi_amount,
                    'cash_amount': sale.cash_amount,
                    'payment_method': sale.payment_method,
                    'payment_method_display': sale.get_payment_method_display(),
                    'split_details': method_display,
                    'formatted_sale_price': format_tenge(sale.sale_price),
                    'time_display': format_sale_time(sale.created_at, now),
                },
                'stats': all_stats,
            })
        else:
            errors = {field: [str(e) for e in err_list] for field, err_list in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_delete_sale(request, sale_id):
    """API для удаления записи."""
    sale = get_object_or_404(Sale, id=sale_id)
    sale.delete()
    all_stats = get_all_periods_stats()

    return JsonResponse({
        'success': True,
        'deleted_id': sale_id,
        'stats': all_stats,
    })


def custom_login_view(request):
    """Страница входа."""
    if request.user.is_authenticated:
        return redirect('sales:index')

    error_message = None
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or 'sales:index'
            return redirect(next_url)
        else:
            error_message = 'Неверный логин или пароль. Проверьте данные и попробуйте снова.'
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {
        'form': form,
        'error_message': error_message,
    })


def custom_logout_view(request):
    """Выход из системы."""
    if request.method in ['POST', 'GET']:
        logout(request)
    return redirect('login')
