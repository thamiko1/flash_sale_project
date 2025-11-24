from django.urls import path
from . import views

urlpatterns = [
    path('flash-sale/order/', views.create_flash_sale_order, name='create_flash_sale_order'),

    path('payment/simulate/', views.simulate_payment, name='simulate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),

    path('order/<str:order_number>/status/', views.check_order_status, name='check_order_status'),
    path('user/orders/', views.user_orders, name='user_orders'),

    path('flash-sale/<int:event_id>/status/', views.flash_sale_status, name='flash_sale_status'),
]

