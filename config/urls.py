from django.contrib import admin
from django.urls import path, include
from sales.views import custom_login_view, custom_logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', custom_login_view, name='login'),
    path('logout/', custom_logout_view, name='logout'),
    path('', include('sales.urls', namespace='sales')),
]
