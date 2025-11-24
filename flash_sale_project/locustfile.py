from locust import HttpUser, task, between
import random

class FlashSaleUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def create_order(self):
        user_id = random.randint(1, 100000)
        self.client.post("/api/flash-sale/order/", json={
            "user_email": f"user{user_id}@test.com",
            "flash_sale_event_id": 1,
            "payment_method": "credit_card"
        })
