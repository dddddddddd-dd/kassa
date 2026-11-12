import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from sales.models import Sale
from sales.utils import format_tenge


class PharmacySalesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'pharmacist'
        self.password = 'pharmacy123'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_model_split_payment_auto_distribution(self):
        """Проверка модели: Kaspi, Наличные и раздельная оплата (Kaspi + Нал)."""
        # 100% Kaspi
        sale_kaspi = Sale.objects.create(sale_price=3000, payment_method=Sale.PAYMENT_KASPI)
        self.assertEqual(sale_kaspi.kaspi_amount, 3000)
        self.assertEqual(sale_kaspi.cash_amount, 0)

        # 100% Cash
        sale_cash = Sale.objects.create(sale_price=2000, payment_method=Sale.PAYMENT_CASH)
        self.assertEqual(sale_cash.kaspi_amount, 0)
        self.assertEqual(sale_cash.cash_amount, 2000)

        # Split 50/50
        sale_split = Sale.objects.create(
            sale_price=5000,
            payment_method=Sale.PAYMENT_SPLIT,
            kaspi_amount=3000,
            cash_amount=2000
        )
        self.assertEqual(sale_split.kaspi_amount, 3000)
        self.assertEqual(sale_split.cash_amount, 2000)

    def test_tenge_formatting(self):
        """Проверка форматирования чисел (184 000 ₸)."""
        self.assertEqual(format_tenge(184000), '184 000 ₸')
        self.assertEqual(format_tenge(500), '500 ₸')

    def test_unauthenticated_access_redirects_to_login(self):
        """Неавторизованный пользователь перенаправляется на /login/."""
        response = self.client.get(reverse('sales:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_authenticated_access_index(self):
        """Авторизованный пользователь видит только Цену продажи и переключатель оплаты."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('sales:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Цена продажи')
        self.assertNotContains(response, 'Закупочная цена')
        self.assertContains(response, 'Kaspi + Нал')
        self.assertContains(response, 'Отчёт')

    def test_report_page_accessible(self):
        """Страница отчётов открывается и отображает суммы."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('sales:report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Отчёт продаж')
        self.assertContains(response, 'Kaspi')
        self.assertContains(response, 'Наличные')

    def test_api_add_sale_split(self):
        """Добавление раздельной продажи через API."""
        self.client.login(username=self.username, password=self.password)
        payload = {
            'sale_price': 6000,
            'payment_method': 'split',
            'kaspi_amount': 4000,
            'cash_amount': 2000
        }
        response = self.client.post(
            reverse('sales:api_add_sale'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['sale']['sale_price'], 6000)
        self.assertEqual(data['sale']['kaspi_amount'], 4000)
        self.assertEqual(data['sale']['cash_amount'], 2000)
        self.assertEqual(data['sale']['payment_method'], 'split')

    def test_api_edit_sale(self):
        """Редактирование записи."""
        self.client.login(username=self.username, password=self.password)
        sale = Sale.objects.create(sale_price=2000, payment_method='cash')

        response = self.client.post(
            reverse('sales:api_edit_sale', kwargs={'sale_id': sale.id}),
            data=json.dumps({'sale_price': 2500, 'payment_method': 'kaspi', 'kaspi_amount': 2500, 'cash_amount': 0}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        sale.refresh_from_db()
        self.assertEqual(sale.sale_price, 2500)
        self.assertEqual(sale.kaspi_amount, 2500)

    def test_api_delete_sale(self):
        """Удаление записи."""
        self.client.login(username=self.username, password=self.password)
        sale = Sale.objects.create(sale_price=1500, payment_method='kaspi')

        response = self.client.post(
            reverse('sales:api_delete_sale', kwargs={'sale_id': sale.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Sale.objects.filter(id=sale.id).exists())
