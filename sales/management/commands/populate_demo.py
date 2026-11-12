from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from sales.models import Sale
from sales.utils import TIMEZONE_ALMATY


class Command(BaseCommand):
    help = 'Создаёт тестовые продажи и пользователя-фармацевта (demo / demo123)'

    def handle(self, *args, **options):
        # Создаём демо-пользователя, если его нет
        user, created = User.objects.get_or_create(username='demo')
        if created:
            user.set_password('demo123')
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS('Пользователь demo создан (пароль: demo123).'))
        else:
            self.stdout.write('Пользователь demo уже существует.')

        # Добавим несколько демонстрационных продаж за сегодня и вчера
        if Sale.objects.count() == 0:
            now = timezone.now().astimezone(TIMEZONE_ALMATY)

            sales_data = [
                (4500, 3100, Sale.PAYMENT_KASPI, now - timedelta(minutes=15)),
                (1200, 750, Sale.PAYMENT_CASH, now - timedelta(minutes=45)),
                (8900, 6200, Sale.PAYMENT_KASPI, now - timedelta(hours=2)),
                (350, 180, Sale.PAYMENT_CASH, now - timedelta(hours=3, minutes=20)),
                (12500, 9400, Sale.PAYMENT_KASPI, now - timedelta(hours=4)),
                (2100, 1400, Sale.PAYMENT_KASPI, now - timedelta(days=1, hours=2)),
                (6400, 4800, Sale.PAYMENT_CASH, now - timedelta(days=2)),
            ]

            for sale_price, cost_price, pay_method, dt in sales_data:
                sale = Sale.objects.create(
                    sale_price=sale_price,
                    cost_price=cost_price,
                    payment_method=pay_method
                )
                # Устанавливаем конкретное время для реалистичности демо
                Sale.objects.filter(id=sale.id).update(created_at=dt)

            self.stdout.write(self.style.SUCCESS(f'Успешно создано {len(sales_data)} тестовых продаж.'))
        else:
            self.stdout.write('В базе уже есть записи продаж.')

