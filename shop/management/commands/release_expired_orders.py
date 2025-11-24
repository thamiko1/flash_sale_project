from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from shop.models import SalesOrder, Inventory, FlashSaleEvent


class Command(BaseCommand):
    help = '釋放逾時未付款的訂單庫存'

    def handle(self, *args, **options):
        now = timezone.now()

        expired_orders = SalesOrder.objects.filter(
            status='pending',
            payment_deadline__lt=now
        ).select_related('flash_sale_event')

        count = 0
        for order in expired_orders:
            try:
                with transaction.atomic():
                    order.status = 'expired'
                    order.save()

                    if order.flash_sale_event:
                        inventory = Inventory.objects.select_for_update().get(
                            product=order.flash_sale_event.product
                        )
                        inventory.quantity_reserved -= 1
                        inventory.quantity_available = (
                            inventory.quantity_on_hand - inventory.quantity_reserved
                        )
                        inventory.save()

                        FlashSaleEvent.objects.filter(pk=order.flash_sale_event_id).update(
                            reserved_quantity=F('reserved_quantity') - 1
                        )

                    count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ 釋放訂單: {order.order_number}')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ 處理訂單 {order.order_number} 失敗: {str(e)}')
                )

        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n總共成功釋放 {count} 筆逾時訂單的庫存')
            )
        else:
            self.stdout.write(
                self.style.WARNING('沒有逾時未付款的訂單')
            )

