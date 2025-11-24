## 🚀 環境需求

- Python 3.8+
- Django 4.2+
- Django REST Framework 3.14+
- PostgreSQL

## 📦 安裝與啟動

### 1. 安裝相依套件
在專案根目錄執行：
```bash
python3 -m pip install -r requirements.txt
```

### 2. 建立資料庫
在專案根目錄執行：
```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

### 3. 建立測試資料
在專案根目錄執行：
```bash
python3 manage.py create_test_data
```

這會自動建立：
- 1 個商品（聯名限量服飾）
- 1000 件庫存
- 1 個搶購活動（立即開始，持續 24 小時）

### 4. 啟動伺服器
在專案根目錄執行：
```bash
python3 manage.py runserver
```

伺服器啟動後，可在 http://localhost:8000 使用 API。

### 5. (可選) 建立管理員帳號

```bash
python3 manage.py createsuperuser
```

然後可以在 http://localhost:8000/admin 管理後台查看資料。

## 📡 API 使用說明

### 1️⃣ 建立搶購訂單

**端點**：`POST /api/flash-sale/order/`

**請求範例**：
```bash
curl -X POST http://localhost:8000/api/flash-sale/order/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "user1@example.com",
    "flash_sale_event_id": 1,
    "payment_method": "credit_card"
  }'
```

**回應範例**：
```json
{
    "success": true,
    "order_number": "FS20241121A1B2C3D4",
    "payment_deadline": "2024-11-21T21:00:00Z",
    "payment_method": "credit_card",
    "total_amount": "2990.00",
    "message": "訂單建立成功，請在1小時內完成付款"
}
```

### 2️⃣ 模擬付款

**端點**：`POST /api/payment/simulate/`

**請求範例**：
```bash
curl -X POST http://localhost:8000/api/payment/simulate/ \
  -H "Content-Type: application/json" \
  -d '{
    "order_number": "FS20241121A1B2C3D4"
  }'
```

**回應範例**：
```json
{
    "success": true,
    "message": "請前往付款頁面完成付款",
    "payment_url": "http://localhost:8000/api/payment/callback/?order=FS20241121A1B2C3D4&status=success",
    "order_number": "FS20241121A1B2C3D4",
    "payment_method": "信用卡"
}
```

### 3️⃣ 金流回調（付款成功通知）

**端點**：`GET /api/payment/callback/`

**請求範例**：
```bash
curl "http://localhost:8000/api/payment/callback/?order=FS20241121A1B2C3D4&status=success"
```

**回應範例**：
```json
{
    "success": true,
    "message": "付款成功！",
    "order_number": "FS20241121A1B2C3D4",
    "shipping_priority": 15,
    "paid_at": "2024-11-21T20:05:30Z"
}
```

### 4️⃣ 查詢訂單狀態

**端點**：`GET /api/order/{order_number}/status/`

**請求範例**：
```bash
curl http://localhost:8000/api/order/FS20241121A1B2C3D4/status/
```

**回應範例**：
```json
{
    "order_number": "FS20241121A1B2C3D4",
    "user_email": "user1@example.com",
    "status": "paid",
    "status_display": "已付款",
    "created_at": "2024-11-21T20:00:01Z",
    "payment_deadline": "2024-11-21T21:00:01Z",
    "paid_at": "2024-11-21T20:05:30Z",
    "shipping_priority": 15,
    "total_amount": "2990.00",
    "payment_method": "信用卡",
    "message": "🎉 搶購成功！您的出貨順位是第 15 位"
}
```

### 5️⃣ 查詢用戶所有訂單

**端點**：`GET /api/user/orders/?email={email}`

**請求範例**：
```bash
curl "http://localhost:8000/api/user/orders/?email=user1@example.com"
```

### 6️⃣ 查詢搶購活動狀態

**端點**：`GET /api/flash-sale/{event_id}/status/`

**請求範例**：
```bash
curl http://localhost:8000/api/flash-sale/1/status/
```

**回應範例**：
```json
{
    "event_id": 1,
    "product_name": "聯名限量服飾",
    "product_sku": "LIMITED-SHIRT-001",
    "total_quantity": 1000,
    "reserved_quantity": 50,
    "sold_quantity": 200,
    "remaining": 750,
    "status": "active",
    "status_display": "進行中",
    "start_time": "2024-11-21T20:00:00Z",
    "end_time": "2024-11-22T20:00:00Z",
    "is_active": true,
    "has_stock": true
}
```

## 🔐 核心機制說明

### 1. 如何確保不會超賣？

**三層防護機制**：

```python
with transaction.atomic():
    # Layer 1: 資料庫行級鎖（最關鍵）
    event = FlashSaleEvent.objects.select_for_update().get(id=event_id)
    inventory = Inventory.objects.select_for_update().get(product=event.product)

    # Layer 2: 業務邏輯檢查
    if not event.has_stock():
        return Response({'error': '商品已售罄'})

    if inventory.quantity_available < 1:
        return Response({'error': '庫存不足'})

    # Layer 3: 原子性更新
    inventory.quantity_reserved += 1
    inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
    inventory.save()
