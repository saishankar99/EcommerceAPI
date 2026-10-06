import models 

def test_create_order(client, auth_headers,admin_headers):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 3},headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 2}]}, headers = auth_headers)
    assert response.status_code == 201
    assert response.json()["items"][0]["product_id"]==product_id
    assert response.json()["items"][0]["quantity"] == 2

def test_create_order_with_insufficient_stock(client, auth_headers, admin_headers):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 1}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 2}]}, headers = auth_headers)
    assert response.status_code == 409

def test_create_order_with_unknown_product(client, auth_headers):
    response = client.post('/orders', json = {"items": [{"product_id": 99999, "quantity": 1}]}, headers = auth_headers)
    assert response.status_code == 404

def test_list_orders(client, auth_headers):
    response = client.get("/orders", headers = auth_headers)
    assert response.status_code == 200

def test_get_order_by_id(client, auth_headers, admin_headers):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 2}]}, headers = auth_headers)
    order_id = response.json()["id"]
    response = client.get(f"/orders/{order_id}", headers = auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == order_id

def test_non_existent_order(client, auth_headers):
    response = client.get("/orders/99999", headers = auth_headers)
    assert response.status_code == 404

def test_get_others_order(client, auth_headers, admin_headers):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 1}]}, headers = admin_headers)
    order_id = response.json()["id"]
    response = client.get(f"/orders/{order_id}", headers = auth_headers)
    assert response.status_code == 403

def test_pay_order(client, auth_headers, admin_headers, monkeypatch):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 2}]}, headers = auth_headers)
    order_id = response.json()["id"]
    captured = {}
    class FakeIntentResponse():
        id = "fake_id"
        client_secret = "fake_client_secret"

    def fake_create(*args, **kwargs):
        captured.update(kwargs)
        return FakeIntentResponse()

    monkeypatch.setattr("stripe.PaymentIntent.create", fake_create)
    response = client.post(f"/orders/{order_id}/pay", headers = auth_headers)
    assert response.status_code == 200
    assert response.json()["client_secret"] == "fake_client_secret"

def test_pay_non_pending_order(client, auth_headers, admin_headers, db_session):
    response = client.post('/products', json = {"name": "Test Product", "price": 10.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post('/orders', json = {"items": [{"product_id": product_id, "quantity": 2}]}, headers = auth_headers)
    order_id = response.json()["id"]
    order = db_session.query(models.Order).filter(models.Order.id == order_id).first()
    order.status = models.OrderStatus.paid
    db_session.commit()
    response = client.post(f"/orders/{order_id}/pay", headers = auth_headers)
    assert response.status_code == 409

def test_pay_someone_else_order(client,auth_headers,admin_headers):
    response = client.post("/products", json = {"name": "Test Product", "price": 10.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.post("/orders", json = {"items": [{"product_id": product_id, "quantity": 1}]}, headers = admin_headers)
    order_id = response.json()["id"]
    response = client.post(f"/orders/{order_id}/pay", headers = auth_headers)
    assert response.status_code == 403



