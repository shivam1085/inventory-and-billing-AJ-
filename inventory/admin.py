from django.contrib import admin
from .models import Product, Customer, Sale, SaleItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'selling_price', 'quantity', 'created_at')
    search_fields = ('sku', 'name')
    list_filter = ('created_at',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'phone', 'email')

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'date', 'total_amount')
    inlines = [SaleItemInline]
    search_fields = ('invoice_number', 'customer__name')
    list_filter = ('date',)
