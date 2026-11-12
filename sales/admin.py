from django.contrib import admin
from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale_price', 'cost_price', 'profit_display', 'payment_method', 'created_at')
    list_filter = ('payment_method', 'created_at')
    date_hierarchy = 'created_at'
    search_fields = ('sale_price', 'cost_price')

    @admin.display(description='Прибыль')
    def profit_display(self, obj):
        return f"{obj.profit} ₸"
