from django.contrib import admin
from .models import Product, Inventory, FlashSaleEvent, SalesOrder, SalesOrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'price', 'cost', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sku', 'name']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity_on_hand', 'quantity_reserved', 'quantity_available', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['product__sku', 'product__name']


@admin.register(FlashSaleEvent)
class FlashSaleEventAdmin(admin.ModelAdmin):
    list_display = ['product', 'total_quantity', 'reserved_quantity', 'sold_quantity', 'status', 'start_time', 'end_time']
    list_filter = ['status', 'start_time']
    search_fields = ['product__name', 'product__sku']


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user_email', 'status', 'payment_method', 'shipping_priority', 'total_amount', 'created_at', 'paid_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user_email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']


@admin.register(SalesOrderItem)
class SalesOrderItemAdmin(admin.ModelAdmin):
    list_display = ['sales_order', 'product', 'quantity', 'unit_price', 'subtotal']
    search_fields = ['sales_order__order_number', 'product__sku']

