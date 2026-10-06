import models
def test_post_review_without_paid_order(client, admin_headers, auth_headers):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 1}]}, headers = auth_headers)
    order_id = response.json()["id"]
    response = client.post(f"/products/{product_id}/reviews", json = {"rating": 4, "comment": "Great product!"}, headers = auth_headers)
    assert response.status_code == 403

def test_post_review_with_paid_order(client, admin_headers, auth_headers,db_session):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 1}]}, headers = auth_headers)
    order_id = response.json()["id"]
    order = db_session.query(models.Order).filter(models.Order.id == order_id).first()
    order.status = models.OrderStatus.paid
    db_session.commit()
    response = client.post(f"/products/{product_id}/reviews", json = {"rating": 4, "comment": "Great Product!"}, headers = auth_headers)
    assert response.status_code == 201


