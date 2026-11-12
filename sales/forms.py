from django import forms
from .models import Sale


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['sale_price', 'payment_method', 'kaspi_amount', 'cash_amount']
        widgets = {
            'sale_price': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0',
                'min': '1',
                'step': '1',
                'inputmode': 'numeric',
                'pattern': '[0-9]*',
                'required': 'required',
                'id': 'id_sale_price',
                'autofocus': 'autofocus',
            }),
            'kaspi_amount': forms.NumberInput(attrs={
                'class': 'form-input form-input-split',
                'placeholder': '0',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'pattern': '[0-9]*',
                'id': 'id_kaspi_amount',
            }),
            'cash_amount': forms.NumberInput(attrs={
                'class': 'form-input form-input-split',
                'placeholder': '0',
                'min': '0',
                'step': '1',
                'inputmode': 'numeric',
                'pattern': '[0-9]*',
                'id': 'id_cash_amount',
            }),
            'payment_method': forms.RadioSelect(attrs={
                'class': 'payment-radio',
            }),
        }

    def clean_sale_price(self):
        sale_price = self.cleaned_data.get('sale_price')
        if sale_price is None or sale_price <= 0:
            raise forms.ValidationError('Цена продажи должна быть больше 0.')
        return sale_price

    def clean(self):
        cleaned_data = super().clean()
        sale_price = cleaned_data.get('sale_price') or 0
        payment_method = cleaned_data.get('payment_method')
        kaspi_amount = cleaned_data.get('kaspi_amount') or 0
        cash_amount = cleaned_data.get('cash_amount') or 0

        if payment_method == Sale.PAYMENT_SPLIT:
            if kaspi_amount + cash_amount != sale_price:
                if kaspi_amount == 0 and cash_amount == 0:
                    cleaned_data['kaspi_amount'] = sale_price // 2
                    cleaned_data['cash_amount'] = sale_price - cleaned_data['kaspi_amount']
                elif kaspi_amount > 0 and cash_amount == 0:
                    cleaned_data['cash_amount'] = max(0, sale_price - kaspi_amount)
                elif cash_amount > 0 and kaspi_amount == 0:
                    cleaned_data['kaspi_amount'] = max(0, sale_price - cash_amount)
        elif payment_method == Sale.PAYMENT_KASPI:
            cleaned_data['kaspi_amount'] = sale_price
            cleaned_data['cash_amount'] = 0
        elif payment_method == Sale.PAYMENT_CASH:
            cleaned_data['cash_amount'] = sale_price
            cleaned_data['kaspi_amount'] = 0

        return cleaned_data
