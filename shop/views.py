from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import Product, Inventory, FlashSaleEvent, SalesOrder, SalesOrderItem


@api_view(['POST'])
def create_flash_sale_order(request):
    """
    建立搶購訂單 API
    POST /api/flash-sale/order/
    Body: {
        "user_email": "user@example.com",
        "flash_sale_event_id": 1,
        "payment_method": "credit_card"  # or "line_pay"
    }
    """
    user_email = request.data.get('user_email')
    event_id = request.data.get('flash_sale_event_id')
    payment_method = request.data.get('payment_method')

    if not all([user_email, event_id, payment_method]):
        return Response(
            {'error': '缺少必要參數'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if payment_method not in ['credit_card', 'line_pay']:
        return Response(
            {'error': '付款方式不正確'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            # 鎖定活動記錄（防止併發）
            event: FlashSaleEvent
            event = FlashSaleEvent.objects.select_for_update().get(id=event_id)

            # 檢查活動是否有效
            if not event.is_active():
                return Response(
                    {'error': '活動尚未開始或已結束'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 檢查是否還有庫存（防止超賣）
            if not event.has_stock():
                return Response(
                    {'error': '商品已售罄'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 檢查用戶是否已經下過單
            existing_order = SalesOrder.objects.filter(
                user_email=user_email,
                flash_sale_event=event,
                status__in=['pending', 'paid']
            ).exists()

            if existing_order:
                return Response(
                    {'error': '您已經有一筆進行中的訂單'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 鎖定庫存
            inventory = Inventory.objects.select_for_update().get(product=event.product)

            if inventory.quantity_available < 1:
                return Response(
                    {'error': '庫存不足'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 更新庫存（預留）
            inventory.quantity_reserved += 1
            inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
            inventory.save()

            # 更新活動預留數量（使用資料庫原子更新，避免併發競爭）
            FlashSaleEvent.objects.filter(pk=event.pk).update(
                reserved_quantity=F('reserved_quantity') + 1
            )

            # 建立訂單
            order_number = f"FS{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
            payment_deadline = timezone.now() + timedelta(hours=1)

            order = SalesOrder.objects.create(
                order_number=order_number,
                user_email=user_email,
                flash_sale_event=event,
                payment_method=payment_method,
                payment_deadline=payment_deadline,
                status='pending',
                total_amount=event.product.price
            )

            # 建立訂單明細
            SalesOrderItem.objects.create(
                sales_order=order,
                product=event.product,
                quantity=1,
                unit_price=event.product.price,
                subtotal=event.product.price
            )

            return Response({
                'success': True,
                'order_number': order.order_number,
                'payment_deadline': payment_deadline,
                'payment_method': payment_method,
                'total_amount': str(order.total_amount),
                'message': '訂單建立成功，請在1小時內完成付款'
            }, status=status.HTTP_201_CREATED)

    except FlashSaleEvent.DoesNotExist:
        return Response(
            {'error': '活動不存在'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'系統錯誤: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def simulate_payment(request):
    """
    模擬付款操作
    POST /api/payment/simulate/
    Body: {
        "order_number": "FS202411210001ABCD"
    }
    """
    order_number = request.data.get('order_number')

    if not order_number:
        return Response(
            {'error': '缺少訂單編號'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order: SalesOrder
        order = SalesOrder.objects.get(order_number=order_number)

        if order.status != 'pending':
            return Response(
                {'error': f'訂單狀態不正確: {order.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.is_expired():
            return Response(
                {'error': '訂單已逾期'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 模擬付款成功，返回付款 URL（實際應該跳轉到金流頁面）
        payment_url = f"http://localhost:8000/api/payment/callback/?order={order_number}&status=success"

        return Response({
            'success': True,
            'message': '請前往付款頁面完成付款',
            'payment_url': payment_url,
            'order_number': order_number,
            'payment_method': order.get_payment_method_display()
        })

    except SalesOrder.DoesNotExist:
        return Response(
            {'error': '訂單不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET', 'POST'])
def payment_callback(request):
    """
    接收金流付款成功通知
    GET/POST /api/payment/callback/
    Params: order=FS202411210001ABCD&status=success
    """
    order_number = request.GET.get('order') or request.data.get('order_number')
    payment_status = request.GET.get('status') or request.data.get('status')

    if not order_number:
        return Response(
            {'error': '缺少訂單編號'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            order = SalesOrder.objects.select_for_update().get(order_number=order_number)

            if order.status != 'pending':
                return Response({
                    'success': False,
                    'message': f'訂單已處理過，目前狀態: {order.get_status_display()}'
                })

            if payment_status == 'success':
                # 付款成功
                paid_time = timezone.now()
                order.status = 'paid'
                order.paid_at = paid_time

                # 計算出貨順位（已付款訂單中的排序）
                shipping_priority = SalesOrder.objects.filter(
                    flash_sale_event=order.flash_sale_event,
                    status='paid',
                    paid_at__lt=paid_time
                ).count() + 1

                order.shipping_priority = shipping_priority
                order.save()

                # 更新庫存（從預留變成實際銷售）
                inventory = Inventory.objects.select_for_update().get(
                    product=order.flash_sale_event.product
                )
                inventory.quantity_reserved -= 1
                inventory.quantity_on_hand -= 1
                inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
                inventory.save()

                # 更新活動統計（原子更新，避免遺失更新）
                FlashSaleEvent.objects.filter(pk=order.flash_sale_event_id).update(
                    reserved_quantity=F('reserved_quantity') - 1,
                    sold_quantity=F('sold_quantity') + 1,
                )

                return Response({
                    'success': True,
                    'message': '付款成功！',
                    'order_number': order.order_number,
                    'shipping_priority': shipping_priority,
                    'paid_at': paid_time
                })
            else:
                # 付款失敗，釋放庫存
                order.status = 'cancelled'
                order.save()

                inventory = Inventory.objects.select_for_update().get(
                    product=order.flash_sale_event.product
                )
                inventory.quantity_reserved -= 1
                inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
                inventory.save()

                # 釋放活動預留數量（原子更新）
                FlashSaleEvent.objects.filter(pk=order.flash_sale_event_id).update(
                    reserved_quantity=F('reserved_quantity') - 1
                )

                return Response({
                    'success': False,
                    'message': '付款失敗，訂單已取消'
                })

    except SalesOrder.DoesNotExist:
        return Response(
            {'error': '訂單不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def check_order_status(request, order_number):
    """
    查詢訂單狀態與出貨順位
    GET /api/order/{order_number}/status/
    """
    try:
        order = SalesOrder.objects.select_related(
            'flash_sale_event',
            'flash_sale_event__product'
        ).get(order_number=order_number)

        response_data = {
            'order_number': order.order_number,
            'user_email': order.user_email,
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': order.created_at,
            'payment_deadline': order.payment_deadline,
            'paid_at': order.paid_at,
            'shipping_priority': order.shipping_priority,
            'total_amount': str(order.total_amount),
            'payment_method': order.get_payment_method_display() if order.payment_method else None,
        }

        # 如果訂單已付款，顯示出貨順位
        if order.status == 'paid' and order.shipping_priority:
            response_data['message'] = f'🎉 搶購成功！您的出貨順位是第 {order.shipping_priority} 位'
        elif order.status == 'pending':
            if order.is_expired():
                response_data['message'] = '⏰ 訂單已逾期'
            else:
                remaining_time = order.payment_deadline - timezone.now()
                minutes_left = int(remaining_time.total_seconds() / 60)
                response_data['message'] = f'⏳ 請在 {minutes_left} 分鐘內完成付款'
        elif order.status == 'expired':
            response_data['message'] = '⏰ 訂單已逾期'
        elif order.status == 'cancelled':
            response_data['message'] = '❌ 訂單已取消'

        return Response(response_data)

    except SalesOrder.DoesNotExist:
        return Response(
            {'error': '訂單不存在'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def user_orders(request):
    """
    查詢用戶的所有訂單
    GET /api/user/orders/?email=user@example.com
    """
    user_email = request.GET.get('email')

    if not user_email:
        return Response(
            {'error': '缺少 email 參數'},
            status=status.HTTP_400_BAD_REQUEST
        )

    orders = SalesOrder.objects.filter(user_email=user_email).order_by('-created_at')

    orders_data = [{
        'order_number': order.order_number,
        'status': order.status,
        'status_display': order.get_status_display(),
        'created_at': order.created_at,
        'paid_at': order.paid_at,
        'shipping_priority': order.shipping_priority,
        'total_amount': str(order.total_amount),
        'payment_method': order.get_payment_method_display() if order.payment_method else None,
    } for order in orders]

    return Response({
        'user_email': user_email,
        'total_orders': len(orders_data),
        'orders': orders_data
    })


@api_view(['GET'])
def flash_sale_status(request, event_id):
    """
    查詢搶購活動狀態
    GET /api/flash-sale/{event_id}/status/
    """
    try:
        event = FlashSaleEvent.objects.select_related('product').get(id=event_id)

        return Response({
            'event_id': event.id,
            'product_name': event.product.name,
            'product_sku': event.product.sku,
            'total_quantity': event.total_quantity,
            'reserved_quantity': event.reserved_quantity,
            'sold_quantity': event.sold_quantity,
            'remaining': event.total_quantity - event.reserved_quantity - event.sold_quantity,
            'status': event.status,
            'status_display': event.get_status_display(),
            'start_time': event.start_time,
            'end_time': event.end_time,
            'is_active': event.is_active(),
            'has_stock': event.has_stock(),
        })

    except FlashSaleEvent.DoesNotExist:
        return Response(
            {'error': '活動不存在'},
            status=status.HTTP_404_NOT_FOUND
        )

