from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from shop.models import Product, Inventory, FlashSaleEvent


class Command(BaseCommand):
    help = '建立測試資料'

    def handle(self, *args, **options):
        self.stdout.write('正在建立測試資料...\n')

        # 建立商品
        product, created = Product.objects.get_or_create(
            sku='LIMITED-SHIRT-001',
            defaults={
                'name': '聯名限量服飾',
                'price': 2990,
                'cost': 1000,
                'status': 'active'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ 建立商品: {product.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'○ 商品已存在: {product.name}'))

        # 建立庫存
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            defaults={
                'quantity_on_hand': 1000,
                'quantity_reserved': 0,
                'quantity_available': 1000
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ 建立庫存: {inventory.quantity_on_hand} 件'))
        else:
            self.stdout.write(self.style.WARNING(f'○ 庫存已存在: 可售 {inventory.quantity_available} 件'))

        # 建立搶購活動
        flash_sale, created = FlashSaleEvent.objects.get_or_create(
            product=product,
            defaults={
                'total_quantity': 1000,
                'reserved_quantity': 0,
                'sold_quantity': 0,
                'start_time': timezone.now(),
                'end_time': timezone.now() + timedelta(days=1),
                'status': 'active'
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ 建立搶購活動: ID={flash_sale.id}'))
            self.stdout.write(self.style.SUCCESS(f'  開始時間: {flash_sale.start_time}'))
            self.stdout.write(self.style.SUCCESS(f'  結束時間: {flash_sale.end_time}'))
        else:
            self.stdout.write(self.style.WARNING(f'○ 搶購活動已存在: ID={flash_sale.id}'))

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ 測試資料建立完成！'))
        self.stdout.write('='*60)
        self.stdout.write(f'\n搶購活動 ID: {flash_sale.id}')
        self.stdout.write(f'商品名稱: {product.name}')
        self.stdout.write(f'限量數量: {flash_sale.total_quantity} 件')
        self.stdout.write(f'商品價格: NT$ {product.price}')
        self.stdout.write(f'\n現在可以開始測試搶購功能了！')

