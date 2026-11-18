
from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/', views.cart, name='cart'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
path('logout/', views.user_logout, name='logout'),
path('address/', views.delivery_address, name='address'),
path('checkout/', views.checkout, name='checkout'),

path('place-order/', views.place_order, name='place_order'),

path('order-success/<int:order_id>/',
     views.order_success, name='order_success'),

path('order-history/', views.order_history, name='order_history'),

path('order-detail/<int:order_id>/',
     views.order_detail, name='order_detail'),
]