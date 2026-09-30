from collections import Counter
import re

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def dashboard_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    return response.text


def test_dashboard_serves_local_mobile_ui():
    html = dashboard_html()
    assert "M.S.B" in html
    assert 'id="analysis-form"' in html
    assert 'dir="rtl"' in html


def test_dashboard_ids_are_unique():
    html = dashboard_html()
    ids = re.findall(r'\bid="([^"]+)"', html)
    duplicates = sorted(value for value, count in Counter(ids).items() if count > 1)
    assert duplicates == []


def test_research_form_has_one_submit_handler_and_uses_requested_simulations():
    html = dashboard_html()
    assert html.count('$("research-form").addEventListener("submit"') == 1
    assert 'simulations: Number($("simulations").value)' in html
    assert 'split(/[,،]/)' in html
    assert "JSON.stringify(body, null, 2)" not in html
