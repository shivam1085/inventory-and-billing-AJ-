from django.urls import path
from . import views, api

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('sales/create/', views.create_sale, name='create_sale'),
    path('sales/<int:pk>/receipt/', views.sale_receipt, name='sale_receipt'),
    
    # API endpoints
    path('api/products/<int:product_id>/', api.get_product_price, name='api_product_price'),
]