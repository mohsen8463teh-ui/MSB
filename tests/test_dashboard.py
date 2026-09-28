from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_dashboard_serves_local_mobile_ui():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "M.S.B" in response.text
    assert 'id="analysis-form"' in response.text
    assert 'dir="rtl"' in response.text
