from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
	path('', views.index, name='index'),
	path('shop/', views.shop, name='shop'),
	path('product/<int:id>/', views.product_detail, name='product_detail'),
	path('cart/', views.cart_view, name='cart'),
	path('checkout/', views.checkout, name='checkout'),
	path('contact/', views.contact, name='contact'),
	path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
	path('change_cart_view/', views.change_cart_view, name='change_cart_view'),
	path('remove_from_cart/', views.remove_from_cart, name='remove_from_cart'),
]
