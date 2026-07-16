from app import app


def test_healthz():
    client = app.test_client()
    response = client.get("/healthz")
    assert response.status_code == 200


def test_checkout_returns_order_id():
    client = app.test_client()
    response = client.post("/checkout")
    assert response.status_code in (200, 500)
    assert "order_id" in response.get_json()


def test_metrics_exposed():
    client = app.test_client()
    response = client.get("/metrics")
    assert response.status_code == 200
