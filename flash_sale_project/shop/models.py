from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta


class Product(models.Model):
    """商品表"""
    sku = models.CharField(max_length=50, unique=True, verbose_name='商品編號')
    name = models.CharField(max_length=200, verbose_name='商品名稱')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='售價')
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本')
    status = models.CharField(max_length=20, default='active', verbose_name='狀態')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        db_table = 'products'
        verbose_name = '商品'
        verbose_name_plural = '商品'

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Inventory(models.Model):
    """庫存表"""
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory',
        verbose_name='商品'
    )
    quantity_on_hand = models.IntegerField(default=0, verbose_name='實際庫存')
    quantity_reserved = models.IntegerField(default=0, verbose_name='預留庫存')
    quantity_available = models.IntegerField(default=0, verbose_name='可售庫存')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    version = models.IntegerField(default=0, verbose_name='版本號')

    class Meta:
        db_table = 'inventory'
        verbose_name = '庫存'
        verbose_name_plural = '庫存'

    def __str__(self):
        return f"{self.product.sku} - 可售: {self.quantity_available}"


class FlashSaleEvent(models.Model):
    """搶購活動表"""
    STATUS_CHOICES = [
        ('pending', '待開始'),
        ('active', '進行中'),
        ('ended', '已結束'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='flash_sales',
        verbose_name='商品'
    )
    total_quantity = models.IntegerField(verbose_name='總限量數')
    reserved_quantity = models.IntegerField(default=0, verbose_name='已預留數量')
    sold_quantity = models.IntegerField(default=0, verbose_name='已售出數量')
    start_time = models.DateTimeField(verbose_name='開始時間')
    end_time = models.DateTimeField(verbose_name='結束時間')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='活動狀態'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        db_table = 'flash_sale_events'
        verbose_name = '搶購活動'
        verbose_name_plural = '搶購活動'

    def __str__(self):
        return f"搶購: {self.product.name} ({self.get_status_display()})"

    def is_active(self):
        """檢查活動是否有效"""
        now = timezone.now()
        return self.status == 'active' and self.start_time <= now <= self.end_time

    def has_stock(self):
        """檢查是否還有庫存"""
        return (self.reserved_quantity + self.sold_quantity) < self.total_quantity


class SalesOrder(models.Model):
    """訂單主檔"""
    STATUS_CHOICES = [
        ('pending', '待付款'),
        ('paid', '已付款'),
        ('shipped', '已出貨'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('expired', '已逾期'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', '信用卡'),
        ('line_pay', 'Line Pay'),
    ]

    order_number = models.CharField(max_length=50, unique=True, verbose_name='訂單編號')
    user_email = models.EmailField(verbose_name='用戶Email')
    flash_sale_event = models.ForeignKey(
        FlashSaleEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='搶購活動'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        verbose_name='付款方式'
    )
    payment_deadline = models.DateTimeField(null=True, verbose_name='付款期限')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='付款時間')
    shipping_priority = models.IntegerField(null=True, blank=True, verbose_name='出貨順位')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='訂單狀態'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='總金額')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        db_table = 'sales_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user_email']),
            models.Index(fields=['paid_at']),
            models.Index(fields=['flash_sale_event', 'status', 'paid_at']),
        ]
        verbose_name = '訂單'
        verbose_name_plural = '訂單'

    def __str__(self):
        return f"{self.order_number} - {self.get_status_display()}"

    def is_expired(self):
        """檢查訂單是否已逾期"""
        if self.status == 'pending' and self.payment_deadline:
            return timezone.now() > self.payment_deadline
        return False


class SalesOrderItem(models.Model):
    """訂單明細"""
    sales_order = models.ForeignKey(
        SalesOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='訂單'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    quantity = models.IntegerField(verbose_name='數量')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='單價')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='小計')

    class Meta:
        db_table = 'sales_order_items'
        verbose_name = '訂單明細'
        verbose_name_plural = '訂單明細'

    def __str__(self):
        return f"{self.sales_order.order_number} - {self.product.sku} x {self.quantity}"

