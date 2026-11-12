from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.index, name='index'),
    path('report/', views.report_view, name='report'),
    path('api/sales/add/', views.api_add_sale, name='api_add_sale'),
    path('api/sales/<int:sale_id>/edit/', views.api_edit_sale, name='api_edit_sale'),
    path('api/sales/<int:sale_id>/delete/', views.api_delete_sale, name='api_delete_sale'),
]
