from datetime import date
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from app.cache import TTLCache
from app.main import app
from app.services.fx_service import FXService


class MockTransport:
    def __init__(self, response_data, status_code=200):
        self.response_data = response_data
        self.status_code = status_code

    async def handle_request(self, request):
        return httpx.Response(
            status_code=self.status_code,
            json=self.response_data,
            request=request,
        )


@pytest.fixture
def api_client():
    transport = MockTransport(
        {
            "amount": "250",
            "base": "EUR",
            "date": "2026-08-28",
            "rates": {
                "TRY": 48.20
            },
        }
    )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(transport.handle_request)
    )

    service = FXService(
        cache=TTLCache(ttl_seconds=300),
        client=client,
    )

    import app.main as main

    original_service = main.fx_service
    main.fx_service = service

    test_client = TestClient(app)

    yield test_client

    main.fx_service = original_service


def test_convert_endpoint_success(api_client):
    response = api_client.get(
        "/tools/convert",
        params={
            "amount": "250",
            "from": "EUR",
            "to": "TRY",
            "date": "2026-08-28",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["amount"] == "250"
    assert data["from"] == "EUR"
    assert data["to"] == "TRY"
    assert Decimal(data["rate"]) == Decimal("48.20")
    assert Decimal(data["result"]) == Decimal("12050.00")
    assert data["rate_date"] == "2026-08-28"
    assert data["asked_date"] == "2026-08-28"
    assert data["source"] == "frankfurter"


def test_convert_endpoint_missing_amount(api_client):
    response = api_client.get(
        "/tools/convert",
        params={
            "from": "EUR",
            "to": "TRY",
        },
    )

    assert response.status_code == 422


def test_convert_endpoint_zero_amount(api_client):
    response = api_client.get(
        "/tools/convert",
        params={
            "amount": "0",
            "from": "EUR",
            "to": "TRY",
        },
    )

    assert response.status_code == 400


def test_convert_endpoint_negative_amount(api_client):
    response = api_client.get(
        "/tools/convert",
        params={
            "amount": "-10",
            "from": "EUR",
            "to": "TRY",
        },
    )

    assert response.status_code == 400


def test_convert_endpoint_invalid_date(api_client):
    response = api_client.get(
        "/tools/convert",
        params={
            "amount": "100",
            "from": "EUR",
            "to": "TRY",
            "date": "not-a-date",
        },
    )

    assert response.status_code == 422