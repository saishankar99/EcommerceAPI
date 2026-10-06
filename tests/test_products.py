def test_get_products(client):
    response = client.get("/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_product_with_id(client,admin_headers):
    response = client.post("/products", json={"name": "Test Product", "price": 10.0, "stock": 2}, headers=admin_headers)
    product_id = response.json()["id"]
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Product"
    assert response.json()["id"] == product_id

def test_get_nonexistent_product(client):
    response = client.get("/products/9999")
    assert response.status_code == 404

def test_create_product(client, admin_headers):
    response = client.post("/products", json = {"name": "New Product", "price": 20.0, "stock": 5},headers = admin_headers)
    assert response.status_code == 201
    assert response.json()["name"] == "New Product"

def test_create_product_without_admin(client,auth_headers):
    response = client.post("/products", json = {"name": "Unauthorized Product", "price": 30.0, "stock": 5}, headers=auth_headers)
    assert response.status_code == 403

def test_update_product(client, admin_headers):
    response = client.post("/products", json = {"name": "Product to Update", "price": 5.0, "stock": 3}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.patch(f"/products/{product_id}", json = {"name": "Updated Product", "stock": 10}, headers = admin_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Product"
    assert response.json()["stock"] == 10

def test_delete_product(client, admin_headers):
    response = client.post("/products", json = {"name": "Product to Delete", "price": 15.0, "stock": 4}, headers = admin_headers)
    product_id = response.json()["id"]
    response = client.delete(f"/products/{product_id}", headers = admin_headers)
    assert response.status_code == 204
    
