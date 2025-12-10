from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.shop, name='shop'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
]
