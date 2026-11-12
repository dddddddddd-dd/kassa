from django.db import models
from django.core.validators import MinValueValidator


class Sale(models.Model):
    PAYMENT_KASPI = 'kaspi'
    PAYMENT_CASH = 'cash'
    PAYMENT_SPLIT = 'split'
    PAYMENT_CHOICES = [
        (PAYMENT_KASPI, 'Kaspi'),
        (PAYMENT_CASH, 'Наличные'),
        (PAYMENT_SPLIT, 'Kaspi + Нал'),
    ]

    sale_price = models.PositiveIntegerField(
        verbose_name='Цена продажи (₸)',
        validators=[MinValueValidator(1, message='Цена продажи должна быть больше 0.')]
    )
    cost_price = models.PositiveIntegerField(
        verbose_name='Закупочная цена (₸)',
        default=0,
        blank=True
    )
    kaspi_amount = models.PositiveIntegerField(
        verbose_name='Сумма Kaspi (₸)',
        default=0
    )
    cash_amount = models.PositiveIntegerField(
        verbose_name='Сумма Наличные (₸)',
        default=0
    )
    payment_method = models.CharField(
        verbose_name='Способ оплаты',
        max_length=10,
        choices=PAYMENT_CHOICES,
        default=PAYMENT_KASPI
    )
    created_at = models.DateTimeField(
        verbose_name='Дата и время продажи',
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'Продажа'
        verbose_name_plural = 'Продажи'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Автоматическое распределение сумм при сохранении
        if self.payment_method == self.PAYMENT_KASPI:
            self.kaspi_amount = self.sale_price
            self.cash_amount = 0
        elif self.payment_method == self.PAYMENT_CASH:
            self.cash_amount = self.sale_price
            self.kaspi_amount = 0
        else:
            # Смешанная оплата (split)
            if self.kaspi_amount + self.cash_amount != self.sale_price:
                if self.kaspi_amount > self.sale_price:
                    self.kaspi_amount = self.sale_price
                    self.cash_amount = 0
                else:
                    self.cash_amount = self.sale_price - self.kaspi_amount
        super().save(*args, **kwargs)

    @property
    def profit(self):
        return self.sale_price - self.cost_price

    def __str__(self):
        return f"{self.sale_price} ₸ ({self.get_payment_method_display()}) — {self.created_at.strftime('%d.%m.%Y %H:%M')}"