```

**核心原理**：
- ✅ `select_for_update()`: 在交易期間鎖定資料列，其他請求必須等待
- ✅ `transaction.atomic()`: 確保所有操作要嘛全部成功，要嘛全部失敗
- ✅ 先檢查再扣減，扣減後立即更新 `quantity_available`

**為什麼這樣設計？**
- 即使 20,000 人同時搶購，資料庫鎖確保同一時間只有一個請求能修改庫存
- 預留機制 (`quantity_reserved`) 確保下單時立即佔位，不會被其他人搶走
- 原子性交易確保不會出現「檢查通過但扣減失敗」的不一致狀態

### 2. 如何處理一小時未付款釋放名額？

**定時任務機制**：

```bash
# 手動執行（測試用）
python3 manage.py release_expired_orders

# 編輯 crontab: crontab -e
# 加入以下內容（依你的環境調整 python 路徑）：
*/1 * * * * cd /Users/thamiko/flash_sale_project && /usr/local/bin/python3 manage.py release_expired_orders
```

**執行邏輯**：
1. 找出所有 `status=pending` 且 `payment_deadline < now` 的訂單
2. 將訂單狀態改為 `expired`
3. 釋放庫存：`quantity_reserved -= 1`、`quantity_available += 1`
4. 更新活動統計：`reserved_quantity -= 1`

**為什麼這樣設計？**
- 定時任務可靠且簡單，不需要複雜的消息隊列
- 每分鐘執行一次，最多 59 秒的延遲是可接受的
- 交易保證資料一致性

### 3. 如何決定出貨順位？

**付款時自動計算**：

```python
# 付款成功時，計算比這筆訂單更早付款的數量
shipping_priority = SalesOrder.objects.filter(
    flash_sale_event=order.flash_sale_event,
    status='paid',
    paid_at__lt=paid_time  # 比當前付款時間早
).count() + 1

order.shipping_priority = shipping_priority
order.save()
```

**特點**：
- ✅ 使用 `paid_at` 時間戳（精確到毫秒）
- ✅ 付款時立即計算並儲存
- ✅ 查詢時直接讀取，無需重新計算
- ✅ 公平公正，誰先付款誰先出貨

## ⚡ 真實大流量環境優化建議

### 目前實作的限制

| 問題        | 影響                                               | 嚴重程度  |
|------------|----------------------------------------------------|----------|
| 資料庫鎖競爭 | 20,000 人搶購時大量請求排隊（同一活動的行級鎖會排隊）      | ⚠️ 中    |
| 單機瓶頸    | 單一 Django + PostgreSQL 節點，可用連線數與 CPU 有上限  | ⚠️ 中〜高 |
| 定時任務延遲 | 每分鐘批次釋放逾期訂單，最差約 59 秒延遲                 | ⚠️ 低    |

### 如果從 2萬人 → 20萬人，優化策略：

#### 🔥 **優先級 1: 引入 Redis**

**目標**：減少資料庫壓力，提升響應速度

```python
# 活動開始前，將庫存載入 Redis
redis_client.set('flash_sale:1:stock', 1000)

# 搶購時先扣 Redis（原子操作）
remaining = redis_client.decr('flash_sale:1:stock')
if remaining < 0:
    redis_client.incr('flash_sale:1:stock')  # 還原
    return Response({'error': '已售罄'})

# 扣減成功後，非同步寫入 DB
task_create_order.delay(user_email, event_id)
```

**效果**：
- ✅ Redis 單機可處理 10萬+ TPS
- ✅ 避免資料庫鎖競爭
- ✅ 響應速度

#### 🔥 **優先級 2: 水平擴展 + Load Balancer**

```
                    ┌─── Django Instance 1
Client → Nginx ────┼─── Django Instance 2
                    ├─── Django Instance 3
                    └─── Django Instance N
                              ↓
                      PostgreSQL + Redis
```

**實施步驟**：
1. 使用 Gunicorn + Gevent 提升單機併發能力
2. 部署多台 Django 實例
3. 使用 Nginx 做load balancer

#### 🔥 **優先級 3: 使用 Celery 非同步處理**

```python
# 立即回應用戶「排隊中」
@api_view(['POST'])
def create_order(request):
    task = create_order_task.delay(user_email, event_id)
    return Response({'task_id': task.id, 'message': '排隊中，請稍候查詢結果'})

# 背景慢慢處理
@celery_app.task
def create_order_task(user_email, event_id):
    # 真正的訂單建立邏輯
    ...
```

#### **優先級 4: PostgreSQL 優化**

```sql
-- 建立複合索引
CREATE INDEX idx_order_event_status_paid
ON sales_orders(flash_sale_event_id, status, paid_at);
```

#### **優先級 5: CDN**

- 活動頁面放 CDN
- 庫存數量用 WebSocket 推送更新 (Without WebSocket, a frontend might call:
    /api/flash-sale/1/status/ every second to update remaining stock.
    /api/order/{order_number}/status/ every second to see if payment is done.)
- 減少後端壓力

### 完整架構圖（20萬人規模）

```
                Client (200K users)
                        ↓
                CloudFlare CDN
                        ↓
                  Nginx (Load Balancer)
                        ↓
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
      Django          Django          Django
        ↓               ↓               ↓
        └───────────────┼───────────────┘
                        ↓
            ┌───────────┴───────────┐
            ↓                       ↓
    Redis Cluster           PostgreSQL
            ↓
    Celery Workers
```